"""炸板池数据同步 Command。"""

from datetime import date

from loguru import logger

from src.modules.data_engineering.domain.model.broken_board import BrokenBoardStock
from src.modules.data_engineering.domain.ports.providers.market_sentiment_provider import (
    IMarketSentimentProvider,
)
from src.modules.data_engineering.domain.ports.repositories.broken_board_repo import (
    IBrokenBoardRepository,
)


class SyncBrokenBoardCmd:
    """
    同步炸板池数据命令。
    
    从 AkShare 获取炸板池数据并写入 PostgreSQL。
    """

    def __init__(
        self,
        sentiment_provider: IMarketSentimentProvider,
        broken_board_repo: IBrokenBoardRepository,
    ):
        self.sentiment_provider = sentiment_provider
        self.broken_board_repo = broken_board_repo

    async def execute(self, trade_date: date) -> int:
        """
        执行炸板池数据同步。
        
        Args:
            trade_date: 交易日期
            
        Returns:
            同步条数
            
        Raises:
            Exception: 同步失败时抛出
        """
        logger.info(f"开始同步炸板池数据：{trade_date}")
        
        broken_board_dtos = await self.sentiment_provider.fetch_broken_board_pool(trade_date)
        
        if not broken_board_dtos:
            logger.info(f"炸板池数据为空：{trade_date}")
            return 0
        
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
        
        count = await self.broken_board_repo.save_all(broken_board_entities)
        logger.info(f"炸板池数据同步成功：{count} 条")
        
        return count
