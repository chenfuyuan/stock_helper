"""
Spec: de-clean-arch-refactor § 领域建模修正
测试 SyncTask Pydantic 迁移后行为方法正常。
"""

from datetime import datetime

from src.modules.data_engineering.domain.model.enums import (
    SyncJobType,
    SyncTaskStatus,
)
from src.modules.data_engineering.domain.model.sync_task import SyncTask


class TestSyncTaskStart:
    """测试 start() 行为方法"""

    def test_start_设置状态为RUNNING(self) -> None:
        task = SyncTask()
        task.start()
        assert task.status == SyncTaskStatus.RUNNING

    def test_start_设置started_at(self) -> None:
        task = SyncTask()
        assert task.started_at is None
        task.start()
        assert task.started_at is not None
        assert isinstance(task.started_at, datetime)

    def test_start_更新updated_at(self) -> None:
        task = SyncTask()
        old_updated = task.updated_at
        task.start()
        assert task.updated_at >= old_updated


class TestSyncTaskComplete:
    """测试 complete() 行为方法"""

    def test_complete_设置状态为COMPLETED(self) -> None:
        task = SyncTask()
        task.start()
        task.complete()
        assert task.status == SyncTaskStatus.COMPLETED

    def test_complete_设置completed_at(self) -> None:
        task = SyncTask()
        task.start()
        assert task.completed_at is None
        task.complete()
        assert task.completed_at is not None


class TestSyncTaskFail:
    """测试 fail() 行为方法"""

    def test_fail_设置状态为FAILED(self) -> None:
        task = SyncTask()
        task.start()
        task.fail()
        assert task.status == SyncTaskStatus.FAILED


class TestSyncTaskPause:
    """测试 pause() 行为方法"""

    def test_pause_设置状态为PAUSED(self) -> None:
        task = SyncTask()
        task.start()
        task.pause()
        assert task.status == SyncTaskStatus.PAUSED


class TestSyncTaskUpdateProgress:
    """测试 update_progress() 行为方法"""

    def test_update_progress_累加total_processed(self) -> None:
        task = SyncTask()
        task.start()
        task.update_progress(processed_count=10, new_offset=50)
        assert task.total_processed == 10
        assert task.current_offset == 50

        task.update_progress(processed_count=20, new_offset=100)
        assert task.total_processed == 30
        assert task.current_offset == 100


class TestSyncTaskIsResumable:
    """测试 is_resumable() 行为方法"""

    def test_RUNNING状态可恢复(self) -> None:
        task = SyncTask(status=SyncTaskStatus.RUNNING)
        assert task.is_resumable() is True

    def test_PAUSED状态可恢复(self) -> None:
        task = SyncTask(status=SyncTaskStatus.PAUSED)
        assert task.is_resumable() is True

    def test_COMPLETED状态不可恢复(self) -> None:
        task = SyncTask(status=SyncTaskStatus.COMPLETED)
        assert task.is_resumable() is False

    def test_FAILED状态不可恢复(self) -> None:
        task = SyncTask(status=SyncTaskStatus.FAILED)
        assert task.is_resumable() is False

    def test_PENDING状态不可恢复(self) -> None:
        task = SyncTask(status=SyncTaskStatus.PENDING)
        assert task.is_resumable() is False


class TestSyncTaskPydanticFeatures:
    """测试 Pydantic 特性（from_attributes、默认值等）"""

    def test_默认值正确(self) -> None:
        task = SyncTask()
        assert task.job_type == SyncJobType.DAILY_HISTORY
        assert task.status == SyncTaskStatus.PENDING
        assert task.current_offset == 0
        assert task.batch_size == 50
        assert task.total_processed == 0
        assert task.config == {}

    def test_指定job_type创建(self) -> None:
        task = SyncTask(job_type=SyncJobType.FINANCE_HISTORY, batch_size=100)
        assert task.job_type == SyncJobType.FINANCE_HISTORY
        assert task.batch_size == 100

    def test_id自动生成(self) -> None:
        t1 = SyncTask()
        t2 = SyncTask()
        assert t1.id != t2.id
