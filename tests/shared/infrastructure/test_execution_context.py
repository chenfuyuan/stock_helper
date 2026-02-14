"""
任务 12.1：测试 ExecutionContext 设置/获取/重置/并行隔离。

覆盖：设置、获取、重置、以及 asyncio 并行任务间上下文隔离。
"""

import asyncio

import pytest

from src.shared.infrastructure.execution_context import (
    ExecutionContext,
    current_execution_ctx,
)


def test_get_returns_none_or_execution_context():
    """current_execution_ctx.get() 返回 None 或 ExecutionContext（未设置时默认 None）。"""
    ctx = current_execution_ctx.get()
    assert ctx is None or isinstance(ctx, ExecutionContext)


def test_set_and_get():
    """设置后在同一上下文中可正确获取。"""
    ctx = ExecutionContext(session_id="session-123")
    token = current_execution_ctx.set(ctx)
    try:
        got = current_execution_ctx.get()
        assert got is not None
        assert got.session_id == "session-123"
    finally:
        current_execution_ctx.reset(token)


def test_reset_restores_previous():
    """reset(token) 后恢复为设置前的值（通常为 None）。"""
    token = current_execution_ctx.set(ExecutionContext(session_id="a"))
    current_execution_ctx.reset(token)
    # 当前 context 应恢复；若之前为 None 则仍为 None
    got = current_execution_ctx.get()
    assert got is None or got.session_id != "a"


def test_nested_set_and_reset():
    """嵌套 set/reset 后恢复外层值。"""
    inner_ctx = ExecutionContext(session_id="inner")
    outer_ctx = ExecutionContext(session_id="outer")
    outer_token = current_execution_ctx.set(outer_ctx)
    try:
        assert current_execution_ctx.get().session_id == "outer"
        inner_token = current_execution_ctx.set(inner_ctx)
        try:
            assert current_execution_ctx.get().session_id == "inner"
        finally:
            current_execution_ctx.reset(inner_token)
        assert current_execution_ctx.get().session_id == "outer"
    finally:
        current_execution_ctx.reset(outer_token)


@pytest.mark.asyncio
async def test_parallel_tasks_isolated():
    """并行 asyncio 任务各自拥有独立上下文，互不干扰。"""
    results: list[tuple[str, str | None]] = []

    async def task(session_id: str) -> None:
        token = current_execution_ctx.set(
            ExecutionContext(session_id=session_id)
        )
        try:
            await asyncio.sleep(0.01)
            ctx = current_execution_ctx.get()
            results.append((session_id, ctx.session_id if ctx else None))
        finally:
            current_execution_ctx.reset(token)

    await asyncio.gather(
        task("session-a"),
        task("session-b"),
        task("session-c"),
    )

    assert len(results) == 3
    ids_seen = {r[1] for r in results}
    assert ids_seen == {"session-a", "session-b", "session-c"}
