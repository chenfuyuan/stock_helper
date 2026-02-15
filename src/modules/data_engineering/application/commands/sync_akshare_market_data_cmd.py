from dataclasses import dataclass
from datetime import date

from loguru import logger

from src.modules.data_engineering.domain.model.broken_board import BrokenBoardStock
from src.modules.data_engineering.domain.model.dragon_tiger import DragonTigerDetail
from src.modules.data_engineering.domain.model.limit_up_pool import LimitUpPoolStock
from src.modules.data_engineering.domain.model.previous_limit_up import PreviousLimitUpStock
from src.modules.data_engineering.domain.model.sector_capital_flow import SectorCapitalFlow
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
from src.shared.application.use_cases import BaseUseCase


@dataclass
class AkShareSyncResult:
    """AkShare 市场数据同步结果"""

    trade_date: date
    limit_up_pool_count: int
    broken_board_count: int
    previous_limit_up_count: int
    dragon_tiger_count: int
    sector_capital_flow_count: int
    errors: list[str]


class SyncAkShareMarketDataCmd(BaseUseCase):
    """
    同步 AkShare 市场数据命令
    从 AkShare 获取市场情绪与资金数据并写入 PostgreSQL
    
    执行流程（错误隔离）：
    1. 获取涨停池数据
    2. 获取炸板池数据
    3. 获取昨日涨停表现数据
    4. 获取龙虎榜数据
    5. 获取板块资金流向数据
    单类数据失败不中断其他类型的同步
    """

    def __init__(
        self,
        sentiment_provider: IMarketSentimentProvider,
        dragon_tiger_provider: IDragonTigerProvider,
        capital_flow_provider: ISectorCapitalFlowProvider,
        limit_up_pool_repo: ILimitUpPoolRepository,
        broken_board_repo: IBrokenBoardRepository,
        previous_limit_up_repo: IPreviousLimitUpRepository,
        dragon_tiger_repo: IDragonTigerRepository,
        sector_capital_flow_repo: ISectorCapitalFlowRepository,
    ):
        self.sentiment_provider = sentiment_provider
        self.dragon_tiger_provider = dragon_tiger_provider
        self.capital_flow_provider = capital_flow_provider
        self.limit_up_pool_repo = limit_up_pool_repo
        self.broken_board_repo = broken_board_repo
        self.previous_limit_up_repo = previous_limit_up_repo
        self.dragon_tiger_repo = dragon_tiger_repo
        self.sector_capital_flow_repo = sector_capital_flow_repo

    async def execute(self, trade_date: date) -> AkShareSyncResult:
        """
        执行 AkShare 市场数据同步
        
        Args:
            trade_date: 交易日期
            
        Returns:
            AkShareSyncResult: 同步结果摘要
        """
        logger.info(f"开始同步 AkShare 市场数据：{trade_date}")

        errors = []
        limit_up_pool_count = 0
        broken_board_count = 0
        previous_limit_up_count = 0
        dragon_tiger_count = 0
        sector_capital_flow_count = 0

        # 1. 同步涨停池数据
        try:
            limit_up_dtos = await self.sentiment_provider.fetch_limit_up_pool(trade_date)
            if limit_up_dtos:
                limit_up_entities = [
                    LimitUpPoolStock(
                        trade_date=trade_date,
                        third_code=dto.third_code,
                        stock_name=dto.stock_name,
                        pct_chg=dto.pct_chg,
                        close=dto.close,
                        amount=dto.amount,
                        turnover_rate=dto.turnover_rate,
                        consecutive_boards=dto.consecutive_boards,
                        first_limit_up_time=dto.first_limit_up_time,
                        last_limit_up_time=dto.last_limit_up_time,
                        industry=dto.industry,
                    )
                    for dto in limit_up_dtos
                ]
                limit_up_pool_count = await self.limit_up_pool_repo.save_all(limit_up_entities)
                logger.info(f"涨停池数据同步成功：{limit_up_pool_count} 条")
        except Exception as e:
            error_msg = f"涨停池数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 2. 同步炸板池数据
        try:
            broken_board_dtos = await self.sentiment_provider.fetch_broken_board_pool(trade_date)
            if broken_board_dtos:
                broken_board_entities = [
                    BrokenBoardStock(
                        trade_date=trade_date,
                        third_code=dto.third_code,
                        stock_name=dto.stock_name,
                        pct_chg=dto.pct_chg,
                        close=dto.close,
                        amount=dto.amount,
                        turnover_rate=dto.turnover_rate,
                        open_count=dto.open_count,
                        first_limit_up_time=dto.first_limit_up_time,
                        last_open_time=dto.last_open_time,
                        industry=dto.industry,
                    )
                    for dto in broken_board_dtos
                ]
                broken_board_count = await self.broken_board_repo.save_all(broken_board_entities)
                logger.info(f"炸板池数据同步成功：{broken_board_count} 条")
        except Exception as e:
            error_msg = f"炸板池数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 3. 同步昨日涨停表现数据
        try:
            previous_limit_up_dtos = await self.sentiment_provider.fetch_previous_limit_up(
                trade_date
            )
            if previous_limit_up_dtos:
                previous_limit_up_entities = [
                    PreviousLimitUpStock(
                        trade_date=trade_date,
                        third_code=dto.third_code,
                        stock_name=dto.stock_name,
                        pct_chg=dto.pct_chg,
                        close=dto.close,
                        amount=dto.amount,
                        turnover_rate=dto.turnover_rate,
                        yesterday_consecutive_boards=dto.yesterday_consecutive_boards,
                        industry=dto.industry,
                    )
                    for dto in previous_limit_up_dtos
                ]
                previous_limit_up_count = await self.previous_limit_up_repo.save_all(
                    previous_limit_up_entities
                )
                logger.info(f"昨日涨停表现数据同步成功：{previous_limit_up_count} 条")
        except Exception as e:
            error_msg = f"昨日涨停表现数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 4. 同步龙虎榜数据
        try:
            dragon_tiger_dtos = await self.dragon_tiger_provider.fetch_dragon_tiger_detail(
                trade_date
            )
            if dragon_tiger_dtos:
                dragon_tiger_entities = [
                    DragonTigerDetail(
                        trade_date=trade_date,
                        third_code=dto.third_code,
                        stock_name=dto.stock_name,
                        pct_chg=dto.pct_chg,
                        close=dto.close,
                        reason=dto.reason,
                        net_amount=dto.net_amount,
                        buy_amount=dto.buy_amount,
                        sell_amount=dto.sell_amount,
                        buy_seats=dto.buy_seats,
                        sell_seats=dto.sell_seats,
                    )
                    for dto in dragon_tiger_dtos
                ]
                dragon_tiger_count = await self.dragon_tiger_repo.save_all(dragon_tiger_entities)
                logger.info(f"龙虎榜数据同步成功：{dragon_tiger_count} 条")
        except Exception as e:
            error_msg = f"龙虎榜数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # 5. 同步板块资金流向数据
        try:
            capital_flow_dtos = await self.capital_flow_provider.fetch_sector_capital_flow()
            if capital_flow_dtos:
                capital_flow_entities = [
                    SectorCapitalFlow(
                        trade_date=trade_date,
                        sector_name=dto.sector_name,
                        sector_type=dto.sector_type,
                        net_amount=dto.net_amount,
                        inflow_amount=dto.inflow_amount,
                        outflow_amount=dto.outflow_amount,
                        pct_chg=dto.pct_chg,
                    )
                    for dto in capital_flow_dtos
                ]
                sector_capital_flow_count = await self.sector_capital_flow_repo.save_all(
                    capital_flow_entities
                )
                logger.info(f"板块资金流向数据同步成功：{sector_capital_flow_count} 条")
        except Exception as e:
            error_msg = f"板块资金流向数据同步失败：{str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        logger.info(
            f"AkShare 市场数据同步完成：{trade_date}，"
            f"涨停池 {limit_up_pool_count}，炸板池 {broken_board_count}，"
            f"昨日涨停 {previous_limit_up_count}，龙虎榜 {dragon_tiger_count}，"
            f"资金流向 {sector_capital_flow_count}，错误 {len(errors)}"
        )

        return AkShareSyncResult(
            trade_date=trade_date,
            limit_up_pool_count=limit_up_pool_count,
            broken_board_count=broken_board_count,
            previous_limit_up_count=previous_limit_up_count,
            dragon_tiger_count=dragon_tiger_count,
            sector_capital_flow_count=sector_capital_flow_count,
            errors=errors,
        )
