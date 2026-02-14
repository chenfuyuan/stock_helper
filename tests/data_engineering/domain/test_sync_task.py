"""
单元测试：SyncTask 和 SyncFailureRecord 实体创建与状态转换（任务 9.1）
"""

from datetime import datetime

from src.modules.data_engineering.domain.model.enums import (
    SyncJobType,
    SyncTaskStatus,
)
from src.modules.data_engineering.domain.model.sync_failure_record import (
    SyncFailureRecord,
)
from src.modules.data_engineering.domain.model.sync_task import SyncTask


def test_sync_task_creation():
    """测试 SyncTask 实体创建"""
    task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.PENDING,
        batch_size=50,
    )

    assert task.job_type == SyncJobType.DAILY_HISTORY
    assert task.status == SyncTaskStatus.PENDING
    assert task.batch_size == 50
    assert task.current_offset == 0
    assert task.total_processed == 0


def test_sync_task_start():
    """测试任务启动：状态转换为 RUNNING，记录启动时间"""
    task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.PENDING,
        batch_size=50,
    )

    before_start = datetime.now()
    task.start()
    after_start = datetime.now()

    assert task.status == SyncTaskStatus.RUNNING
    assert task.started_at is not None
    assert before_start <= task.started_at <= after_start
    assert task.updated_at is not None


def test_sync_task_update_progress():
    """测试进度更新：递增处理量和偏移量"""
    task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.RUNNING,
        batch_size=50,
        current_offset=0,
        total_processed=0,
    )

    task.update_progress(processed_count=50, new_offset=50)

    assert task.total_processed == 50
    assert task.current_offset == 50

    task.update_progress(processed_count=30, new_offset=80)

    assert task.total_processed == 80
    assert task.current_offset == 80


def test_sync_task_complete():
    """测试任务完成：状态转换为 COMPLETED，记录完成时间"""
    task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.RUNNING,
        batch_size=50,
    )

    before_complete = datetime.now()
    task.complete()
    after_complete = datetime.now()

    assert task.status == SyncTaskStatus.COMPLETED
    assert task.completed_at is not None
    assert before_complete <= task.completed_at <= after_complete


def test_sync_task_fail():
    """测试任务失败：状态转换为 FAILED"""
    task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.RUNNING,
        batch_size=50,
    )

    task.fail()

    assert task.status == SyncTaskStatus.FAILED


def test_sync_task_pause():
    """测试任务暂停：状态转换为 PAUSED"""
    task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.RUNNING,
        batch_size=50,
    )

    task.pause()

    assert task.status == SyncTaskStatus.PAUSED


def test_sync_task_is_resumable():
    """测试任务可恢复判断：RUNNING 或 PAUSED 状态可恢复"""
    running_task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.RUNNING,
        batch_size=50,
    )
    assert running_task.is_resumable() is True

    paused_task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.PAUSED,
        batch_size=50,
    )
    assert paused_task.is_resumable() is True

    completed_task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.COMPLETED,
        batch_size=50,
    )
    assert completed_task.is_resumable() is False


def test_sync_failure_record_creation():
    """测试 SyncFailureRecord 实体创建"""
    record = SyncFailureRecord(
        job_type=SyncJobType.FINANCE_INCREMENTAL,
        third_code="000001.SZ",
        error_message="API 调用超时",
        max_retries=3,
    )

    assert record.job_type == SyncJobType.FINANCE_INCREMENTAL
    assert record.third_code == "000001.SZ"
    assert record.error_message == "API 调用超时"
    assert record.retry_count == 0
    assert record.max_retries == 3


def test_sync_failure_record_can_retry():
    """测试失败记录可重试判断"""
    record = SyncFailureRecord(
        job_type=SyncJobType.FINANCE_INCREMENTAL,
        third_code="000001.SZ",
        error_message="API 调用超时",
        retry_count=1,
        max_retries=3,
    )

    assert record.can_retry() is True

    # 超过最大重试次数
    record.retry_count = 3
    assert record.can_retry() is False

    # 已解决
    record.retry_count = 1
    record.resolve()
    assert record.can_retry() is False


def test_sync_failure_record_increment_retry():
    """测试递增重试次数"""
    record = SyncFailureRecord(
        job_type=SyncJobType.FINANCE_INCREMENTAL,
        third_code="000001.SZ",
        error_message="API 调用超时",
        max_retries=3,
    )

    before_increment = datetime.now()
    record.increment_retry()
    after_increment = datetime.now()

    assert record.retry_count == 1
    assert record.last_attempt_at is not None
    assert before_increment <= record.last_attempt_at <= after_increment

    record.increment_retry()
    assert record.retry_count == 2


def test_sync_failure_record_resolve():
    """测试标记为已解决"""
    record = SyncFailureRecord(
        job_type=SyncJobType.FINANCE_INCREMENTAL,
        third_code="000001.SZ",
        error_message="API 调用超时",
        max_retries=3,
    )

    before_resolve = datetime.now()
    record.resolve()
    after_resolve = datetime.now()

    assert record.resolved_at is not None
    assert before_resolve <= record.resolved_at <= after_resolve
    assert record.is_resolved() is True
