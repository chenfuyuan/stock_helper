"""
generate_and_parse 异步函数的单元测试。

覆盖 spec llm-json-retry 的全部 Scenario：
- 首次成功 / 参数透传
- 首次失败重试成功 / 重试 prompt 包含错误信息 / 多次重试
- 重试耗尽 / max_retries=0
- LLM 连接异常透传 / 重试中连接异常
- 重试日志
"""

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import generate_and_parse

# ---------------------------------------------------------------------------
# 测试用 DTO 与辅助
# ---------------------------------------------------------------------------


class _SimpleDTO(BaseModel):
    score: int
    signal: str


_VALID_JSON = '{"score": 85, "signal": "bullish"}'
_INVALID_JSON = "这不是 JSON"


class _FakeLLMConnectionError(Exception):
    """模拟 LLMConnectionError，不依赖 llm_platform 模块。"""


# ---------------------------------------------------------------------------
# Scenario: 首次调用即成功
# ---------------------------------------------------------------------------


class TestFirstCallSuccess:
    @pytest.mark.asyncio
    async def test_single_call_returns_dto(self):
        mock_llm = AsyncMock(return_value=_VALID_JSON)
        result = await generate_and_parse(
            mock_llm,
            _SimpleDTO,
            prompt="分析",
            max_retries=1,
        )
        assert result.score == 85
        assert result.signal == "bullish"
        mock_llm.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario: 参数透传到 llm_call
# ---------------------------------------------------------------------------


class TestParameterPassthrough:
    @pytest.mark.asyncio
    async def test_prompt_system_message_temperature(self):
        mock_llm = AsyncMock(return_value=_VALID_JSON)
        await generate_and_parse(
            mock_llm,
            _SimpleDTO,
            prompt="分析这只股票",
            system_message="你是分析师",
            temperature=0.3,
        )
        mock_llm.assert_called_once_with("分析这只股票", "你是分析师", 0.3)


# ---------------------------------------------------------------------------
# Scenario: 首次失败、重试成功
# ---------------------------------------------------------------------------


class TestRetrySuccess:
    @pytest.mark.asyncio
    async def test_first_fail_retry_success(self):
        mock_llm = AsyncMock(side_effect=[_INVALID_JSON, _VALID_JSON])
        result = await generate_and_parse(
            mock_llm,
            _SimpleDTO,
            prompt="分析",
            max_retries=1,
        )
        assert result.score == 85
        assert mock_llm.call_count == 2


# ---------------------------------------------------------------------------
# Scenario: 重试 prompt 包含错误信息
# ---------------------------------------------------------------------------


class TestRetryPromptContent:
    @pytest.mark.asyncio
    async def test_retry_prompt_contains_error(self):
        mock_llm = AsyncMock(side_effect=[_INVALID_JSON, _VALID_JSON])
        await generate_and_parse(
            mock_llm,
            _SimpleDTO,
            prompt="原始prompt",
            max_retries=1,
        )
        # 第二次调用的 prompt 应包含错误反馈
        retry_prompt = mock_llm.call_args_list[1][0][0]
        assert "原始prompt" in retry_prompt
        assert "无法解析为合法 JSON" in retry_prompt


# ---------------------------------------------------------------------------
# Scenario: 多次重试
# ---------------------------------------------------------------------------


class TestMultipleRetries:
    @pytest.mark.asyncio
    async def test_two_retries_third_succeeds(self):
        mock_llm = AsyncMock(
            side_effect=[_INVALID_JSON, _INVALID_JSON, _VALID_JSON]
        )
        result = await generate_and_parse(
            mock_llm,
            _SimpleDTO,
            prompt="分析",
            max_retries=2,
        )
        assert result.score == 85
        assert mock_llm.call_count == 3


# ---------------------------------------------------------------------------
# Scenario: 所有尝试均失败（重试耗尽）
# ---------------------------------------------------------------------------


class TestAllAttemptsFail:
    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self):
        mock_llm = AsyncMock(return_value=_INVALID_JSON)
        with pytest.raises(LLMJsonParseError):
            await generate_and_parse(
                mock_llm,
                _SimpleDTO,
                prompt="分析",
                max_retries=1,
            )
        assert mock_llm.call_count == 2  # 1 初始 + 1 重试


# ---------------------------------------------------------------------------
# Scenario: max_retries 为 0 时不重试
# ---------------------------------------------------------------------------


class TestNoRetry:
    @pytest.mark.asyncio
    async def test_max_retries_zero_no_retry(self):
        mock_llm = AsyncMock(return_value=_INVALID_JSON)
        with pytest.raises(LLMJsonParseError):
            await generate_and_parse(
                mock_llm,
                _SimpleDTO,
                prompt="分析",
                max_retries=0,
            )
        mock_llm.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario: LLM 连接失败不重试
# ---------------------------------------------------------------------------


class TestLLMConnectionErrorPassthrough:
    @pytest.mark.asyncio
    async def test_connection_error_not_retried(self):
        mock_llm = AsyncMock(side_effect=_FakeLLMConnectionError("连接超时"))
        with pytest.raises(_FakeLLMConnectionError):
            await generate_and_parse(
                mock_llm,
                _SimpleDTO,
                prompt="分析",
                max_retries=2,
            )
        mock_llm.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario: 重试中 LLM 连接失败
# ---------------------------------------------------------------------------


class TestConnectionErrorDuringRetry:
    @pytest.mark.asyncio
    async def test_connection_error_during_retry_propagates(self):
        mock_llm = AsyncMock(
            side_effect=[_INVALID_JSON, _FakeLLMConnectionError("网络中断")]
        )
        with pytest.raises(_FakeLLMConnectionError):
            await generate_and_parse(
                mock_llm,
                _SimpleDTO,
                prompt="分析",
                max_retries=2,
            )
        assert mock_llm.call_count == 2  # 第一次解析失败，第二次连接异常


# ---------------------------------------------------------------------------
# Scenario: 重试日志（验证不报错，日志内容为可选断言）
# ---------------------------------------------------------------------------


class TestRetryLogging:
    @pytest.mark.asyncio
    async def test_retry_with_context_label(self):
        """重试时应记录 WARNING 日志（含 context_label）。不报非预期异常即通过。"""
        mock_llm = AsyncMock(side_effect=[_INVALID_JSON, _VALID_JSON])
        result = await generate_and_parse(
            mock_llm,
            _SimpleDTO,
            prompt="分析",
            max_retries=1,
            context_label="估值建模师",
        )
        assert result.score == 85
