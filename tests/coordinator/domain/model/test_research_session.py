"""
任务 12.2：测试 ResearchSession 生命周期（running → completed / partial / failed）。
"""

from datetime import datetime, timezone
from uuid import UUID

from src.modules.coordinator.domain.model.research_session import (
    ResearchSession,
)


def test_session_starts_running():
    """新建会话状态为 running。"""
    now = datetime.now(timezone.utc)
    session = ResearchSession(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        symbol="AAPL",
        created_at=now,
    )
    assert session.status == "running"
    assert session.completed_at is None
    assert session.duration_ms is None


def test_complete_updates_status_and_times():
    """complete() 将状态置为 completed 并写入完成时间与耗时。"""
    now = datetime.now(timezone.utc)
    session = ResearchSession(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        symbol="MSFT",
        created_at=now,
    )
    completed_at = now.replace(microsecond=0)
    duration_ms = 5000
    session.complete(completed_at=completed_at, duration_ms=duration_ms)
    assert session.status == "completed"
    assert session.completed_at == completed_at
    assert session.duration_ms == duration_ms


def test_fail_updates_status_and_times():
    """fail() 将状态置为 failed 并写入完成时间与耗时。"""
    now = datetime.now(timezone.utc)
    session = ResearchSession(
        id=UUID("00000000-0000-0000-0000-000000000003"),
        symbol="GOOG",
        created_at=now,
    )
    completed_at = now.replace(microsecond=0)
    duration_ms = 100
    session.fail(completed_at=completed_at, duration_ms=duration_ms)
    assert session.status == "failed"
    assert session.completed_at == completed_at
    assert session.duration_ms == duration_ms


def test_mark_partial_updates_status_and_times():
    """mark_partial() 将状态置为 partial 并写入完成时间与耗时。"""
    now = datetime.now(timezone.utc)
    session = ResearchSession(
        id=UUID("00000000-0000-0000-0000-000000000004"),
        symbol="AMZN",
        created_at=now,
    )
    completed_at = now.replace(microsecond=0)
    duration_ms = 3000
    session.mark_partial(completed_at=completed_at, duration_ms=duration_ms)
    assert session.status == "partial"
    assert session.completed_at == completed_at
    assert session.duration_ms == duration_ms
