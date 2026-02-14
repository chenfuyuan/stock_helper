"""
查询个股关系网络用例。

查询指定股票及其关联的维度节点与关系。
"""

from typing import Optional

from loguru import logger

from src.modules.knowledge_center.domain.dtos.graph_query_dtos import StockGraphDTO
from src.modules.knowledge_center.domain.ports.graph_repository import IGraphRepository


class GetStockGraphQuery:
    """
    查询个股关系网络用例。
    
    查询指定股票的关系网络，包含该股票节点及其所有直接关联的维度节点和关系。
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
        depth: int = 1,
    ) -> Optional[StockGraphDTO]:
        """
        执行个股关系网络查询。
        
        Args:
            third_code: 股票第三方代码
            depth: 遍历深度，默认 1（MVP 阶段仅支持 1）
        
        Returns:
            StockGraphDTO（包含节点和关系列表），股票不存在时返回 None
        """
        logger.info(f"查询个股关系网络: third_code={third_code}, depth={depth}")
        
        graph = await self._graph_repo.find_stock_graph(
            third_code=third_code,
            depth=depth,
        )
        
        if graph:
            logger.info(
                f"查询完成，返回 {len(graph.nodes)} 个节点，{len(graph.relationships)} 条关系"
            )
        else:
            logger.warning(f"Stock 节点不存在: third_code={third_code}")
        
        return graph
