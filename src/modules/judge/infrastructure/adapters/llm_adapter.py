"""
Judge 模块的 LLM Port 实现。

内部委托 llm_platform 的 LLMService.generate()，不直接依赖 llm_platform 的 router/registry。
"""

from typing import Optional

from src.modules.judge.domain.ports.llm_port import ILLMPort
from src.modules.llm_platform.application.services.llm_service import (
    LLMService,
)


class LLMAdapter(ILLMPort):
    """通过 llm_platform 的 LLMService 调用大模型。"""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        return await self._llm.generate(
            prompt=prompt,
            system_message=system_message,
            temperature=temperature,
        )
