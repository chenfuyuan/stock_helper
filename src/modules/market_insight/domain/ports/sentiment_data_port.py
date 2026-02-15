from abc import ABC, abstractmethod
from datetime import date

from src.modules.market_insight.domain.dtos.sentiment_dtos import (
    BrokenBoardItemDTO,
    LimitUpPoolItemDTO,
    PreviousLimitUpItemDTO,
)


class ISentimentDataPort(ABC):
    """
    市场情绪数据端口（MI 领域层接口）
    用于从 data_engineering 模块消费市场情绪相关数据
    """

    @abstractmethod
    async def get_limit_up_pool(self, trade_date: date) -> list[LimitUpPoolItemDTO]:
        """
        获取指定日期的涨停池数据
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[LimitUpPoolItemDTO]: 涨停池数据列表
        """
        pass

    @abstractmethod
    async def get_broken_board_pool(self, trade_date: date) -> list[BrokenBoardItemDTO]:
        """
        获取指定日期的炸板池数据
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[BrokenBoardItemDTO]: 炸板池数据列表
        """
        pass

    @abstractmethod
    async def get_previous_limit_up(self, trade_date: date) -> list[PreviousLimitUpItemDTO]:
        """
        获取昨日涨停今日表现数据
        
        Args:
            trade_date: 交易日期（今日日期）
            
        Returns:
            list[PreviousLimitUpItemDTO]: 昨日涨停表现数据列表
        """
        pass
