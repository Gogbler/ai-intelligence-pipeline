"""Rate Limit and HTTP 429 Handling Engine.

Implements exponential backoff with full jitter to handle rate limits
gracefully across high-concurrency extraction workloads.
"""

import asyncio
import random
from typing import Callable, Any, Optional
from app.utils.logger import get_logger

logger = get_logger("RateLimiter")


class RateLimitError(Exception):
    """Raised when upstream API responds with HTTP 429 Too Many Requests."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ContextOverflowError(Exception):
    """Raised when upstream API responds with HTTP 413 Payload Too Large."""
    pass


async def execute_with_backoff(
    coro_func: Callable[..., Any],
    *args,
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    provider_name: str = "LLM",
    on_retry: Optional[Callable[[int, float], None]] = None,
    **kwargs,
) -> Any:
    """Execute an asynchronous function with exponential backoff and randomized jitter for HTTP 429."""
    attempt = 0
    while True:
        try:
            return await coro_func(*args, **kwargs)
        except RateLimitError as e:
            attempt += 1
            if attempt > max_retries:
                logger.error(f"[{provider_name}] Max retries ({max_retries}) exceeded on rate limit. Giving up.")
                raise

            # Use retry-after header if provided, otherwise compute exponential backoff with full jitter
            if e.retry_after and e.retry_after > 0:
                sleep_seconds = e.retry_after + random.uniform(0.1, 0.5)
            else:
                calculated = base_delay * (backoff_factor ** (attempt - 1))
                sleep_seconds = random.uniform(0.5, min(max_delay, calculated))

            logger.warning(
                f"[{provider_name}] Rate limit (429) encountered. Attempt {attempt}/{max_retries}. "
                f"Backing off for {sleep_seconds:.2f}s with jitter..."
            )
            if on_retry:
                try:
                    on_retry(attempt, sleep_seconds)
                except Exception:
                    pass
            await asyncio.sleep(sleep_seconds)

        except ContextOverflowError:
            logger.error(f"[{provider_name}] Payload too large (413). Cannot retry without chunking.")
            raise

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
                attempt += 1
                if attempt > max_retries:
                    raise RateLimitError(f"[{provider_name}] Max retries exceeded for 429: {e}")
                calculated = base_delay * (backoff_factor ** (attempt - 1))
                sleep_seconds = random.uniform(0.5, min(max_delay, calculated))
                logger.warning(
                    f"[{provider_name}] Rate limit detected in error. Attempt {attempt}/{max_retries}. Sleeping {sleep_seconds:.2f}s."
                )
                if on_retry:
                    try:
                        on_retry(attempt, sleep_seconds)
                    except Exception:
                        pass
                await asyncio.sleep(sleep_seconds)
            else:
                # Non-rate-limit exception; propagate immediately
                raise
