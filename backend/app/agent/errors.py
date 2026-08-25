import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── custom exceptions ────────────────────────────────────────────────

class AgentTimeoutError(Exception):
    """Raised when the agent exceeds the 120-second wall-clock limit."""


class AgentCancelledError(Exception):
    """Raised when the user cancels the run via the API."""


# ── timeout wrapper ──────────────────────────────────────────────────

async def run_with_timeout(coro, timeout: float = 120.0) -> Any:
    """Wrap any awaitable with a hard wall-clock timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise AgentTimeoutError(
            f"Agent run exceeded {timeout}s limit"
        ) from None


# ── exponential-backoff retry (for LLM-level failures) ───────────────

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for async functions.
    Delays: 2 s → 4 s → 8 s  (base_delay * 2^attempt).
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return await fn(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "Retry %d/%d for %s after %.1fs — %s",
                            attempt + 1, max_retries, fn.__name__, delay, exc,
                        )
                        await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


# ── safe tool wrapper (belt-and-suspenders) ──────────────────────────

def safe_tool_result(tool_name: str, error: Exception) -> str:
    """
    Return a descriptive error string the ReAct loop can reason about.
    Used as a fallback when LangChain's handle_tool_error isn't enough.
    """
    msg = str(error) or type(error).__name__
    return (
        f"[ERROR in tool '{tool_name}']: {msg}. "
        "Please check your input format and try again, or use a different tool."
    )