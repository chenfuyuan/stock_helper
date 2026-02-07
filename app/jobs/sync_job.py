import json
import os
from datetime import datetime
from loguru import logger
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.repositories.stock_repository import StockRepositoryImpl
from app.infrastructure.repositories.stock_daily_repository import StockDailyRepositoryImpl
from app.infrastructure.acl.tushare_service import TushareService
from app.application.stock.use_cases.sync_daily_history import SyncDailyHistoryUseCase

STATE_FILE = "sync_daily_state.json"

def load_offset() -> int:
    """从文件加载同步进度"""
    if not os.path.exists(STATE_FILE):
        return 0
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("offset", 0)
    except Exception:
        return 0

def save_offset(offset: int):
    """保存同步进度到文件"""
    with open(STATE_FILE, "w") as f:
        json.dump({"offset": offset}, f)

async def sync_history_daily_data_job():
    """
    定时任务：同步股票历史日线数据（全量历史）
    """
    logger.info("Running sync_history_daily_data_job...")
    
    # 1. 获取当前进度
    offset = load_offset()
    limit = 500
    
    # 2. 依赖注入
    # 注意：Job 运行在独立线程/协程中，需要手动创建 DB Session
    async with AsyncSessionLocal() as session:
        stock_repo = StockRepositoryImpl(session)
        daily_repo = StockDailyRepositoryImpl(session)
        provider = TushareService()
        
        use_case = SyncDailyHistoryUseCase(stock_repo, daily_repo, provider)
        
        # 3. 执行同步
        result = await use_case.execute(limit=limit, offset=offset)
        
        synced_count = result["synced_stocks"]
        total_msg = result["message"]
        
        logger.info(f"Job result: {total_msg}")
        
        # 4. 更新进度
        if synced_count > 0:
            # 只有确实同步到了数据才更新 offset
            new_offset = offset + limit
            save_offset(new_offset)
            logger.info(f"Updated offset to {new_offset}")
        else:
            # 如果没有同步到数据，可能是跑完了所有股票
            # 或者本批次全失败了。
            if "No stocks found" in total_msg:
                logger.info("All stocks synced. Resetting offset to 0.")
                save_offset(0)
            else:
                # 还有一种情况是本批次股票都存在但都没有数据或都失败了
                # 这种情况下我们也应该往下走，否则会死循环
                new_offset = offset + limit
                save_offset(new_offset)
                logger.info(f"No valid data in this batch, moving to next batch. Offset: {new_offset}")

from app.application.stock.use_cases.sync_daily_by_date import SyncDailyByDateUseCase

async def sync_daily_by_date_job(trade_date: str = None):
    """
    定时任务：同步指定日期的所有股票日线数据（增量更新）
    如果不传日期，默认同步当天
    """
    logger.info(f"Running sync_daily_by_date_job...")
    
    async with AsyncSessionLocal() as session:
        daily_repo = StockDailyRepositoryImpl(session)
        provider = TushareService()
        
        # 使用 UseCase 封装业务逻辑
        use_case = SyncDailyByDateUseCase(daily_repo, provider)
        
        try:
            result = await use_case.execute(trade_date=trade_date)
            logger.info(f"Job result: {result['message']}")
                
        except Exception as e:
            logger.error(f"Job failed: {str(e)}")
