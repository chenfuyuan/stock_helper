"""
Spec: de-clean-arch-refactor § 领域建模修正
测试 SyncFailureRecord Pydantic 迁移后行为方法正常。
"""

from datetime import datetime

from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.modules.data_engineering.domain.model.sync_failure_record import (
    SyncFailureRecord,
)


class TestSyncFailureRecordCanRetry:
    """测试 can_retry() 行为方法"""

    def test_初始状态可重试(self) -> None:
        record = SyncFailureRecord(max_retries=3)
        assert record.can_retry() is True

    def test_重试次数未达上限可重试(self) -> None:
        record = SyncFailureRecord(retry_count=2, max_retries=3)
        assert record.can_retry() is True

    def test_重试次数达上限不可重试(self) -> None:
        record = SyncFailureRecord(retry_count=3, max_retries=3)
        assert record.can_retry() is False

    def test_超过上限不可重试(self) -> None:
        record = SyncFailureRecord(retry_count=5, max_retries=3)
        assert record.can_retry() is False

    def test_已解决不可重试(self) -> None:
        record = SyncFailureRecord(
            retry_count=1, max_retries=3, resolved_at=datetime.now()
        )
        assert record.can_retry() is False


class TestSyncFailureRecordIncrementRetry:
    """测试 increment_retry() 行为方法"""

    def test_递增retry_count(self) -> None:
        record = SyncFailureRecord()
        assert record.retry_count == 0
        record.increment_retry()
        assert record.retry_count == 1
        record.increment_retry()
        assert record.retry_count == 2

    def test_更新last_attempt_at(self) -> None:
        record = SyncFailureRecord()
        assert record.last_attempt_at is None
        record.increment_retry()
        assert record.last_attempt_at is not None
        assert isinstance(record.last_attempt_at, datetime)


class TestSyncFailureRecordResolve:
    """测试 resolve() 行为方法"""

    def test_标记resolved_at(self) -> None:
        record = SyncFailureRecord()
        assert record.resolved_at is None
        record.resolve()
        assert record.resolved_at is not None

    def test_解决后is_resolved返回True(self) -> None:
        record = SyncFailureRecord()
        assert record.is_resolved() is False
        record.resolve()
        assert record.is_resolved() is True


class TestSyncFailureRecordIsResolved:
    """测试 is_resolved() 行为方法"""

    def test_未解决返回False(self) -> None:
        record = SyncFailureRecord()
        assert record.is_resolved() is False

    def test_已解决返回True(self) -> None:
        record = SyncFailureRecord(resolved_at=datetime.now())
        assert record.is_resolved() is True


class TestSyncFailureRecordPydanticFeatures:
    """测试 Pydantic 特性"""

    def test_默认值正确(self) -> None:
        record = SyncFailureRecord()
        assert record.job_type == SyncJobType.DAILY_HISTORY
        assert record.third_code == ""
        assert record.error_message == ""
        assert record.retry_count == 0
        assert record.max_retries == 3

    def test_指定参数创建(self) -> None:
        record = SyncFailureRecord(
            job_type=SyncJobType.FINANCE_INCREMENTAL,
            third_code="000001.SZ",
            error_message="连接超时",
            max_retries=5,
        )
        assert record.job_type == SyncJobType.FINANCE_INCREMENTAL
        assert record.third_code == "000001.SZ"
        assert record.error_message == "连接超时"
        assert record.max_retries == 5

    def test_id自动生成(self) -> None:
        r1 = SyncFailureRecord()
        r2 = SyncFailureRecord()
        assert r1.id != r2.id
