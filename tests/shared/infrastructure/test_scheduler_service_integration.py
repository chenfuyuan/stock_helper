"""集成测试：SchedulerService.load_persisted_jobs。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.shared.infrastructure.scheduler.scheduler_service import SchedulerService


class _DummySessionContext:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_load_persisted_jobs_registers_enabled_configs(monkeypatch) -> None:
    """应从持久化配置中注册可用 job。"""
    cfg = SimpleNamespace(
        job_id="sync_daily_by_date",
        job_name="日线增量同步",
        cron_expression="0 18 * * *",
        timezone="Asia/Shanghai",
        job_kwargs={"target_date": "20260215"},
    )

    repo = AsyncMock()
    repo.get_all_enabled.return_value = [cfg]

    monkeypatch.setattr(
        "src.shared.infrastructure.scheduler.scheduler_service.SchedulerJobConfigRepository",
        lambda session: repo,
    )

    trigger_marker = object()
    monkeypatch.setattr(
        "src.shared.infrastructure.scheduler.scheduler_service.CronTrigger.from_crontab",
        lambda expr, timezone: trigger_marker,
    )

    scheduler = AsyncMock()
    scheduler.add_job = AsyncMock()
    # add_job 在真实 APScheduler 是同步函数，这里用普通 mock 更贴近
    from unittest.mock import Mock

    scheduler.add_job = Mock()
    monkeypatch.setattr(SchedulerService, "get_scheduler", classmethod(lambda cls: scheduler))

    async def _job() -> None:
        return None

    async def _session_factory():
        return None

    # 传入可用 session 工厂
    session_factory = lambda: _DummySessionContext(session=object())

    await SchedulerService.load_persisted_jobs(
        registry={"sync_daily_by_date": _job},
        session_factory=session_factory,
    )

    scheduler.add_job.assert_called_once()
    kwargs = scheduler.add_job.call_args.kwargs
    assert kwargs["id"] == "sync_daily_by_date"
    assert kwargs["trigger"] is trigger_marker


@pytest.mark.asyncio
async def test_load_persisted_jobs_db_error_degrades(monkeypatch) -> None:
    """数据库失败时应降级，不抛出异常。"""

    def _broken_session_factory():
        raise RuntimeError("db down")

    # 不应抛异常
    await SchedulerService.load_persisted_jobs(
        registry={},
        session_factory=_broken_session_factory,
    )
