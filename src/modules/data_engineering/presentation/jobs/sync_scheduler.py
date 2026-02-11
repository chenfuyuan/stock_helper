from datetime import datetime
from loguru import logger

from src.modules.data_engineering.application.factories.sync_factory import SyncUseCaseFactory
from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.shared.config import settings


async def sync_history_daily_data_job():
    """
    定时任务：同步股票历史日线数据（全量历史）
    
    描述:
        使用 SyncEngine 一次触发、自动分批、跑完全量。
        进度由 SyncEngine 管理（存储在 DB），支持断点续跑。
        
    改进:
        - 移除 JSON 文件进度管理，改为 DB 持久化
        - 通过工厂获取 SyncEngine，避免 Presentation 层直接依赖 Infrastructure
        - 一次触发即可跑完全量，无需外部循环
    """
    logger.info("开始执行历史日线全量同步任务...")
    
    try:
        async with SyncUseCaseFactory.create_sync_engine() as engine:
            config = {
                "batch_size": settings.SYNC_DAILY_HISTORY_BATCH_SIZE,
            }
            
            task = await engine.run_history_sync(
                job_type=SyncJobType.DAILY_HISTORY,
                config=config
            )
            
            logger.info(
                f"历史日线同步完成：task_id={task.id}, "
                f"status={task.status.value}, total_processed={task.total_processed}"
            )
            
    except Exception as e:
        logger.error(f"历史日线同步任务失败：{str(e)}", exc_info=True)


async def sync_daily_data_job():
    """
    定时任务：每日增量同步日线数据
    
    描述:
        每天收盘后执行，同步当天的股票日线数据。
        包含遗漏检测与自动补偿：若 DB 中最新交易日与当前日期有间隔，自动补偿缺失日期。
        
    改进:
        - 通过 SyncEngine 的增量同步方法，自动检测并补偿遗漏日期
        - 无需手动管理日期区间
    """
    logger.info("开始执行日线增量同步任务...")
    
    try:
        async with SyncUseCaseFactory.create_sync_engine() as engine:
            today_str = datetime.now().strftime("%Y%m%d")
            
            result = await engine.run_incremental_daily_sync(target_date=today_str)
            
            logger.info(
                f"日线增量同步完成：synced_dates={result.get('synced_dates')}, "
                f"total_count={result.get('total_count')}, message={result.get('message')}"
            )
            
    except Exception as e:
        logger.error(f"日线增量同步任务失败：{str(e)}", exc_info=True)


async def sync_finance_history_job():
    """
    定时任务：同步历史财务数据（全量历史）
    
    描述:
        使用 SyncEngine 一次触发、自动分批、跑完全量。
        进度由 SyncEngine 管理（存储在 DB），支持断点续跑。
        
    改进:
        - 移除 JSON 文件进度管理，改为 DB 持久化
        - 通过工厂获取 SyncEngine，避免 Presentation 层直接依赖 Infrastructure
        - 起始日期和批大小从配置读取
    """
    logger.info("开始执行历史财务全量同步任务...")
    
    try:
        async with SyncUseCaseFactory.create_sync_engine() as engine:
            config = {
                "batch_size": settings.SYNC_FINANCE_HISTORY_BATCH_SIZE,
                "start_date": settings.SYNC_FINANCE_HISTORY_START_DATE,
                "end_date": datetime.now().strftime("%Y%m%d"),
            }
            
            task = await engine.run_history_sync(
                job_type=SyncJobType.FINANCE_HISTORY,
                config=config
            )
            
            logger.info(
                f"历史财务同步完成：task_id={task.id}, "
                f"status={task.status.value}, total_processed={task.total_processed}"
            )
            
    except Exception as e:
        logger.error(f"历史财务同步任务失败：{str(e)}", exc_info=True)


async def sync_incremental_finance_job():
    """
    定时任务：增量同步财务数据
    
    描述:
        定期检查并同步最新的财务数据公告。
        包含失败重试机制：自动重试 DB 中未解决的失败记录。
        
    改进:
        - 移除 JSON 文件失败记录，改为 DB 持久化
        - 通过工厂获取 Use Case，封装依赖注入
        - 失败重试和缺数补齐上限从配置读取
    """
    logger.info("开始执行财务增量同步任务...")
    
    try:
        async with SyncUseCaseFactory.create_incremental_finance_use_case() as use_case:
            result = await use_case.execute()
            
            logger.info(
                f"财务增量同步完成：synced_count={result.get('synced_count')}, "
                f"failed_count={result.get('failed_count')}, "
                f"retry_count={result.get('retry_count')}, "
                f"retry_success_count={result.get('retry_success_count')}, "
                f"target_period={result.get('target_period')}"
            )
            
    except Exception as e:
        logger.error(f"财务增量同步任务失败：{str(e)}", exc_info=True)
