"""
指标计算 Port 的 Infrastructure 实现。
委托给 calculator 模块（可在此处或 calculator 内依赖第三方库如 ta-lib、pandas），
Application 仅依赖 Domain 的 IIndicatorCalculator，不直接引用本实现。
"""

from typing import List

from src.modules.research.domain.dtos.daily_bar_input import DailyBarInput
from src.modules.research.domain.dtos.indicators_snapshot import (
    TechnicalIndicatorsSnapshot,
)
from src.modules.research.domain.ports.indicator_calculator import (
    IIndicatorCalculator,
)
from src.modules.research.infrastructure.indicators.calculator import (
    compute_technical_indicators,
)


class IndicatorCalculatorAdapter(IIndicatorCalculator):
    """基于日线计算技术指标，实现可依赖第三方库；本实现使用 calculator 模块。"""

    def compute(self, bars: List[DailyBarInput]) -> TechnicalIndicatorsSnapshot:
        return compute_technical_indicators(bars)
