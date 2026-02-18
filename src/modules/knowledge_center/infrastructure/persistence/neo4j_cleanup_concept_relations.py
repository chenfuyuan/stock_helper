"""
Neo4j 概念关系数据清理脚本。

用于删除 Neo4j 中的所有概念关系数据，但保留股票图谱功能。
仅删除 Concept 节点间的关系，保留 Stock 节点和其他维度节点的关系。
"""

from loguru import logger
from neo4j import Driver

from src.modules.knowledge_center.infrastructure.config import neo4j_config
from src.modules.knowledge_center.infrastructure.persistence.neo4j_driver_factory import (
    create_neo4j_driver,
)


def cleanup_concept_relations(driver: Driver) -> None:
    """
    清理 Neo4j 中的概念关系数据。
    
    删除所有 Concept 节点间的关系，但保留：
    - Stock 节点及其关系
    - Concept 节点本身
    - Stock 与 Concept 之间的 BELONGS_TO_CONCEPT 关系
    
    Args:
        driver: Neo4j Driver 实例
    """
    with driver.session() as session:
        try:
            # 删除 Concept 节点间的所有关系
            logger.info("开始删除 Concept 节点间的关系...")
            result = session.run("""
                MATCH (c1:Concept)-[r]-(c2:Concept)
                DELETE r
                RETURN count(r) as deleted_count
            """)
            deleted_count = result.single()["deleted_count"]
            logger.info(f"已删除 {deleted_count} 条概念关系")
            
            # 验证清理结果
            logger.info("验证概念关系清理结果...")
            result = session.run("""
                MATCH (c1:Concept)-[r]-(c2:Concept)
                RETURN count(r) as remaining_count
            """)
            remaining_count = result.single()["remaining_count"]
            
            if remaining_count == 0:
                logger.info("✓ 概念关系清理完成")
            else:
                logger.warning(f"⚠️  仍有 {remaining_count} 条概念关系未清理")
                
        except Exception as e:
            logger.error(f"清理概念关系失败: {str(e)}")
            raise


def verify_stock_graph_integrity(driver: Driver) -> None:
    """
    验证股票图谱数据的完整性。
    
    确保股票相关数据未被误删。
    
    Args:
        driver: Neo4j Driver 实例
    """
    with driver.session() as session:
        try:
            # 检查 Stock 节点数量
            result = session.run("MATCH (s:Stock) RETURN count(s) as stock_count")
            stock_count = result.single()["stock_count"]
            logger.info(f"Stock 节点数量: {stock_count}")
            
            # 检查 Stock 与 Concept 的关系
            result = session.run("""
                MATCH (s:Stock)-[r:BELONGS_TO_CONCEPT]-(c:Concept)
                RETURN count(r) as relation_count
            """)
            relation_count = result.single()["relation_count"]
            logger.info(f"Stock-Concept 关系数量: {relation_count}")
            
            # 检查其他维度节点
            dimensions = ["Industry", "Area", "Market", "Exchange"]
            for dimension in dimensions:
                result = session.run(f"MATCH (n:{dimension}) RETURN count(n) as count")
                count = result.single()["count"]
                logger.info(f"{dimension} 节点数量: {count}")
            
            logger.info("✓ 股票图谱完整性验证通过")
            
        except Exception as e:
            logger.error(f"验证股票图谱完整性失败: {str(e)}")
            raise


def main() -> None:
    """主函数：执行概念关系清理。"""
    logger.info("开始清理 Neo4j 概念关系数据...")
    
    try:
        # 创建 Neo4j 连接
        driver = create_neo4j_driver(neo4j_config)
        
        # 清理概念关系
        cleanup_concept_relations(driver)
        
        # 验证股票图谱完整性
        verify_stock_graph_integrity(driver)
        
        logger.info("✓ Neo4j 概念关系清理完成")
        
    except Exception as e:
        logger.error(f"清理失败: {str(e)}")
        raise
    finally:
        if 'driver' in locals():
            driver.close()


if __name__ == "__main__":
    main()
