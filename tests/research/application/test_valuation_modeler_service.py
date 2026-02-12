"""
任务 10.2 + 10.5：估值建模师 Application 输入校验与 E2E mock 测试。
传入缺失 symbol 时断言被拒绝；mock 数据 Port 返回 None（标的不存在）时断言明确错误；
mock 财务数据返回空列表时断言明确错误；
E2E：mock 三个 Port 返回固定数据，断言完整编排返回结果包含 valuation_verdict、input、valuation_indicators、output 等字段。
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock

from src.shared.domain.exceptions import BadRequestException
from src.modules.research.application.valuation_modeler_service import (
    ValuationModelerService,
)
from src.modules.research.domain.ports.dto_valuation_inputs import (
    StockOverviewInput,
    ValuationDailyInput,
    ValuationSnapshotDTO,
)
from src.modules.research.domain.ports.dto_financial_inputs import FinanceRecordInput
from src.modules.research.domain.valuation_dtos import (
    ValuationResultDTO,
    IntrinsicValueRangeDTO,
    ValuationModelAgentResult,
)


class _MockSnapshotBuilder:
    """Mock 快照构建器，返回固定快照。"""

    def build(self, overview, historical_valuations, finance_records):
        return ValuationSnapshotDTO(
            stock_name="平安银行",
            stock_code="000001.SZ",
            current_date="2024-12-31",
            industry="银行",
            current_price=10.5,
            total_mv=20.0,
            pe_ttm=5.2,
            pe_percentile=15,
            pb=0.65,
            pb_percentile=20,
            ps_ttm=1.2,
            ps_percentile=25,
            dv_ratio=3.5,
            roe=18.0,
            gros_profit_margin=36.0,
            gross_margin_trend="同比上升 2.0%",
            net_profit_margin=20.0,
            debt_to_assets=60.0,
            growth_rate_avg=22.0,
            peg_ratio=0.24,
            graham_intrinsic_val=26.83,
            graham_safety_margin=155.5,
        )


@pytest.mark.asyncio
async def test_missing_symbol_raises_bad_request():
    """传入缺失 symbol 时断言被拒绝并返回可区分错误。"""
    mock_data = AsyncMock()
    mock_builder = _MockSnapshotBuilder()
    mock_agent = AsyncMock()

    svc = ValuationModelerService(
        valuation_data_port=mock_data,
        snapshot_builder=mock_builder,
        modeler_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await svc.run(symbol="")
    assert "symbol" in exc_info.value.message.lower() or "必填" in exc_info.value.message

    with pytest.raises(BadRequestException):
        await svc.run(symbol="   ")


@pytest.mark.asyncio
async def test_stock_not_exist_raises_bad_request():
    """mock 数据 Port 返回 None（标的不存在）时断言明确错误。"""
    mock_data = AsyncMock()
    mock_data.get_stock_overview.return_value = None

    mock_builder = _MockSnapshotBuilder()
    mock_agent = AsyncMock()

    svc = ValuationModelerService(
        valuation_data_port=mock_data,
        snapshot_builder=mock_builder,
        modeler_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await svc.run(symbol="INVALID.SZ")
    assert "不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_empty_finance_records_raises_bad_request():
    """mock 财务数据返回空列表时断言明确错误信息。"""
    mock_data = AsyncMock()
    mock_data.get_stock_overview.return_value = StockOverviewInput(
        stock_name="测试股票",
        industry="测试行业",
        third_code="000001.SZ",
        current_price=10.0,
        total_mv=100000.0,
        pe_ttm=5.0,
        pb=0.6,
        ps_ttm=1.0,
        dv_ratio=3.0,
    )
    mock_data.get_valuation_dailies.return_value = []
    mock_data.get_finance_for_valuation.return_value = []  # 空财务数据

    mock_builder = _MockSnapshotBuilder()
    mock_agent = AsyncMock()

    svc = ValuationModelerService(
        valuation_data_port=mock_data,
        snapshot_builder=mock_builder,
        modeler_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await svc.run(symbol="000001.SZ")
    assert "无财务数据" in exc_info.value.message or "无数据" in exc_info.value.message


@pytest.mark.asyncio
async def test_full_flow_returns_valuation_result_with_all_fields():
    """E2E：mock 三个 Port，完整编排返回包含 valuation_verdict、input、valuation_indicators、output 等字段。"""
    mock_data = AsyncMock()
    mock_data.get_stock_overview.return_value = StockOverviewInput(
        stock_name="平安银行",
        industry="银行",
        third_code="000001.SZ",
        current_price=10.5,
        total_mv=200000.0,
        pe_ttm=5.2,
        pb=0.65,
        ps_ttm=1.2,
        dv_ratio=3.5,
    )
    mock_data.get_valuation_dailies.return_value = [
        ValuationDailyInput(
            trade_date=date(2023, 1, 1) + __import__("datetime").timedelta(days=i * 3),
            close=10.0,
            pe_ttm=5.0,
            pb=0.6,
            ps_ttm=1.0,
        )
        for i in range(100)
    ]
    mock_data.get_finance_for_valuation.return_value = [
        FinanceRecordInput(
            end_date=date(2024, 9, 30),
            ann_date=date(2024, 9, 30),
            third_code="000001.SZ",
            eps=2.0,
            bps=16.0,
            gross_margin=36.0,
            roe_waa=18.0,
            netprofit_margin=20.0,
            debt_to_assets=60.0,
            profit_dedt=1200.0,
        ),
        FinanceRecordInput(
            end_date=date(2024, 6, 30),
            ann_date=date(2024, 6, 30),
            third_code="000001.SZ",
            gross_margin=35.0,
            profit_dedt=1100.0,
        ),
    ]

    mock_agent = AsyncMock()
    mock_agent.analyze.return_value = ValuationModelAgentResult(
        result=ValuationResultDTO(
            valuation_verdict="Undervalued (低估)",
            confidence_score=0.85,
            estimated_intrinsic_value_range=IntrinsicValueRangeDTO(
                lower_bound="基于 Graham 模型推导的 26.8 元",
                upper_bound="基于历史均值 PE 推导的 35.0 元",
            ),
            key_evidence=["PE 处于历史 15% 分位", "PEG 仅为 0.24"],
            risk_factors=["毛利率同比上升但仍需观察"],
            reasoning_summary="综合三模型显示低估，具有投资价值。",
        ),
        raw_llm_output='{"valuation_verdict":"Undervalued (低估)"}',
        user_prompt="test user prompt",
    )

    from src.modules.research.infrastructure.valuation_snapshot.snapshot_builder import (
        ValuationSnapshotBuilderImpl,
    )

    svc = ValuationModelerService(
        valuation_data_port=mock_data,
        snapshot_builder=ValuationSnapshotBuilderImpl(),
        modeler_agent_port=mock_agent,
    )

    result = await svc.run(symbol="000001.SZ")

    # 断言完整响应结构
    assert "valuation_verdict" in result
    assert result["valuation_verdict"] == "Undervalued (低估)"
    assert "confidence_score" in result
    assert result["confidence_score"] == 0.85
    assert "estimated_intrinsic_value_range" in result
    assert "key_evidence" in result
    assert len(result["key_evidence"]) >= 1
    assert "risk_factors" in result
    assert "reasoning_summary" in result
    assert "input" in result
    assert "output" in result
    assert "valuation_indicators" in result
    assert isinstance(result["valuation_indicators"], dict)
