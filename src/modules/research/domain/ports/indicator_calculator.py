"""
计算技术指标的 Port。
Domain 层仅定义契约；具体实现在 Infrastructure 层，可依赖第三方库（如 ta-lib、pandas）。
Application 通过此 Port 获取指标快照，不直接依赖实现或第三方库。
"""
from abc import ABC, abstractmethod
from typing import List

from src.modules.research.domain.dtos.indicators_snapshot import TechnicalIndicatorsSnapshot
from src.modules.research.domain.dtos.daily_bar_input import DailyBarInput


class IIndicatorCalculator(ABC):
    """入参日线 DTO 列表，出参与 spec 输入契约一致的技术指标快照。"""

    @abstractmethod
    def compute(self, bars: List[DailyBarInput]) -> TechnicalIndicatorsSnapshot:
        raise NotImplementedError
