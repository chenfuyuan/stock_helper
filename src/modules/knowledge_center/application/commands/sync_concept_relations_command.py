"""
概念关系同步命令。

编排 PostgreSQL → Neo4j 同步流程，支持 rebuild（全量重建）和 incremental（增量追加）两种模式。
"""

from loguru import logger
from pydantic import BaseModel, Field

from src.modules.knowledge_center.domain.dtos.concept_relation_sync_dtos import (
    ConceptRelationSyncDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.domain.ports.concept_relation_repository import (
    IConceptRelationRepository,
)
from src.modules.knowledge_center.domain.ports.graph_repository import IGraphRepository


class SyncConceptRelationsResult(BaseModel):
    """概念关系同步结果 DTO。"""

    mode: str = Field(description="同步模式（rebuild / incremental）")
    total_relations: int = Field(description="从 PG 读取的已确认关系总数")
    deleted_count: int = Field(
        default=0, description="Neo4j 中删除的旧关系数量（rebuild 模式）"
    )
    sync_result: SyncResult = Field(description="Neo4j 同步结果")

    @property
    def sync_success(self) -> int:
        """同步成功数量（便捷属性）。"""
        return self.sync_result.success

    @property
    def sync_failed(self) -> int:
        """同步失败数量（便捷属性）。"""
        return self.sync_result.failed

    @property
    def duration_ms(self) -> float:
        """同步耗时（便捷属性）。"""
        return self.sync_result.duration_ms


class SyncConceptRelationsCmd:
    """
    概念关系同步命令。
    
    将 PostgreSQL 中已确认的概念关系同步到 Neo4j 图谱，构建 Concept 间的关系网络。
    """

    def __init__(
        self,
        pg_repository: IConceptRelationRepository,
        graph_repository: IGraphRepository,
    ):
        """
        初始化命令。
        
        Args:
            pg_repository: PostgreSQL 概念关系仓储
            graph_repository: Neo4j 图谱仓储
        """
        self._pg_repo = pg_repository
        self._graph_repo = graph_repository

    async def execute(
        self,
        mode: str = "incremental",
        batch_size: int = 500,
    ) -> SyncConceptRelationsResult:
        """
        执行概念关系同步。
        
        模式说明：
        - rebuild（全量重建）：删除 Neo4j 中所有 Concept 间关系 → 从 PG 全量同步
        - incremental（增量追加）：仅同步新增的已确认关系（简化实现：全量覆盖，利用 MERGE 幂等性）
        
        Args:
            mode: 同步模式（rebuild / incremental）
            batch_size: Neo4j 批量写入批次大小
        
        Returns:
            SyncConceptRelationsResult：同步结果统计
        """
        if mode not in ["rebuild", "incremental"]:
            raise ValueError(f"无效的同步模式: {mode}，仅支持 rebuild 或 incremental")

        logger.info(f"开始概念关系同步，模式: {mode}")

        deleted_count = 0

        # 1. 如果是 rebuild 模式，先删除 Neo4j 中的 Concept 间关系
        if mode == "rebuild":
            logger.info("执行全量重建，删除 Neo4j 中所有 Concept 间关系")
            deleted_count = await self._graph_repo.delete_all_concept_inter_relationships()
            logger.info(f"已删除 {deleted_count} 条 Concept 间关系")

        # 2. 从 PostgreSQL 读取所有已确认的概念关系
        confirmed_relations = await self._pg_repo.get_all_confirmed()
        logger.info(f"从 PostgreSQL 读取 {len(confirmed_relations)} 条已确认关系")

        if not confirmed_relations:
            logger.warning("无已确认关系需要同步")
            return SyncConceptRelationsResult(
                mode=mode,
                total_relations=0,
                deleted_count=deleted_count,
                sync_result=SyncResult(
                    total=0,
                    success=0,
                    failed=0,
                    duration_ms=0.0,
                    error_details=[],
                ),
            )

        # 3. 转换为同步 DTO
        sync_dtos = [
            ConceptRelationSyncDTO(
                pg_id=relation.id,  # type: ignore
                source_concept_code=relation.source_concept_code,
                target_concept_code=relation.target_concept_code,
                relation_type=relation.relation_type,
                source_type=relation.source_type,
                confidence=relation.confidence,
            )
            for relation in confirmed_relations
        ]

        # 4. 批量写入 Neo4j（MERGE 保证幂等性）
        sync_result = await self._graph_repo.merge_concept_relations(
            relations=sync_dtos, batch_size=batch_size
        )

        logger.info(
            f"概念关系同步完成，模式: {mode}, "
            f"总数={sync_result.total}, 成功={sync_result.success}, 失败={sync_result.failed}"
        )

        return SyncConceptRelationsResult(
            mode=mode,
            total_relations=len(confirmed_relations),
            deleted_count=deleted_count,
            sync_result=sync_result,
        )
