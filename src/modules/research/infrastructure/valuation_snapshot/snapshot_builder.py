"""
估值快照构建实现。
将三类原始数据（股票概览、历史估值日线、财务指标）转为 ValuationSnapshotDTO。
实现预计算逻辑：历史分位点、PEG、Graham Number、安全边际、毛利率趋势。
所有数值计算在代码中完成，LLM 仅做定性解读。
财务指标超出合理范围时替换为 N/A 并记录 WARNING，避免脏数据传入 LLM。
"""

import logging
import math
from datetime import date, datetime
from typing import Any, List, Optional, Tuple

from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)
from src.modules.research.domain.dtos.types import PlaceholderValue
from src.modules.research.domain.dtos.valuation_inputs import (
    StockOverviewInput,
    ValuationDailyInput,
)
from src.modules.research.domain.dtos.valuation_snapshot import (
    ValuationSnapshotDTO,
)
from src.modules.research.domain.ports.valuation_snapshot_builder import (
    IValuationSnapshotBuilder,
)

logger = logging.getLogger(__name__)

NA = "N/A"
MIN_HISTORICAL_DATA_FOR_PERCENTILE = 60  # 最少 60 个交易日才计算分位点

# 财务指标合理性边界（百分比等），超出则替换为 N/A 并记录 WARNING
GROSS_MARGIN_BOUNDS: Tuple[float, float] = (-100, 100)
ROE_BOUNDS: Tuple[float, float] = (-500, 500)
NET_MARGIN_BOUNDS: Tuple[float, float] = (-1000, 1000)
DEBT_RATIO_BOUNDS: Tuple[float, float] = (0, 300)


def _validate_financial_metric(
    value: Optional[float],
    bounds: Tuple[float, float],
    metric_name: str,
    stock_code: str,
) -> PlaceholderValue:
    """
    校验财务指标是否在合理范围内。
    在范围内返回原值；超出范围返回 N/A 并记录 WARNING（含字段名、原始值、stock_code）。
    """
    if value is None:
        return NA
    low, high = bounds
    if low <= value <= high:
        return value
    logger.warning(
        "财务指标超出合理范围，已替换为 N/A：字段=%s，原始值=%s，stock_code=%s",
        metric_name,
        value,
        stock_code,
    )
    return NA


def _calculate_percentile(
    values: List[Optional[float]], current: Optional[float]
) -> Any:
    """
    计算当前值在历史序列中的百分位排名（0–100）。
    跳过 None、负值、0 值；有效数据不足 60 条时返回 N/A。
    percentile = (当前值在有效序列中的排名 / 有效序列长度) × 100。
    """
    if current is None or current <= 0:
        return NA

    # 过滤有效数据
    valid = [v for v in values if v is not None and v > 0]
    if len(valid) < MIN_HISTORICAL_DATA_FOR_PERCENTILE:
        return NA

    # 计算排名（当前值小于等于多少个历史值）
    rank = sum(1 for v in valid if v <= current)
    percentile = round((rank / len(valid)) * 100)
    return percentile


def _calculate_peg(
    pe_ttm: Optional[float], growth_rate_avg: Optional[float]
) -> Any:
    """
    计算 PEG 比率：PEG = PE-TTM / growth_rate_avg。
    增速 ≤ 0 或 PE/增速为 None 时返回 N/A。
    """
    if pe_ttm is None or growth_rate_avg is None or growth_rate_avg <= 0:
        return NA
    if pe_ttm <= 0:
        return NA
    return round(pe_ttm / growth_rate_avg, 2)


def _calculate_graham_number(
    eps: Optional[float], bps: Optional[float]
) -> Any:
    """
    计算格雷厄姆数字：Graham = sqrt(22.5 × EPS × BPS)。
    EPS 或 BPS ≤ 0 或为 None 时返回 N/A。
    """
    if eps is None or bps is None or eps <= 0 or bps <= 0:
        return NA
    try:
        graham = math.sqrt(22.5 * eps * bps)
        return round(graham, 2)
    except (ValueError, OverflowError):
        return NA


