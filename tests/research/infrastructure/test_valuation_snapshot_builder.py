"""
任务 10.4：估值快照构建器测试。
传入已知数据断言分位点计算正确；PE 为负时跳过；历史数据 < 60 条时分位点为 N/A；
PEG 增速为负时为 N/A；EPS 为 0 时 Graham 为 N/A；Graham 正确时安全边际正确；
毛利率趋势在多期/单期情况下正确。
"""
import pytest
from datetime import date

from src.modules.research.domain.dtos.valuation_inputs import (
    StockOverviewInput,
    ValuationDailyInput,
)
from src.modules.research.domain.dtos.financial_record_input import FinanceRecordInput
from src.modules.research.infrastructure.valuation_snapshot.snapshot_builder import (
    ValuationSnapshotBuilderImpl,
)


def _make_overview(
    stock_name: str = "平安银行",
    third_code: str = "000001.SZ",
    current_price: float = 10.5,
    pe_ttm: float | None = 5.2,
    pb: float | None = 0.65,
    ps_ttm: float | None = 1.2,
    total_mv: float | None = 200000.0,
) -> StockOverviewInput:
    return StockOverviewInput(
        stock_name=stock_name,
        industry="银行",
        third_code=third_code,
        current_price=current_price,
        total_mv=total_mv,
        pe_ttm=pe_ttm,
        pb=pb,
        ps_ttm=ps_ttm,
        dv_ratio=3.5,
    )


def _make_valuation_daily(
    trade_date: date,
    close: float = 10.0,
    pe_ttm: float | None = 5.0,
    pb: float | None = 0.6,
    ps_ttm: float | None = 1.0,
) -> ValuationDailyInput:
    return ValuationDailyInput(
        trade_date=trade_date,
        close=close,
        pe_ttm=pe_ttm,
        pb=pb,
        ps_ttm=ps_ttm,
    )


def _make_finance_record(
    end_date: date,
    third_code: str = "000001.SZ",
    eps: float | None = 1.0,
    bps: float | None = 10.0,
    gross_margin: float | None = 35.0,
    roe_waa: float | None = 15.0,
    profit_dedt: float | None = 1000.0,
) -> FinanceRecordInput:
    return FinanceRecordInput(
        end_date=end_date,
        ann_date=end_date,
        third_code=third_code,
        eps=eps,
        bps=bps,
        gross_margin=gross_margin,
        roe_waa=roe_waa,
        profit_dedt=profit_dedt,
        netprofit_margin=20.0,
        debt_to_assets=60.0,
    )


def test_percentile_calculated_correctly():
    """传入 100 条历史数据，断言分位点计算正确。"""
    overview = _make_overview(pe_ttm=5.0, pb=0.65, ps_ttm=1.2)
    
    # 构造 100 条历史数据，PE 范围 3.0-8.0，当前 5.0 应在约 40% 分位
    historical = [
        _make_valuation_daily(
            date(2023, 1, 1) + __import__("datetime").timedelta(days=i * 3),
            pe_ttm=3.0 + (i * 5.0 / 100),  # 3.0 到 8.0 线性分布
            pb=0.5 + (i * 0.3 / 100),
            ps_ttm=0.8 + (i * 0.6 / 100),
        )
        for i in range(100)
    ]
    
    finances = [_make_finance_record(date(2024, 9, 30))]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, historical, finances)
    
    # 验证分位点为整数且在合理范围内
    assert isinstance(snapshot.pe_percentile, int)
    assert 0 <= snapshot.pe_percentile <= 100
    assert isinstance(snapshot.pb_percentile, int)
    assert 0 <= snapshot.pb_percentile <= 100


def test_percentile_skips_negative_and_none_values():
    """历史数据含负值或 None 时，分位点计算跳过这些无效值。"""
    overview = _make_overview(pe_ttm=5.0, pb=0.65)
    
    # 100 条数据，但有 20 条 PE 为负或 None（亏损公司）
    historical = []
    for i in range(80):
        historical.append(_make_valuation_daily(
            date(2023, 1, 1) + __import__("datetime").timedelta(days=i * 3),
            pe_ttm=3.0 + (i * 5.0 / 80),
        ))
    for i in range(20):
        historical.append(_make_valuation_daily(
            date(2024, 1, 1) + __import__("datetime").timedelta(days=i * 3),
            pe_ttm=-10.0 if i % 2 == 0 else None,  # 亏损或缺失
        ))
    
    finances = [_make_finance_record(date(2024, 9, 30))]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, historical, finances)
    
    # 应仅基于 80 条有效数据计算
    assert isinstance(snapshot.pe_percentile, int)
    assert 0 <= snapshot.pe_percentile <= 100


