"""涨停池数据同步 Command。"""

from datetime import date

from loguru import logger

from src.modules.data_engineering.domain.model.limit_up_pool import LimitUpPoolStock
from src.modules.data_engineering.domain.ports.providers.market_sentiment_provider import (
    IMarketSentimentProvider,
)
from src.modules.data_engineering.domain.ports.repositories.limit_up_pool_repo import (
    ILimitUpPoolRepository,
)


class SyncLimitUpPoolCmd:
    """
    同步涨停池数据命令。
    
    从 AkShare 获取涨停池数据并写入 PostgreSQL。
    """

    def __init__(
        self,
        sentiment_provider: IMarketSentimentProvider,
        limit_up_pool_repo: ILimitUpPoolRepository,
    ):
        self.sentiment_provider = sentiment_provider
        self.limit_up_pool_repo = limit_up_pool_repo

    async def execute(self, trade_date: date) -> int:
        """
        执行涨停池数据同步。
        
        Args:
            trade_date: 交易日期
            
        Returns:
            同步条数
            
        Raises:
            Exception: 同步失败时抛出
        """
        logger.info(f"开始同步涨停池数据：{trade_date}")
        
        limit_up_dtos = await self.sentiment_provider.fetch_limit_up_pool(trade_date)
        
        if not limit_up_dtos:
            logger.info(f"涨停池数据为空：{trade_date}")
            return 0
        
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
        
        count = await self.limit_up_pool_repo.save_all(limit_up_entities)
        logger.info(f"涨停池数据同步成功：{count} 条")
        
        return count
