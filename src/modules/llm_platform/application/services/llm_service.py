"""
LLM 平台门面服务：统一大模型调用与调用审计。
"""

import time
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from loguru import logger

from src.modules.llm_platform.domain.dtos.llm_call_log_dtos import LLMCallLog
from src.modules.llm_platform.domain.ports.llm import ILLMProvider
from src.modules.llm_platform.infrastructure.registry import LLMRegistry
from src.modules.llm_platform.infrastructure.router import LLMRouter
from src.shared.infrastructure.execution_context import current_execution_ctx

if TYPE_CHECKING:
    from src.modules.llm_platform.domain.ports.llm_call_log_repository import (
        ILLMCallLogRepository,
    )


class LLMService(ILLMProvider):
    """
    LLM 平台门面服务 (Facade Service)
    对外提供统一的大模型调用能力，封装了底层的路由、注册和适配逻辑。
    其他模块应通过此服务使用大模型能力，而非直接依赖基础设施层。
    当注入 ILLMCallLogRepository 时，每次 generate 调用会审计写入日志（写入失败不阻塞主流程）。
    """

    def __init__(
        self,
        registry: LLMRegistry | None = None,
        call_log_repository: "ILLMCallLogRepository | None" = None,
    ) -> None:
        self.registry = registry or LLMRegistry()
        self.router = LLMRouter(self.registry)
        self._call_log_repository = call_log_repository

    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        alias: Optional[str] = None,
        tags: Optional[List[str]] = None,
        caller_module: str = "",
        caller_agent: Optional[str] = None,
    ) -> str:
        """
        调用大模型生成文本。支持通过别名指定模型或通过标签进行动态路由。

        Args:
            prompt: 用户输入的提示词。
            system_message: 系统预设消息（System Prompt）。
            temperature: 采样温度 (0.0 - 2.0)，控制输出的随机性。
            alias: 指定要使用的模型配置别名。如果提供，将忽略 tags。
            tags: 模型筛选标签。
            caller_module: 调用方模块名（用于审计日志，可选）。
            caller_agent: 调用方 Agent 标识（用于审计日志，可选）。

        Returns:
            大模型生成的文本内容。

        Raises:
            Exception: 当没有匹配的模型或底层 API 调用失败时抛出。
        """
        logger.info("LLM Generation request received. Alias=%s, Tags=%s", alias, tags)
        ctx = current_execution_ctx.get()
        session_uuid: UUID | None = UUID(ctx.session_id) if ctx else None
        started = time.perf_counter()
        try:
            result = await self.router.generate(
                prompt,
                system_message,
                temperature,
                alias=alias,
                tags=tags,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.info("LLM Generation completed successfully.")
            await self._write_call_log(
                session_id=session_uuid,
                caller_module=caller_module,
                caller_agent=caller_agent,
                prompt_text=prompt,
                system_message=system_message,
                completion_text=result,
                temperature=temperature,
                latency_ms=latency_ms,
                status="success",
                error_message=None,
            )
            return result
        except Exception as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.error("LLM Generation failed: %s", str(e))
            await self._write_call_log(
                session_id=session_uuid,
                caller_module=caller_module,
                caller_agent=caller_agent,
                prompt_text=prompt,
                system_message=system_message,
                completion_text=None,
                temperature=temperature,
                latency_ms=latency_ms,
                status="failed",
                error_message=str(e),
            )
            raise

    async def _write_call_log(
        self,
        *,
        session_id: UUID | None = None,
        caller_module: str,
        caller_agent: Optional[str],
        prompt_text: str,
        system_message: Optional[str],
        completion_text: Optional[str],
        temperature: float,
        latency_ms: int,
        status: str,
        error_message: Optional[str],
    ) -> None:
        """写入调用日志，失败仅打 warning 不阻塞。"""
        if not self._call_log_repository:
            return
        log = LLMCallLog(
            id=uuid4(),
            session_id=session_id,
            caller_module=caller_module or "unknown",
            caller_agent=caller_agent,
            model_name="routed",
            vendor="llm_platform",
            prompt_text=prompt_text,
            system_message=system_message,
            completion_text=completion_text,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            temperature=temperature,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
        try:
            await self._call_log_repository.save(log)
        except Exception as e:
            logger.warning("LLM 调用日志写入失败，不阻塞主流程: %s", str(e))
