"""
市场行情数据查询接口
用于从 data_engineering 获取日线行情数据
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

from src.modules.market_insight.domain.dtos.insight_dtos import StockDailyDTO


class IMarketDataPort(ABC):
    """市场行情数据查询接口"""
    
    @abstractmethod
    async def get_daily_bars_by_date(self, trade_date: date) -> List[StockDailyDTO]:
        """
        获取指定交易日全市场日线数据
        :param trade_date: 交易日期
        :return: 股票日线 DTO 列表
        """
        pass
