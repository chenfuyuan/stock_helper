"""
获取财务数据 Port 的 Adapter。
内部调用 data_engineering 的 GetFinanceForTickerUseCase（Application 接口），
不直接依赖 data_engineering 的 repository 或 domain。
"""

from typing import List

from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    FinanceIndicatorDTO,
    GetFinanceForTickerUseCase,
)
from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)
from src.modules.research.domain.ports.financial_data import IFinancialDataPort


def _to_finance_record(d: FinanceIndicatorDTO) -> FinanceRecordInput:
    """将 data_engineering 的 DTO 转为 Research 的 FinanceRecordInput。"""
    return FinanceRecordInput(
        end_date=d.end_date,
        ann_date=d.ann_date,
        third_code=d.third_code,
        source=d.source,
        gross_margin=d.gross_margin,
        netprofit_margin=d.netprofit_margin,
        roe_waa=d.roe_waa,
        roic=d.roic,
        eps=d.eps,
        bps=d.bps,
        profit_dedt=d.profit_dedt,
        ocfps=d.ocfps,
        fcff_ps=d.fcff_ps,
        current_ratio=d.current_ratio,
        quick_ratio=d.quick_ratio,
        debt_to_assets=d.debt_to_assets,
        interestdebt=d.interestdebt,
        netdebt=d.netdebt,
        invturn_days=d.invturn_days,
        arturn_days=d.arturn_days,
        assets_turn=d.assets_turn,
        total_revenue_ps=d.total_revenue_ps,
        fcff=d.fcff,
    )


class FinancialDataAdapter(IFinancialDataPort):
    """通过 data_engineering 的 Application 接口获取财务数据，转为 Research 的 FinanceRecordInput。"""

    def __init__(self, get_finance_use_case: GetFinanceForTickerUseCase):
        self._get_finance = get_finance_use_case

    async def get_finance_records(self, ticker: str, limit: int = 5) -> List[FinanceRecordInput]:
        dto_list = await self._get_finance.execute(ticker=ticker, limit=limit)
        return [_to_finance_record(d) for d in dto_list]
