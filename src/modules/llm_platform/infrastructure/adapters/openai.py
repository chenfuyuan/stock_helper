from typing import Optional
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError
from loguru import logger

from src.shared.domain.exceptions import LLMConnectionError
from src.modules.llm_platform.infrastructure.adapters.base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
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
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"LLM Connection/RateLimit Error: {str(e)}")
            raise LLMConnectionError(f"LLM Service Unavailable: {str(e)}")
        except APIError as e:
            logger.error(f"LLM API Error: {str(e)}")
            raise LLMConnectionError(f"LLM API Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected LLM Error: {str(e)}")
            raise LLMConnectionError(f"Unexpected Error: {str(e)}")
