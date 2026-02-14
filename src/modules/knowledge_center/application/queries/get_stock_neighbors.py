"""
查询同维度股票用例。

根据指定维度（行业/地域/市场/交易所）查询与目标股票共享同一维度的其他股票。
"""

from loguru import logger

from src.modules.knowledge_center.domain.dtos.graph_query_dtos import StockNeighborDTO
from src.modules.knowledge_center.domain.ports.graph_repository import IGraphRepository


class GetStockNeighborsQuery:
    """
    查询同维度股票用例。
    
    查询与指定股票共享同一维度节点的其他股票列表。
    """

    def __init__(self, graph_repo: IGraphRepository):
        """
        初始化查询用例。
        
        Args:
            graph_repo: 图谱仓储接口
        """
        self._graph_repo = graph_repo

    async def execute(
        self,
        third_code: str,
        dimension: str,
        limit: int = 20,
        dimension_name: str | None = None,
    ) -> list[StockNeighborDTO]:
        """
        执行同维度股票查询。
        
        Args:
            third_code: 股票第三方代码
            dimension: 维度类型（industry/area/market/exchange/concept）
            limit: 返回数量上限，默认 20
            dimension_name: 维度名称，当 dimension="concept" 时必填
        
        Returns:
            StockNeighborDTO 列表（不包含查询股票自身）
        """
        logger.info(
            f"查询同维度股票: third_code={third_code}, dimension={dimension}, "
            f"dimension_name={dimension_name}, limit={limit}"
        )
        
        neighbors = await self._graph_repo.find_neighbors(
            third_code=third_code,
            dimension=dimension,
            limit=limit,
            dimension_name=dimension_name,
        )
        
        logger.info(f"查询完成，返回 {len(neighbors)} 条同{dimension}股票记录")
        return neighbors
