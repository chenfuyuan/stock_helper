"""
构建估值快照的 Port。
Domain 层定义「构建估值快照」契约，具体实现（含预计算逻辑）在 Infrastructure 层。
"""
from abc import ABC, abstractmethod
from typing import List

from src.modules.research.domain.ports.dto_valuation_inputs import (
    StockOverviewInput,
    ValuationDailyInput,
    ValuationSnapshotDTO,
)
from src.modules.research.domain.ports.dto_financial_inputs import FinanceRecordInput


class IValuationSnapshotBuilder(ABC):
    """
    将原始数据（股票概览、历史估值日线、财务指标）预计算为估值快照 DTO。
    包含历史分位点、PEG、Graham Number、安全边际、毛利率趋势等预计算模型。
    """

    @abstractmethod
    def build(
        self,
        overview: StockOverviewInput,
        historical_valuations: List[ValuationDailyInput],
        finance_records: List[FinanceRecordInput],
    ) -> ValuationSnapshotDTO:
        """
        将三类数据转为与 User Prompt 模板一一对应的估值快照。
        所有估值模型的数值计算在此完成，LLM 仅做定性解读。
        """
        raise NotImplementedError
