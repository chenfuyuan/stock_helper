from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.modules.data_engineering.domain.model.stock_daily import StockDaily


class IMarketQuoteRepository(ABC):
    @abstractmethod
    async def save_all(self, dailies: List[StockDaily]) -> int:
        pass

    @abstractmethod
    async def get_by_third_code_and_date_range(
        self, third_code: str, start_date: date, end_date: date
    ) -> List[StockDaily]:
        """按第三方代码与日期区间查询日线，供 Application 层只读使用。"""

    @abstractmethod
    async def get_latest_by_third_code(self, third_code: str) -> Optional[StockDaily]:
        """
        查询指定标的最新的一条日线数据
        :param third_code: 股票代码
        :return: 最新日线对象，无数据返回 None
        """

    @abstractmethod
    async def get_latest_trade_date(self) -> Optional[date]:
        """
        查询数据库中最新的交易日期（max(trade_date)）

        用于日线增量同步的遗漏检测：与当前日期比较，判断是否需要补偿缺失的日期区间。

        Returns:
            最新交易日期，若数据库为空则返回 None
        """

    @abstractmethod
    async def get_valuation_dailies(
        self, third_code: str, start_date: date, end_date: date
    ) -> List[StockDaily]:
        """
        按第三方代码与日期区间查询日线（含估值字段），供估值分析使用。
        返回的 StockDaily 包含 pe_ttm、pb、ps_ttm、dv_ratio、total_mv 等估值字段。
        """

    @abstractmethod
    async def get_all_by_trade_date(self, trade_date: date) -> List[StockDaily]:
        """
        查询指定交易日的全市场日线数据
        :param trade_date: 交易日期
        :return: 该日期的所有股票日线数据列表
        """
