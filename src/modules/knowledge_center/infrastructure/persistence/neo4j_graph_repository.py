"""
Neo4j GraphRepository 实现。

实现 IGraphRepository 接口，提供基于 Neo4j 的图谱持久化与查询能力。
"""

import time
from typing import Any

from loguru import logger
from neo4j import Driver

from src.modules.knowledge_center.domain.dtos.concept_relation_query_dtos import (
    ConceptChainNodeDTO,
    ConceptRelationQueryDTO,
)
from src.modules.knowledge_center.domain.dtos.concept_relation_sync_dtos import (
    ConceptRelationSyncDTO,
)
from src.modules.knowledge_center.domain.dtos.concept_sync_dtos import (
    ConceptGraphSyncDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_query_dtos import (
    GraphNodeDTO,
    GraphRelationshipDTO,
    StockGraphDTO,
    StockNeighborDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import (
    DimensionDTO,
    StockGraphSyncDTO,
    SyncResult,
)
from src.modules.knowledge_center.domain.exceptions import (
    GraphQueryError,
    GraphSyncError,
    Neo4jConnectionError,
)
from src.modules.knowledge_center.domain.ports.graph_repository import IGraphRepository


class Neo4jGraphRepository(IGraphRepository):
    """
    Neo4j 图谱仓储实现。
    
    使用 Neo4j Python Driver 实现图谱节点与关系的批量写入、查询能力。
    """

    def __init__(self, driver: Driver):
        """
        初始化 Neo4j 图谱仓储。
        
        Args:
            driver: Neo4j Driver 实例
        """
        self._driver = driver

    @staticmethod
    def _normalize_dimension_name(value: object) -> str | None:
        """规范化维度名称，过滤空白字符串。"""
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return str(value)

    async def ensure_constraints(self) -> None:
        """
        确保图谱唯一约束存在（幂等）。
        
        创建以下唯一约束：
        - Stock.third_code
        - Industry.name
        - Area.name
        - Market.name
        - Exchange.name
        """
        constraints = [
            "CREATE CONSTRAINT stock_third_code_unique IF NOT EXISTS FOR (s:STOCK) REQUIRE s.third_code IS UNIQUE",
            "CREATE CONSTRAINT industry_name_unique IF NOT EXISTS FOR (i:INDUSTRY) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT area_name_unique IF NOT EXISTS FOR (a:AREA) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT market_name_unique IF NOT EXISTS FOR (m:MARKET) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT exchange_name_unique IF NOT EXISTS FOR (e:EXCHANGE) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT concept_code_unique IF NOT EXISTS FOR (c:CONCEPT) REQUIRE c.code IS UNIQUE",
        ]

        try:
            with self._driver.session() as session:
                for constraint_cypher in constraints:
                    session.run(constraint_cypher)
            logger.info("Neo4j 图谱唯一约束创建完成（幂等）")
        except Exception as e:
            logger.error(f"创建 Neo4j 唯一约束失败: {str(e)}")
            raise Neo4jConnectionError(
                message="创建图谱 Schema 约束失败",
                details={"error": str(e)},
            )

    async def merge_stocks(
        self,
        stocks: list[StockGraphSyncDTO],
        batch_size: int = 500,
    ) -> SyncResult:
        """
        批量写入/更新 Stock 节点及其维度关系。
        
        使用 UNWIND + MERGE 实现批量写入，自动创建维度节点并建立关系。
        """
        if not stocks:
            return SyncResult(
                total=0,
                success=0,
                failed=0,
                duration_ms=0.0,
                error_details=[],
            )

        start_time = time.time()
        total = len(stocks)
        success = 0
        failed = 0
        error_details: list[str] = []

        # Cypher 批量写入语句
        cypher = """
        UNWIND $stocks AS stock
        MERGE (s:STOCK {third_code: stock.third_code})
        SET s.symbol = stock.symbol,
            s.name = stock.name,
            s.fullname = stock.fullname,
            s.list_date = stock.list_date,
            s.list_status = stock.list_status,
            s.curr_type = stock.curr_type,
            s.roe = stock.roe,
            s.roa = stock.roa,
            s.gross_margin = stock.gross_margin,
            s.debt_to_assets = stock.debt_to_assets,
            s.pe_ttm = stock.pe_ttm,
            s.pb = stock.pb,
            s.total_mv = stock.total_mv
        
        WITH s, stock
        
        FOREACH (ind IN CASE WHEN stock.industry IS NOT NULL AND trim(stock.industry) <> '' THEN [1] ELSE [] END |
            MERGE (i:INDUSTRY {name: stock.industry})
            MERGE (s)-[:BELONGS_TO_INDUSTRY]->(i)
        )
        
        FOREACH (ar IN CASE WHEN stock.area IS NOT NULL AND trim(stock.area) <> '' THEN [1] ELSE [] END |
            MERGE (a:AREA {name: stock.area})
            MERGE (s)-[:LOCATED_IN]->(a)
        )
        
        FOREACH (mkt IN CASE WHEN stock.market IS NOT NULL AND trim(stock.market) <> '' THEN [1] ELSE [] END |
            MERGE (m:MARKET {name: stock.market})
            MERGE (s)-[:TRADES_ON]->(m)
        )
        
        FOREACH (ex IN CASE WHEN stock.exchange IS NOT NULL AND trim(stock.exchange) <> '' THEN [1] ELSE [] END |
            MERGE (e:EXCHANGE {name: stock.exchange})
            MERGE (s)-[:LISTED_ON]->(e)
        )
        """

        try:
            with self._driver.session() as session:
                # 分批处理
                for i in range(0, total, batch_size):
                    batch = stocks[i : i + batch_size]
                    batch_data: list[dict[str, object]] = []
                    for stock in batch:
                        stock_payload = stock.model_dump(mode="json")
                        stock_payload["industry"] = self._normalize_dimension_name(
                            stock_payload.get("industry")
                        )
                        stock_payload["area"] = self._normalize_dimension_name(
                            stock_payload.get("area")
                        )
                        stock_payload["market"] = self._normalize_dimension_name(
                            stock_payload.get("market")
                        )
                        stock_payload["exchange"] = self._normalize_dimension_name(
                            stock_payload.get("exchange")
                        )
                        batch_data.append(stock_payload)

                    try:
                        session.run(cypher, stocks=batch_data)
                        success += len(batch)
                        logger.info(f"成功同步批次 {i // batch_size + 1}，共 {len(batch)} 条记录")
                    except Exception as e:
                        logger.warning(
                            f"批次 {i // batch_size + 1} 同步失败，将降级为单条重试: {str(e)}"
                        )
                        for stock_payload in batch_data:
                            third_code = str(stock_payload.get("third_code", "UNKNOWN"))
                            try:
                                session.run(cypher, stocks=[stock_payload])
                                success += 1
                            except Exception as single_error:
                                failed += 1
                                error_msg = f"third_code={third_code} 同步失败: {str(single_error)}"
                                error_details.append(error_msg)
                                logger.error(error_msg)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Stock 节点批量同步完成: 总数={total}, 成功={success}, 失败={failed}, 耗时={duration_ms:.2f}ms"  # noqa: E501
            )
            
            return SyncResult(
                total=total,
                success=success,
                failed=failed,
                duration_ms=duration_ms,
                error_details=error_details,
            )
        except Exception as e:
            logger.error(f"批量同步 Stock 节点失败: {str(e)}")
            raise GraphSyncError(
                message="批量同步 Stock 节点失败",
                details={"error": str(e)},
            )

    async def merge_dimensions(self, dimensions: list[DimensionDTO]) -> None:
        """
        批量写入/更新维度节点。

        使用 UNWIND + MERGE，按标签分组写入维度节点。
        """
        if not dimensions:
            return

        grouped: dict[str, list[str]] = {
            "INDUSTRY": [],
            "AREA": [],
            "MARKET": [],
            "EXCHANGE": [],
        }
        for dimension in dimensions:
            normalized_name = self._normalize_dimension_name(dimension.name)
            if normalized_name:
                grouped[dimension.label].append(normalized_name)

        try:
            with self._driver.session() as session:
                for label, names in grouped.items():
                    if not names:
                        continue
                    cypher = f"""
                    UNWIND $names AS name
                    WITH trim(name) AS name
                    WHERE name <> ''
                    MERGE (d:{label} {{name: name}})
                    """
                    session.run(cypher, names=names)
            logger.info("维度节点批量写入完成")
        except Exception as e:
            logger.error(f"批量写入维度节点失败: {str(e)}")
            raise GraphSyncError(
                message="批量写入维度节点失败",
                details={"error": str(e)},
            )

    async def find_neighbors(
        self,
        third_code: str,
        dimension: str,
        limit: int = 20,
        dimension_name: str | None = None,
    ) -> list[StockNeighborDTO]:
        """
        查询与指定股票共享同一维度节点的其他股票。
        
        Args:
            third_code: 股票第三方代码
            dimension: 维度类型（industry/area/market/exchange/concept）
            limit: 返回数量上限
            dimension_name: 维度名称，当 dimension="concept" 时必填
        
        Returns:
            StockNeighborDTO 列表（不包含查询股票自身）
        """
        # 根据维度类型构造 Cypher 查询
        dimension_map = {
            "industry": ("INDUSTRY", "BELONGS_TO_INDUSTRY"),
            "area": ("AREA", "LOCATED_IN"),
            "market": ("MARKET", "TRADES_ON"),
            "exchange": ("EXCHANGE", "LISTED_ON"),
            "concept": ("CONCEPT", "BELONGS_TO_CONCEPT"),
        }
        
        if dimension not in dimension_map:
            raise GraphQueryError(
                message=f"无效的维度类型: {dimension}",
                details={"valid_dimensions": list(dimension_map.keys())},
            )
        
        # concept 维度必须提供 dimension_name
        if dimension == "concept" and not dimension_name:
            raise GraphQueryError(
                message="查询概念维度邻居时必须提供 dimension_name 参数",
                details={"dimension": dimension},
            )
        
        # 根据维度类型构建不同的查询
        if dimension == "industry":
            cypher = """
            MATCH (s:STOCK {third_code: $third_code})-[:BELONGS_TO_INDUSTRY]->(i:INDUSTRY)<-[:BELONGS_TO_INDUSTRY]-(neighbor:STOCK)
            WHERE neighbor.third_code <> $third_code
            RETURN neighbor.third_code AS third_code,
                   neighbor.name AS name,
                   i.name AS industry,
                   NULL AS area,
                   NULL AS market,
                   NULL AS exchange
            LIMIT $limit
            """
        elif dimension == "area":
            cypher = """
            MATCH (s:STOCK {third_code: $third_code})-[:LOCATED_IN]->(a:AREA)<-[:LOCATED_IN]-(neighbor:STOCK)
            WHERE neighbor.third_code <> $third_code
            RETURN neighbor.third_code AS third_code,
                   neighbor.name AS name,
                   NULL AS industry,
                   a.name AS area,
                   NULL AS market,
                   NULL AS exchange
            LIMIT $limit
            """
        elif dimension == "market":
            cypher = """
            MATCH (s:STOCK {third_code: $third_code})-[:TRADES_ON]->(m:MARKET)<-[:TRADES_ON]-(neighbor:STOCK)
            WHERE neighbor.third_code <> $third_code
            RETURN neighbor.third_code AS third_code,
                   neighbor.name AS name,
                   NULL AS industry,
                   NULL AS area,
                   m.name AS market,
                   NULL AS exchange
            LIMIT $limit
            """
        elif dimension == "exchange":
            cypher = """
            MATCH (s:STOCK {third_code: $third_code})-[:LISTED_ON]->(e:EXCHANGE)<-[:LISTED_ON]-(neighbor:STOCK)
            WHERE neighbor.third_code <> $third_code
            RETURN neighbor.third_code AS third_code,
                   neighbor.name AS name,
                   NULL AS industry,
                   NULL AS area,
                   NULL AS market,
                   e.name AS exchange
            LIMIT $limit
            """
        elif dimension == "concept":
            cypher = """
            MATCH (s:STOCK {third_code: $third_code})-[:BELONGS_TO_CONCEPT]->(c:CONCEPT {name: $dimension_name})<-[:BELONGS_TO_CONCEPT]-(neighbor:STOCK)
            WHERE neighbor.third_code <> $third_code
            RETURN neighbor.third_code AS third_code,
                   neighbor.name AS name,
                   NULL AS industry,
                   NULL AS area,
                   NULL AS market,
                   NULL AS exchange
            LIMIT $limit
            """
        
        try:
            with self._driver.session() as session:
                params = {
                    "third_code": third_code,
                    "limit": limit,
                }
                if dimension == "concept":
                    params["dimension_name"] = dimension_name
                
                result = session.run(cypher, **params)
                
                neighbors = []
                for record in result:
                    neighbors.append(
                        StockNeighborDTO(
                            third_code=record["third_code"],
                            name=record["name"],
                            industry=record.get("industry"),
                            area=record.get("area"),
                            market=record.get("market"),
                            exchange=record.get("exchange"),
                        )
                    )
                
                logger.info(
                    f"查询同{dimension}股票完成: third_code={third_code}, 返回{len(neighbors)}条"
                )
                return neighbors
        except Exception as e:
            logger.error(f"查询同维度股票失败: {str(e)}")
            raise GraphQueryError(
                message=f"查询同{dimension}股票失败",
                details={"third_code": third_code, "error": str(e)},
            )

    async def find_stock_graph(
        self,
        third_code: str,
        depth: int = 1,
    ) -> StockGraphDTO | None:
        """
        查询指定股票的关系网络（depth=1）。
        
        返回该股票及其所有直接关联的维度节点和关系。
        """
        cypher = """
        OPTIONAL MATCH (s:STOCK {third_code: $third_code})
        WHERE s IS NOT NULL
        OPTIONAL MATCH (s)-[r]->(d)
        WHERE d:INDUSTRY OR d:AREA OR d:MARKET OR d:EXCHANGE OR d:CONCEPT
        RETURN s, collect({rel: type(r), target: d}) AS connections
        """
        
        try:
            with self._driver.session() as session:
                result = session.run(cypher, third_code=third_code)
                record = result.single()
                
                if not record or record["s"] is None:
                    logger.warning(f"Stock 节点不存在: third_code={third_code}")
                    return None
                
                # 构建节点列表
                nodes: list[GraphNodeDTO] = []
                relationships: list[GraphRelationshipDTO] = []
                
                # 添加 Stock 节点
                stock_node = record["s"]
                stock_props: dict[str, Any] = dict(stock_node.items())
                nodes.append(
                    GraphNodeDTO(
                        label="STOCK",
                        id=stock_props["third_code"],
                        properties=stock_props,
                    )
                )
                
                # 添加维度节点与关系
                connections = record["connections"]
                for conn in connections:
                    if conn["rel"] and conn["target"]:
                        target_node = conn["target"]
                        target_props: dict[str, Any] = dict(target_node.items())
                        target_labels = list(target_node.labels)
                        target_label = target_labels[0] if target_labels else "UNKNOWN"
                        
                        nodes.append(
                            GraphNodeDTO(
                                label=target_label,
                                id=target_props.get("name", ""),
                                properties=target_props,
                            )
                        )
                        
                        relationships.append(
                            GraphRelationshipDTO(
                                source_id=stock_props["third_code"],
                                target_id=target_props.get("name", ""),
                                relationship_type=conn["rel"],
                            )
                        )
                
                logger.info(
                    f"查询 Stock 关系网络完成: third_code={third_code}, 节点数={len(nodes)}, 关系数={len(relationships)}"  # noqa: E501
                )
                
                return StockGraphDTO(
                    nodes=nodes,
                    relationships=relationships,
                )
        except Exception as e:
            logger.error(f"查询 Stock 关系网络失败: {str(e)}")
            raise GraphQueryError(
                message="查询 Stock 关系网络失败",
                details={"third_code": third_code, "error": str(e)},
            )

    async def merge_concepts(
        self,
        concepts: list[ConceptGraphSyncDTO],
        batch_size: int = 500,
    ) -> SyncResult:
        """
        批量写入/更新 Concept 节点及其与 Stock 的关系。
        
        使用 UNWIND + MERGE 实现批量写入，仅当 Stock 节点存在时才创建关系。
        """
        if not concepts:
            return SyncResult(
                total=0,
                success=0,
                failed=0,
                duration_ms=0.0,
                error_details=[],
            )

        start_time = time.time()
        total = len(concepts)
        success = 0
        failed = 0
        error_details: list[str] = []

        # Cypher 批量写入语句
        cypher = """
        UNWIND $concepts AS concept
        MERGE (c:CONCEPT {code: concept.code})
        SET c.name = concept.name
        
        WITH c, concept
        UNWIND concept.stock_third_codes AS stock_code
        MATCH (s:STOCK {third_code: stock_code})
        MERGE (s)-[:BELONGS_TO_CONCEPT]->(c)
        """

        try:
            with self._driver.session() as session:
                # 分批处理
                for i in range(0, total, batch_size):
                    batch = concepts[i : i + batch_size]
                    batch_data: list[dict[str, object]] = [
                        concept.model_dump(mode="json") for concept in batch
                    ]

                    try:
                        session.run(cypher, concepts=batch_data)
                        success += len(batch)
                        logger.info(f"成功同步概念批次 {i // batch_size + 1}，共 {len(batch)} 条记录")
                    except Exception as e:
                        logger.warning(
                            f"概念批次 {i // batch_size + 1} 同步失败，将降级为单条重试: {str(e)}"
                        )
                        for concept_payload in batch_data:
                            concept_code = str(concept_payload.get("code", "UNKNOWN"))
                            try:
                                session.run(cypher, concepts=[concept_payload])
                                success += 1
                            except Exception as single_error:
                                failed += 1
                                error_msg = f"concept_code={concept_code} 同步失败: {str(single_error)}"
                                error_details.append(error_msg)
                                logger.error(error_msg)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Concept 节点批量同步完成: 总数={total}, 成功={success}, 失败={failed}, 耗时={duration_ms:.2f}ms"
            )
            
            return SyncResult(
                total=total,
                success=success,
                failed=failed,
                duration_ms=duration_ms,
                error_details=error_details,
            )
        except Exception as e:
            logger.error(f"批量同步 Concept 节点失败: {str(e)}")
            raise GraphSyncError(
                message="批量同步 Concept 节点失败",
                details={"error": str(e)},
            )

    async def delete_all_concept_relationships(self) -> int:
        """
        删除所有 BELONGS_TO_CONCEPT 关系。
        
        Concept 节点本身保留，仅删除关系。
        
        Returns:
            int：删除的关系数量
        """
        cypher = """
        MATCH ()-[r:BELONGS_TO_CONCEPT]->()
        DELETE r
        RETURN count(r) AS deleted_count
        """

        try:
            with self._driver.session() as session:
                result = session.run(cypher)
                record = result.single()
                deleted_count = record["deleted_count"] if record else 0
                
                logger.info(f"删除所有 BELONGS_TO_CONCEPT 关系：{deleted_count} 条")
                return deleted_count
        except Exception as e:
            logger.error(f"删除 BELONGS_TO_CONCEPT 关系失败: {str(e)}")
            raise GraphSyncError(
                message="删除概念关系失败",
                details={"error": str(e)},
            )

    async def merge_concept_relations(
        self,
        relations: list[ConceptRelationSyncDTO],
        batch_size: int = 500,
    ) -> SyncResult:
        """
        批量写入/更新 Concept 节点间的关系。
        
        使用 Cypher UNWIND + MATCH Concept + MERGE 关系实现批量写入。
        每条关系使用独立的关系类型（IS_UPSTREAM_OF 等），
        并携带 source_type、confidence、pg_id 属性。
        """
        if not relations:
            return SyncResult(
                total=0,
                success=0,
                failed=0,
                duration_ms=0.0,
                error_details=[],
            )

        start_time = time.time()
        total = len(relations)
        success = 0
        failed = 0
        error_details: list[str] = []

        # 按关系类型分组，每种类型使用独立的 MERGE 语句
        grouped_by_type: dict[str, list[ConceptRelationSyncDTO]] = {}
        for relation in relations:
            rel_type = relation.relation_type
            if rel_type not in grouped_by_type:
                grouped_by_type[rel_type] = []
            grouped_by_type[rel_type].append(relation)

        try:
            with self._driver.session() as session:
                for rel_type, rel_batch in grouped_by_type.items():
                    # 为每种关系类型构建 Cypher
                    cypher = f"""
                    UNWIND $relations AS rel
                    MATCH (source:CONCEPT {{code: rel.source_concept_code}})
                    MATCH (target:CONCEPT {{code: rel.target_concept_code}})
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r.source_type = rel.source_type,
                        r.confidence = rel.confidence,
                        r.pg_id = rel.pg_id
                    """

                    # 分批处理
                    for i in range(0, len(rel_batch), batch_size):
                        batch = rel_batch[i : i + batch_size]
                        batch_data: list[dict[str, object]] = [
                            r.model_dump(mode="json") for r in batch
                        ]

                        try:
                            session.run(cypher, relations=batch_data)
                            success += len(batch)
                            logger.info(
                                f"成功同步概念关系批次（{rel_type}），共 {len(batch)} 条记录"
                            )
                        except Exception as e:
                            logger.warning(
                                f"概念关系批次（{rel_type}）同步失败，将降级为单条重试: {str(e)}"
                            )
                            for rel_payload in batch_data:
                                rel_id = rel_payload.get("pg_id", "UNKNOWN")
                                try:
                                    session.run(cypher, relations=[rel_payload])
                                    success += 1
                                except Exception as single_error:
                                    failed += 1
                                    error_msg = (
                                        f"pg_id={rel_id} 同步失败: {str(single_error)}"
                                    )
                                    error_details.append(error_msg)
                                    logger.error(error_msg)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"概念关系批量同步完成: 总数={total}, 成功={success}, 失败={failed}, 耗时={duration_ms:.2f}ms"
            )

            return SyncResult(
                total=total,
                success=success,
                failed=failed,
                duration_ms=duration_ms,
                error_details=error_details,
            )
        except Exception as e:
            logger.error(f"批量同步概念关系失败: {str(e)}")
            raise GraphSyncError(
                message="批量同步概念关系失败",
                details={"error": str(e)},
            )

    async def delete_all_concept_inter_relationships(self) -> int:
        """
        删除所有 Concept 节点之间的关系。
        
        仅删除 Concept 间关系（IS_UPSTREAM_OF 等），保留 BELONGS_TO_CONCEPT 关系。
        """
        # 使用正则匹配删除所有非 BELONGS_TO_CONCEPT 的 Concept 间关系
        cypher = """
        MATCH (c1:CONCEPT)-[r]->(c2:CONCEPT)
        WHERE type(r) <> 'BELONGS_TO_CONCEPT'
        DELETE r
        RETURN count(r) AS deleted_count
        """

        try:
            with self._driver.session() as session:
                result = session.run(cypher)
                record = result.single()
                deleted_count = record["deleted_count"] if record else 0

                logger.info(f"删除所有 Concept 间关系：{deleted_count} 条")
                return deleted_count
        except Exception as e:
            logger.error(f"删除 Concept 间关系失败: {str(e)}")
            raise GraphSyncError(
                message="删除 Concept 间关系失败",
                details={"error": str(e)},
            )

    async def find_concept_relations(
        self,
        concept_code: str,
        direction: str = "both",
        relation_types: list[str] | None = None,
    ) -> list[ConceptRelationQueryDTO]:
        """
        查询指定概念的直接关系。
        
        Args:
            concept_code: 概念代码
            direction: 查询方向（outgoing / incoming / both）
            relation_types: 关系类型筛选列表
        
        Returns:
            概念关系查询结果列表
        """
        # 构建 Cypher 查询
        if direction == "outgoing":
            cypher_pattern = "(c:CONCEPT {code: $code})-[r]->(target:CONCEPT)"
            return_source = "c.code"
            return_target = "target.code"
        elif direction == "incoming":
            cypher_pattern = "(source:CONCEPT)-[r]->(c:CONCEPT {code: $code})"
            return_source = "source.code"
            return_target = "c.code"
        else:  # both
            cypher_pattern = """
            (c:CONCEPT {code: $code})-[r]->(target:CONCEPT)
            UNION ALL
            MATCH (source:CONCEPT)-[r]->(c:CONCEPT {code: $code})
            """
            # 对于 both 模式，使用 UNION ALL 查询
            cypher = f"""
            MATCH (c:CONCEPT {{code: $code}})-[r]->(target:CONCEPT)
            WHERE type(r) <> 'BELONGS_TO_CONCEPT'
            {self._build_relation_type_filter(relation_types, 'r')}
            RETURN c.code AS source_concept_code, target.code AS target_concept_code,
                   type(r) AS relation_type, r.source_type AS source_type,
                   r.confidence AS confidence, r.pg_id AS pg_id
            UNION ALL
            MATCH (source:CONCEPT)-[r]->(c:CONCEPT {{code: $code}})
            WHERE type(r) <> 'BELONGS_TO_CONCEPT'
            {self._build_relation_type_filter(relation_types, 'r')}
            RETURN source.code AS source_concept_code, c.code AS target_concept_code,
                   type(r) AS relation_type, r.source_type AS source_type,
                   r.confidence AS confidence, r.pg_id AS pg_id
            """

            try:
                with self._driver.session() as session:
                    result = session.run(cypher, code=concept_code)
                    records = result.data()

                    relations = [
                        ConceptRelationQueryDTO(
                            source_concept_code=record["source_concept_code"],
                            target_concept_code=record["target_concept_code"],
                            relation_type=record["relation_type"],
                            source_type=record.get("source_type", "UNKNOWN"),
                            confidence=record.get("confidence", 1.0),
                            pg_id=record.get("pg_id"),
                        )
                        for record in records
                    ]

                    logger.debug(
                        f"查询概念关系: code={concept_code}, direction={direction}, "
                        f"返回 {len(relations)} 条"
                    )
                    return relations
            except Exception as e:
                logger.error(f"查询概念关系失败: {str(e)}")
                raise GraphQueryError(
                    message="查询概念关系失败",
                    details={"error": str(e), "concept_code": concept_code},
                )

        # 单向查询（outgoing 或 incoming）
        cypher = f"""
        MATCH {cypher_pattern}
        WHERE type(r) <> 'BELONGS_TO_CONCEPT'
        {self._build_relation_type_filter(relation_types, 'r')}
        RETURN {return_source} AS source_concept_code,
               {return_target} AS target_concept_code,
               type(r) AS relation_type,
               r.source_type AS source_type,
               r.confidence AS confidence,
               r.pg_id AS pg_id
        """

        try:
            with self._driver.session() as session:
                result = session.run(cypher, code=concept_code)
                records = result.data()

                relations = [
                    ConceptRelationQueryDTO(
                        source_concept_code=record["source_concept_code"],
                        target_concept_code=record["target_concept_code"],
                        relation_type=record["relation_type"],
                        source_type=record.get("source_type", "UNKNOWN"),
                        confidence=record.get("confidence", 1.0),
                        pg_id=record.get("pg_id"),
                    )
                    for record in records
                ]

                logger.debug(
                    f"查询概念关系: code={concept_code}, direction={direction}, "
                    f"返回 {len(relations)} 条"
                )
                return relations
        except Exception as e:
            logger.error(f"查询概念关系失败: {str(e)}")
            raise GraphQueryError(
                message="查询概念关系失败",
                details={"error": str(e), "concept_code": concept_code},
            )

    async def find_concept_chain(
        self,
        concept_code: str,
        direction: str = "outgoing",
        max_depth: int = 3,
        relation_types: list[str] | None = None,
    ) -> list[ConceptChainNodeDTO]:
        """
        查询产业链路径（变长路径遍历）。
        
        从指定概念出发，沿指定方向遍历 Concept 间关系，返回路径上的所有节点。
        """
        # 构建路径方向
        if direction == "outgoing":
            path_pattern = f"(start:CONCEPT {{code: $code}})-[rels*1..{max_depth}]->(end:CONCEPT)"
        elif direction == "incoming":
            path_pattern = f"(start:CONCEPT)<-[rels*1..{max_depth}]-(end:CONCEPT {{code: $code}})"
        else:  # both
            path_pattern = f"(start:CONCEPT {{code: $code}})-[rels*1..{max_depth}]-(end:CONCEPT)"

        # 构建关系类型过滤
        rel_filter = ""
        if relation_types:
            rel_types_str = "|".join(f":{rt}" for rt in relation_types)
            if direction == "outgoing":
                path_pattern = f"(start:CONCEPT {{code: $code}})-[rels{rel_types_str}*1..{max_depth}]->(end:CONCEPT)"
            elif direction == "incoming":
                path_pattern = f"(start:CONCEPT)<-[rels{rel_types_str}*1..{max_depth}]-(end:CONCEPT {{code: $code}})"
            else:
                path_pattern = f"(start:CONCEPT {{code: $code}})-[rels{rel_types_str}*1..{max_depth}]-(end:CONCEPT)"

        cypher = f"""
        MATCH path = {path_pattern}
        WHERE ALL(r IN rels WHERE type(r) <> 'BELONGS_TO_CONCEPT')
        WITH nodes(path) AS node_list, relationships(path) AS rel_list
        UNWIND range(0, size(node_list)-1) AS idx
        RETURN node_list[idx].code AS concept_code,
               node_list[idx].name AS concept_name,
               idx AS depth,
               CASE WHEN idx > 0 THEN type(rel_list[idx-1]) ELSE null END AS relation_from_previous
        ORDER BY depth
        """

        try:
            with self._driver.session() as session:
                result = session.run(cypher, code=concept_code)
                records = result.data()

                # 去重（同一深度的同一概念可能通过多条路径到达）
                seen = set()
                nodes = []
                for record in records:
                    key = (record["concept_code"], record["depth"])
                    if key not in seen:
                        seen.add(key)
                        nodes.append(
                            ConceptChainNodeDTO(
                                concept_code=record["concept_code"],
                                concept_name=record.get("concept_name"),
                                depth=record["depth"],
                                relation_from_previous=record.get("relation_from_previous"),
                            )
                        )

                logger.debug(
                    f"查询产业链路径: code={concept_code}, direction={direction}, "
                    f"max_depth={max_depth}, 返回 {len(nodes)} 个节点"
                )
                return nodes
        except Exception as e:
            logger.error(f"查询产业链路径失败: {str(e)}")
            raise GraphQueryError(
                message="查询产业链路径失败",
                details={"error": str(e), "concept_code": concept_code},
            )

    def _build_relation_type_filter(self, relation_types: list[str] | None, var: str) -> str:
        """
        构建关系类型过滤条件。
        
        Args:
            relation_types: 关系类型列表
            var: 关系变量名
        
        Returns:
            Cypher WHERE 子句片段
        """
        if not relation_types:
            return ""
        types_str = ", ".join(f"'{rt}'" for rt in relation_types)
        return f"AND type({var}) IN [{types_str}]"
