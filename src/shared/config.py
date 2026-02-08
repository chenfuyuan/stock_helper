from typing import List, Union

from pydantic import AnyHttpUrl, PostgresDsn, validator
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

    # Tushare 配置
    TUSHARE_TOKEN: str = "your_tushare_token_here"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
