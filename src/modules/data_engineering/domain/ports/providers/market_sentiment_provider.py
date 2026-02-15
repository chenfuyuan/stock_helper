from abc import ABC, abstractmethod
from datetime import date

from src.modules.data_engineering.domain.dtos.market_sentiment_dtos import (
    BrokenBoardDTO,
    LimitUpPoolDTO,
    PreviousLimitUpDTO,
)


class IMarketSentimentProvider(ABC):
    """
    市场情绪数据提供者 Port
    定义从外部数据源获取市场情绪相关数据的能力（涨停池、炸板池、昨日涨停表现）
    """

    @abstractmethod
    async def fetch_limit_up_pool(self, trade_date: date) -> list[LimitUpPoolDTO]:
        """
        获取指定日期的涨停池数据（含连板天数）
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[LimitUpPoolDTO]: 涨停池数据列表
        """

    @abstractmethod
    async def fetch_broken_board_pool(self, trade_date: date) -> list[BrokenBoardDTO]:
        """
        获取指定日期的炸板池数据
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[BrokenBoardDTO]: 炸板池数据列表
        """

    @abstractmethod
    async def fetch_previous_limit_up(self, trade_date: date) -> list[PreviousLimitUpDTO]:
        """
        获取昨日涨停股今日表现数据
        
        Args:
            trade_date: 交易日期（今日日期，即表现观察日）
            
        Returns:
            list[PreviousLimitUpDTO]: 昨日涨停表现数据列表
        """
