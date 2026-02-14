"""
Knowledge Center 模块专属配置。

定义 Neo4j 连接配置，从环境变量加载。
"""

from pydantic_settings import BaseSettings


class Neo4jConfig(BaseSettings):
    """
    Neo4j 连接配置。
    
    从环境变量读取 Neo4j 连接参数。
    """

    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


neo4j_config = Neo4jConfig()
