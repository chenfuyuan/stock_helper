from typing import Optional

from loguru import logger
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from src.modules.llm_platform.domain.exceptions import LLMConnectionError
from src.modules.llm_platform.infrastructure.adapters.base import (
    BaseLLMProvider,
)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI 接口适配器
    支持 OpenAI 官方 API 以及兼容 OpenAI 协议的第三方服务（如 SiliconFlow）
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(model)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        调用 LLM 生成文本
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        try:
            # 记录请求的关键信息（不含敏感 key）
            logger.info(
                f"开始调用 LLM: {self.model} | Prompt 长度: {len(prompt)}, message: {messages}"
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                extra_body={"reasoning_split": True},
            )
            content = response.choices[0].message.content
            # API 可能返回 None（如部分 tool/function 场景），契约要求返回 str，统一转为空字符串
            result = content if content is not None else ""

            # 记录响应摘要，便于调试。如果是长文本，只截取前 50 个字符。
            log_preview = (
                result.replace("\n", " ")[:50] + "..."
                if len(result) > 50
                else result
            )
            logger.info(
                f"LLM 响应成功 | 长度: {len(result)} | 内容预览: {log_preview}"
            )
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
