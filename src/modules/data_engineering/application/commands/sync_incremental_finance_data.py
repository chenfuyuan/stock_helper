from datetime import date, datetime, timedelta
from typing import Any, Dict, Set

from loguru import logger

from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.modules.data_engineering.domain.model.sync_failure_record import (
    SyncFailureRecord,
)
from src.modules.data_engineering.domain.ports.providers.financial_data_provider import (
    IFinancialDataProvider,
)
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import (
    IFinancialDataRepository,
)
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)
from src.modules.data_engineering.domain.ports.repositories.sync_task_repo import (
    ISyncTaskRepository,
)
from src.modules.data_engineering.infrastructure.config import de_config


class SyncIncrementalFinanceDataUseCase:
    """
    增量同步股票财务指标用例

    策略:
    - 策略 A（高优先级）：今日披露名单驱动
    - 策略 B（低优先级）：长尾轮询（缺数补齐）
    - 策略 C（前置步骤）：失败重试（从 DB 读取未解决的失败记录）
    """

    def __init__(
        self,
        finance_repo: IFinancialDataRepository,
        stock_repo: IStockBasicRepository,
        sync_task_repo: ISyncTaskRepository,
        data_provider: IFinancialDataProvider,
    ):
        self.finance_repo = finance_repo
        self.stock_repo = stock_repo
        self.sync_task_repo = sync_task_repo
        self.data_provider = data_provider

    def _get_target_period(self, current_date: date) -> str:
        """根据当前日期确定目标报告期"""
        year = current_date.year
        month = current_date.month

        if 1 <= month <= 4:
            # 1-4月，目标是去年的年报 (Q4)
            return f"{year-1}1231"
        elif 5 <= month <= 8:
            # 5-8月，目标是今年的一季报 (Q1)
            return f"{year}0331"
        elif 9 <= month <= 10:
            # 9-10月，目标是今年的中报 (Q2)
            return f"{year}0630"
        else:
            # 11-12月，目标是今年的三季报 (Q3)
            return f"{year}0930"

    async def execute(self, actual_date: str = None) -> Dict[str, Any]:
        """
        执行增量同步逻辑

        Args:
            actual_date: 可选，用于模拟日期 (YYYYMMDD)

        Returns:
            同步结果摘要
        """
        # 1. 确定基准日期和目标报告期
        if actual_date:
            try:
                current_date = datetime.strptime(actual_date, "%Y%m%d").date()
            except ValueError:
                current_date = date.today()
        else:
            current_date = date.today()
            actual_date = current_date.strftime("%Y%m%d")

        target_period = self._get_target_period(current_date)
        logger.info(f"开始财务增量同步：当前日期={actual_date}，目标报告期={target_period}")

        # 策略 C（前置）: 失败重试（从 DB 读取未解决的失败记录）
        retry_count = 0
        retry_success_count = 0

        try:
            logger.info("开始重试之前失败的记录...")
            unresolved_failures = await self.sync_task_repo.get_unresolved_failures(
                job_type=SyncJobType.FINANCE_INCREMENTAL
            )
            logger.info(f"找到 {len(unresolved_failures)} 条未解决的失败记录")

            for failure in unresolved_failures:
                retry_count += 1
                try:
                    logger.info(f"重试 {failure.third_code}（已重试 {failure.retry_count} 次）")

                    target_date_formatted = (
                        f"{target_period[:4]}{target_period[4:6]}{target_period[6:]}"
                    )
                    finances = await self.data_provider.fetch_fina_indicator(
                        third_code=failure.third_code,
                        end_date=target_date_formatted,
                    )

                    if finances:
                        await self.finance_repo.save_all(finances)
                        await self.sync_task_repo.resolve_failure(failure.id)
                        retry_success_count += 1
                        logger.info(f"重试成功：{failure.third_code}")
                    else:
                        # 无数据，递增重试次数
                        failure.increment_retry()
                        await self.sync_task_repo.update_failure(failure)
                        logger.warning(f"重试无数据：{failure.third_code}")

                except Exception as e:
                    logger.error(f"重试失败：{failure.third_code} - {str(e)}")
                    failure.increment_retry()
                    await self.sync_task_repo.update_failure(failure)

            logger.info(f"失败重试完成：总计 {retry_count} 条，成功 {retry_success_count} 条")
        except Exception as e:
            logger.error(f"失败重试阶段发生错误：{str(e)}")

        # 2. 构建任务队列
        tasks: Set[str] = set()

        # 策略 A: 获取今日披露名单（高优先级）
        try:
            logger.info(f"获取 {actual_date} 的披露名单...")
            disclosures = await self.data_provider.fetch_disclosure_date(actual_date=actual_date)
            for d in disclosures:
                end_date_str = (
                    d.end_date.strftime("%Y%m%d")
                    if hasattr(d.end_date, "strftime")
                    else str(d.end_date).replace("-", "")
                )
                if end_date_str == target_period:
                    tasks.add(d.third_code)
            logger.info(f"从披露计划中找到 {len(tasks)} 只股票")
        except Exception as e:
            logger.error(f"获取披露名单失败：{str(e)}")

        # 策略 B: 长尾轮询（低优先级，缺数补齐）
        check_threshold = current_date - timedelta(days=3)
        limit = de_config.SYNC_INCREMENTAL_MISSING_LIMIT  # 从配置读取

        try:
            logger.info(f"从数据库查询缺失财务数据的股票（上限 {limit} 只）...")
            missing_stocks = await self.stock_repo.get_missing_finance_stocks(
                target_period=target_period,
                check_threshold_date=check_threshold,
                limit=limit,
            )
            initial_task_count = len(tasks)
            tasks.update(missing_stocks)
            logger.info(
                f"从缺数补齐中新增 {len(tasks) - initial_task_count} 只股票，总任务数：{len(tasks)}"
            )
        except Exception as e:
            logger.error(f"查询缺失股票失败：{str(e)}")

        # 3. 执行同步
        synced_count = 0
        failed_count = 0

        for code in tasks:
            try:
                target_date_formatted = (
                    f"{target_period[:4]}{target_period[4:6]}{target_period[6:]}"
                )

                finances = await self.data_provider.fetch_fina_indicator(
                    third_code=code, end_date=target_date_formatted
                )

                if finances:
                    await self.finance_repo.save_all(finances)
                    synced_count += 1
                    await self.stock_repo.update_last_finance_sync_date(
                        third_codes=[code], sync_date=current_date
                    )
                else:
                    # 无数据也更新检查时间（避免短期内重复查询）
                    await self.stock_repo.update_last_finance_sync_date(
                        third_codes=[code], sync_date=current_date
                    )

            except Exception as e:
                logger.error(f"同步 {code} 失败：{str(e)}")
                failed_count += 1

                # 写入失败记录到 DB
                try:
                    failure_record = SyncFailureRecord(
                        job_type=SyncJobType.FINANCE_INCREMENTAL,
                        third_code=code,
                        error_message=str(e)[:500],  # 限制长度
                        max_retries=de_config.SYNC_FAILURE_MAX_RETRIES,
                    )
                    failure_record.increment_retry()  # 初始尝试算第 1 次
                    await self.sync_task_repo.create_failure(failure_record)
                except Exception as save_err:
                    logger.error(f"保存失败记录失败：{code} - {str(save_err)}")

        return {
            "status": "success",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "retry_count": retry_count,
            "retry_success_count": retry_success_count,
            "target_period": target_period,
            "message": (  # noqa: E501
                f"成功同步 {synced_count} 只股票，失败 {failed_count} 只；"
                f"重试 {retry_count} 条记录，成功 {retry_success_count} 条"
            ),
        }
