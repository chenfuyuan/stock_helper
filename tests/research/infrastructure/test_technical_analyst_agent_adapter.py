"""
技术分析 Agent Port 的 Infrastructure 实现测试。
Agent 负责加载 Prompt、调用 LLM、解析结果；合法 JSON 返回 DTO，非法则抛出。
"""
from unittest.mock import AsyncMock

import pytest

from src.modules.research.domain.dtos import TechnicalAnalysisAgentResult
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.modules.research.domain.indicators_snapshot import TechnicalIndicatorsSnapshot
from src.modules.research.domain.ports.llm import ILLMPort
from src.modules.research.infrastructure.adapters.technical_analyst_agent_adapter import (
    TechnicalAnalystAgentAdapter,
)


@pytest.mark.asyncio
async def test_agent_adapter_valid_json_returns_agent_result():
    """LLM 返回合法 JSON 时，Agent 解析并返回 TechnicalAnalysisAgentResult（含 result、raw_llm_output、user_prompt）。"""
    valid_json = '{"signal":"BEARISH","confidence":0.6,"summary_reasoning":"RSI 超买","key_technical_levels":{"support":9.0,"resistance":12.0},"risk_warning":"跌破支撑"}'
    mock_llm = AsyncMock(spec=ILLMPort)
    mock_llm.generate.return_value = valid_json

    adapter = TechnicalAnalystAgentAdapter(llm_port=mock_llm)
    snapshot = TechnicalIndicatorsSnapshot(current_price=10.0, rsi_value=75.0)
    result = await adapter.analyze(
        ticker="000001.SZ",
        analysis_date="2024-01-15",
        snapshot=snapshot,
    )

    assert isinstance(result, TechnicalAnalysisAgentResult)
    assert result.result.signal == "BEARISH"
    assert result.result.confidence == 0.6
    assert result.result.key_technical_levels.support == 9.0
    assert result.result.key_technical_levels.resistance == 12.0
    assert result.raw_llm_output == valid_json
    assert isinstance(result.user_prompt, str) and len(result.user_prompt) > 0
    mock_llm.generate.assert_called_once()
    call_kw = mock_llm.generate.call_args[1]
    assert "000001.SZ" in call_kw["prompt"] or call_kw["prompt"]
    assert call_kw["temperature"] == 0.3


@pytest.mark.asyncio
async def test_agent_adapter_invalid_json_raises():
    """LLM 返回非 JSON 时，Agent 抛出 LLMOutputParseError（Spec：解析失败场景）。"""
    mock_llm = AsyncMock(spec=ILLMPort)
    mock_llm.generate.return_value = "not json at all"

    adapter = TechnicalAnalystAgentAdapter(llm_port=mock_llm)
    snapshot = TechnicalIndicatorsSnapshot()

    with pytest.raises(LLMOutputParseError):
        await adapter.analyze(
            ticker="000001.SZ",
            analysis_date="2024-01-15",
            snapshot=snapshot,
        )
