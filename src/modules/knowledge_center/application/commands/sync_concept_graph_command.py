"""
同步概念图谱命令用例

编排从 data_engineering PostgreSQL 读取概念数据、转换并写入 Neo4j 图谱的完整流程
"""

from loguru import logger

from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.domain.ports.graph_repository import IGraphRepository
from src.modules.knowledge_center.infrastructure.adapters.concept_data_adapter import (
    ConceptDataAdapter,
)


class SyncConceptGraphCommand:
    """
    同步概念图谱命令用例
    
    全量同步概念数据到 Neo4j 图谱：
    1. 通过 ConceptDataAdapter 从 data_engineering PostgreSQL 获取概念数据
    2. 将数据转换为 ConceptGraphSyncDTO
    3. 先删除所有现有的 BELONGS_TO_CONCEPT 关系
    4. 调用 GraphRepository.merge_concepts 批量写入 Neo4j
    """

    def __init__(
        self,
        graph_repo: IGraphRepository,
        concept_adapter: ConceptDataAdapter,
    ):
        """
        初始化概念同步命令用例
        
        Args:
            graph_repo: 图谱仓储接口
            concept_adapter: 概念数据适配器
        """
        self._graph_repo = graph_repo
        self._concept_adapter = concept_adapter

    async def execute(self, batch_size: int = 500) -> SyncResult:
        """
        执行概念图谱全量同步
        
        采用"先删后建"策略：
        1. 删除所有现有的 BELONGS_TO_CONCEPT 关系
        2. 批量写入 Concept 节点和新的关系
        
        Args:
            batch_size: 每批提交的记录数
        
        Returns:
            SyncResult：同步结果摘要
        """
        logger.info(f"开始全量同步概念图谱数据: batch_size={batch_size}")

        # 1. 从 data_engineering PostgreSQL 获取概念数据
        concepts = await self._concept_adapter.fetch_all_concepts_for_sync()

        if not concepts:
            logger.warning("未获取到概念数据，跳过同步")
            return SyncResult(
                total=0,
                success=0,
                failed=0,
                duration_ms=0.0,
                error_details=[],
            )

        logger.info(f"获取到 {len(concepts)} 个概念板块数据")

        # 2. 确保图谱约束存在（幂等）
        await self._graph_repo.ensure_constraints()

        # 3. 先删除所有现有的 BELONGS_TO_CONCEPT 关系
        deleted_count = await self._graph_repo.delete_all_concept_relationships()
        logger.info(f"已删除 {deleted_count} 条现有概念关系")

        # 4. 批量写入 Concept 节点和关系到 Neo4j
        result = await self._graph_repo.merge_concepts(
            concepts=concepts,
            batch_size=batch_size,
        )

        logger.info(
            f"概念图谱全量同步完成: total={result.total}, success={result.success}, "
            f"failed={result.failed}, duration={result.duration_ms:.2f}ms"
        )

        return result
