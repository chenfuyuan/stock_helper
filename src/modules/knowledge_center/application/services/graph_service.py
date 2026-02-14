"""
图谱服务门面。

聚合图谱同步与查询能力，作为 Presentation 层的统一入口。
"""

from typing import Optional

from loguru import logger

from src.modules.knowledge_center.application.commands.sync_graph_command import (
    SyncGraphCommand,
)
from src.modules.knowledge_center.application.queries.get_stock_graph import (
    GetStockGraphQuery,
)
from src.modules.knowledge_center.application.queries.get_stock_neighbors import (
    GetStockNeighborsQuery,
)
from src.modules.knowledge_center.domain.dtos.graph_query_dtos import (
    StockGraphDTO,
    StockNeighborDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.domain.ports.graph_repository import IGraphRepository


class GraphService:
    """
    图谱服务门面。
    
    聚合同步命令与查询用例，提供统一的服务接口。
    """

    def __init__(
        self,
        graph_repo: IGraphRepository,
        sync_command: SyncGraphCommand,
        neighbors_query: GetStockNeighborsQuery,
        graph_query: GetStockGraphQuery,
    ):
        """
        初始化图谱服务。
        
        Args:
            graph_repo: 图谱仓储接口（Port）
            sync_command: 同步命令用例
            neighbors_query: 同维度查询用例
            graph_query: 关系网络查询用例
        """
        self._graph_repo = graph_repo
        self._sync_command = sync_command
        self._neighbors_query = neighbors_query
        self._graph_query = graph_query

    async def sync_full_graph(
        self,
        include_finance: bool = False,
        batch_size: int = 500,
        skip: int = 0,
        limit: int = 10000,
    ) -> SyncResult:
        """
        全量同步图谱数据。
        
        Args:
            include_finance: 是否包含财务快照
            batch_size: 批量大小
            skip: 跳过前 N 条记录
            limit: 查询数量上限
        
        Returns:
            SyncResult：同步结果摘要
        """
        logger.info("GraphService: 开始全量同步图谱")
        result = await self._sync_command.execute_full_sync(
            include_finance=include_finance,
            batch_size=batch_size,
            skip=skip,
            limit=limit,
        )
        logger.info(f"GraphService: 全量同步完成，成功 {result.success} 条")
        return result

    async def sync_incremental_graph(
        self,
        third_codes: list[str] | None,
        include_finance: bool = False,
        batch_size: int = 500,
        window_days: int = 3,
        limit: int = 10000,
    ) -> SyncResult:
        """
        增量同步指定股票数据。
        
        Args:
            third_codes: 股票代码列表；为空时按时间窗口自动确定
            include_finance: 是否包含财务快照
            batch_size: 批量大小
            window_days: 自动模式下时间窗口天数
            limit: 自动模式下扫描上限
        
        Returns:
            SyncResult：同步结果摘要
        """
        logger.info(f"GraphService: 开始增量同步 {len(third_codes or [])} 只股票")
        result = await self._sync_command.execute_incremental_sync(
            third_codes=third_codes,
            include_finance=include_finance,
            batch_size=batch_size,
            window_days=window_days,
            limit=limit,
        )
        logger.info(f"GraphService: 增量同步完成，成功 {result.success} 条")
        return result

    async def get_stock_neighbors(
        self,
        third_code: str,
        dimension: str,
        limit: int = 20,
    ) -> list[StockNeighborDTO]:
        """
        查询同维度股票。
        
        Args:
            third_code: 股票第三方代码
            dimension: 维度类型（industry/area/market/exchange）
            limit: 返回数量上限
        
        Returns:
            StockNeighborDTO 列表
        """
        logger.info(f"GraphService: 查询 {third_code} 的同{dimension}股票")
        neighbors = await self._neighbors_query.execute(
            third_code=third_code,
            dimension=dimension,
            limit=limit,
        )
        return neighbors

    async def get_stock_graph(
        self,
        third_code: str,
        depth: int = 1,
    ) -> Optional[StockGraphDTO]:
        """
        查询个股关系网络。
        
        Args:
            third_code: 股票第三方代码
            depth: 遍历深度，默认 1
        
        Returns:
            StockGraphDTO 或 None（股票不存在时）
        """
        logger.info(f"GraphService: 查询 {third_code} 的关系网络")
        graph = await self._graph_query.execute(
            third_code=third_code,
            depth=depth,
        )
        return graph
