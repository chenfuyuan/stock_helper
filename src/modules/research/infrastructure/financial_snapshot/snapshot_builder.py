"""
财务快照构建实现。
将多期 FinanceRecordInput 转为 FinancialSnapshotDTO（与 User Prompt 模板占位符一一对应）。
实现派生指标计算：quality_ratio、季度标签、YoY 增速（数据不足时标记 N/A）。
"""

from datetime import date
from typing import Any, Callable, Optional

from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)
from src.modules.research.domain.dtos.financial_snapshot import (
    FinancialSnapshotDTO,
)
from src.modules.research.domain.ports.financial_snapshot_builder import (
    IFinancialSnapshotBuilder,
)

NA = "N/A"


def _end_date_to_quarter(d: date) -> str:
    """由 end_date 推算季度标签，如 2024-09-30 -> 2024Q3。"""
    q = (d.month - 1) // 3 + 1
    return f"{d.year}Q{q}"


def _compute_quality_ratio(ocfps: Optional[float], eps: Optional[float]) -> Any:
    """quality_ratio = OCFPS / EPS，EPS 为 0 或 None 时返回 N/A。"""
    if eps is None or eps == 0 or ocfps is None:
        return NA
    return round(ocfps / eps, 2)


def _compute_yoy_series(
    records: list[FinanceRecordInput],
    value_getter: Callable[[FinanceRecordInput], Optional[float]],
) -> list[Any]:
    """
    计算 YoY 增速序列。需要找到去年同期记录。
    value_getter(record) -> float，用于同比计算的数值。
    """
    if len(records) < 2:
        return []
    result: list[Any] = []
    by_quarter: dict[str, FinanceRecordInput] = {}
    for r in records:
        by_quarter[_end_date_to_quarter(r.end_date)] = r
    for r in records:
        _end_date_to_quarter(r.end_date)
        prev_q = f"{r.end_date.year - 1}Q{(r.end_date.month - 1) // 3 + 1}"
        prev = by_quarter.get(prev_q)
        if prev is None:
            result.append(NA)
            continue
        curr_val = value_getter(r)
        prior_val = value_getter(prev)
        if curr_val is None or prior_val is None or prior_val == 0:
            result.append(NA)
            continue
        try:
            pct = round((curr_val - prior_val) / prior_val * 100, 1)
            result.append(pct)
        except (TypeError, ZeroDivisionError):
            result.append(NA)
    return result


class FinancialSnapshotBuilderImpl(IFinancialSnapshotBuilder):
    """IFinancialSnapshotBuilder 的实现。"""

    def build(self, records: list[FinanceRecordInput]) -> FinancialSnapshotDTO:
        """
        将多期财务记录转为 FinancialSnapshotDTO。
        按 end_date 降序排列（调用方应已保证顺序；本实现再次排序以确保）。
        提取最新期为静态快照，构建历史趋势序列，计算派生指标与 YoY。
        """
        if not records:
            return FinancialSnapshotDTO()

        sorted_records = sorted(records, key=lambda r: r.end_date, reverse=True)
        latest = sorted_records[0]

        # 派生指标
        quality_ratio = _compute_quality_ratio(latest.ocfps, latest.eps)
        # eps_deducted：无每股扣非 EPS 时用 profit_dedt 作为代理值
        eps_deducted = latest.profit_dedt if latest.profit_dedt is not None else NA

        # 季度标签
        quarter_list = [_end_date_to_quarter(r.end_date) for r in sorted_records]

        # 趋势序列（最新在前）
        gross_margin_series = [
            r.gross_margin if r.gross_margin is not None else NA for r in sorted_records
        ]
        roic_series = [r.roic if r.roic is not None else NA for r in sorted_records]
        fcff_series = [r.fcff if r.fcff is not None else NA for r in sorted_records]
        invturn_days_series = [
            r.invturn_days if r.invturn_days is not None else NA for r in sorted_records
        ]
        arturn_days_series = [
            r.arturn_days if r.arturn_days is not None else NA for r in sorted_records
        ]

        # YoY 增速（数据不足时标记 N/A）
        revenue_growth_series = (
            _compute_yoy_series(
                sorted_records,
                lambda r: r.total_revenue_ps,
            )
            if len(sorted_records) >= 2
            else [NA] * len(sorted_records)
        )
        profit_growth_series = (
            _compute_yoy_series(
                sorted_records,
                lambda r: r.profit_dedt,
            )
            if len(sorted_records) >= 2
            else [NA] * len(sorted_records)
        )
        # 若 YoY 计算返回空（无同期可比），用 N/A 填充
        if len(revenue_growth_series) < len(sorted_records):
            revenue_growth_series = [NA] * len(sorted_records)
        if len(profit_growth_series) < len(sorted_records):
            profit_growth_series = [NA] * len(sorted_records)

        return FinancialSnapshotDTO(
            symbol=latest.third_code,
            report_period=_end_date_to_quarter(latest.end_date),
            source=latest.source,
            gross_margin=(latest.gross_margin if latest.gross_margin is not None else NA),
            netprofit_margin=(
                latest.netprofit_margin if latest.netprofit_margin is not None else NA
            ),
            roe_waa=latest.roe_waa if latest.roe_waa is not None else NA,
            roic=latest.roic if latest.roic is not None else NA,
            eps=latest.eps if latest.eps is not None else NA,
            eps_deducted=eps_deducted,
            bps=latest.bps if latest.bps is not None else NA,
            ocfps=latest.ocfps if latest.ocfps is not None else NA,
            fcff_ps=latest.fcff_ps if latest.fcff_ps is not None else NA,
            quality_ratio=quality_ratio,
            current_ratio=(latest.current_ratio if latest.current_ratio is not None else NA),
            quick_ratio=(latest.quick_ratio if latest.quick_ratio is not None else NA),
            debt_to_assets=(latest.debt_to_assets if latest.debt_to_assets is not None else NA),
            interestdebt=(latest.interestdebt if latest.interestdebt is not None else NA),
            netdebt=latest.netdebt if latest.netdebt is not None else NA,
            invturn_days=(latest.invturn_days if latest.invturn_days is not None else NA),
            arturn_days=(latest.arturn_days if latest.arturn_days is not None else NA),
            assets_turn=(latest.assets_turn if latest.assets_turn is not None else NA),
            quarter_list=quarter_list,
            revenue_growth_series=revenue_growth_series,
            profit_growth_series=profit_growth_series,
            gross_margin_series=gross_margin_series,
            roic_series=roic_series,
            fcff_series=fcff_series,
            invturn_days_series=invturn_days_series,
            arturn_days_series=arturn_days_series,
        )
