"""
LLM 平台模块专属配置。

将 LLM、博查 Web Search 相关配置从 shared/config 下沉到本模块，实现配置按 Bounded Context 隔离。
"""

from pydantic_settings import BaseSettings


class LLMPlatformConfig(BaseSettings):
    """LLM 平台模块配置：模型供应商与博查 API 参数。"""

    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = "your_llm_api_key_here"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-3.5-turbo"
    BOCHA_API_KEY: str = ""
    BOCHA_BASE_URL: str = "https://api.bochaai.com"

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


llm_config = LLMPlatformConfig()
