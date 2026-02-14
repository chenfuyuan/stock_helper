"""
获取日线数据的 Port。
Research 仅依赖此抽象，由 Infrastructure 的 Adapter 调用 data_engineering 的 Application 接口。
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

from src.modules.research.domain.dtos.daily_bar_input import DailyBarInput


class IMarketQuotePort(ABC):
    """按标的与日期区间获取日线，返回 Research 约定的输入结构。"""

    @abstractmethod
    async def get_daily_bars(
        self, ticker: str, start_date: date, end_date: date
    ) -> List[DailyBarInput]:
        raise NotImplementedError