def _calculate_safety_margin(
    graham_value: Any, current_price: Optional[float]
) -> Any:
    """
    计算安全边际：Safety Margin = (Graham - Price) / Price × 100。
    Graham 为 N/A 或 Price ≤ 0 时返回 N/A。
    正数代表价格低于内在价值（有安全边际）。
    """
    if graham_value == NA or current_price is None or current_price <= 0:
        return NA
    if not isinstance(graham_value, (int, float)):
        return NA
    try:
        margin = ((graham_value - current_price) / current_price) * 100
        return round(margin, 1)
    except (ZeroDivisionError, ValueError):
        return NA


def _calculate_gross_margin_trend(records: List[FinanceRecordInput]) -> str:
    """
    计算毛利率同比趋势描述。
    比较最新期与上一期 gross_margin，输出描述性字符串。
    仅 1 期数据时返回 N/A。两期毛利率任一期超出 GROSS_MARGIN_BOUNDS 时返回 N/A，避免荒谬趋势描述。
    """
    if len(records) < 2:
        return NA

    # 已按 end_date 降序排列，records[0] 为最新期
    latest = records[0].gross_margin
    previous = records[1].gross_margin

    if latest is None or previous is None:
        return NA

    low, high = GROSS_MARGIN_BOUNDS
    if not (low <= latest <= high) or not (low <= previous <= high):
        return NA

    if previous == 0:
        return NA

    diff = latest - previous
    if abs(diff) < 0.01:  # 差异小于 0.01% 视为持平
        return "持平"
    elif diff > 0:
        return f"同比上升 {abs(diff):.1f}%"
    else:
        return f"同比下降 {abs(diff):.1f}%"


def _calculate_avg_profit_growth(
    records: List[FinanceRecordInput],
) -> Optional[float]:
    """
    计算最近 4 季度利润 YoY 增速的平均值。
    需要找到相邻同期记录计算 YoY，再对最近 4 个 YoY 求平均。
    数据不足或增速无法计算时返回 None。
    """
    if len(records) < 2:
        return None

    # 按 end_date 推算季度标签
    def _end_date_to_quarter(d: date) -> str:
        q = (d.month - 1) // 3 + 1
        return f"{d.year}Q{q}"

    # 构建季度 -> 记录映射
    by_quarter: dict[str, FinanceRecordInput] = {}
    for r in records:
        by_quarter[_end_date_to_quarter(r.end_date)] = r

    # 计算 YoY 增速序列（使用 profit_dedt 作为利润指标）
    yoy_list: List[float] = []
    for r in records:
        _end_date_to_quarter(r.end_date)
        prev_q = f"{r.end_date.year - 1}Q{(r.end_date.month - 1) // 3 + 1}"
        prev = by_quarter.get(prev_q)
        if prev is None:
            continue
        curr_val = r.profit_dedt
        prior_val = prev.profit_dedt
        if curr_val is None or prior_val is None or prior_val == 0:
            continue
        try:
            yoy_pct = ((curr_val - prior_val) / prior_val) * 100
            yoy_list.append(yoy_pct)
        except (TypeError, ZeroDivisionError):
            continue

    # 取最近 4 个 YoY（如果不足 4 个就用全部）
    if not yoy_list:
        return None

    recent_yoy = yoy_list[:4]
    return round(sum(recent_yoy) / len(recent_yoy), 1)


