"""Unit tests for Rate Limiting and HTTP 429 Exponential Backoff with Jitter."""

import asyncio
import pytest
from app.llm.rate_limiter import execute_with_backoff, RateLimitError


def test_successful_execution_without_retry():
    calls = 0

    async def dummy_coro():
        nonlocal calls
        calls += 1
        return "SUCCESS"

    res = asyncio.run(execute_with_backoff(dummy_coro, base_delay=0.01))
    assert res == "SUCCESS"
    assert calls == 1


def test_retry_on_429_then_succeed():
    calls = 0

    async def flaky_coro():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RateLimitError("429 Too Many Requests")
        return "RECOVERED"

    res = asyncio.run(execute_with_backoff(flaky_coro, max_retries=4, base_delay=0.01, backoff_factor=1.5))
    assert res == "RECOVERED"
    assert calls == 3


def test_exceeding_max_retries_raises():
    calls = 0

    async def always_429():
        nonlocal calls
        calls += 1
        raise RateLimitError("Persistent 429")

    with pytest.raises(RateLimitError):
        asyncio.run(execute_with_backoff(always_429, max_retries=2, base_delay=0.01))

    assert calls == 3  # initial + 2 retries
