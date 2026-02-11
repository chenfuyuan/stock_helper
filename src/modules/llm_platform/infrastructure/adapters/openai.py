from typing import Optional

from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError
from loguru import logger

from src.modules.llm_platform.domain.exceptions import LLMConnectionError
from src.modules.llm_platform.infrastructure.adapters.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI 接口适配器
    支持 OpenAI 官方 API 以及兼容 OpenAI 协议的第三方服务（如 SiliconFlow）
    """
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(model)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
    async def generate(
        self, 
        prompt: str, 
        system_message: Optional[str] = None, 
        temperature: float = 0.7
    ) -> str:
        """
        调用 LLM 生成文本
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        logger.debug(f"Calling LLM API: model={self.model}, prompt_length={len(prompt)}")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            content = response.choices[0].message.content
            # API 可能返回 None（如部分 tool/function 场景），契约要求返回 str，统一转为空字符串
            result = content if content is not None else ""
            logger.debug(f"LLM Response received: length={len(result)}")
            return result
            
        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"LLM Connection/RateLimit Error: {str(e)}")
            raise LLMConnectionError(f"LLM Service Unavailable: {str(e)}")
        except APIError as e:
            logger.error(f"LLM API Error: {str(e)}")
            raise LLMConnectionError(f"LLM API Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected LLM Error: {str(e)}")
            raise LLMConnectionError(f"Unexpected Error: {str(e)}")
