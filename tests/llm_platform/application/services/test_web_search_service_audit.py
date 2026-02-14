"""
任务 12.5：测试 WebSearchService 调用日志（成功、失败、无上下文降级）。
"""

from unittest.mock import AsyncMock

import pytest

from src.modules.llm_platform.application.services.web_search_service import (
    WebSearchService,
)
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
)
from src.shared.infrastructure.execution_context import (
    ExecutionContext,
    current_execution_ctx,
)


@pytest.fixture
def mock_api_call_log_repository():
    """Mock IExternalAPICallLogRepository。"""
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def mock_provider():
    """Mock IWebSearchProvider。"""
    return AsyncMock()


@pytest.mark.asyncio
async def test_web_search_success_writes_log_with_session_id(
    mock_provider, mock_api_call_log_repository
):
    """搜索成功时写入外部 API 调用日志，session_id 来自 ExecutionContext。"""
    mock_provider.search = AsyncMock(
        return_value=WebSearchResponse(
            query="测试", total_matches=0, results=[]
        )
    )
    service = WebSearchService(
        provider=mock_provider,
        api_call_log_repository=mock_api_call_log_repository,
    )

    token = current_execution_ctx.set(
        ExecutionContext(session_id="cccccccc-dddd-eeee-ffff-000000000001")
    )
    try:
        request = WebSearchRequest(query="测试")
        response = await service.search(request)
        assert response.query == "测试"
        assert mock_api_call_log_repository.save.await_count == 1
        log = mock_api_call_log_repository.save.await_args[0][0]
        assert str(log.session_id) == "cccccccc-dddd-eeee-ffff-000000000001"
        assert log.status == "success"
        assert log.status_code == 200
        assert log.error_message is None
    finally:
        current_execution_ctx.reset(token)


@pytest.mark.asyncio
async def test_web_search_failure_writes_log_with_failed_status(
    mock_provider, mock_api_call_log_repository
):
    """搜索抛异常时仍写入调用日志，status=failed。"""
    mock_provider.search = AsyncMock(side_effect=Exception("网络错误"))
    service = WebSearchService(
        provider=mock_provider,
        api_call_log_repository=mock_api_call_log_repository,
    )

    token = current_execution_ctx.set(
        ExecutionContext(session_id="dddddddd-eeee-ffff-0000-111111111111")
    )
    try:
        with pytest.raises(Exception, match="网络错误"):
            await service.search(WebSearchRequest(query="测试"))
        assert mock_api_call_log_repository.save.await_count == 1
        log = mock_api_call_log_repository.save.await_args[0][0]
        assert log.status == "failed"
        assert log.error_message == "网络错误"
        assert log.response_data is None
    finally:
        current_execution_ctx.reset(token)


@pytest.mark.asyncio
async def test_web_search_no_context_writes_log_with_null_session_id(
    mock_provider, mock_api_call_log_repository
):
    """无 ExecutionContext 时仍可搜索并写日志，session_id 为 None。"""
    mock_provider.search = AsyncMock(
        return_value=WebSearchResponse(query="q", total_matches=0, results=[])
    )
    service = WebSearchService(
        provider=mock_provider,
        api_call_log_repository=mock_api_call_log_repository,
    )

    response = await service.search(WebSearchRequest(query="q"))
    assert response.query == "q"
    assert mock_api_call_log_repository.save.await_count == 1
    log = mock_api_call_log_repository.save.await_args[0][0]
    assert log.session_id is None
    assert log.status == "success"
