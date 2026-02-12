from typing import List, Union, Optional
import json

from pydantic import AnyHttpUrl, PostgresDsn, validator, BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用全局配置类
    使用 Pydantic BaseSettings 自动加载环境变量
    """
    PROJECT_NAME: str = "Stock Helper"
    API_V1_STR: str = "/api/v1"
    
    # 运行环境: local, dev, prod
    ENVIRONMENT: str = "local"
    
    # CORS (跨域资源共享) 配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """
        验证并处理 CORS 域名配置
        支持逗号分隔的字符串或列表格式
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 数据库配置
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "stock_helper"
    POSTGRES_PORT: int = 5432
    SQLALCHEMY_DATABASE_URI: Union[str, PostgresDsn] | None = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, str]) -> str:
        """
        组装数据库连接字符串
        如果未直接提供 URI，则根据各个参数构建 PostgreSQL 异步连接字符串
        """
        if isinstance(v, str):
            return v
        
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"{values.get('POSTGRES_DB') or ''}",
        ).unicode_string()

    # Tushare 数据接口配置
    TUSHARE_TOKEN: str = "your_tushare_token_here"
    
    # Tushare API 限速配置：最小调用间隔（秒）
    # 默认 0.35s ≈ 170 次/分钟，低于 Tushare 大部分 API 的 200 次/分钟限制
    TUSHARE_MIN_INTERVAL: float = 0.35

    # 数据同步引擎配置
    # 历史日线同步的每批股票数量，影响单次批处理的消息条数和内存占用
    SYNC_DAILY_HISTORY_BATCH_SIZE: int = 50
    # 历史财务同步的每批股票数量
    SYNC_FINANCE_HISTORY_BATCH_SIZE: int = 100
    # 历史财务同步的起始日期（格式：YYYYMMDD），建议根据具体存储需求调整
    SYNC_FINANCE_HISTORY_START_DATE: str = "20200101"
    # 增量财务同步中"缺数补齐"查询的上限条数，用于性能保护
    SYNC_INCREMENTAL_MISSING_LIMIT: int = 300
    # 同步失败后的最大重试次数，建议范围 3-10
    SYNC_FAILURE_MAX_RETRIES: int = 3

    # LLM 平台配置
    # 默认使用的模型供应商
    LLM_PROVIDER: str = "openai"  # 可选: openai, anthropic, azure 等
    LLM_API_KEY: str = "your_llm_api_key_here"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-3.5-turbo"

    # 博查 AI Web Search 配置
    BOCHA_API_KEY: str = ""
    BOCHA_BASE_URL: str = "https://api.bochaai.com"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
