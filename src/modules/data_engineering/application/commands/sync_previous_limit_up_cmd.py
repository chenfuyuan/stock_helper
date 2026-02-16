"""昨日涨停表现数据同步 Command。"""

from datetime import date

from loguru import logger

from src.modules.data_engineering.domain.model.previous_limit_up import PreviousLimitUpStock
from src.modules.data_engineering.domain.ports.providers.market_sentiment_provider import (
    IMarketSentimentProvider,
)
from src.modules.data_engineering.domain.ports.repositories.previous_limit_up_repo import (
    IPreviousLimitUpRepository,
)


class SyncPreviousLimitUpCmd:
    """
    同步昨日涨停表现数据命令。
    
    从 AkShare 获取昨日涨停股票的今日表现并写入 PostgreSQL。
    """

    def __init__(
        self,
        sentiment_provider: IMarketSentimentProvider,
        previous_limit_up_repo: IPreviousLimitUpRepository,
    ):
        self.sentiment_provider = sentiment_provider
        self.previous_limit_up_repo = previous_limit_up_repo

    async def execute(self, trade_date: date) -> int:
        """
        执行昨日涨停表现数据同步。
        
        Args:
            trade_date: 交易日期
            
        Returns:
            同步条数
            
        Raises:
            Exception: 同步失败时抛出
        """
        logger.info(f"开始同步昨日涨停表现数据：{trade_date}")
        
        previous_limit_up_dtos = await self.sentiment_provider.fetch_previous_limit_up(
            trade_date
        )
        
        if not previous_limit_up_dtos:
            logger.info(f"昨日涨停表现数据为空：{trade_date}")
            return 0
        
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
        
        count = await self.previous_limit_up_repo.save_all(previous_limit_up_entities)
        logger.info(f"昨日涨停表现数据同步成功：{count} 条")
        
        return count
