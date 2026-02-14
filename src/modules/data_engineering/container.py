"""
数据工程模块 Composition Root。

统一封装日线、财务、股票基础信息、估值日线等 UseCase 的组装逻辑，
供 Research 等模块通过本 Container 获取 Application 层能力，不直接依赖 Infrastructure 实现。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.application.queries.get_daily_bars_for_ticker import (
    GetDailyBarsForTickerUseCase,
)
from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    GetFinanceForTickerUseCase,
)
from src.modules.data_engineering.application.queries.get_stock_basic_info import (
    GetStockBasicInfoUseCase,
)
from src.modules.data_engineering.application.queries.get_valuation_dailies_for_ticker import (
    GetValuationDailiesForTickerUseCase,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_finance_repo import (
    StockFinanceRepositoryImpl,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import (
    StockDailyRepositoryImpl,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import (
    StockRepositoryImpl,
)


class DataEngineeringContainer:
    """数据工程模块的依赖组装容器。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._market_quote_repo = StockDailyRepositoryImpl(session)
        self._financial_repo = StockFinanceRepositoryImpl(session)
        self._stock_repo = StockRepositoryImpl(session)

    def get_daily_bars_use_case(self) -> GetDailyBarsForTickerUseCase:
        """组装按标的查询日线的 UseCase。"""
        return GetDailyBarsForTickerUseCase(market_quote_repo=self._market_quote_repo)

    def get_finance_use_case(self) -> GetFinanceForTickerUseCase:
        """组装按标的查询财务数据的 UseCase。"""
        return GetFinanceForTickerUseCase(financial_repo=self._financial_repo)

    def get_stock_basic_info_use_case(self) -> GetStockBasicInfoUseCase:
        """组装获取股票基础信息（含最新行情）的 UseCase。"""
        return GetStockBasicInfoUseCase(
            stock_repo=self._stock_repo,
            daily_repo=self._market_quote_repo,
        )

    def get_valuation_dailies_use_case(
        self,
    ) -> GetValuationDailiesForTickerUseCase:
        """组装按标的查询估值日线的 UseCase。"""
        return GetValuationDailiesForTickerUseCase(market_quote_repo=self._market_quote_repo)
