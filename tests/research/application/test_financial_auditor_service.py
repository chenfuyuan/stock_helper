"""
Task 3.3：财务审计员 Application 输入校验与无数据拒绝测试。
传入缺失 symbol 时断言被拒绝；mock 财务数据 Port 返回空列表时断言返回明确错误信息。
"""

from unittest.mock import AsyncMock

import pytest

from src.modules.research.application.financial_auditor_service import (
    FinancialAuditorService,
)
from src.modules.research.domain.dtos.financial_dtos import (
    DimensionAnalysisDTO,
    FinancialAuditAgentResult,
    FinancialAuditResultDTO,
)
from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)
from src.modules.research.domain.dtos.financial_snapshot import (
    FinancialSnapshotDTO,
)
from src.shared.domain.exceptions import BadRequestException


class _MockSnapshotBuilder:
    def build(self, records):
        return FinancialSnapshotDTO()


@pytest.mark.asyncio
async def test_missing_symbol_raises_bad_request():
    """传入缺失 symbol 时断言被拒绝并返回可区分错误。"""
    mock_data = AsyncMock()
    mock_builder = _MockSnapshotBuilder()
    mock_agent = AsyncMock()

    svc = FinancialAuditorService(
        financial_data_port=mock_data,
        snapshot_builder=mock_builder,
        auditor_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await svc.run(symbol="")
    assert (
        "symbol" in exc_info.value.message.lower()
        or "必填" in exc_info.value.message
    )

    with pytest.raises(BadRequestException):
        await svc.run(symbol="   ")


@pytest.mark.asyncio
async def test_empty_finance_records_raises_bad_request():
    """mock 财务数据 Port 返回空列表时断言返回明确错误信息。"""
    mock_data = AsyncMock()
    mock_data.get_finance_records.return_value = []

    mock_builder = _MockSnapshotBuilder()
    mock_agent = AsyncMock()

    svc = FinancialAuditorService(
        financial_data_port=mock_data,
        snapshot_builder=mock_builder,
        auditor_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await svc.run(symbol="000001.SZ")
    assert (
        "无财务数据" in exc_info.value.message
        or "无数据" in exc_info.value.message
    )


@pytest.mark.asyncio
async def test_limit_out_of_range_raises_bad_request():
    """limit 不在 1～20 时抛出 BadRequestException。"""
    mock_data = AsyncMock()
    mock_builder = _MockSnapshotBuilder()
    mock_agent = AsyncMock()
    svc = FinancialAuditorService(
        financial_data_port=mock_data,
        snapshot_builder=mock_builder,
        auditor_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await svc.run(symbol="000001.SZ", limit=0)
    assert (
        "limit" in exc_info.value.message.lower()
        or "1" in exc_info.value.message
    )

    with pytest.raises(BadRequestException):
        await svc.run(symbol="000001.SZ", limit=21)

    mock_data.get_finance_records.assert_not_called()


@pytest.mark.asyncio
async def test_full_flow_returns_audit_result_with_all_fields():
    """E2E：mock 三个 Port，完整编排返回
    包含 financial_score、signal、
    dimension_analyses 等字段。
    """
    from datetime import date

    mock_data = AsyncMock()
    mock_data.get_finance_records.return_value = [
        FinanceRecordInput(
            end_date=date(2024, 9, 30),
            ann_date=date(2024, 9, 30),
            third_code="000001.SZ",
            gross_margin=36.0,
            roic=12.0,
            eps=1.2,
            ocfps=1.5,
        )
    ]

    from src.modules.research.infrastructure.financial_snapshot.snapshot_builder import (  # noqa: E501
        FinancialSnapshotBuilderImpl,
    )

    mock_agent = AsyncMock()
    mock_agent.audit.return_value = FinancialAuditAgentResult(
        result=FinancialAuditResultDTO(
            financial_score=78,
            signal="BULLISH",
            confidence=0.82,
            summary_reasoning="ROIC 12%",
            dimension_analyses=[
                DimensionAnalysisDTO(
                    dimension=f"维度{i}",
                    score=75.0,
                    assessment="良好",
                    key_findings=[],
                )
                for i in range(5)
            ],
            key_risks=[],
            risk_warning="",
        ),
        raw_llm_output='{"financial_score":78}',
        user_prompt="test prompt",
    )

    svc = FinancialAuditorService(
        financial_data_port=mock_data,
        snapshot_builder=FinancialSnapshotBuilderImpl(),
        auditor_agent_port=mock_agent,
    )

    result = await svc.run(symbol="000001.SZ")

    assert "financial_score" in result
    assert result["financial_score"] == 78
    assert "signal" in result
    assert result["signal"] == "BULLISH"
    assert "dimension_analyses" in result
    assert len(result["dimension_analyses"]) == 5
    assert "input" in result
    assert "output" in result
    assert "financial_indicators" in result
    assert isinstance(result["financial_indicators"], dict)
