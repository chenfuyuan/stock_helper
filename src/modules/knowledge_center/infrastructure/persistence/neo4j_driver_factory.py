"""
Neo4j Driver 工厂函数。

提供创建与管理 Neo4j Driver 的工厂方法。
"""

from neo4j import Driver, GraphDatabase

from src.modules.knowledge_center.infrastructure.config import Neo4jConfig


def create_neo4j_driver(config: Neo4jConfig) -> Driver:
    """
    创建 Neo4j Driver 实例。
    
    Args:
        config: Neo4j 连接配置
    
    Returns:
        Neo4j Driver 实例
    """
    return GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
    )
