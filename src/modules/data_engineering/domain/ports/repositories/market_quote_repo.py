from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional
from src.modules.data_engineering.domain.model.daily_bar import StockDaily


class IMarketQuoteRepository(ABC):
    @abstractmethod
    async def save_all(self, dailies: List[StockDaily]) -> int:
        pass

    @abstractmethod
    async def get_by_third_code_and_date_range(
        self, third_code: str, start_date: date, end_date: date
    ) -> List[StockDaily]:
        """按第三方代码与日期区间查询日线，供 Application 层只读使用。"""
        pass

    @abstractmethod
    async def get_latest_trade_date(self) -> Optional[date]:
        """
        查询数据库中最新的交易日期（max(trade_date)）
        
        用于日线增量同步的遗漏检测：与当前日期比较，判断是否需要补偿缺失的日期区间。
        
        Returns:
            最新交易日期，若数据库为空则返回 None
        """
        pass