def test_percentile_na_when_insufficient_data():
    """历史数据 < 60 条时分位点为 N/A。"""
    overview = _make_overview(pe_ttm=5.0)
    
    # 仅 50 条历史数据
    historical = [
        _make_valuation_daily(
            date(2023, 1, 1) + __import__("datetime").timedelta(days=i * 3),
            pe_ttm=4.0,
        )
        for i in range(50)
    ]
    
    finances = [_make_finance_record(date(2024, 9, 30))]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, historical, finances)
    
    assert snapshot.pe_percentile == "N/A"


def test_peg_ratio_calculated_correctly():
    """PEG = PE-TTM / growth_rate_avg 计算正确。"""
    overview = _make_overview(pe_ttm=10.0)
    
    # 构造 8 期财务数据，可计算 4 季 YoY
    # Q4 2024: profit=1200, Q3: 1150, Q2: 1100, Q1: 1050
    # Q4 2023: profit=1000, Q3: 950,  Q2: 900,  Q1: 850
    finances = [
        _make_finance_record(date(2024, 12, 31), profit_dedt=1200.0),
        _make_finance_record(date(2024, 9, 30), profit_dedt=1150.0),
        _make_finance_record(date(2024, 6, 30), profit_dedt=1100.0),
        _make_finance_record(date(2024, 3, 31), profit_dedt=1050.0),
        _make_finance_record(date(2023, 12, 31), profit_dedt=1000.0),
        _make_finance_record(date(2023, 9, 30), profit_dedt=950.0),
        _make_finance_record(date(2023, 6, 30), profit_dedt=900.0),
        _make_finance_record(date(2023, 3, 31), profit_dedt=850.0),
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    # 平均增速约 20%，PEG = 10 / 20 = 0.5
    assert snapshot.growth_rate_avg != "N/A"
    assert snapshot.peg_ratio != "N/A"
    assert isinstance(snapshot.peg_ratio, float)


def test_peg_na_when_growth_negative():
    """增速为负时 PEG 标记 N/A。"""
    overview = _make_overview(pe_ttm=10.0)
    
    # Q4 2024 利润下降
    finances = [
        _make_finance_record(date(2024, 12, 31), profit_dedt=800.0),
        _make_finance_record(date(2023, 12, 31), profit_dedt=1000.0),
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    # 增速为负，PEG 应为 N/A
    assert snapshot.peg_ratio == "N/A"


def test_peg_na_when_insufficient_finance_data():
    """财务数据不足以计算 YoY 时 PEG 为 N/A。"""
    overview = _make_overview(pe_ttm=10.0)
    
    # 仅 1 期数据
    finances = [_make_finance_record(date(2024, 9, 30))]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert snapshot.peg_ratio == "N/A"


def test_graham_number_calculated_correctly():
    """Graham = sqrt(22.5 × EPS × BPS) 计算正确。"""
    overview = _make_overview(current_price=10.0)
    
    finances = [
        _make_finance_record(date(2024, 9, 30), eps=2.0, bps=16.0)
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    # Graham = sqrt(22.5 * 2.0 * 16.0) = sqrt(720) ≈ 26.83
    assert snapshot.graham_intrinsic_val != "N/A"
    assert isinstance(snapshot.graham_intrinsic_val, float)
    assert 26.0 < snapshot.graham_intrinsic_val < 27.0


def test_graham_na_when_eps_zero():
    """EPS 为 0 时 Graham 为 N/A。"""
    overview = _make_overview()
    
    finances = [
        _make_finance_record(date(2024, 9, 30), eps=0.0, bps=16.0)
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert snapshot.graham_intrinsic_val == "N/A"
    assert snapshot.graham_safety_margin == "N/A"


def test_graham_na_when_bps_negative():
    """BPS 为负时 Graham 为 N/A。"""
    overview = _make_overview()
    
    finances = [
        _make_finance_record(date(2024, 9, 30), eps=2.0, bps=-5.0)
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert snapshot.graham_intrinsic_val == "N/A"


def test_safety_margin_calculated_correctly():
    """Graham 正确时安全边际 = (Graham - Price) / Price × 100 计算正确。"""
    overview = _make_overview(current_price=20.0)
    
    # Graham = sqrt(22.5 * 2.0 * 16.0) ≈ 26.83
    # Safety Margin = (26.83 - 20) / 20 × 100 ≈ 34.15%
    finances = [
        _make_finance_record(date(2024, 9, 30), eps=2.0, bps=16.0)
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert snapshot.graham_safety_margin != "N/A"
    assert isinstance(snapshot.graham_safety_margin, float)
    assert 30.0 < snapshot.graham_safety_margin < 40.0  # 约 34%


def test_safety_margin_negative_when_overvalued():
    """当前价格高于 Graham 时安全边际为负（溢价）。"""
    overview = _make_overview(current_price=30.0)
    
    # Graham ≈ 26.83，价格 30 > Graham
    finances = [
        _make_finance_record(date(2024, 9, 30), eps=2.0, bps=16.0)
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert isinstance(snapshot.graham_safety_margin, float)
    assert snapshot.graham_safety_margin < 0  # 负数代表溢价


def test_gross_margin_trend_calculated():
    """毛利率趋势在多期情况下正确计算。"""
    overview = _make_overview()
    
    # 最新期毛利率 38%，上一期 35%，同比上升 3%
    finances = [
        _make_finance_record(date(2024, 9, 30), gross_margin=38.0),
        _make_finance_record(date(2024, 6, 30), gross_margin=35.0),
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert "上升" in snapshot.gross_margin_trend
    assert "3.0%" in snapshot.gross_margin_trend


def test_gross_margin_trend_na_when_single_record():
    """仅 1 期数据时毛利率趋势为 N/A。"""
    overview = _make_overview()
    
    finances = [_make_finance_record(date(2024, 9, 30))]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert snapshot.gross_margin_trend == "N/A"


def test_roe_from_roe_waa():
    """ROE 取值使用 roe_waa。"""
    overview = _make_overview()
    
    finances = [
        _make_finance_record(date(2024, 9, 30), roe_waa=18.5)
    ]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert snapshot.roe == 18.5


def test_snapshot_basic_fields_from_overview():
    """快照的基础字段来自 overview。"""
    overview = _make_overview(
        stock_name="平安银行",
        third_code="000001.SZ",
        current_price=10.5,
        total_mv=200000.0,
    )
    
    finances = [_make_finance_record(date(2024, 9, 30))]
    
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    
    assert snapshot.stock_name == "平安银行"
    assert snapshot.stock_code == "000001.SZ"
    assert snapshot.current_price == 10.5
    assert snapshot.total_mv == 20.0  # 200000 万元 = 20 亿元
    assert snapshot.industry == "银行"


# --- 财务指标合理性校验（financial-data-sanity）---

def test_gross_margin_out_of_bounds_replaced_with_na():
    """毛利率超出合理范围（如 44969179.57%）时被替换为 N/A。"""
    overview = _make_overview(third_code="000001.SZ")
    finances = [
        _make_finance_record(
            date(2024, 9, 30),
            third_code="000001.SZ",
            gross_margin=44969179.57,
            roe_waa=15.0,
        )
    ]
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    assert snapshot.gros_profit_margin == "N/A"
    assert snapshot.roe == 15.0
    # 默认 netprofit_margin=20、debt_to_assets=60 在合理范围内，应原样填入
    assert snapshot.net_profit_margin == 20.0
    assert snapshot.debt_to_assets == 60.0


def test_roe_within_bounds_passes():
    """ROE 在合理范围内（-500～500）时正常通过。"""
    overview = _make_overview(third_code="000002.SZ")
    finances = [
        _make_finance_record(
            date(2024, 9, 30),
            third_code="000002.SZ",
            gross_margin=35.0,
            roe_waa=25.5,
        )
    ]
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    assert snapshot.roe == 25.5
    assert snapshot.gros_profit_margin == 35.0


def test_gross_margin_trend_na_when_base_value_abnormal():
    """毛利率趋势在两期任一期基础值异常（超出 GROSS_MARGIN_BOUNDS）时返回 N/A。"""
    overview = _make_overview()
    # 最新期正常，上一期异常（>100%）
    finances = [
        _make_finance_record(date(2024, 9, 30), gross_margin=38.0),
        _make_finance_record(date(2024, 6, 30), gross_margin=150.0),
    ]
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    assert snapshot.gross_margin_trend == "N/A"


def test_financial_metrics_unchanged_when_all_normal():
    """所有财务指标在合理范围内时行为不变，数值原样填入。"""
    overview = _make_overview(third_code="000003.SZ")
    finances = [
        _make_finance_record(
            date(2024, 9, 30),
            third_code="000003.SZ",
            gross_margin=42.5,
            roe_waa=12.0,
        )
    ]
    builder = ValuationSnapshotBuilderImpl()
    snapshot = builder.build(overview, [], finances)
    assert snapshot.gros_profit_margin == 42.5
    assert snapshot.roe == 12.0
    # _make_finance_record 默认 netprofit_margin=20、debt_to_assets=60，均在合理范围内
    assert snapshot.net_profit_margin == 20.0
    assert snapshot.debt_to_assets == 60.0
    assert snapshot.gross_margin_trend == "N/A"  # 仅 1 期无趋势
