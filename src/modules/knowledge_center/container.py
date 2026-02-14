"""
Knowledge Center 模块依赖注入容器。

集中管理模块内所有组件的依赖关系与生命周期。
"""

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    GetFinanceForTickerUseCase,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_finance_repo import (
    StockFinanceRepositoryImpl,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import (
    StockRepositoryImpl,
)

from src.modules.knowledge_center.application.commands.sync_graph_command import (
    SyncGraphCommand,
)
from src.modules.knowledge_center.application.queries.get_stock_graph import (
    GetStockGraphQuery,
)
from src.modules.knowledge_center.application.queries.get_stock_neighbors import (
    GetStockNeighborsQuery,
)
from src.modules.knowledge_center.application.services.graph_service import GraphService
from src.modules.knowledge_center.infrastructure.adapters.data_engineering_adapter import (
    DataEngineeringAdapter,
)
from src.modules.knowledge_center.infrastructure.config import neo4j_config

if TYPE_CHECKING:
    from neo4j import Driver

    from src.modules.knowledge_center.infrastructure.persistence.neo4j_graph_repository import (
        Neo4jGraphRepository,
    )


@lru_cache(maxsize=1)
def _get_neo4j_driver() -> Any:
    """获取全局 Neo4j Driver（进程内单例）。"""
    from src.modules.knowledge_center.infrastructure.persistence.neo4j_driver_factory import (
        create_neo4j_driver,
    )

    return create_neo4j_driver(neo4j_config)


def close_knowledge_center_driver() -> None:
    """关闭全局 Neo4j Driver（应用 shutdown 时调用）。"""
    _get_neo4j_driver().close()
    _get_neo4j_driver.cache_clear()


class KnowledgeCenterContainer:
    """
    Knowledge Center 模块依赖注入容器。
    
    注册所有组件并管理依赖关系。
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        from src.modules.knowledge_center.infrastructure.persistence.neo4j_graph_repository import (
            Neo4jGraphRepository,
        )

        self._session = session
        self._driver = _get_neo4j_driver()
        self._graph_repository = Neo4jGraphRepository(driver=self._driver)

    def graph_repository(self) -> "Neo4jGraphRepository":
        """返回图谱仓储实现。"""
        return self._graph_repository

    def data_engineering_adapter(self) -> DataEngineeringAdapter:
        """组装 DataEngineeringAdapter（依赖请求级 DB session）。"""
        if self._session is None:
            raise RuntimeError(
                "KnowledgeCenterContainer 需要 session 才能提供 data_engineering_adapter"
            )
        stock_repo = StockRepositoryImpl(self._session)
        finance_repo = StockFinanceRepositoryImpl(self._session)
        finance_use_case = GetFinanceForTickerUseCase(financial_repo=finance_repo)
        return DataEngineeringAdapter(
            stock_repo=stock_repo,
            get_finance_use_case=finance_use_case,
        )

    def sync_graph_command(self) -> SyncGraphCommand:
        """组装图谱同步命令。"""
        return SyncGraphCommand(
            graph_repo=self.graph_repository(),
            data_adapter=self.data_engineering_adapter(),
        )

    def get_stock_neighbors_query(self) -> GetStockNeighborsQuery:
        """组装同维度股票查询用例。"""
        return GetStockNeighborsQuery(graph_repo=self.graph_repository())

    def get_stock_graph_query(self) -> GetStockGraphQuery:
        """组装个股关系网络查询用例。"""
        return GetStockGraphQuery(graph_repo=self.graph_repository())

    def graph_service(self) -> GraphService:
        """组装图谱门面服务。"""
        return GraphService(
            graph_repo=self.graph_repository(),
            sync_command=self.sync_graph_command(),
            neighbors_query=self.get_stock_neighbors_query(),
            graph_query=self.get_stock_graph_query(),
        )
