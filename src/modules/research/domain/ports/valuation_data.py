"""
获取估值所需数据的 Port。
Research 仅依赖此抽象，由 Infrastructure 的 Adapter 调用 data_engineering 的 Application 接口。
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)
from src.modules.research.domain.dtos.valuation_inputs import (
    StockOverviewInput,
    ValuationDailyInput,
)


class IValuationDataPort(ABC):
    """
    获取估值建模师所需的三类数据：股票概览、历史估值日线、财务指标。
    返回 Research 约定的输入结构。
    """

    @abstractmethod
    async def get_stock_overview(
        self, symbol: str
    ) -> Optional[StockOverviewInput]:
        """
        获取股票基础信息与最新市场估值数据。
        返回 None 表示标的不存在。
        """
        raise NotImplementedError

    @abstractmethod
    async def get_valuation_dailies(
        self, ticker: str, start_date: date, end_date: date
    ) -> List[ValuationDailyInput]:
        """
        获取历史估值日线（含 PE、PB、PS 等），用于历史分位点计算。
        """
        raise NotImplementedError

    @abstractmethod
    async def get_finance_for_valuation(
        self, ticker: str, limit: int = 5
    ) -> List[FinanceRecordInput]:
        """
        获取财务指标数据（含 EPS、BPS、ROE 等），用于 PEG 计算与 Graham 计算。
        """
        raise NotImplementedError
