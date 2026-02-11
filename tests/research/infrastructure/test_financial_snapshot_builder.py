"""
Task 5.4：财务快照构建器测试。
传入已知多期数据断言快照各字段正确；EPS 为 0 时 quality_ratio 为 N/A；仅 1 期数据时 YoY 为 N/A。
"""
import pytest
from datetime import date

from src.modules.research.domain.ports.dto_financial_inputs import (
    FinanceRecordInput,
)
from src.modules.research.infrastructure.financial_snapshot.snapshot_builder import (
    FinancialSnapshotBuilderImpl,
)


def _make_record(
    end_date: date,
    third_code: str = "000001.SZ",
    eps: float | None = 1.0,
    ocfps: float | None = 1.2,
    gross_margin: float | None = 35.0,
    roic: float | None = 10.0,
    total_revenue_ps: float | None = 10.0,
    profit_dedt: float | None = 1.0,
) -> FinanceRecordInput:
    return FinanceRecordInput(
        end_date=end_date,
        ann_date=end_date,
        third_code=third_code,
        gross_margin=gross_margin,
        roic=roic,
        eps=eps,
        ocfps=ocfps,
        total_revenue_ps=total_revenue_ps,
        profit_dedt=profit_dedt,
    )


def test_snapshot_builder_quality_ratio_computed():
    """派生指标 quality_ratio = OCFPS / EPS 计算正确。"""
    records = [
        _make_record(date(2024, 9, 30), eps=1.0, ocfps=1.5),
    ]
    builder = FinancialSnapshotBuilderImpl()
    snap = builder.build(records)
    assert snap.quality_ratio == 1.5


def test_snapshot_builder_quality_ratio_na_when_eps_zero():
    """EPS 为 0 时 quality_ratio 标记为 N/A。"""
    records = [
        _make_record(date(2024, 9, 30), eps=0.0, ocfps=1.0),
    ]
    builder = FinancialSnapshotBuilderImpl()
    snap = builder.build(records)
    assert snap.quality_ratio == "N/A"


def test_snapshot_builder_single_record_yoy_na():
    """仅 1 期数据时 YoY 增速为 N/A。"""
    records = [_make_record(date(2024, 9, 30))]
    builder = FinancialSnapshotBuilderImpl()
    snap = builder.build(records)
    assert snap.revenue_growth_series == ["N/A"]
    assert snap.profit_growth_series == ["N/A"]


def test_snapshot_builder_multi_record_snapshot_fields():
    """多期数据时快照各字段正确提取。"""
    records = [
        _make_record(
            date(2024, 9, 30),
            gross_margin=36.0,
            roic=12.0,
            eps=1.2,
            ocfps=1.5,
        ),
        _make_record(date(2024, 6, 30), gross_margin=35.0, roic=11.0),
    ]
    builder = FinancialSnapshotBuilderImpl()
    snap = builder.build(records)
    assert snap.symbol == "000001.SZ"
    assert snap.report_period == "2024Q3"
    assert snap.gross_margin == 36.0
    assert snap.roic == 12.0
    assert snap.quality_ratio == 1.25  # 1.5 / 1.2
    assert snap.quarter_list == ["2024Q3", "2024Q2"]
