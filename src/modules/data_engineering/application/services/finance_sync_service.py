"""财务数据同步服务。

负责财务数据的同步，包括：
- 财务增量同步（每日新增财务数据）
- 财务历史全量同步（初始化或修复时使用）
"""

from datetime import datetime
from typing import Optional

from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    IncrementalFinanceSyncResult,
)
from src.modules.data_engineering.application.factories.sync_factory import (
    SyncUseCaseFactory,
)
from src.modules.data_engineering.application.services.base import SyncServiceBase
from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.modules.data_engineering.domain.model.sync_task import SyncTask
from src.modules.data_engineering.infrastructure.config import de_config


class FinanceSyncService(SyncServiceBase):
    """
    财务数据同步服务。

    负责财务数据的增量同步和历史全量同步。
    所有方法都继承自基类的 `_execute_with_tracking`，
    自动获得 session 管理、ExecutionTracker 集成和统一日志。

    Example:
        ```python
        service = FinanceSyncService()

        # 执行财务增量同步
        result = await service.run_incremental_sync(target_date="20250215")
        print(f"同步成功: {result.synced_count} 条记录")

        # 执行财务历史全量同步
        task = await service.run_history_sync()
        ```
    """

    def _get_service_name(self) -> str:
        """返回服务名称，用于日志和追踪。"""
        return "FinanceSyncService"

    async def run_incremental_sync(
        self,
        target_date: Optional[str] = None
    ) -> IncrementalFinanceSyncResult:
        """
        执行财务增量同步。

        使用 SyncUseCaseFactory 创建增量同步用例，执行财务增量同步任务。
        自动处理 session 管理、ExecutionTracker 集成和日志记录。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            IncrementalFinanceSyncResult，包含:
            - synced_count: 同步成功的记录数
            - failed_count: 失败的记录数
            - retry_count: 重试次数
            - retry_success_count: 重试成功的次数
            - target_period: 目标同步周期

        Example:
            ```python
            service = FinanceSyncService()
            result = await service.run_incremental_sync(target_date="20250215")
            print(f"同步完成: {result.synced_count} 条记录")
            print(f"失败: {result.failed_count} 条记录")
            ```
        """
        date_str = target_date or datetime.now().strftime("%Y%m%d")

        async def _do_sync() -> IncrementalFinanceSyncResult:
            async with SyncUseCaseFactory.create_incremental_finance_use_case() as use_case:
                return await use_case.execute(actual_date=date_str)

        return await self._execute_with_tracking(
            job_id="sync_incremental_finance",
            operation=_do_sync,
            success_message=(
                f"财务增量同步完成：日期={date_str}"
            ),
        )

    async def run_history_sync(self) -> SyncTask:
        """
        执行财务历史全量同步（仅供 REST API 调用，不注册到调度器）。

        使用 SyncUseCaseFactory 创建同步引擎，执行财务历史全量同步任务。
        适用于初始化数据或修复数据不一致的场景。

        Returns:
            SyncTask 对象，包含:
            - id: 任务 ID
            - status: 任务状态
            - total_processed: 处理的总记录数
            - created_at: 创建时间
            - updated_at: 更新时间

        Example:
            ```python
            service = FinanceSyncService()
            task = await service.run_history_sync()
            print(f"任务状态: {task.status.value}")
            print(f"处理记录: {task.total_processed}")
            ```
        """
        async def _do_sync() -> SyncTask:
            async with SyncUseCaseFactory.create_sync_engine() as engine:
                config = {
                    "batch_size": de_config.SYNC_FINANCE_HISTORY_BATCH_SIZE,
                    "start_date": de_config.SYNC_FINANCE_HISTORY_START_DATE,
                    "end_date": datetime.now().strftime("%Y%m%d"),
                }
                return await engine.run_history_sync(
                    job_type=SyncJobType.FINANCE_HISTORY,
                    config=config,
                )

        return await self._execute_with_tracking(
            job_id="sync_history_finance",
            operation=_do_sync,
            success_message="财务历史全量同步完成",
        )
