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


class SyncConceptDataCmd(BaseUseCase):
    """
    同步概念数据命令
    从 akshare 获取概念板块及成份股数据并写入 PostgreSQL
    
    执行流程：
    1. 获取概念列表
    2. 逐概念获取成份股（错误隔离）
    3. UPSERT 概念记录
    4. 全量替换成份股映射
    5. 报告结果
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
        执行概念数据同步
        
        Returns:
            ConceptSyncResult: 同步结果摘要
        """
        start_time = time.time()
        logger.info("开始同步概念数据（akshare → PostgreSQL）")

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
        logger.info(f"获取到 {total_concepts} 个概念板块，开始获取成份股")

        # 2. 逐概念获取成份股（错误隔离）
        success_count = 0
        failed_count = 0
        all_concepts: list[Concept] = []
        all_stocks: list[ConceptStock] = []

        for concept_info in concept_infos:
            try:
                # 获取成份股
                constituents = await self.concept_provider.fetch_concept_constituents(
                    concept_info.name
                )

                # 记录概念
                all_concepts.append(
                    Concept(code=concept_info.code, name=concept_info.name)
                )

                # 记录成份股映射
                for constituent in constituents:
                    all_stocks.append(
                        ConceptStock(
                            concept_code=concept_info.code,
                            third_code=constituent.stock_code,
                            stock_name=constituent.stock_name,
                        )
                    )

                success_count += 1
                logger.debug(
                    f"成功获取概念「{concept_info.name}」({concept_info.code})，"
                    f"成份股数：{len(constituents)}"
                )

            except Exception as e:
                failed_count += 1
                logger.error(
                    f"获取概念「{concept_info.name}」({concept_info.code}) 成份股失败：{str(e)}，跳过"
                )
                continue

        logger.info(
            f"概念成份股获取完成：成功 {success_count}/{total_concepts}，"
            f"失败 {failed_count}，总成份股映射 {len(all_stocks)} 条"
        )

        # 3. UPSERT 概念记录
        if all_concepts:
            try:
                upserted_count = await self.concept_repo.upsert_concepts(all_concepts)
                logger.info(f"UPSERT 概念记录：{upserted_count} 条")
            except Exception as e:
                logger.error(f"UPSERT 概念记录失败：{str(e)}")
                raise

        # 4. 全量替换成份股映射
        try:
            inserted_stocks = await self.concept_repo.replace_all_concept_stocks(all_stocks)
            logger.info(f"全量替换成份股映射：{inserted_stocks} 条")
        except Exception as e:
            logger.error(f"替换成份股映射失败：{str(e)}")
            raise

        elapsed_time = time.time() - start_time
        result = ConceptSyncResult(
            total_concepts=total_concepts,
            success_concepts=success_count,
            failed_concepts=failed_count,
            total_stocks=len(all_stocks),
            elapsed_time=elapsed_time,
        )

        logger.info(
            f"概念数据同步完成：概念 {success_count}/{total_concepts}，"
            f"成份股映射 {len(all_stocks)} 条，耗时 {elapsed_time:.2f}s"
        )

        return result
