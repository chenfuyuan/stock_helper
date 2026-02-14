"""
Debate 模块的 LLM Port。

与 Research 的 ILLMPort 签名一致但独立定义，由 Infrastructure 的 LLMAdapter 桥接 llm_platform。
"""

from abc import ABC, abstractmethod
from typing import Optional


class ILLMPort(ABC):
    """调用 LLM 的抽象接口。"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """生成文本。"""
        raise NotImplementedError
