"""
获取财务指标数据的 Port。
Research 仅依赖此抽象，由 Infrastructure 的 Adapter 调用 data_engineering 的 Application 接口。
"""

from abc import ABC, abstractmethod
from typing import List

from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)


class IFinancialDataPort(ABC):
    """按标的获取最近 N 期财务指标，返回 Research 约定的输入结构。"""

    @abstractmethod
    async def get_finance_records(
        self, ticker: str, limit: int = 5
    ) -> List[FinanceRecordInput]:
        raise NotImplementedError
