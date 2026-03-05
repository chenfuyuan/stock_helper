"""
获取估值数据 Port 的 Adapter。
内部调用 data_engineering 的三个 Application 接口：
- GetStockBasicInfoUseCase（获取股票概览）
- GetValuationDailiesForTickerUseCase（获取历史估值日线）
- GetFinanceForTickerUseCase（获取财务指标）
不直接依赖 data_engineering 的 repository 或 domain。
"""

import logging
from datetime import date
from typing import Any, List, Optional

from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    FinanceIndicatorDTO,
    GetFinanceForTickerUseCase,
)
from src.modules.data_engineering.application.queries.get_stock_basic_info import (
    GetStockBasicInfoUseCase,
)
from src.modules.data_engineering.application.queries.get_valuation_dailies_for_ticker import (
    GetValuationDailiesForTickerUseCase,
    ValuationDailyDTO,
)
from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)
from src.modules.research.domain.dtos.valuation_inputs import (
    StockOverviewInput,
    ValuationDailyInput,
)
from src.modules.research.domain.ports.valuation_data import IValuationDataPort

logger = logging.getLogger(__name__)


def _to_stock_overview(
    basic_info_result: Any,
) -> Optional[StockOverviewInput]:
    """
    将 GetStockBasicInfoUseCase 的返回结果（StockBasicInfoDTO）
    转为 Research 的 StockOverviewInput。
    若 latest_trade_date 为空（标的存在但无日线数据），返回 None 并记录 WARNING。
    """
    # basic_info_result 目前为 StockBasicInfoDTO，直接展开字段
    if basic_info_result.latest_trade_date is None:
        logger.warning(
            "股票日线数据为空，无法构建估值概览：symbol=%s",
            getattr(basic_info_result, "name", "unknown"),
        )
        return None
    return StockOverviewInput(
        stock_name=basic_info_result.name,
        industry=basic_info_result.industry or "未知行业",
        third_code=basic_info_result.third_code,
        current_price=basic_info_result.latest_close,
        total_mv=None,
        pe_ttm=basic_info_result.latest_pct_chg,
        pb=None,
        ps_ttm=None,
        dv_ratio=None,
    )


def _to_valuation_daily(d: ValuationDailyDTO) -> ValuationDailyInput:
    """将 data_engineering 的 ValuationDailyDTO 转为 Research 的 ValuationDailyInput。"""
    return ValuationDailyInput(
        trade_date=d.trade_date,
        close=d.close,
        pe_ttm=d.pe_ttm,
        pb=d.pb,
        ps_ttm=d.ps_ttm,
    )


def _to_finance_record(d: FinanceIndicatorDTO) -> FinanceRecordInput:
    """将 data_engineering 的 FinanceIndicatorDTO 转为 Research 的 FinanceRecordInput。"""
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


class ValuationDataAdapter(IValuationDataPort):
    """
    通过 data_engineering 的 Application 接口获取估值所需的三类数据，
    转为 Research 的输入 DTO。
    """

    def __init__(
        self,
        get_stock_basic_info_use_case: GetStockBasicInfoUseCase,
        get_valuation_dailies_use_case: GetValuationDailiesForTickerUseCase,
        get_finance_use_case: GetFinanceForTickerUseCase,
    ):
        self._get_stock_basic_info = get_stock_basic_info_use_case
        self._get_valuation_dailies = get_valuation_dailies_use_case
        self._get_finance = get_finance_use_case

    async def get_stock_overview(self, symbol: str) -> Optional[StockOverviewInput]:
        """
        获取股票基础信息与最新市场估值数据。
        返回 None 表示标的不存在。
        """
        basic_info = await self._get_stock_basic_info.execute(symbol=symbol)
        if basic_info is None:
            return None
        overview = _to_stock_overview(basic_info)
        return overview

    async def get_valuation_dailies(
        self, ticker: str, start_date: date, end_date: date
    ) -> List[ValuationDailyInput]:
        """获取历史估值日线（含 PE、PB、PS 等），用于历史分位点计算。"""
        dto_list = await self._get_valuation_dailies.execute(
            ticker=ticker, start_date=start_date, end_date=end_date
        )
        return [_to_valuation_daily(d) for d in dto_list]

    async def get_finance_for_valuation(
        self, ticker: str, limit: int = 5
    ) -> List[FinanceRecordInput]:
        """获取财务指标数据（含 EPS、BPS、ROE 等），用于 PEG 计算与 Graham 计算。"""
        dto_list = await self._get_finance.execute(ticker=ticker, limit=limit)
        return [_to_finance_record(d) for d in dto_list]
