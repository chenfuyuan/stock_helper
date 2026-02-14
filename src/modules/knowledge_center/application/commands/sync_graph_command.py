"""
同步图谱命令用例。

编排从 data_engineering 读取数据、转换并写入 Neo4j 图谱的完整流程。
"""

from loguru import logger

from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.domain.ports.graph_repository import IGraphRepository
from src.modules.knowledge_center.infrastructure.adapters.data_engineering_adapter import (
    DataEngineeringAdapter,
)


class SyncGraphCommand:
    """
    同步图谱命令用例。
    
    全量或增量同步股票数据到 Neo4j 图谱：
    1. 通过 DataEngineeringAdapter 从 data_engineering 模块获取数据
    2. 将数据转换为 StockGraphSyncDTO
    3. 调用 GraphRepository.merge_stocks 批量写入 Neo4j
    """

    def __init__(
        self,
        graph_repo: IGraphRepository,
        data_adapter: DataEngineeringAdapter,
    ):
        """
        初始化同步命令用例。
        
        Args:
            graph_repo: 图谱仓储接口
            data_adapter: Data Engineering 适配器
        """
        self._graph_repo = graph_repo
        self._data_adapter = data_adapter

    async def execute_full_sync(
        self,
        include_finance: bool = False,
        batch_size: int = 500,
        skip: int = 0,
        limit: int = 10000,
    ) -> SyncResult:
        """
        执行全量同步。
        
        Args:
            include_finance: 是否包含财务快照数据
            batch_size: 每批提交的记录数
            skip: 跳过前 N 条记录
            limit: 查询数量上限
        
        Returns:
            SyncResult：同步结果摘要
        """
        logger.info(
            f"开始全量同步图谱数据: include_finance={include_finance}, batch_size={batch_size}, skip={skip}, limit={limit}"  # noqa: E501
        )
        
        # 1. 从 data_engineering 获取数据
        stocks = await self._data_adapter.fetch_all_stocks_for_sync(
            include_finance=include_finance,
            skip=skip,
            limit=limit,
        )
        
        if not stocks:
            logger.warning("未获取到股票数据，跳过同步")
            return SyncResult(
                total=0,
                success=0,
                failed=0,
                duration_ms=0.0,
                error_details=[],
            )
        
        # 2. 确保图谱约束存在（幂等）
        await self._graph_repo.ensure_constraints()
        
        # 3. 批量写入 Neo4j
        result = await self._graph_repo.merge_stocks(
            stocks=stocks,
            batch_size=batch_size,
        )
        
        logger.info(
            f"全量同步完成: total={result.total}, success={result.success}, failed={result.failed}, duration={result.duration_ms:.2f}ms"  # noqa: E501
        )
        
        return result

    async def execute_incremental_sync(
        self,
        third_codes: list[str] | None,
        include_finance: bool = False,
        batch_size: int = 500,
        window_days: int = 3,
        limit: int = 10000,
    ) -> SyncResult:
        """
        执行增量同步（指定股票代码列表）。
        
        Args:
            third_codes: 股票代码列表；为空时按时间窗口自动确定
            include_finance: 是否包含财务快照数据
            batch_size: 每批提交的记录数
            window_days: 自动模式下时间窗口天数
            limit: 自动模式下扫描上限
        
        Returns:
            SyncResult：同步结果摘要
        """
        logger.info(
            f"开始增量同步图谱数据: codes={len(third_codes or [])}, include_finance={include_finance}, batch_size={batch_size}, window_days={window_days}, limit={limit}"  # noqa: E501
        )

        # 1. 从 data_engineering 获取增量数据（显式代码或时间窗口）
        stocks = await self._data_adapter.fetch_stocks_for_incremental_sync(
            third_codes=third_codes,
            include_finance=include_finance,
            window_days=window_days,
            limit=limit,
        )
        
        if not stocks:
            logger.warning("未获取到指定股票数据，跳过同步")
            return SyncResult(
                total=0,
                success=0,
                failed=0,
                duration_ms=0.0,
                error_details=[],
            )
        
        # 2. 确保图谱约束存在（幂等）
        await self._graph_repo.ensure_constraints()
        
        # 3. 批量写入 Neo4j
        result = await self._graph_repo.merge_stocks(
            stocks=stocks,
            batch_size=batch_size,
        )
        
        logger.info(
            f"增量同步完成: total={result.total}, success={result.success}, failed={result.failed}, duration={result.duration_ms:.2f}ms"  # noqa: E501
        )
        
        return result
