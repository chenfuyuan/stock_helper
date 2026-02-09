from typing import Optional, List
from loguru import logger
from src.shared.domain.ports.llm import ILLMProvider
from src.modules.llm_platform.infrastructure.router import LLMRouter
from src.modules.llm_platform.infrastructure.registry import LLMRegistry

class LLMService(ILLMProvider):
    """
    LLM 平台门面服务 (Facade Service)
    对外提供统一的大模型调用能力，封装了底层的路由、注册和适配逻辑。
    其他模块应通过此服务使用大模型能力，而非直接依赖基础设施层。
    """
    def __init__(self, registry: LLMRegistry = None):
        """
        初始化 LLM 服务。
        
        Args:
            registry (LLMRegistry, optional): LLM 注册表实例。如果未提供，将使用默认单例。
        """
        self.registry = registry or LLMRegistry()
        self.router = LLMRouter(self.registry)

    async def generate(
        self, 
        prompt: str, 
        system_message: Optional[str] = None, 
        temperature: float = 0.7,
        alias: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        调用大模型生成文本。支持通过别名指定模型或通过标签进行动态路由。
        
        Args:
            prompt (str): 用户输入的提示词。
            system_message (Optional[str]): 系统预设消息（System Prompt）。
            temperature (float): 采样温度 (0.0 - 2.0)，控制输出的随机性。
            alias (Optional[str]): 指定要使用的模型配置别名。如果提供，将忽略 tags。
            tags (Optional[List[str]]): 模型筛选标签。如果提供，将在匹配标签的模型中根据优先级选择。
            
        Returns:
            str: 大模型生成的文本内容。
            
        Raises:
            Exception: 当没有匹配的模型或底层 API 调用失败时抛出。
        """
        logger.info(f"LLM Generation request received. Alias={alias}, Tags={tags}")
        try:
            result = await self.router.generate(
                prompt, 
                system_message, 
                temperature, 
                alias=alias, 
                tags=tags
            )
            logger.info("LLM Generation completed successfully.")
            return result
        except Exception as e:
            logger.error(f"LLM Generation failed: {str(e)}")
            raise e
