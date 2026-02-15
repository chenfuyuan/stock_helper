"""集成测试：调度 API 持久化行为。"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.modules.data_engineering.presentation.rest import router as de_router
from src.modules.data_engineering.presentation.rest import scheduler_routes


class _FakeScheduler:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)

    def remove_job(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)

    def add_job(self, func, trigger=None, id=None, replace_existing=True, kwargs=None, **extra):
        self.jobs[id] = {
            "func": func,
            "trigger": trigger,
            "kwargs": kwargs or {},
            "extra": extra,
        }


class _FakeJobConfigRepo:
    store: dict[str, dict] = {}

    def __init__(self, session):
        self._session = session

    async def upsert(self, job_id: str, job_name: str, cron_expression: str, timezone: str = "Asia/Shanghai", enabled: bool = True, job_kwargs=None):
        self.store[job_id] = {
            "job_id": job_id,
            "job_name": job_name,
            "cron_expression": cron_expression,
            "timezone": timezone,
            "enabled": enabled,
            "job_kwargs": job_kwargs,
        }

    async def update_enabled(self, job_id: str, enabled: bool) -> None:
        if job_id in self.store:
            self.store[job_id]["enabled"] = enabled


async def _fake_session_dep():
    yield object()


@pytest.mark.asyncio
async def test_schedule_and_stop_persist_to_db(monkeypatch) -> None:
    """schedule/stop 应同步写入持久化配置。"""
    app = FastAPI()
    app.include_router(de_router, prefix="/api/v1")

    fake_scheduler = _FakeScheduler()
    _FakeJobConfigRepo.store = {}

    monkeypatch.setattr(scheduler_routes, "SchedulerJobConfigRepository", _FakeJobConfigRepo)
    monkeypatch.setattr(
        scheduler_routes.SchedulerService,
        "get_scheduler",
        classmethod(lambda cls: fake_scheduler),
    )
    app.dependency_overrides[scheduler_routes.get_async_session] = _fake_session_dep

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.post(
            "/api/v1/scheduler/jobs/sync_daily_by_date/schedule",
            json={"hour": 20, "minute": 0},
        )
        assert resp1.status_code == 200
        assert _FakeJobConfigRepo.store["sync_daily_by_date"]["cron_expression"] == "0 20 * * *"
        assert _FakeJobConfigRepo.store["sync_daily_by_date"]["enabled"] is True

        resp2 = await client.post("/api/v1/scheduler/jobs/sync_daily_by_date/stop")
        assert resp2.status_code == 200
        assert _FakeJobConfigRepo.store["sync_daily_by_date"]["enabled"] is False

    app.dependency_overrides.clear()
