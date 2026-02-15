"""单元测试：ExecutionTracker。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.shared.infrastructure.scheduler.execution_tracker import ExecutionTracker


@pytest.mark.asyncio
async def test_execution_tracker_success_updates_log() -> None:
    """正常执行应写入 SUCCESS 日志。"""
    repo = AsyncMock()
    repo.create.return_value = SimpleNamespace(id="log-1")

    async with ExecutionTracker(job_id="sync_daily_by_date", repo=repo):
        pass

    repo.create.assert_awaited_once()
    repo.update.assert_awaited_once()
    kwargs = repo.update.await_args.kwargs
    assert kwargs["status"] == "SUCCESS"
    assert kwargs["error_message"] is None
    assert isinstance(kwargs["duration_ms"], int)


@pytest.mark.asyncio
async def test_execution_tracker_failure_updates_log_and_reraises() -> None:
    """异常执行应写入 FAILED，且异常继续向上抛出。"""
    repo = AsyncMock()
    repo.create.return_value = SimpleNamespace(id="log-2")

    with pytest.raises(ValueError, match="boom"):
        async with ExecutionTracker(job_id="sync_daily_by_date", repo=repo):
            raise ValueError("boom")

    repo.update.assert_awaited_once()
    kwargs = repo.update.await_args.kwargs
    assert kwargs["status"] == "FAILED"
    assert "ValueError: boom" in (kwargs["error_message"] or "")


@pytest.mark.asyncio
async def test_execution_tracker_db_write_failure_does_not_interrupt_job() -> None:
    """日志写入失败不应中断业务执行。"""
    repo = AsyncMock()
    repo.create.side_effect = RuntimeError("db unavailable")

    # create 失败时，__aenter__ 会吞掉异常；业务代码应继续执行
    async with ExecutionTracker(job_id="sync_daily_by_date", repo=repo):
        result = 1 + 1

    assert result == 2
    repo.update.assert_not_awaited()
