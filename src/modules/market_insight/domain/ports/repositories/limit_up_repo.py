"""
涨停股持久化接口
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

from src.modules.market_insight.domain.model.limit_up_stock import LimitUpStock


class ILimitUpRepository(ABC):
    """涨停股持久化接口"""
    
    @abstractmethod
    async def save_all(self, stocks: List[LimitUpStock]) -> int:
        """
        批量 UPSERT 涨停股数据
        :param stocks: 涨停股实体列表
        :return: 影响行数
        """
        pass
    
    @abstractmethod
    async def get_by_date(self, trade_date: date) -> List[LimitUpStock]:
        """
        查询指定日期的所有涨停股
        :param trade_date: 交易日期
        :return: 涨停股列表
        """
        pass
    
    @abstractmethod
    async def get_by_date_and_concept(
        self, trade_date: date, concept_code: str
    ) -> List[LimitUpStock]:
        """
        查询指定日期、指定概念下的涨停股
        :param trade_date: 交易日期
        :param concept_code: 概念代码
        :return: 涨停股列表
        """
        pass
