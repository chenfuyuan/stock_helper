"""
任务 12.8：测试历史查询 API（列表筛选/分页、详情、404、空结果）。
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.modules.coordinator.domain.model.research_session import (
    ResearchSession,
)
from src.modules.coordinator.infrastructure.persistence.research_session_repository import (
    PgResearchSessionRepository,
)
from src.shared.infrastructure.db.session import get_db_session


@pytest.fixture
async def session_with_data(db_session):
    """在测试 DB 中插入一条研究会话，用于列表/详情查询。"""
    repo = PgResearchSessionRepository(db_session)
    now = datetime.now(timezone.utc)
    session = ResearchSession(
        id=uuid4(),
        symbol="AAPL",
        status="completed",
        selected_experts=["technical_analyst"],
        options={},
        trigger_source="api",
        created_at=now,
        completed_at=now,
        duration_ms=1000,
    )
    await repo.save_session(session)
    return session


@pytest.fixture
def app():
    """延迟导入 app，避免收集阶段加载 langgraph 等依赖。"""
    from src.main import app as _app

    return _app


@pytest.mark.asyncio
async def test_list_sessions_returns_summaries(app, db_session, session_with_data):
    """GET /coordinator/research/sessions 返回会话摘要列表。"""

    async def override():
        yield db_session

    app.dependency_overrides[get_db_session] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/coordinator/research/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        ids = [s["id"] for s in data]
        assert str(session_with_data.id) in ids
        one = next(s for s in data if s["id"] == str(session_with_data.id))
        assert one["symbol"] == "AAPL"
        assert one["status"] == "completed"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_sessions_filter_by_symbol(app, db_session, session_with_data):
    """GET /coordinator/research/sessions?symbol=AAPL 仅返回该 symbol 的会话。"""

    async def override():
        yield db_session

    app.dependency_overrides[get_db_session] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/coordinator/research/sessions?symbol=AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["symbol"] == "AAPL" for s in data)
        resp_other = await client.get("/api/v1/coordinator/research/sessions?symbol=MSFT")
        other = resp_other.json()
        assert other == [] or all(s["symbol"] == "MSFT" for s in other)
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_sessions_pagination(app, db_session, session_with_data):
    """GET /coordinator/research/sessions?skip=0&limit=1 分页生效。"""

    async def override():
        yield db_session

    app.dependency_overrides[get_db_session] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/coordinator/research/sessions?skip=0&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 1
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_get_session_detail_returns_detail_and_node_executions(
    app, db_session, session_with_data
):
    """GET /coordinator/research/sessions/{id} 返回会话详情及节点执行列表。"""

    async def override():
        yield db_session

    app.dependency_overrides[get_db_session] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(f"/api/v1/coordinator/research/sessions/{session_with_data.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(session_with_data.id)
        assert data["symbol"] == "AAPL"
        assert data["status"] == "completed"
        assert "node_executions" in data
        assert isinstance(data["node_executions"], list)
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_get_session_detail_not_found_returns_404(app, db_session):
    """GET /coordinator/research/sessions/{id} 当会话不存在时返回 404。"""

    async def override():
        yield db_session

    app.dependency_overrides[get_db_session] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(f"/api/v1/coordinator/research/sessions/{uuid4()}")
        assert resp.status_code == 404
        assert "会话不存在" in resp.json().get("detail", "")
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_sessions_empty_result(app, db_session):
    """无会话时 GET /coordinator/research/sessions 返回空列表。"""

    async def override():
        yield db_session

    app.dependency_overrides[get_db_session] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 使用一个不存在的 symbol 确保空结果
            resp = await client.get("/api/v1/coordinator/research/sessions?symbol=__NO_SYMBOL__")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_db_session, None)
