"""
调用 LLM 的 Port。
Research 仅依赖此抽象，由 Infrastructure 的 Adapter 调用 llm_platform 的 Application 接口。
"""
from abc import ABC, abstractmethod
from typing import Optional


class ILLMPort(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        raise NotImplementedError
