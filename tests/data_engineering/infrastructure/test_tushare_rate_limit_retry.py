"""单元测试：TuShare 频率超限退避重试。"""

from unittest.mock import AsyncMock

import pytest

from src.modules.data_engineering.infrastructure.external_apis.tushare.client import (
    TushareClient,
)


class _FakeLimiter:
    async def acquire(self) -> None:
        return None


@pytest.mark.asyncio
async def test_rate_limit_retry_first_retry_success(monkeypatch) -> None:
    """首次频率超限后重试成功。"""
    client = object.__new__(TushareClient)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client._get_tushare_rate_limiter",
        lambda: _FakeLimiter(),
    )

    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client.asyncio.sleep",
        _fake_sleep,
    )

    run = AsyncMock(side_effect=[Exception("调用频率每分钟超限"), {"ok": True}])
    client._run_in_executor = run

    result = await client._rate_limited_call(lambda: None)

    assert result == {"ok": True}
    assert sleep_calls == [3.0]
    assert run.await_count == 2


@pytest.mark.asyncio
async def test_rate_limit_retry_multiple_then_success(monkeypatch) -> None:
    """多次频率超限后重试成功。"""
    client = object.__new__(TushareClient)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client._get_tushare_rate_limiter",
        lambda: _FakeLimiter(),
    )

    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client.asyncio.sleep",
        _fake_sleep,
    )

    run = AsyncMock(
        side_effect=[
            Exception("频率限制"),
            Exception("每分钟访问过高"),
            {"ok": True},
        ]
    )
    client._run_in_executor = run

    result = await client._rate_limited_call(lambda: None)

    assert result == {"ok": True}
    assert sleep_calls == [3.0, 6.0]
    assert run.await_count == 3


@pytest.mark.asyncio
async def test_rate_limit_retry_exceed_then_raise(monkeypatch) -> None:
    """超过最大重试次数后抛出原始异常。"""
    client = object.__new__(TushareClient)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client._get_tushare_rate_limiter",
        lambda: _FakeLimiter(),
    )

    async def _fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client.asyncio.sleep",
        _fake_sleep,
    )

    run = AsyncMock(side_effect=[Exception("频率超限")] * 4)
    client._run_in_executor = run

    with pytest.raises(Exception, match="频率超限"):
        await client._rate_limited_call(lambda: None)

    assert run.await_count == 4


@pytest.mark.asyncio
async def test_non_rate_limit_error_no_retry(monkeypatch) -> None:
    """非频率异常不触发重试。"""
    client = object.__new__(TushareClient)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client._get_tushare_rate_limiter",
        lambda: _FakeLimiter(),
    )

    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "src.modules.data_engineering.infrastructure.external_apis.tushare.client.asyncio.sleep",
        _fake_sleep,
    )

    run = AsyncMock(side_effect=RuntimeError("network timeout"))
    client._run_in_executor = run

    with pytest.raises(RuntimeError, match="network timeout"):
        await client._rate_limited_call(lambda: None)

    assert run.await_count == 1
    assert sleep_calls == []
