"""
Neo4j GraphRepository 实现。

实现 IGraphRepository 接口，提供基于 Neo4j 的图谱持久化与查询能力。
"""

import time
from typing import Any

from loguru import logger
from neo4j import Driver

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

    
    
    async def clear_all_graph_data(self) -> dict:
        """
        清空整个图谱数据。
        
        删除所有节点和关系，用于完全重建图谱。
        
        Returns:
            dict：包含删除的节点数和关系数的统计信息
        """
        # 先统计当前数据量
        count_cypher = """
        MATCH (n) 
        OPTIONAL MATCH ()-[r]->() 
        RETURN count(DISTINCT n) AS node_count, count(r) AS relationship_count
        """
        
        # 清空所有数据
        clear_cypher = """
        MATCH (n) 
        DETACH DELETE n
        """
        
        try:
            with self._driver.session() as session:
                # 1. 统计当前数据量
                count_result = session.run(count_cypher)
                count_record = count_result.single()
                node_count = count_record["node_count"] if count_record else 0
                relationship_count = count_record["relationship_count"] if count_record else 0
                
                logger.info(f"开始清空图谱，当前节点数: {node_count}, 关系数: {relationship_count}")
                
                # 2. 执行清空操作
                session.run(clear_cypher)
                
                logger.info(f"图谱清空完成，已删除 {node_count} 个节点和 {relationship_count} 条关系")
                
                return {
                    "deleted_nodes": node_count,
                    "deleted_relationships": relationship_count,
                    "message": f"成功清空图谱，删除了 {node_count} 个节点和 {relationship_count} 条关系"
                }
        except Exception as e:
            logger.error(f"清空图谱失败: {str(e)}")
            raise GraphSyncError(
                message="清空图谱失败",
                details={"error": str(e)},
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
