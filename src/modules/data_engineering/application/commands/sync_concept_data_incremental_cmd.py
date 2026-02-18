import time

from loguru import logger

from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    ConceptSyncResult,
)
from src.modules.data_engineering.domain.model.concept import Concept, ConceptStock
from src.modules.data_engineering.domain.ports.providers.concept_data_provider import (
    IConceptDataProvider,
)
from src.modules.data_engineering.domain.ports.repositories.concept_repo import (
    IConceptRepository,
)
from src.shared.application.use_cases import BaseUseCase


class SyncConceptDataIncrementalCmd(BaseUseCase):
    """
    增量同步概念数据命令
    逐个概念获取后立即落库，提高内存效率和容错性
    
    执行流程：
    1. 获取概念列表
    2. 逐个概念获取成份股并立即落库
    3. 报告结果
    """

    def __init__(
        self,
        concept_provider: IConceptDataProvider,
        concept_repo: IConceptRepository,
    ):
        self.concept_provider = concept_provider
        self.concept_repo = concept_repo

    async def execute(self) -> ConceptSyncResult:
        """
        执行增量概念数据同步
        
        Returns:
            ConceptSyncResult: 同步结果摘要
        """
        start_time = time.time()
        logger.info("开始增量同步概念数据（逐个落库模式）")

        # 1. 获取概念列表
        try:
            concept_infos = await self.concept_provider.fetch_concept_list()
            if not concept_infos:
                logger.warning("未获取到概念数据，同步结束")
                return ConceptSyncResult(
                    total_concepts=0,
                    success_concepts=0,
                    failed_concepts=0,
                    total_stocks=0,
                    elapsed_time=time.time() - start_time,
                )
        except Exception as e:
            logger.error(f"获取概念列表失败：{str(e)}")
            raise

        total_concepts = len(concept_infos)
        logger.info(f"获取到 {total_concepts} 个概念板块，开始增量同步")

        # 2. 逐个概念获取成份股并立即落库
        success_count = 0
        failed_count = 0
        total_stocks = 0

        for idx, concept_info in enumerate(concept_infos, 1):
            try:
                # 获取成份股
                constituents = await self.concept_provider.fetch_concept_constituents(
                    concept_info.name
                )

                # 在单个事务中完成概念和成份股的落库
                concept = Concept(code=concept_info.code, name=concept_info.name)
                stocks = [
                    ConceptStock(
                        concept_code=concept_info.code,
                        third_code=constituent.stock_code,
                        stock_name=constituent.stock_name,
                    )
                    for constituent in constituents
                ]
                
                total_rows = await self.concept_repo.upsert_concept_with_stocks(concept, stocks)

                success_count += 1
                total_stocks += len(constituents)
                
                logger.info(
                    f"[{idx}/{total_concepts}] ✓ 概念「{concept_info.name}」({concept_info.code}) "
                    f"事务提交：总计 {total_rows} 行"
                )

            except Exception as e:
                failed_count += 1
                logger.error(
                    f"[{idx}/{total_concepts}] ✗ 概念「{concept_info.name}」({concept_info.code}) "
                    f"同步失败：{str(e)}，跳过"
                )
                continue

        elapsed_time = time.time() - start_time
        result = ConceptSyncResult(
            total_concepts=total_concepts,
            success_concepts=success_count,
            failed_concepts=failed_count,
            total_stocks=total_stocks,
            elapsed_time=elapsed_time,
        )

        logger.info(
            f"增量概念数据同步完成：成功 {success_count}/{total_concepts}，"
            f"失败 {failed_count}，总成份股 {total_stocks} 条，耗时 {elapsed_time:.2f}s"
        )

        return result
