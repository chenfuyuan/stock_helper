"""AkShare 市场数据同步服务。

负责 AkShare 市场数据的同步，包括：
- 涨停池数据同步
- 炸板池数据同步
- 昨日涨停表现数据同步
- 龙虎榜数据同步
- 板块资金流向数据同步
"""

from datetime import date, datetime
from typing import Optional

from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    AkShareSyncResult,
)
from src.modules.data_engineering.application.services.base import SyncServiceBase
from src.modules.data_engineering.container import DataEngineeringContainer


class MarketDataSyncService(SyncServiceBase):
    """
    AkShare 市场数据同步服务。

    负责 AkShare 市场数据的同步，包括涨停池、炸板池、昨日涨停、
    龙虎榜、板块资金流向等 5 类数据。

    所有方法都继承自基类的 `_execute_with_tracking`，
    自动获得 session 管理、ExecutionTracker 集成和统一日志。

    错误隔离：单个子任务失败不中断其他任务的执行。

    Example:
        ```python
        service = MarketDataSyncService()

        # 执行市场数据同步
        result = await service.run_sync(target_date="20250215")
        print(f"涨停池: {result.limit_up_pool_count} 条记录")
        print(f"龙虎榜: {result.dragon_tiger_count} 条记录")
        ```
    """

    def _get_service_name(self) -> str:
        """返回服务名称，用于日志和追踪。"""
        return "MarketDataSyncService"

    async def run_sync(
        self,
        target_date: Optional[str] = None
    ) -> AkShareSyncResult:
        """
        执行 AkShare 市场数据同步。

        依次调用 5 个子 Command 完成数据同步，实现错误隔离：
        单个子任务失败不中断其他任务的执行。

        同步的数据类型：
        1. 涨停池数据
        2. 炸板池数据
        3. 昨日涨停表现数据
        4. 龙虎榜数据
        5. 板块资金流向数据

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            AkShareSyncResult，包含:
            - trade_date: 交易日期
            - limit_up_pool_count: 涨停池记录数
            - broken_board_count: 炸板池记录数
            - previous_limit_up_count: 昨日涨停记录数
            - dragon_tiger_count: 龙虎榜记录数
            - sector_capital_flow_count: 板块资金流向记录数
            - errors: 错误列表

        Example:
            ```python
            service = MarketDataSyncService()
            result = await service.run_sync(target_date="20250215")
            print(f"同步完成：涨停池 {result.limit_up_pool_count} 条")
            if result.errors:
                print(f"警告：{len(result.errors)} 个错误")
            ```
        """
        # 转换日期格式
        if target_date:
            trade_date = datetime.strptime(target_date, "%Y%m%d").date()
        else:
            trade_date = datetime.now().date()

        async def _do_sync() -> AkShareSyncResult:
            # 使用 Container 获取 Command
            container = DataEngineeringContainer()
            sync_cmd = container.get_sync_akshare_market_data_cmd()

            # 执行同步
            return await sync_cmd.execute(trade_date=trade_date)

        return await self._execute_with_tracking(
            job_id="sync_akshare_market_data",
            operation=_do_sync,
            success_message=(
                f"AkShare 市场数据同步完成：日期={trade_date}"
            ),
        )
