"""
调用 LLM 的 Port 的 Adapter。
内部调用 llm_platform 的 LLMService.generate（Application 接口），
不直接依赖 llm_platform 的 router、registry 或 adapter 实现类。
"""
from typing import Optional

from src.modules.llm_platform.application.services.llm_service import LLMService
from src.modules.research.domain.ports.llm import ILLMPort


class LLMAdapter(ILLMPort):
    """通过 llm_platform 的 LLMService 调用大模型。"""

    def __init__(self, llm_service: LLMService):
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
