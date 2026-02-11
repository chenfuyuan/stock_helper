import json
import os
from datetime import datetime
from loguru import logger
from src.shared.infrastructure.db.session import AsyncSessionLocal
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import StockRepositoryImpl
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import StockDailyRepositoryImpl
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_finance_repo import StockFinanceRepositoryImpl
from src.modules.data_engineering.infrastructure.external_apis.tushare.client import TushareClient
from src.modules.data_engineering.application.commands.sync_daily_history import SyncDailyHistoryUseCase
from src.modules.data_engineering.application.commands.sync_daily_bar_cmd import SyncDailyByDateUseCase
from src.modules.data_engineering.application.commands.sync_finance_cmd import SyncFinanceHistoryUseCase
from src.modules.data_engineering.application.commands.sync_incremental_finance_data import SyncIncrementalFinanceDataUseCase

STATE_FILE = "sync_daily_state.json"
FINANCE_STATE_FILE = "sync_finance_state.json"
FINANCE_FAILURE_FILE = "sync_finance_failures.json"

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

def load_finance_offset() -> int:
    if not os.path.exists(FINANCE_STATE_FILE):
        return 0
    try:
        with open(FINANCE_STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("offset", 0)
    except Exception:
        return 0

def save_finance_offset(offset: int):
    with open(FINANCE_STATE_FILE, "w") as f:
        json.dump({"offset": offset}, f)

def load_finance_failures() -> list[str]:
    """加载失败的股票代码"""
    if not os.path.exists(FINANCE_FAILURE_FILE):
        return []
    try:
        with open(FINANCE_FAILURE_FILE, "r") as f:
            data = json.load(f)
            return data.get("failures", [])
    except Exception:
        return []

def save_finance_failures(failures: list[str]):
    """保存失败的股票代码"""
    with open(FINANCE_FAILURE_FILE, "w") as f:
        json.dump({"failures": list(set(failures))}, f) # 去重保存

def append_finance_failures(new_failures: list[str]):
    """追加失败记录"""
    if not new_failures:
        return
    current = load_finance_failures()
    current.extend(new_failures)
    save_finance_failures(current)

async def sync_history_daily_data_job():
    """
    定时任务：同步股票历史日线数据（全量历史）
    
    描述:
        该任务会循环执行，直到同步完所有股票的历史数据。
        使用分页机制（offset/limit）来控制每次同步的股票数量，避免内存溢出。
        进度会保存在本地文件 `sync_daily_state.json` 中，以便中断后恢复。
    """
    logger.info("Running sync_history_daily_data_job (Loop Mode)...")
    
    limit = 50
    
    while True:
        # 1. 获取当前进度
        offset = load_offset()
        logger.info(f"Starting batch sync from offset {offset} with limit {limit}")
        
        # 2. 依赖注入
        async with AsyncSessionLocal() as session:
            stock_repo = StockRepositoryImpl(session)
            daily_repo = StockDailyRepositoryImpl(session)
            provider = TushareClient()
            
            use_case = SyncDailyHistoryUseCase(stock_repo, daily_repo, provider)
            
            try:
                # 3. 执行同步
                logger.debug(f"Executing SyncDailyHistoryUseCase with limit={limit}, offset={offset}")
                result = await use_case.execute(limit=limit, offset=offset)
                
                synced_count = result["synced_stocks"]
                total_rows = result["total_rows"]
                
                logger.info(f"Batch completed. Synced {synced_count} stocks, {total_rows} rows.")
                
                if synced_count == 0:
                    logger.info("No more stocks to sync. Resetting offset to 0 and pausing.")
                    save_offset(0)
                    break
                
                # 4. 更新进度
                offset += synced_count
                save_offset(offset)
                logger.debug(f"Updated offset to {offset}")
                
            except Exception as e:
                logger.exception(f"Job execution failed: {str(e)}")
                break

async def sync_daily_data_job():
    """
    定时任务：每日增量同步
    
    描述:
        每天收盘后执行，同步当天的股票日线数据。
        会自动获取当前日期作为同步日期。
    """
    logger.info("Running sync_daily_data_job...")
    
    async with AsyncSessionLocal() as session:
        daily_repo = StockDailyRepositoryImpl(session)
        provider = TushareClient()
        
        use_case = SyncDailyByDateUseCase(daily_repo, provider)
        
        today_str = datetime.now().strftime("%Y%m%d")
        
        try:
            logger.info(f"Starting daily sync for date: {today_str}")
            await use_case.execute(trade_date=today_str)
            logger.info(f"Daily sync job completed for date: {today_str}")
        except Exception as e:
            logger.exception(f"Daily sync job failed: {str(e)}")

async def sync_finance_history_job():
    """
    定时任务：同步历史财务数据（分批执行，带进度保存）

    描述:
        每批处理 100 只股票，进度保存在 sync_finance_state.json。
        Tushare 限速 200 次/分钟，单批约 100 次请求，耗时约 35s，安全不超限。
    """
    logger.info("Running sync_finance_history_job...")
    limit = 100
    start_date = "20200101"
    end_date = datetime.now().strftime("%Y%m%d")
    offset = load_finance_offset()

    async with AsyncSessionLocal() as session:
        stock_repo = StockRepositoryImpl(session)
        finance_repo = StockFinanceRepositoryImpl(session)
        provider = TushareClient()
        use_case = SyncFinanceHistoryUseCase(stock_repo, finance_repo, provider)

        try:
            logger.info(
                f"Starting finance history sync from {start_date} to {end_date}, offset={offset}, limit={limit}"
            )
            result = await use_case.execute(
                start_date=start_date,
                end_date=end_date,
                offset=offset,
                limit=limit,
            )
            batch_size = result.get("batch_size", 0)
            count = result.get("count", 0)
            if batch_size == 0:
                logger.info("No more stocks to sync. Resetting offset to 0.")
                save_finance_offset(0)
            else:
                offset += batch_size
                save_finance_offset(offset)
                logger.info(
                    f"Finance history batch completed. Synced {count} rows, offset now {offset}"
                )
        except Exception as e:
            logger.exception(f"Finance history sync job failed: {str(e)}")

async def sync_incremental_finance_job():
    """
    定时任务：增量同步财务数据
    
    描述:
        定期检查并同步最新的财务数据公告。
    """
    logger.info("Running sync_incremental_finance_job...")
    
    async with AsyncSessionLocal() as session:
        stock_repo = StockRepositoryImpl(session)
        finance_repo = StockFinanceRepositoryImpl(session)
        provider = TushareClient()
        
        use_case = SyncIncrementalFinanceDataUseCase(finance_repo, stock_repo, provider)
        
        try:
            logger.info("Starting incremental finance sync execution...")
            await use_case.execute()
            logger.info("Incremental finance sync job completed.")
        except Exception as e:
            logger.exception(f"Incremental finance sync job failed: {str(e)}")
