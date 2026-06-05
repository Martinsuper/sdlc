import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


async def run_with_timeout(coro: Coroutine[Any, Any, T], timeout: float) -> T:
    return await asyncio.wait_for(coro, timeout=timeout)


async def retry_async(
    fn: Callable[..., Coroutine[Any, Any, T]],
    retries: int = 3,
    backoff: float = 1.0,
    *args: Any,
    **kwargs: Any,
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return await fn(*args, **kwargs)
        except BaseException as exc:
            last_exc = exc
            if attempt < retries:
                delay = backoff * (2**attempt)
                await asyncio.sleep(delay)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("retry_async: unreachable")
