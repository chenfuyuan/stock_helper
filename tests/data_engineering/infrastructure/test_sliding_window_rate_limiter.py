"""单元测试：SlidingWindowRateLimiter。"""

import pytest

from src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter import (
    SlidingWindowRateLimiter,
)


@pytest.mark.asyncio
async def test_acquire_within_limit_no_wait(monkeypatch):
    """窗口内未达上限时应立即通过。"""
    limiter = SlidingWindowRateLimiter(max_calls=3, window_seconds=60.0)

    values = [0.0, 1.0, 2.0]
    last = values[-1]

    def _fake_monotonic() -> float:
        nonlocal last
        if values:
            last = values.pop(0)
        return last

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter.time.monotonic",
        _fake_monotonic,
    )

    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter.asyncio.sleep",
        _fake_sleep,
    )

    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()

    assert sleep_calls == []


@pytest.mark.asyncio
async def test_acquire_waits_when_limit_reached(monkeypatch):
    """窗口达到上限时应等待最早时间戳滑出窗口。"""
    limiter = SlidingWindowRateLimiter(max_calls=2, window_seconds=10.0)

    # 1) 第一次 acquire: now=0
    # 2) 第二次 acquire: now=1
    # 3) 第三次 acquire 进入时 now=5（需等待 5 秒）
    # 4) sleep 后再次 now=10（0 已滑出窗口）
    values = [0.0, 1.0, 5.0, 10.0]
    last = values[-1]

    def _fake_monotonic() -> float:
        nonlocal last
        if values:
            last = values.pop(0)
        return last

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter.time.monotonic",
        _fake_monotonic,
    )

    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter.asyncio.sleep",
        _fake_sleep,
    )

    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_acquire_burst_friendly_after_idle(monkeypatch):
    """空闲后应允许突发调用，无固定间隔等待。"""
    limiter = SlidingWindowRateLimiter(max_calls=5, window_seconds=60.0)

    # 先有两次历史调用，然后长时间空闲，后续突发三次
    values = [0.0, 1.0, 120.0, 120.1, 120.2]
    last = values[-1]

    def _fake_monotonic() -> float:
        nonlocal last
        if values:
            last = values.pop(0)
        return last

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter.time.monotonic",
        _fake_monotonic,
    )

    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.rate_limiter.asyncio.sleep",
        _fake_sleep,
    )

    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()

    assert sleep_calls == []
