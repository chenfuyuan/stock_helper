"""
Web 搜索应用服务：执行搜索并可选记录外部 API 调用日志。
"""
import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from src.shared.infrastructure.execution_context import current_execution_ctx
from src.modules.llm_platform.domain.ports.web_search import IWebSearchProvider
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
)

if TYPE_CHECKING:
    from src.shared.domain.dtos.external_api_call_log_dtos import ExternalAPICallLog
    from src.shared.domain.ports.external_api_call_log_repository import IExternalAPICallLogRepository

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Web 搜索应用服务

    作为跨模块调用的 Application 入口，对外暴露搜索能力。
    通过依赖注入接收 IWebSearchProvider 实现，隐藏 Infrastructure 实现细节。
    当注入 IExternalAPICallLogRepository 时，每次 search 会记录调用日志（写入失败不阻塞主流程）。
    """

    def __init__(
        self,
        provider: IWebSearchProvider,
        api_call_log_repository: "IExternalAPICallLogRepository | None" = None,
    ) -> None:
        self.provider = provider
        self._api_call_log_repository = api_call_log_repository

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        """
        执行 Web 搜索

        Args:
            request: 搜索请求

        Returns:
            WebSearchResponse: 搜索结果

        Raises:
            WebSearchConfigError: 配置错误
            WebSearchConnectionError: 网络连接错误
            WebSearchError: 搜索错误
        """
        logger.info("开始搜索，查询词: %s, 时效: %s, 条数: %s", request.query, request.freshness, request.count)

        ctx = current_execution_ctx.get()
        session_uuid: UUID | None = UUID(ctx.session_id) if ctx else None
        started = time.perf_counter()
        request_params = request.model_dump()

        try:
            response = await self.provider.search(request)
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.info("搜索完成，查询词: %s, 返回结果数: %s", request.query, len(response.results))
            await self._write_call_log(
                session_id=session_uuid,
                request_params=request_params,
                response_data=response.model_dump_json(),
                status_code=200,
                latency_ms=latency_ms,
                status="success",
                error_message=None,
            )
            return response
        except Exception as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            await self._write_call_log(
                session_id=session_uuid,
                request_params=request_params,
                response_data=None,
                status_code=None,
                latency_ms=latency_ms,
                status="failed",
                error_message=str(e),
            )
            raise

    async def _write_call_log(
        self,
        *,
        session_id: UUID | None,
        request_params: dict,
        response_data: str | None,
        status_code: int | None,
        latency_ms: int,
        status: str,
        error_message: str | None,
    ) -> None:
        """写入外部 API 调用日志，失败仅打 warning 不阻塞。"""
        if not self._api_call_log_repository:
            return
        from src.shared.domain.dtos.external_api_call_log_dtos import ExternalAPICallLog

        log = ExternalAPICallLog(
            id=uuid4(),
            session_id=session_id,
            service_name="bochai",
            operation="web-search",
            request_params=request_params,
            response_data=response_data,
            status_code=status_code,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
        try:
            await self._api_call_log_repository.save(log)
        except Exception as e:
            logger.warning("外部 API 调用日志写入失败，不阻塞主流程: %s", str(e))