class ValuationSnapshotBuilderImpl(IValuationSnapshotBuilder):
    """IValuationSnapshotBuilder 的实现。"""

    def build(
        self,
        overview: StockOverviewInput,
        historical_valuations: List[ValuationDailyInput],
        finance_records: List[FinanceRecordInput],
    ) -> ValuationSnapshotDTO:
        """
        将三类数据转为 ValuationSnapshotDTO。
        预计算：历史分位点、PEG、Graham Number、安全边际、毛利率趋势。
        财务记录应按 end_date 降序排列。
        """
        # 确保财务记录按 end_date 降序
        sorted_finances = sorted(
            finance_records, key=lambda r: r.end_date, reverse=True
        )

        # 股票信息
        stock_name = overview.stock_name
        stock_code = overview.third_code
        current_date = datetime.now().strftime("%Y-%m-%d")
        industry = overview.industry

        # 市场相对估值（来自 overview）
        current_price = overview.current_price
        # total_mv 单位为万元，转为亿元
        total_mv = (
            round(overview.total_mv / 10000, 2)
            if overview.total_mv is not None
            else NA
        )
        pe_ttm = overview.pe_ttm if overview.pe_ttm is not None else NA
        pb = overview.pb if overview.pb is not None else NA
        ps_ttm = overview.ps_ttm if overview.ps_ttm is not None else NA
        dv_ratio = overview.dv_ratio if overview.dv_ratio is not None else NA

        # 历史分位点（基于历史估值日线）
        historical_pe_values = [v.pe_ttm for v in historical_valuations]
        historical_pb_values = [v.pb for v in historical_valuations]
        historical_ps_values = [v.ps_ttm for v in historical_valuations]

        pe_percentile = _calculate_percentile(
            historical_pe_values, overview.pe_ttm
        )
        pb_percentile = _calculate_percentile(
            historical_pb_values, overview.pb
        )
        ps_percentile = _calculate_percentile(
            historical_ps_values, overview.ps_ttm
        )

        # 基本面质量体检（来自财务数据，经合理性校验后填入）
        latest_finance = sorted_finances[0] if sorted_finances else None
        if latest_finance:
            roe = _validate_financial_metric(
                latest_finance.roe_waa, ROE_BOUNDS, "roe_waa", stock_code
            )
            gros_profit_margin = _validate_financial_metric(
                latest_finance.gross_margin,
                GROSS_MARGIN_BOUNDS,
                "gross_margin",
                stock_code,
            )
            net_profit_margin = _validate_financial_metric(
                latest_finance.netprofit_margin,
                NET_MARGIN_BOUNDS,
                "netprofit_margin",
                stock_code,
            )
            debt_to_assets = _validate_financial_metric(
                latest_finance.debt_to_assets,
                DEBT_RATIO_BOUNDS,
                "debt_to_assets",
                stock_code,
            )
            eps = latest_finance.eps
            bps = latest_finance.bps
        else:
            roe = NA
            gros_profit_margin = NA
            net_profit_margin = NA
            debt_to_assets = NA
            eps = None
            bps = None

        gross_margin_trend = _calculate_gross_margin_trend(sorted_finances)

        # 预计算估值模型
        growth_rate_avg = _calculate_avg_profit_growth(sorted_finances)
        growth_rate_avg_display = (
            growth_rate_avg if growth_rate_avg is not None else NA
        )

        peg_ratio = _calculate_peg(overview.pe_ttm, growth_rate_avg)
        graham_intrinsic_val = _calculate_graham_number(eps, bps)
        graham_safety_margin = _calculate_safety_margin(
            graham_intrinsic_val, current_price
        )

        return ValuationSnapshotDTO(
            stock_name=stock_name,
            stock_code=stock_code,
            current_date=current_date,
            industry=industry,
            current_price=current_price,
            total_mv=total_mv,
            pe_ttm=pe_ttm,
            pe_percentile=pe_percentile,
            pb=pb,
            pb_percentile=pb_percentile,
            ps_ttm=ps_ttm,
            ps_percentile=ps_percentile,
            dv_ratio=dv_ratio,
            roe=roe,
            gros_profit_margin=gros_profit_margin,
            gross_margin_trend=gross_margin_trend,
            net_profit_margin=net_profit_margin,
            debt_to_assets=debt_to_assets,
            growth_rate_avg=growth_rate_avg_display,
            peg_ratio=peg_ratio,
            graham_intrinsic_val=graham_intrinsic_val,
            graham_safety_margin=graham_safety_margin,
        )
