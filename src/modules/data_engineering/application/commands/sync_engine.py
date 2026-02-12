from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
from loguru import logger

from src.modules.data_engineering.domain.model.sync_task import SyncTask
from src.modules.data_engineering.domain.model.sync_failure_record import SyncFailureRecord
from src.modules.data_engineering.domain.model.enums import SyncJobType, SyncTaskStatus
from src.modules.data_engineering.domain.ports.repositories.sync_task_repo import ISyncTaskRepository
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import IStockBasicRepository
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import IMarketQuoteRepository
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import IFinancialDataRepository
from src.modules.data_engineering.domain.ports.providers.market_quote_provider import IMarketQuoteProvider
from src.modules.data_engineering.domain.ports.providers.financial_data_provider import IFinancialDataProvider
from src.modules.data_engineering.application.commands.sync_daily_history import SyncDailyHistoryUseCase
from src.modules.data_engineering.application.commands.sync_finance_cmd import SyncFinanceHistoryUseCase
from src.modules.data_engineering.application.commands.sync_daily_bar_cmd import SyncDailyByDateUseCase
from src.modules.data_engineering.infrastructure.config import de_config


class SyncEngine:
    """
    同步引擎应用服务
    
    统一编排历史全量同步和增量同步，支持以下能力：
    - 一次触发、自动分批、跑完全量
    - 断点续跑（从 RUNNING/PAUSED 任务的 offset 恢复）
    - 同类型任务互斥（同一时间只能有一个 RUNNING 任务）
    - 失败记录追踪（单只股票失败不中断整批）
    """
    
    def __init__(
        self,
        sync_task_repo: ISyncTaskRepository,
        stock_repo: IStockBasicRepository,
        daily_repo: IMarketQuoteRepository,
        finance_repo: IFinancialDataRepository,
        quote_provider: IMarketQuoteProvider,
        finance_provider: IFinancialDataProvider,
    ):
        self.sync_task_repo = sync_task_repo
        self.stock_repo = stock_repo
        self.daily_repo = daily_repo
        self.finance_repo = finance_repo
        self.quote_provider = quote_provider
        self.finance_provider = finance_provider

    async def run_history_sync(self, job_type: SyncJobType, config: Dict[str, Any]) -> SyncTask:
        """
        执行历史全量同步
        
        支持：
        1. 同类型任务互斥：若已存在 RUNNING 任务，拒绝启动并返回已有任务
        2. 断点续跑：若存在 RUNNING/PAUSED 任务，从其 current_offset 恢复
        3. 自动分批循环：直到某批返回 0 条结果，标记 COMPLETED
        
        Args:
            job_type: 任务类型（DAILY_HISTORY / FINANCE_HISTORY）
            config: 任务配置（如 batch_size、start_date、end_date）
            
        Returns:
            完成或失败的 SyncTask
        """
        logger.info(f"开始执行历史同步：job_type={job_type.value}, config={config}")
        
        # 1. 检查是否存在正在运行的同类型任务（互斥）
        latest_task = await self.sync_task_repo.get_latest_by_job_type(job_type)
        if latest_task and latest_task.status == SyncTaskStatus.RUNNING:
            logger.warning(f"已存在正在运行的 {job_type.value} 任务，拒绝启动新任务")
            return latest_task
        
        # 2. 判断是否需要恢复任务（断点续跑）
        # 如果存在之前的任务且处于可恢复状态，则从上次的 offset 继续同步
        if latest_task and latest_task.is_resumable():
            logger.info(
                f"发现可恢复任务，执行断点续跑: task_id={latest_task.id}, "
                f"current_offset={latest_task.current_offset}, job_type={job_type.value}"
            )
            task = latest_task
            task.start()  # 更新状态为 RUNNING
            await self.sync_task_repo.update(task)
        else:
            # 3. 创建新任务
            batch_size = config.get("batch_size") or self._get_default_batch_size(job_type)
            task = SyncTask(
                job_type=job_type,
                status=SyncTaskStatus.PENDING,
                batch_size=batch_size,
                config=config,
            )
            task.start()
            task = await self.sync_task_repo.create(task)
            logger.info(f"创建新任务：task_id={task.id}")
        
        # 4. 循环分批同步，直到某批返回 0 条结果
        try:
            while True:
                logger.info(f"开始处理第 {task.current_offset // task.batch_size + 1} 批，offset={task.current_offset}")
                
                # 调用对应的 Use Case 执行单批同步
                result = await self._execute_batch(job_type, task)
                
                # 判断是否完成
                processed_count = result.get("synced_stocks") or result.get("batch_size") or 0
                if processed_count == 0:
                    logger.info(f"本批未处理任何股票，标记任务为 COMPLETED")
                    task.complete()
                    await self.sync_task_repo.update(task)
                    break
                
                # 更新进度并持久化状态
                new_offset = task.current_offset + task.batch_size
                task.update_progress(processed_count, new_offset)
                await self.sync_task_repo.update(task)
                
                logger.info(
                    f"批处理成功: 已同步 {processed_count} 只股票 | "
                    f"当前总进度: {task.total_processed} | "
                    f"下次 offset: {new_offset}"
                )
        
        except Exception as e:
            logger.error(f"历史同步失败：{str(e)}", exc_info=True)
            task.fail()
            await self.sync_task_repo.update(task)
            raise
        
        logger.info(f"历史同步完成：task_id={task.id}, total_processed={task.total_processed}")
        return task

    async def _execute_batch(self, job_type: SyncJobType, task: SyncTask) -> Dict[str, Any]:
        """
        执行单批同步（内部方法）
        
        根据 job_type 选择对应的 Use Case 执行。
        """
        if job_type == SyncJobType.DAILY_HISTORY:
            use_case = SyncDailyHistoryUseCase(
                stock_repo=self.stock_repo,
                daily_repo=self.daily_repo,
                data_provider=self.quote_provider,
            )
            return await use_case.execute(
                limit=task.batch_size,
                offset=task.current_offset,
            )
        
        elif job_type == SyncJobType.FINANCE_HISTORY:
            use_case = SyncFinanceHistoryUseCase(
                stock_repo=self.stock_repo,
                finance_repo=self.finance_repo,
                data_provider=self.finance_provider,
            )
            start_date = task.config.get("start_date") or de_config.SYNC_FINANCE_HISTORY_START_DATE
            end_date = task.config.get("end_date") or ""
            return await use_case.execute(
                start_date=start_date,
                end_date=end_date,
                offset=task.current_offset,
                limit=task.batch_size,
            )
        
        else:
            raise ValueError(f"不支持的 job_type: {job_type}")

    async def run_incremental_daily_sync(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        执行日线增量同步（含遗漏检测与自动补偿）
        
        逻辑：
        1. 查询 DB 中最新的 trade_date
        2. 与 today（或指定日期）比较
        3. 若有间隔，则逐日补同步缺失的日期区间
        4. 无遗漏，则仅同步目标日期
        5. DB 为空时，记录警告并仅同步目标日期
        
        Args:
            target_date: 目标日期（格式：YYYYMMDD），默认为 today
            
        Returns:
            同步结果摘要
        """
        # 确定目标日期
        if not target_date:
            target_date = datetime.now().strftime("%Y%m%d")
        target_date_obj = datetime.strptime(target_date, "%Y%m%d").date()
        
        logger.info(f"开始日线增量同步：target_date={target_date}")
        
        # 查询数据库中最新的交易日期
        latest_trade_date = await self.daily_repo.get_latest_trade_date()
        
        if not latest_trade_date:
            logger.warning("数据库中无日线数据，建议先执行历史全量同步。仅同步目标日期。")
            use_case = SyncDailyByDateUseCase(
                daily_repo=self.daily_repo,
                data_provider=self.quote_provider,
            )
            result = await use_case.execute(trade_date=target_date)
            return {
                "status": "success",
                "synced_dates": [target_date],
                "total_count": result.get("count", 0),
                "message": "数据库为空，仅同步目标日期",
            }
        
        # 计算需要补偿的日期区间
        missing_dates = self._calculate_missing_dates(latest_trade_date, target_date_obj)
        
        if not missing_dates:
            logger.info(f"无遗漏日期，仅同步目标日期 {target_date}")
            use_case = SyncDailyByDateUseCase(
                daily_repo=self.daily_repo,
                data_provider=self.quote_provider,
            )
            result = await use_case.execute(trade_date=target_date)
            return {
                "status": "success",
                "synced_dates": [target_date],
                "total_count": result.get("count", 0),
                "message": "无遗漏，仅同步目标日期",
            }
        
        # 补偿缺失日期 + 目标日期
        logger.info(f"检测到遗漏日期：{len(missing_dates)} 天，开始补偿同步")
        all_dates = missing_dates + [target_date_obj]
        synced_dates = []
        total_count = 0
        
        use_case = SyncDailyByDateUseCase(
            daily_repo=self.daily_repo,
            data_provider=self.quote_provider,
        )
        
        for date_obj in all_dates:
            date_str = date_obj.strftime("%Y%m%d")
            try:
                logger.info(f"正在同步日期：{date_str}")
                result = await use_case.execute(trade_date=date_str)
                synced_dates.append(date_str)
                total_count += result.get("count", 0)
                logger.info(f"成功同步 {date_str}，{result.get('count', 0)} 条记录")
            except Exception as e:
                logger.error(f"同步 {date_str} 失败：{str(e)}")
                # 单日失败不中断，继续后续日期
                continue
        
        return {
            "status": "success",
            "synced_dates": synced_dates,
            "total_count": total_count,
            "message": f"成功补偿 {len(synced_dates)} 个交易日，共 {total_count} 条记录",
        }

    def _calculate_missing_dates(self, latest_date: date, target_date: date) -> List[date]:
        """
        计算缺失的日期区间
        
        注意：这里简单地计算所有日历日，实际上只有交易日才有数据。
        但对于数据同步而言，调用 API 时若非交易日会返回空，不影响正确性。
        """
        if target_date <= latest_date:
            return []
        
        missing_dates = []
        current = latest_date + timedelta(days=1)
        while current < target_date:
            missing_dates.append(current)
            current += timedelta(days=1)
        
        return missing_dates

    def _get_default_batch_size(self, job_type: SyncJobType) -> int:
        """获取默认批大小（从配置读取）"""
        if job_type == SyncJobType.DAILY_HISTORY:
            return de_config.SYNC_DAILY_HISTORY_BATCH_SIZE
        elif job_type == SyncJobType.FINANCE_HISTORY:
            return de_config.SYNC_FINANCE_HISTORY_BATCH_SIZE
        else:
            return 50  # 默认值
