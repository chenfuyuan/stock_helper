"""基础数据同步服务。

负责基础数据的同步，包括：
- 概念数据同步（akshare → PostgreSQL）
- 股票基础信息同步（TuShare → PostgreSQL）
"""

from src.modules.data_engineering.application.commands.sync_concept_data_cmd import (
    SyncConceptDataCmd,
)
from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    ConceptSyncResult,
)
from src.modules.data_engineering.application.factories.sync_factory import (
    SyncUseCaseFactory,
)
from src.modules.data_engineering.application.services.base import SyncServiceBase
from src.modules.data_engineering.container import DataEngineeringContainer


class BasicDataSyncService(SyncServiceBase):
    """
    基础数据同步服务。

    负责概念数据同步和股票基础信息同步。
    概念数据从 akshare 获取，股票基础信息从 TuShare 获取，
    都同步到 PostgreSQL。

    所有方法都继承自基类的 `_execute_with_tracking`，
    自动获得 session 管理、ExecutionTracker 集成和统一日志。

    Example:
        ```python
        service = BasicDataSyncService()

        # 执行概念数据同步
        result = await service.run_concept_sync()
        print(f"同步完成: {result.success_concepts}/{result.total_concepts} 个概念")

        # 执行股票基础信息同步
        stock_result = await service.run_stock_basic_sync()
        print(f"同步完成: {stock_result['synced_count']} 条记录")
        ```
    """

    def _get_service_name(self) -> str:
        """返回服务名称，用于日志和追踪。"""
        return "BasicDataSyncService"

    async def run_concept_sync(self) -> ConceptSyncResult:
        """
        执行概念数据同步（akshare → PostgreSQL）。

        使用 DataEngineeringContainer 获取 SyncConceptDataCmd，
        执行概念数据同步任务。同步包括概念列表和每个概念的成份股。

        Returns:
            ConceptSyncResult，包含:
            - total_concepts: 总概念数
            - success_concepts: 成功同步的概念数
            - failed_concepts: 失败的概念数
            - total_stocks: 总成份股数
            - elapsed_time: 耗时（秒）

        Example:
            ```python
            service = BasicDataSyncService()
            result = await service.run_concept_sync()
            print(f"同步完成: {result.success_concepts}/{result.total_concepts} 个概念")
            print(f"总成份股: {result.total_stocks} 只")
            print(f"耗时: {result.elapsed_time:.2f} 秒")
            ```
        """
        async def _do_sync() -> ConceptSyncResult:
            container = DataEngineeringContainer()

            sync_cmd = SyncConceptDataCmd(
                concept_provider=container.concept_provider(),
                concept_repo=container.concept_repository(),
            )

            return await sync_cmd.execute()

        return await self._execute_with_tracking(
            job_id="sync_concept_data",
            operation=_do_sync,
            success_message="概念数据同步完成",
        )

    async def run_stock_basic_sync(self) -> dict:
        """
        执行股票基础信息同步（TuShare → PostgreSQL）。

        使用 SyncUseCaseFactory 创建同步用例，执行股票基础信息同步任务。
        同步包括股票代码、名称、行业、地区等基础信息。

        Returns:
            同步结果摘要字典，包含:
            - synced_count: 同步成功的记录数
            - message: 状态消息
            - status: 状态（success/failed）

        Example:
            ```python
            service = BasicDataSyncService()
            result = await service.run_stock_basic_sync()
            print(f"同步完成: {result['synced_count']} 条记录")
            print(f"状态: {result['status']}")
            ```
        """
        async def _do_sync() -> dict:
            async with SyncUseCaseFactory.create_sync_stock_basic_use_case() as use_case:
                result = await use_case.execute()

                return {
                    "synced_count": result.synced_count,
                    "message": result.message,
                    "status": result.status,
                }

        sync_result = await self._execute_with_tracking(
            job_id="sync_stock_basic",
            operation=_do_sync,
            success_message="股票基础信息同步完成",
        )

        return sync_result
