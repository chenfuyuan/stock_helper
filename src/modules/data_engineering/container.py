"""
数据工程模块 Composition Root。

统一封装日线、财务、股票基础信息、估值日线等 UseCase 的组装逻辑，
供 Research 等模块通过本 Container 获取 Application 层能力，不直接依赖 Infrastructure 实现。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.application.commands.sync_akshare_market_data_cmd import (
    SyncAkShareMarketDataCmd,
)
from src.modules.data_engineering.application.commands.sync_broken_board_cmd import (
    SyncBrokenBoardCmd,
)
from src.modules.data_engineering.application.commands.sync_concept_data_cmd import (
    SyncConceptDataCmd,
)
from src.modules.data_engineering.application.commands.sync_dragon_tiger_cmd import (
    SyncDragonTigerCmd,
)
from src.modules.data_engineering.application.commands.sync_limit_up_pool_cmd import (
    SyncLimitUpPoolCmd,
)
from src.modules.data_engineering.application.commands.sync_previous_limit_up_cmd import (
    SyncPreviousLimitUpCmd,
)
from src.modules.data_engineering.application.commands.sync_sector_capital_flow_cmd import (
    SyncSectorCapitalFlowCmd,
)
from src.modules.data_engineering.application.queries.get_broken_board_by_date import (
    GetBrokenBoardByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_daily_bars_by_date import (
    GetDailyBarsByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_daily_bars_for_ticker import (
    GetDailyBarsForTickerUseCase,
)
from src.modules.data_engineering.application.queries.get_dragon_tiger_by_date import (
    GetDragonTigerByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    GetFinanceForTickerUseCase,
)
from src.modules.data_engineering.application.queries.get_limit_up_pool_by_date import (
    GetLimitUpPoolByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_previous_limit_up_by_date import (
    GetPreviousLimitUpByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_sector_capital_flow_by_date import (
    GetSectorCapitalFlowByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_stock_basic_info import (
    GetStockBasicInfoUseCase,
)
from src.modules.data_engineering.application.queries.get_valuation_dailies_for_ticker import (
    GetValuationDailiesForTickerUseCase,
)
from src.modules.data_engineering.domain.ports.providers.concept_data_provider import (
    IConceptDataProvider,
)
from src.modules.data_engineering.domain.ports.providers.dragon_tiger_provider import (
    IDragonTigerProvider,
)
from src.modules.data_engineering.domain.ports.providers.market_sentiment_provider import (
    IMarketSentimentProvider,
)
from src.modules.data_engineering.domain.ports.providers.sector_capital_flow_provider import (
    ISectorCapitalFlowProvider,
)
from src.modules.data_engineering.domain.ports.repositories.broken_board_repo import (
    IBrokenBoardRepository,
)
from src.modules.data_engineering.domain.ports.repositories.concept_repo import (
    IConceptRepository,
)
from src.modules.data_engineering.domain.ports.repositories.dragon_tiger_repo import (
    IDragonTigerRepository,
)
from src.modules.data_engineering.domain.ports.repositories.limit_up_pool_repo import (
    ILimitUpPoolRepository,
)
from src.modules.data_engineering.domain.ports.repositories.previous_limit_up_repo import (
    IPreviousLimitUpRepository,
)
from src.modules.data_engineering.domain.ports.repositories.sector_capital_flow_repo import (
    ISectorCapitalFlowRepository,
)
from src.modules.data_engineering.infrastructure.external_apis.akshare.client import (
    AkShareConceptClient,
)
from src.modules.data_engineering.infrastructure.external_apis.akshare.market_data_client import (
    AkShareMarketDataClient,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_broken_board_repo import (
    PgBrokenBoardRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_concept_repo import (
    PgConceptRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_dragon_tiger_repo import (
    PgDragonTigerRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_limit_up_pool_repo import (
    PgLimitUpPoolRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_previous_limit_up_repo import (
    PgPreviousLimitUpRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_sector_capital_flow_repo import (
    PgSectorCapitalFlowRepository,
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
        
        # 概念数据相关组件
        self._concept_provider: IConceptDataProvider = AkShareConceptClient(request_interval=0.3)
        self._concept_repo: IConceptRepository = PgConceptRepository(session)
        
        # AkShare 市场数据相关组件
        self._akshare_market_data_client = AkShareMarketDataClient(request_interval=0.3)
        self._sentiment_provider: IMarketSentimentProvider = self._akshare_market_data_client
        self._dragon_tiger_provider: IDragonTigerProvider = self._akshare_market_data_client
        self._capital_flow_provider: ISectorCapitalFlowProvider = self._akshare_market_data_client
        
        # AkShare 市场数据 Repositories
        self._limit_up_pool_repo: ILimitUpPoolRepository = PgLimitUpPoolRepository(session)
        self._broken_board_repo: IBrokenBoardRepository = PgBrokenBoardRepository(session)
        self._previous_limit_up_repo: IPreviousLimitUpRepository = PgPreviousLimitUpRepository(
            session
        )
        self._dragon_tiger_repo: IDragonTigerRepository = PgDragonTigerRepository(session)
        self._sector_capital_flow_repo: ISectorCapitalFlowRepository = (
            PgSectorCapitalFlowRepository(session)
        )

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

    def get_concept_repository(self) -> IConceptRepository:
        """获取概念数据仓储实例，供 KC 模块使用。"""
        return self._concept_repo

    def get_sync_concept_data_cmd(self) -> SyncConceptDataCmd:
        """组装概念数据同步命令。"""
        return SyncConceptDataCmd(
            concept_provider=self._concept_provider,
            concept_repo=self._concept_repo,
        )

    def get_daily_bars_by_date_use_case(self) -> GetDailyBarsByDateUseCase:
        """组装按日期查询全市场日线的 UseCase。"""
        return GetDailyBarsByDateUseCase(market_quote_repo=self._market_quote_repo)
    
    def get_sync_akshare_market_data_cmd(self) -> SyncAkShareMarketDataCmd:
        """组装 AkShare 市场数据同步命令。"""
        return SyncAkShareMarketDataCmd(
            sentiment_provider=self._sentiment_provider,
            dragon_tiger_provider=self._dragon_tiger_provider,
            capital_flow_provider=self._capital_flow_provider,
            limit_up_pool_repo=self._limit_up_pool_repo,
            broken_board_repo=self._broken_board_repo,
            previous_limit_up_repo=self._previous_limit_up_repo,
            dragon_tiger_repo=self._dragon_tiger_repo,
            sector_capital_flow_repo=self._sector_capital_flow_repo,
        )
    
    def get_limit_up_pool_by_date_use_case(self) -> GetLimitUpPoolByDateUseCase:
        """组装按日期查询涨停池的 UseCase。"""
        return GetLimitUpPoolByDateUseCase(limit_up_pool_repo=self._limit_up_pool_repo)
    
    def get_broken_board_by_date_use_case(self) -> GetBrokenBoardByDateUseCase:
        """组装按日期查询炸板池的 UseCase。"""
        return GetBrokenBoardByDateUseCase(broken_board_repo=self._broken_board_repo)
    
    def get_previous_limit_up_by_date_use_case(self) -> GetPreviousLimitUpByDateUseCase:
        """组装按日期查询昨日涨停表现的 UseCase。"""
        return GetPreviousLimitUpByDateUseCase(
            previous_limit_up_repo=self._previous_limit_up_repo
        )
    
    def get_dragon_tiger_by_date_use_case(self) -> GetDragonTigerByDateUseCase:
        """组装按日期查询龙虎榜的 UseCase。"""
        return GetDragonTigerByDateUseCase(dragon_tiger_repo=self._dragon_tiger_repo)
    
    def get_sector_capital_flow_by_date_use_case(self) -> GetSectorCapitalFlowByDateUseCase:
        """组装按日期查询板块资金流向的 UseCase。"""
        return GetSectorCapitalFlowByDateUseCase(
            sector_capital_flow_repo=self._sector_capital_flow_repo
        )
    
    def get_sync_limit_up_pool_cmd(self) -> SyncLimitUpPoolCmd:
        """组装涨停池数据同步命令。"""
        return SyncLimitUpPoolCmd(
            sentiment_provider=self._sentiment_provider,
            limit_up_pool_repo=self._limit_up_pool_repo,
        )
    
    def get_sync_broken_board_cmd(self) -> SyncBrokenBoardCmd:
        """组装炸板池数据同步命令。"""
        return SyncBrokenBoardCmd(
            sentiment_provider=self._sentiment_provider,
            broken_board_repo=self._broken_board_repo,
        )
    
    def get_sync_previous_limit_up_cmd(self) -> SyncPreviousLimitUpCmd:
        """组装昨日涨停表现数据同步命令。"""
        return SyncPreviousLimitUpCmd(
            sentiment_provider=self._sentiment_provider,
            previous_limit_up_repo=self._previous_limit_up_repo,
        )
    
    def get_sync_dragon_tiger_cmd(self) -> SyncDragonTigerCmd:
        """组装龙虎榜数据同步命令。"""
        return SyncDragonTigerCmd(
            dragon_tiger_provider=self._dragon_tiger_provider,
            dragon_tiger_repo=self._dragon_tiger_repo,
        )
    
    def get_sync_sector_capital_flow_cmd(self) -> SyncSectorCapitalFlowCmd:
        """组装板块资金流向数据同步命令。"""
        return SyncSectorCapitalFlowCmd(
            capital_flow_provider=self._capital_flow_provider,
            sector_capital_flow_repo=self._sector_capital_flow_repo,
        )
