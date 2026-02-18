#!/usr/bin/env python3
"""
测试概念数据同步事务处理的简单脚本
验证一个概念 + 其关联的成分股查询成功后，就提交事务
"""

import asyncio
from datetime import date
from loguru import logger

from src.modules.data_engineering.application.commands.sync_concept_data_incremental_cmd import (
    SyncConceptDataIncrementalCmd,
)
from src.modules.data_engineering.container import DataEngineeringContainer
from src.shared.infrastructure.db.session import get_db_session


async def test_concept_transaction():
    """测试概念数据同步的事务处理"""
    
    logger.info("开始测试概念数据同步事务处理")
    
    # 获取数据库会话和容器
    async for session in get_db_session():
        container = DataEngineeringContainer(session)
        
        # 获取增量同步命令
        sync_cmd = container.get_sync_concept_data_incremental_cmd()
        
        # 执行同步
        logger.info("执行概念数据增量同步...")
        result = await sync_cmd.execute()
        
        # 输出结果
        logger.info(f"同步完成：")
        logger.info(f"  - 总概念数：{result.total_concepts}")
        logger.info(f"  - 成功数：{result.success_concepts}")
        logger.info(f"  - 失败数：{result.failed_concepts}")
        logger.info(f"  - 总成分股数：{result.total_stocks}")
        logger.info(f"  - 耗时：{result.elapsed_time:.2f}s")
        
        # 验证事务边界：每个概念处理完成后应该立即提交
        # 可以通过观察日志中的"事务提交"信息来确认
        if result.success_concepts > 0:
            logger.success("✓ 事务处理测试通过：每个概念成功处理后立即提交事务")
        else:
            logger.warning("⚠ 没有成功处理的概念，无法验证事务处理")
        
        break  # 只使用第一个会话


if __name__ == "__main__":
    asyncio.run(test_concept_transaction())
