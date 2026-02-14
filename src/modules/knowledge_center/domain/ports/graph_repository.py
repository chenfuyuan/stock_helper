"""
GraphRepository Port 接口。

定义图谱持久化的抽象接口，由 Infrastructure 层的 Neo4j 实现提供具体实现。
"""

from abc import ABC, abstractmethod

from src.modules.knowledge_center.domain.dtos.graph_query_dtos import (
    StockGraphDTO,
    StockNeighborDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import (
    DimensionDTO,
    StockGraphSyncDTO,
    SyncResult,
)


class IGraphRepository(ABC):
    """
    图谱仓储接口。
    
    定义图谱 Schema 管理、节点与关系的批量写入、以及查询能力。
    """

    @abstractmethod
    async def ensure_constraints(self) -> None:
        """
        确保图谱唯一约束存在。
        
        在 Neo4j 中创建以下唯一约束（幂等）：
        - Stock.third_code
        - Industry.name
        - Area.name
        - Market.name
        - Exchange.name
        """

    @abstractmethod
    async def merge_stocks(
        self,
        stocks: list[StockGraphSyncDTO],
        batch_size: int = 500,
    ) -> SyncResult:
        """
        批量写入/更新 Stock 节点及其维度关系。
        
        使用 Cypher UNWIND + MERGE 实现批量写入，确保幂等性。
        自动创建 Industry/Area/Market/Exchange 维度节点并建立关系。
        
        Args:
            stocks: Stock 同步 DTO 列表
            batch_size: 每批提交的记录数，默认 500
        
        Returns:
            SyncResult：包含成功/失败数、耗时与错误详情
        """

    @abstractmethod
    async def merge_dimensions(self, dimensions: list[DimensionDTO]) -> None:
        """
        批量写入/更新维度节点。

        Args:
            dimensions: 维度节点 DTO 列表
        """

    @abstractmethod
    async def find_neighbors(
        self,
        third_code: str,
        dimension: str,
        limit: int = 20,
    ) -> list[StockNeighborDTO]:
        """
        查询与指定股票共享同一维度节点的其他股票。
        
        Args:
            third_code: 股票第三方代码
            dimension: 维度类型，枚举值：industry / area / market / exchange
            limit: 返回数量上限，默认 20
        
        Returns:
            StockNeighborDTO 列表（不包含查询股票自身）
        """

    @abstractmethod
    async def find_stock_graph(
        self,
        third_code: str,
        depth: int = 1,
    ) -> StockGraphDTO | None:
        """
        查询指定股票的关系网络。
        
        返回该股票及其所有直接关联的维度节点和关系（depth=1）。
        
        Args:
            third_code: 股票第三方代码
            depth: 遍历深度，默认 1（MVP 阶段仅支持 1）
        
        Returns:
            StockGraphDTO（包含节点和关系列表），股票不存在时返回 None
        """
