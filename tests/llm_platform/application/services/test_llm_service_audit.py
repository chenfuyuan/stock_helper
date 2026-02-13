"""
任务 12.4：测试 LLMService 调用审计（成功、失败、无上下文降级）。
"""
from unittest.mock import AsyncMock

import pytest

from src.modules.llm_platform.application.services.llm_service import LLMService
from src.shared.infrastructure.execution_context import (
    ExecutionContext,
    current_execution_ctx,
)


@pytest.fixture
def mock_call_log_repository():
    """Mock ILLMCallLogRepository，记录每次 save 调用。"""
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def llm_service_with_audit(mock_call_log_repository):
    """带审计仓储的 LLMService，router 需在测试中替换为 mock。"""
    return LLMService(call_log_repository=mock_call_log_repository)


@pytest.mark.asyncio
async def test_llm_success_writes_call_log_with_session_id(
    llm_service_with_audit, mock_call_log_repository
):
    """成功调用时写入审计日志，且 session_id 来自 ExecutionContext。"""
    llm_service_with_audit.router = AsyncMock()
    llm_service_with_audit.router.generate = AsyncMock(return_value="模型回复内容")

    token = current_execution_ctx.set(ExecutionContext(session_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))
    try:
        result = await llm_service_with_audit.generate(
            prompt="你好",
            caller_module="research",
            caller_agent="technical_analyst",
        )
        assert result == "模型回复内容"
        assert mock_call_log_repository.save.await_count == 1
        call_args = mock_call_log_repository.save.await_args
        log = call_args[0][0]
        assert str(log.session_id) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert log.status == "success"
        assert log.completion_text == "模型回复内容"
        assert log.error_message is None
    finally:
        current_execution_ctx.reset(token)


@pytest.mark.asyncio
async def test_llm_failure_writes_call_log_with_failed_status(
    llm_service_with_audit, mock_call_log_repository
):
    """LLM 调用抛异常时仍写入审计日志，status=failed，error_message 有值。"""
    llm_service_with_audit.router = AsyncMock()
    llm_service_with_audit.router.generate = AsyncMock(
        side_effect=Exception("API 超时")
    )

    token = current_execution_ctx.set(ExecutionContext(session_id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff"))
    try:
        with pytest.raises(Exception, match="API 超时"):
            await llm_service_with_audit.generate(prompt="你好")
        assert mock_call_log_repository.save.await_count == 1
        log = mock_call_log_repository.save.await_args[0][0]
        assert log.status == "failed"
        assert log.error_message == "API 超时"
        assert log.completion_text is None
    finally:
        current_execution_ctx.reset(token)


@pytest.mark.asyncio
async def test_llm_no_context_writes_log_with_null_session_id(
    llm_service_with_audit, mock_call_log_repository
):
    """无 ExecutionContext 时仍可调用并写日志，session_id 为 None（降级）。"""
    llm_service_with_audit.router = AsyncMock()
    llm_service_with_audit.router.generate = AsyncMock(return_value="ok")

    # 不设置 current_execution_ctx
    result = await llm_service_with_audit.generate(prompt="hello")
    assert result == "ok"
    assert mock_call_log_repository.save.await_count == 1
    log = mock_call_log_repository.save.await_args[0][0]
    assert log.session_id is None
    assert log.status == "success"
