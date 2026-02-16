"""数据同步应用服务——统一编排所有数据同步任务。

封装 session 管理、Container/Factory 构建、ExecutionTracker 集成、日期转换等编排逻辑，
对 Presentation 层暴露简单的异步方法。
"""

from datetime import datetime
from typing import Optional

from loguru import logger

from src.modules.data_engineering.application.commands.sync_concept_data_cmd import (
    SyncConceptDataCmd,
)
from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    ConceptSyncResult,
    IncrementalFinanceSyncResult,
)
from src.modules.data_engineering.application.factories.sync_factory import (
    SyncUseCaseFactory,
)
from src.modules.data_engineering.container import DataEngineeringContainer
from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.modules.data_engineering.domain.model.sync_task import SyncTask
from src.modules.data_engineering.infrastructure.config import de_config
from src.modules.foundation.infrastructure.execution_tracker import ExecutionTracker
from src.modules.foundation.infrastructure.persistence.repositories.scheduler_execution_log_repo import (
    SchedulerExecutionLogRepository,
)
from src.shared.infrastructure.db.session import AsyncSessionLocal


class DataSyncApplicationService:
    """
    数据同步应用服务。
    
    统一编排所有同步 Job 的编排逻辑（session 管理、Container/Factory 构建、
    ExecutionTracker 集成、日期转换），对外暴露简单的异步方法。
    """

    async def run_daily_incremental_sync(self, target_date: Optional[str] = None) -> dict:
        """
        执行日线增量同步（含遗漏检测与自动补偿）。
        
        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天
            
        Returns:
            同步结果摘要字典
        """
        logger.info(f"开始执行日线增量同步任务... 目标日期: {target_date or '今天'}")

        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id="sync_daily_by_date", repo=repo):
                async with SyncUseCaseFactory.create_sync_engine() as engine:
                    date_str = target_date or datetime.now().strftime("%Y%m%d")
                    result = await engine.run_incremental_daily_sync(target_date=date_str)

                    logger.info(
                        f"日线增量同步完成：synced_dates={result.get('synced_dates')}, "
                        f"total_count={result.get('total_count')}, message={result.get('message')}"
                    )
                    
                    return result

    async def run_incremental_finance_sync(
        self, target_date: Optional[str] = None
    ) -> IncrementalFinanceSyncResult:
        """
        执行财务增量同步。
        
        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天
            
        Returns:
            IncrementalFinanceSyncResult: 同步结果
        """
        logger.info(f"开始执行财务增量同步任务... 基准日期: {target_date or '今天'}")

        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id="sync_incremental_finance", repo=repo):
                async with SyncUseCaseFactory.create_incremental_finance_use_case() as use_case:
                    result = await use_case.execute(actual_date=target_date)

                    logger.info(
                        f"财务增量同步完成：synced_count={result.synced_count}, "
                        f"failed_count={result.failed_count}, "
                        f"retry_count={result.retry_count}, "
                        f"retry_success_count={result.retry_success_count}, "
                        f"target_period={result.target_period}"
                    )
                    
                    return result

    async def run_concept_sync(self) -> ConceptSyncResult:
        """
        执行概念数据同步（akshare → PostgreSQL）。
        
        Returns:
            ConceptSyncResult: 同步结果
        """
        logger.info("开始执行概念数据同步任务...")

        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id="sync_concept_data", repo=repo):
                container = DataEngineeringContainer()
                
                sync_cmd = SyncConceptDataCmd(
                    concept_provider=container.concept_provider(),
                    concept_repo=container.concept_repository(),
                )
                
                result = await sync_cmd.execute()
                
                logger.info(
                    f"概念数据同步完成：总概念数={result.total_concepts}, "
                    f"成功={result.success_concepts}, 失败={result.failed_concepts}, "
                    f"总成份股={result.total_stocks}, 耗时={result.elapsed_time:.2f}s"
                )
                
                return result

    async def run_akshare_market_data_sync(
        self, target_date: Optional[str] = None
    ) -> dict:
        """
        执行 AkShare 市场数据同步（涨停池、炸板池、龙虎榜等）。
        
        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天
            
        Returns:
            同步结果摘要字典
        """
        from datetime import datetime as dt
        
        logger.info(f"开始执行 AkShare 市场数据同步任务... 目标日期: {target_date or '今天'}")

        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id="sync_akshare_market_data", repo=repo):
                container = DataEngineeringContainer(session)
                sync_cmd = container.get_sync_akshare_market_data_cmd()
                
                # 转换日期格式
                if target_date:
                    trade_date = dt.strptime(target_date, "%Y%m%d").date()
                else:
                    trade_date = dt.now().date()
                
                result = await sync_cmd.execute(trade_date=trade_date)
                
                logger.info(
                    f"AkShare市场数据同步完成：涨停池={result.limit_up_pool_count}, "
                    f"炸板池={result.broken_board_count}, 昨日涨停={result.previous_limit_up_count}, "
                    f"龙虎榜={result.dragon_tiger_count}, 板块资金={result.sector_capital_flow_count}"
                )
                
                return {
                    "trade_date": str(result.trade_date),
                    "limit_up_pool_count": result.limit_up_pool_count,
                    "broken_board_count": result.broken_board_count,
                    "previous_limit_up_count": result.previous_limit_up_count,
                    "dragon_tiger_count": result.dragon_tiger_count,
                    "sector_capital_flow_count": result.sector_capital_flow_count,
                    "errors": result.errors,
                }

    async def run_stock_basic_sync(self) -> dict:
        """
        执行股票基础信息同步（TuShare → PostgreSQL）。
        
        Returns:
            同步结果摘要字典
        """
        logger.info("开始执行股票基础信息同步任务...")

        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id="sync_stock_basic", repo=repo):
                async with SyncUseCaseFactory.create_sync_stock_basic_use_case() as use_case:
                    result = await use_case.execute()
                    
                    logger.info(
                        f"股票基础信息同步完成：synced_count={result.synced_count}, "
                        f"message={result.message}"
                    )
                    
                    return {
                        "synced_count": result.synced_count,
                        "message": result.message,
                        "status": result.status,
                    }

    async def run_daily_history_sync(self) -> SyncTask:
        """
        执行日线历史全量同步（仅供 REST API 调用，不注册到调度器）。
        
        Returns:
            SyncTask: 同步任务对象
        """
        logger.info("开始执行历史日线全量同步任务...")

        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id="sync_daily_history", repo=repo):
                async with SyncUseCaseFactory.create_sync_engine() as engine:
                    config = {
                        "batch_size": de_config.SYNC_DAILY_HISTORY_BATCH_SIZE,
                    }

                    task = await engine.run_history_sync(
                        job_type=SyncJobType.DAILY_HISTORY, config=config
                    )

                    logger.info(
                        f"历史日线同步完成：task_id={task.id}, "
                        f"status={task.status.value}, total_processed={task.total_processed}"
                    )
                    
                    return task

    async def run_finance_history_sync(self) -> SyncTask:
        """
        执行财务历史全量同步（仅供 REST API 调用，不注册到调度器）。
        
        Returns:
            SyncTask: 同步任务对象
        """
        logger.info("开始执行历史财务全量同步任务...")

        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id="sync_history_finance", repo=repo):
                async with SyncUseCaseFactory.create_sync_engine() as engine:
                    config = {
                        "batch_size": de_config.SYNC_FINANCE_HISTORY_BATCH_SIZE,
                        "start_date": de_config.SYNC_FINANCE_HISTORY_START_DATE,
                        "end_date": datetime.now().strftime("%Y%m%d"),
                    }

                    task = await engine.run_history_sync(
                        job_type=SyncJobType.FINANCE_HISTORY, config=config
                    )

                    logger.info(
                        f"历史财务同步完成：task_id={task.id}, "
                        f"status={task.status.value}, total_processed={task.total_processed}"
                    )
                    
                    return task
