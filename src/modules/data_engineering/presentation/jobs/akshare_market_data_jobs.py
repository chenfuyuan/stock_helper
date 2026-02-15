"""
AkShare市场数据同步任务
"""

from datetime import datetime
from loguru import logger

from src.modules.data_engineering.application.commands.sync_akshare_market_data_cmd import (
    SyncAkShareMarketDataCmd,
)
from src.modules.data_engineering.container import DataEngineeringContainer
from src.modules.foundation.infrastructure.execution_tracker import ExecutionTracker
from src.modules.foundation.infrastructure.persistence.repositories.scheduler_execution_log_repo import SchedulerExecutionLogRepository
from src.shared.infrastructure.db.session import AsyncSessionLocal


async def sync_akshare_market_data_job(target_date: str | None = None):
    """
    定时任务：同步AkShare市场数据（涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向）
    
    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    logger.info(f"开始执行AkShare市场数据同步任务... 目标日期: {target_date or '今天'}")

    async with AsyncSessionLocal() as session:
        repo = SchedulerExecutionLogRepository(session)
        async with ExecutionTracker(job_id="sync_akshare_market_data", repo=repo):
            # 获取依赖注入容器
            container = DataEngineeringContainer(session)
            
            # 创建AkShare市场数据同步命令
            sync_cmd = container.get_sync_akshare_market_data_cmd()
            
            # 转换日期格式
            from datetime import datetime
            if target_date:
                trade_date = datetime.strptime(target_date, "%Y%m%d").date()
            else:
                trade_date = datetime.now().date()
            
            # 执行同步
            result = await sync_cmd.execute(trade_date=trade_date)
            
            logger.info(
                f"AkShare市场数据同步完成：涨停池={result.limit_up_pool_count}, "
                f"炸板池={result.broken_board_count}, 昨日涨停={result.previous_limit_up_count}, "
                f"龙虎榜={result.dragon_tiger_count}, 板块资金={result.sector_capital_flow_count}"
            )
