"""数据同步应用服务——统一编排所有数据同步任务。

⚠️ 已弃用: 此类已拆分为专门的 Service:
- DailySyncService: 日线数据同步
- FinanceSyncService: 财务数据同步
- MarketDataSyncService: AkShare 市场数据同步
- BasicDataSyncService: 基础数据同步

此类现在仅作为兼容层，方法委托给上述专门 Service。
请直接调用专门的 Service。

封装 session 管理、Container/Factory 构建、ExecutionTracker 集成、日期转换等编排逻辑，
对 Presentation 层暴露简单的异步方法。
"""

import warnings
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
from src.modules.data_engineering.application.services.basic_data_sync_service import (
    BasicDataSyncService,
)
from src.modules.data_engineering.application.services.daily_sync_service import (
    DailySyncService,
)
from src.modules.data_engineering.application.services.finance_sync_service import (
    FinanceSyncService,
)
from src.modules.data_engineering.application.services.market_data_sync_service import (
    MarketDataSyncService,
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
    数据同步应用服务（已弃用）。

    ⚠️ 已弃用: 此类已拆分为专门的 Service:
    - DailySyncService: 日线数据同步
    - FinanceSyncService: 财务数据同步
    - MarketDataSyncService: AkShare 市场数据同步
    - BasicDataSyncService: 基础数据同步

    此类现在仅作为兼容层，方法委托给上述专门 Service。
    请直接调用专门的 Service。

    统一编排所有同步 Job 的编排逻辑（session 管理、Container/Factory 构建、
    ExecutionTracker 集成、日期转换），对外暴露简单的异步方法。
    """

    def __init__(self):
        """
        初始化数据同步应用服务。

        发出弃用警告，并初始化委托的专门 Service。
        """
        warnings.warn(
            "DataSyncApplicationService is deprecated. "
            "Use DailySyncService, FinanceSyncService, MarketDataSyncService, "
            "or BasicDataSyncService directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._daily_service = DailySyncService()
        self._finance_service = FinanceSyncService()
        self._market_data_service = MarketDataSyncService()
        self._basic_data_service = BasicDataSyncService()
        self._logger = logger.bind(service="DataSyncApplicationService")

    async def run_daily_incremental_sync(self, target_date: Optional[str] = None) -> dict:
        """
        执行日线增量同步（含遗漏检测与自动补偿）。

        ⚠️ 已弃用: 此方法委托给 DailySyncService.run_incremental_sync。
        请直接调用 DailySyncService。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            同步结果摘要字典
        """
        self._logger.warning(
            "DataSyncApplicationService.run_daily_incremental_sync is deprecated. "
            "Use DailySyncService.run_incremental_sync directly."
        )
        return await self._daily_service.run_incremental_sync(target_date)

    async def run_incremental_finance_sync(
        self, target_date: Optional[str] = None
    ) -> IncrementalFinanceSyncResult:
        """
        执行财务增量同步。

        ⚠️ 已弃用: 此方法委托给 FinanceSyncService.run_incremental_sync。
        请直接调用 FinanceSyncService。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            IncrementalFinanceSyncResult: 同步结果
        """
        self._logger.warning(
            "DataSyncApplicationService.run_incremental_finance_sync is deprecated. "
            "Use FinanceSyncService.run_incremental_sync directly."
        )
        return await self._finance_service.run_incremental_sync(target_date)

    async def run_concept_sync(self) -> ConceptSyncResult:
        """
        执行概念数据同步（akshare → PostgreSQL）。

        ⚠️ 已弃用: 此方法委托给 BasicDataSyncService.run_concept_sync。
        请直接调用 BasicDataSyncService。

        Returns:
            ConceptSyncResult: 同步结果
        """
        self._logger.warning(
            "DataSyncApplicationService.run_concept_sync is deprecated. "
            "Use BasicDataSyncService.run_concept_sync directly."
        )
        return await self._basic_data_service.run_concept_sync()

    async def run_akshare_market_data_sync(
        self, target_date: Optional[str] = None
    ) -> dict:
        """
        执行 AkShare 市场数据同步（涨停池、炸板池、龙虎榜等）。

        ⚠️ 已弃用: 此方法委托给 MarketDataSyncService.run_sync。
        请直接调用 MarketDataSyncService。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            同步结果摘要字典
        """
        self._logger.warning(
            "DataSyncApplicationService.run_akshare_market_data_sync is deprecated. "
            "Use MarketDataSyncService.run_sync directly."
        )
        result = await self._market_data_service.run_sync(target_date)

        # 保持与原方法相同的返回格式
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

        ⚠️ 已弃用: 此方法委托给 BasicDataSyncService.run_stock_basic_sync。
        请直接调用 BasicDataSyncService。

        Returns:
            同步结果摘要字典
        """
        self._logger.warning(
            "DataSyncApplicationService.run_stock_basic_sync is deprecated. "
            "Use BasicDataSyncService.run_stock_basic_sync directly."
        )
        return await self._basic_data_service.run_stock_basic_sync()

    async def run_daily_history_sync(self) -> SyncTask:
        """
        执行日线历史全量同步（仅供 REST API 调用，不注册到调度器）。

        ⚠️ 已弃用: 此方法委托给 DailySyncService.run_history_sync。
        请直接调用 DailySyncService。

        Returns:
            SyncTask: 同步任务对象
        """
        self._logger.warning(
            "DataSyncApplicationService.run_daily_history_sync is deprecated. "
            "Use DailySyncService.run_history_sync directly."
        )
        return await self._daily_service.run_history_sync()

    async def run_finance_history_sync(self) -> SyncTask:
        """
        执行财务历史全量同步（仅供 REST API 调用，不注册到调度器）。

        ⚠️ 已弃用: 此方法委托给 FinanceSyncService.run_history_sync。
        请直接调用 FinanceSyncService。

        Returns:
            SyncTask: 同步任务对象
        """
        self._logger.warning(
            "DataSyncApplicationService.run_finance_history_sync is deprecated. "
            "Use FinanceSyncService.run_history_sync directly."
        )
        return await self._finance_service.run_history_sync()
