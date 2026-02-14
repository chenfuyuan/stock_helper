"""
概念数据适配器
从 data_engineering 模块读取概念板块数据，转换为 knowledge_center 的 ConceptGraphSyncDTO
"""

from loguru import logger

from src.modules.data_engineering.domain.ports.repositories.concept_repo import (
    IConceptRepository,
)
from src.modules.knowledge_center.domain.dtos.concept_sync_dtos import (
    ConceptGraphSyncDTO,
)


class ConceptDataAdapter:
    """
    概念数据适配器
    
    通过 data_engineering 的 IConceptRepository 获取概念数据，
    转换为 knowledge_center 模块的 ConceptGraphSyncDTO，
    避免直接依赖 data_engineering 的 Domain 实体
    """

    def __init__(self, concept_repo: IConceptRepository):
        """
        初始化概念数据适配器
        
        Args:
            concept_repo: DE 模块的概念数据仓储
        """
        self._concept_repo = concept_repo

    async def fetch_all_concepts_for_sync(self) -> list[ConceptGraphSyncDTO]:
        """
        获取所有概念及其成份股数据并转换为同步 DTO
        
        Returns:
            ConceptGraphSyncDTO 列表
        """
        # 从 DE 的 PostgreSQL 读取概念数据
        concepts_with_stocks = await self._concept_repo.get_all_concepts_with_stocks()

        if not concepts_with_stocks:
            logger.warning("未找到概念数据")
            return []

        logger.info(f"从 data_engineering 获取到 {len(concepts_with_stocks)} 个概念板块")

        # 转换为 KC 的 ConceptGraphSyncDTO
        sync_dtos: list[ConceptGraphSyncDTO] = []
        for concept in concepts_with_stocks:
            # 提取成份股的 third_code 列表
            stock_third_codes = [stock.third_code for stock in concept.stocks]

            sync_dtos.append(
                ConceptGraphSyncDTO(
                    code=concept.code,
                    name=concept.name,
                    stock_third_codes=stock_third_codes,
                )
            )

        logger.info(f"成功转换 {len(sync_dtos)} 条 ConceptGraphSyncDTO")
        return sync_dtos
