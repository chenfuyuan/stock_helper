from abc import ABC, abstractmethod
from typing import Optional

class ILLMProvider(ABC):
    """
    LLM 提供商抽象基类 (Strategy Interface)
    定义了所有 LLM 实现必须遵循的通用接口
    """

    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_message: Optional[str] = None, 
        temperature: float = 0.7
    ) -> str:
        """
        生成文本回复
        
        Args:
            prompt: 用户输入的提示词
            system_message: 系统预设指令 (可选)
            temperature: 温度参数 (0.0 - 1.0)，控制生成随机性
            
        Returns:
            str: 模型生成的文本内容
            
        Raises:
            LLMConnectionError: 当调用底层 API 失败时抛出
        """
        pass
