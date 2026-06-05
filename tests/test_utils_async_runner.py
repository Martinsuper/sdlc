import asyncio

import pytest

from sdlc.utils.async_runner import retry_async, run_with_timeout


@pytest.mark.asyncio
async def test_run_with_timeout_completes():
    async def quick():
        return 42

    result = await run_with_timeout(quick(), timeout=1.0)
    assert result == 42


@pytest.mark.asyncio
async def test_run_with_timeout_raises_on_timeout():
    async def slow():
        await asyncio.sleep(10)

    with pytest.raises(asyncio.TimeoutError):
        await run_with_timeout(slow(), timeout=0.05)


@pytest.mark.asyncio
async def test_retry_async_succeeds_first_try():
    async def ok():
        return "done"

    result = await retry_async(ok, retries=3, backoff=0.01)
    assert result == "done"


@pytest.mark.asyncio
async def test_retry_async_succeeds_after_retries():
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("not yet")
        return "recovered"

    result = await retry_async(flaky, retries=3, backoff=0.01)
    assert result == "recovered"
    assert calls == 3


@pytest.mark.asyncio
async def test_retry_async_raises_last_exception():
    async def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await retry_async(always_fail, retries=2, backoff=0.01)
