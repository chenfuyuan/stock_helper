"""日线数据同步服务。

负责日线数据的同步，包括：
- 日线增量同步（每日新增数据）
- 日线历史全量同步（初始化或修复时使用）
"""

from datetime import datetime
from typing import Optional

from src.modules.data_engineering.application.factories.sync_factory import (
    SyncUseCaseFactory,
)
from src.modules.data_engineering.application.services.base import SyncServiceBase
from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.modules.data_engineering.domain.model.sync_task import SyncTask
from src.modules.data_engineering.infrastructure.config import de_config


class DailySyncService(SyncServiceBase):
    """
    日线数据同步服务。

    负责日线数据的增量同步和历史全量同步。
    所有方法都继承自基类的 `_execute_with_tracking`，
    自动获得 session 管理、ExecutionTracker 集成和统一日志。

    Example:
        ```python
        service = DailySyncService()

        # 执行日线增量同步
        result = await service.run_incremental_sync(target_date="20250215")

        # 执行日线历史全量同步
        task = await service.run_history_sync()
        ```
    """

    def _get_service_name(self) -> str:
        """返回服务名称，用于日志和追踪。"""
        return "DailySyncService"

    async def run_incremental_sync(
        self,
        target_date: Optional[str] = None
    ) -> dict:
        """
        执行日线增量同步（含遗漏检测与自动补偿）。

        使用 SyncUseCaseFactory 创建同步引擎，执行日线增量同步任务。
        自动处理 session 管理、ExecutionTracker 集成和日志记录。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            同步结果摘要字典，包含:
            - synced_dates: 同步的日期列表
            - total_count: 同步的总记录数
            - message: 状态消息

        Example:
            ```python
            service = DailySyncService()
            result = await service.run_incremental_sync(target_date="20250215")
            print(f"同步完成: {result['total_count']} 条记录")
            ```
        """
        date_str = target_date or datetime.now().strftime("%Y%m%d")

        async def _do_sync() -> dict:
            async with SyncUseCaseFactory.create_sync_engine() as engine:
                return await engine.run_incremental_daily_sync(target_date=date_str)

        return await self._execute_with_tracking(
            job_id="sync_daily_by_date",
            operation=_do_sync,
            success_message=(
                f"日线增量同步完成：日期={date_str}"
            ),
        )

    async def run_history_sync(self) -> SyncTask:
        """
        执行日线历史全量同步（仅供 REST API 调用，不注册到调度器）。

        使用 SyncUseCaseFactory 创建同步引擎，执行日线历史全量同步任务。
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
            service = DailySyncService()
            task = await service.run_history_sync()
            print(f"任务状态: {task.status.value}")
            print(f"处理记录: {task.total_processed}")
            ```
        """
        async def _do_sync() -> SyncTask:
            async with SyncUseCaseFactory.create_sync_engine() as engine:
                config = {
                    "batch_size": de_config.SYNC_DAILY_HISTORY_BATCH_SIZE,
                }
                return await engine.run_history_sync(
                    job_type=SyncJobType.DAILY_HISTORY,
                    config=config,
                )

        return await self._execute_with_tracking(
            job_id="sync_daily_history",
            operation=_do_sync,
            success_message="日线历史全量同步完成",
        )
