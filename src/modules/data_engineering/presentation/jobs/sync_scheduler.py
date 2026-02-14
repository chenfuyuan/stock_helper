from datetime import datetime

from loguru import logger

from src.modules.data_engineering.application.factories.sync_factory import (
    SyncUseCaseFactory,
)
from src.modules.data_engineering.application.commands.sync_concept_data_cmd import (
    SyncConceptDataCmd,
)
from src.modules.data_engineering.container import DataEngineeringContainer
from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.modules.data_engineering.infrastructure.config import de_config


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
                "batch_size": de_config.SYNC_DAILY_HISTORY_BATCH_SIZE,
            }

            task = await engine.run_history_sync(job_type=SyncJobType.DAILY_HISTORY, config=config)

            logger.info(
                f"历史日线同步完成：task_id={task.id}, "
                f"status={task.status.value}, total_processed={task.total_processed}"
            )

    except Exception as e:
        logger.error(f"历史日线同步任务失败：{str(e)}", exc_info=True)


async def sync_daily_data_job(target_date: str | None = None):
    """
    定时任务：每日增量同步日线数据

    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    logger.info(f"开始执行日线增量同步任务... 目标日期: {target_date or '今天'}")

    try:
        async with SyncUseCaseFactory.create_sync_engine() as engine:
            date_str = target_date or datetime.now().strftime("%Y%m%d")

            result = await engine.run_incremental_daily_sync(target_date=date_str)

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
                "batch_size": de_config.SYNC_FINANCE_HISTORY_BATCH_SIZE,
                "start_date": de_config.SYNC_FINANCE_HISTORY_START_DATE,
                "end_date": datetime.now().strftime("%Y%m%d"),
            }

            task = await engine.run_history_sync(
                job_type=SyncJobType.FINANCE_HISTORY, config=config
            )

            logger.info(
                f"历史财务同步完成：task_id={task.id}, "
                f"status={task.status.value}, total_processed={task.total_processed}"
            )

    except Exception as e:
        logger.error(f"历史财务同步任务失败：{str(e)}", exc_info=True)


async def sync_incremental_finance_job(target_date: str | None = None):
    """
    定时任务：增量同步财务数据

    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    logger.info(f"开始执行财务增量同步任务... 基准日期: {target_date or '今天'}")

    try:
        async with SyncUseCaseFactory.create_incremental_finance_use_case() as use_case:
            result = await use_case.execute(actual_date=target_date)

            logger.info(
                f"财务增量同步完成：synced_count={result.get('synced_count')}, "
                f"failed_count={result.get('failed_count')}, "
                f"retry_count={result.get('retry_count')}, "
                f"retry_success_count={result.get('retry_success_count')}, "
                f"target_period={result.get('target_period')}"
            )

    except Exception as e:
        logger.error(f"财务增量同步任务失败：{str(e)}", exc_info=True)


async def sync_concept_data_job():
    """
    定时任务：同步概念数据（akshare → PostgreSQL）
    
    描述:
        从 akshare 获取概念板块及成份股数据，持久化到 PostgreSQL。
        使用全量替换策略，确保数据一致性。
    """
    logger.info("开始执行概念数据同步任务...")

    try:
        # 获取依赖注入容器
        container = DataEngineeringContainer()
        
        # 创建概念同步命令
        sync_cmd = SyncConceptDataCmd(
            concept_provider=container.concept_provider(),
            concept_repo=container.concept_repository(),
        )
        
        # 执行同步
        result = await sync_cmd.execute()
        
        logger.info(
            f"概念数据同步完成：总概念数={result.total_concepts}, "
            f"成功={result.success_concepts}, 失败={result.failed_concepts}, "
            f"总成份股={result.total_stocks}, 耗时={result.elapsed_time:.2f}s"
        )

    except Exception as e:
        logger.error(f"概念数据同步任务失败：{str(e)}", exc_info=True)
