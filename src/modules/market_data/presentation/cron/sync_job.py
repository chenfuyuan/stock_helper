import json
import os
from datetime import datetime
from loguru import logger
from src.shared.infrastructure.db.session import AsyncSessionLocal
from src.modules.market_data.infrastructure.adapters.persistence.repositories.stock_repository import StockRepositoryImpl
from src.modules.market_data.infrastructure.adapters.persistence.repositories.stock_daily_repository import StockDailyRepositoryImpl
from src.modules.market_data.infrastructure.adapters.persistence.repositories.stock_finance_repository import StockFinanceRepositoryImpl
from src.modules.market_data.infrastructure.adapters.tushare.tushare_api import TushareService
from src.modules.market_data.application.use_cases.sync_daily_history import SyncDailyHistoryUseCase
from src.modules.market_data.application.use_cases.sync_daily_by_date import SyncDailyByDateUseCase
from src.modules.market_data.application.use_cases.sync_finance_history import SyncFinanceHistoryUseCase
from src.modules.market_data.application.use_cases.sync_incremental_finance_data import SyncIncrementalFinanceDataUseCase

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
    循环执行直到同步完所有数据
    """
    logger.info("Running sync_history_daily_data_job (Loop Mode)...")
    
    limit = 50
    
    while True:
        # 1. 获取当前进度
        offset = load_offset()
        logger.info(f"Starting batch sync from offset {offset} with limit {limit}")
        
        # 2. 依赖注入
        # 注意：每次循环创建一个新的 Session，避免长时间占用
        async with AsyncSessionLocal() as session:
            stock_repo = StockRepositoryImpl(session)
            daily_repo = StockDailyRepositoryImpl(session)
            provider = TushareService()
            
            use_case = SyncDailyHistoryUseCase(stock_repo, daily_repo, provider)
            
            try:
                # 3. 执行同步
                result = await use_case.execute(limit=limit, offset=offset)
                
                synced_count = result["synced_stocks"]
                total_msg = result["message"]
                
                logger.info(f"Batch result: {total_msg}")
                
                # 4. 更新进度与判断循环
                if synced_count > 0:
                    # 只有确实同步到了数据才更新 offset
                    new_offset = offset + limit
                    save_offset(new_offset)
                    logger.info(f"Updated offset to {new_offset}")
                    # 继续下一轮循环
                else:
                    # 如果没有同步到数据
                    if "No stocks found" in total_msg:
                        logger.info("All stocks synced. Resetting offset to 0 and stopping job.")
                        save_offset(0)
                        break  # 退出循环，任务结束
                    else:
                        # 本批次股票存在但无数据（如全失败或无行情），继续下一批
                        new_offset = offset + limit
                        save_offset(new_offset)
                        logger.info(f"No valid data in this batch, moving to next batch. Offset: {new_offset}")
                        # 继续下一轮循环
            except Exception as e:
                logger.error(f"Batch execution failed: {str(e)}")
                # 发生异常时，为了防止死循环重试，可以选择退出或者休眠后重试
                # 这里选择休眠后继续下一轮（假设是临时网络问题），或者你可以选择 break
                # 为了安全起见，这里记录错误并退出当前 Job，等待下一次调度触发（虽然是 Loop 模式，但如果有未捕获异常还是稳妥点）
                # 但这里我们捕获了 Exception，所以可以选择 break 或者 continue
                # 考虑到可能是 API 限制等，我们 break 吧，让调度器下一次再试
                logger.warning("Stopping job due to exception.")
                break

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

async def sync_history_finance_job():
    """
    定时任务：同步股票历史财务指标数据
    """
    logger.info("Running sync_history_finance_job (Loop Mode)...")
    limit = 50
    while True:
        offset = load_finance_offset()
        logger.info(f"Starting finance batch sync from offset {offset} with limit {limit}")
        
        async with AsyncSessionLocal() as session:
            stock_repo = StockRepositoryImpl(session)
            finance_repo = StockFinanceRepositoryImpl(session)
            provider = TushareService()
            
            use_case = SyncFinanceHistoryUseCase(stock_repo, finance_repo, provider)
            
            try:
                result = await use_case.execute(limit=limit, offset=offset)
                synced_count = result["synced_stocks"]
                failed_stocks = result.get("failed_stocks", [])
                total_msg = result["message"]
                
                # 记录失败的股票
                if failed_stocks:
                    logger.warning(f"Recording {len(failed_stocks)} failed stocks.")
                    append_finance_failures(failed_stocks)

                logger.info(f"Finance batch result: {total_msg}")
                
                if synced_count > 0:
                    new_offset = offset + limit
                    save_finance_offset(new_offset)
                else:
                    if "No stocks found" in total_msg:
                        logger.info("All stocks synced (finance). Resetting offset to 0 and stopping job.")
                        save_finance_offset(0)
                        break
                    else:
                        new_offset = offset + limit
                        save_finance_offset(new_offset)
                        logger.info(f"No valid finance data in this batch, moving to next. Offset: {new_offset}")
            except Exception as e:
                logger.error(f"Finance batch execution failed: {str(e)}")
                logger.warning("Stopping finance job due to exception.")
                break

async def sync_incremental_finance_job(actual_date: str = None):
    """
    定时任务：增量同步股票财务指标数据（基于财报披露计划 + 补漏）
    :param actual_date: 实际披露日期，默认当天
    """
    logger.info(f"Running sync_incremental_finance_job for date {actual_date or 'today'}...")
    
    async with AsyncSessionLocal() as session:
        finance_repo = StockFinanceRepositoryImpl(session)
        stock_repo = StockRepositoryImpl(session)
        provider = TushareService()
        
        use_case = SyncIncrementalFinanceDataUseCase(finance_repo, stock_repo, provider)
        
        try:
            result = await use_case.execute(actual_date=actual_date)
            logger.info(f"Incremental finance sync result: {json.dumps(result, ensure_ascii=False)}")
            
            if result['status'] == 'failed':
                logger.error(f"Incremental finance sync failed: {result.get('message')}")
                
        except Exception as e:
            logger.error(f"Incremental finance sync job failed: {str(e)}")

