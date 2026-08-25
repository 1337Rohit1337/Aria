"""
Redis-backed agent run state management.
Gracefully degrades if Redis is unreachable — never blocks the agent.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.redis_client import get_redis_client

logger = logging.getLogger(__name__)

STATE_TTL = 3600        # 1 hour auto-cleanup
STALE_THRESHOLD = 600   # 10 minutes — stale on restart


# ── helpers ──────────────────────────────────────────────────────────

def _key(session_id: str) -> str:
    return f"agent_run:{session_id}"


def _cancel_key(run_id: str) -> str:
    return f"agent_cancel:{run_id}"


def _serialize(state: dict) -> str:
    return json.dumps(state, default=str)


def _deserialize(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    return json.loads(raw)


# ── public API ───────────────────────────────────────────────────────

async def try_acquire(
    session_id: str,
    run_id: str,
    input_text: str,
) -> bool:
    """
    Attempt to claim the run slot for a session.
    Returns False → 409 Conflict (already running).
    Returns True  → slot acquired OR Redis is down (fail-open).
    """
    key = _key(session_id)
    try:
        client = get_redis_client()
        async with client:
            raw = await client.get(key)
            existing = _deserialize(raw)
            if existing and existing.get("status") == "running":
                return False

            state = {
                "session_id": session_id,
                "run_id": run_id,
                "status": "running",
                "current_step": 0,
                "tools_called": [],
                "started_at": datetime.now(timezone.utc).isoformat(),
                "input": input_text[:500],  # cap length to avoid bloated state
            }
            await client.setex(key, STATE_TTL, _serialize(state))
            return True
    except Exception as exc:
        logger.warning("Redis unavailable (try_acquire): %s — failing open", exc)
        return True


async def update(session_id: str, **fields) -> None:
    """Merge fields into the existing state dict."""
    key = _key(session_id)
    try:
        client = get_redis_client()
        async with client:
            state = _deserialize(await client.get(key))
            if not state:
                return
            state.update(fields)
            await client.setex(key, STATE_TTL, _serialize(state))
    except Exception as exc:
        logger.warning("Redis unavailable (update): %s", exc)


async def get(session_id: str) -> Optional[dict]:
    try:
        client = get_redis_client()
        async with client:
            return _deserialize(await client.get(_key(session_id)))
    except Exception as exc:
        logger.warning("Redis unavailable (get): %s", exc)
        return None


async def release(session_id: str) -> None:
    try:
        client = get_redis_client()
        async with client:
            await client.delete(_key(session_id))
    except Exception as exc:
        logger.warning("Redis unavailable (release): %s", exc)


async def mark_finished(session_id: str, status: str, **extra) -> None:
    """Set terminal status and keep the key briefly (60s) for polling."""
    key = _key(session_id)
    try:
        client = get_redis_client()
        async with client:
            state = _deserialize(await client.get(key))
            if not state:
                return
            state["status"] = status
            state.update(extra)
            await client.setex(key, 60, _serialize(state))
    except Exception as exc:
        logger.warning("Redis unavailable (mark_finished): %s", exc)


# ── cancellation ─────────────────────────────────────────────────────

async def request_cancel(run_id: str) -> None:
    try:
        client = get_redis_client()
        async with client:
            await client.setex(_cancel_key(run_id), 300, "true")
    except Exception as exc:
        logger.warning("Redis unavailable (request_cancel): %s", exc)


async def is_cancelled(run_id: str) -> bool:
    try:
        client = get_redis_client()
        async with client:
            val = await client.get(_cancel_key(run_id))
            return val == "true"
    except Exception:
        return False


# ── startup cleanup ──────────────────────────────────────────────────

async def cleanup_stale_runs() -> int:
    """Mark any 'running' states older than STALE_THRESHOLD as failed."""
    cleaned = 0
    try:
        client = get_redis_client()
        async with client:
            cursor = 0
            while True:
                cursor, keys = await client.scan(
                    cursor=cursor, match="agent_run:*", count=100
                )
                for key in keys:
                    raw = await client.get(key)
                    state = _deserialize(raw)
                    if not state or state.get("status") != "running":
                        continue
                    started_raw = state.get("started_at")
                    if not started_raw:
                        continue
                    started = datetime.fromisoformat(started_raw)
                    if (datetime.now(timezone.utc) - started).total_seconds() > STALE_THRESHOLD:
                        state["status"] = "failed"
                        state["error"] = "Stale run cleaned on server restart"
                        await client.setex(key, STATE_TTL, _serialize(state))
                        cleaned += 1
                if cursor == 0:
                    break
    except Exception as exc:
        logger.warning("Redis unavailable (cleanup_stale): %s", exc)
    return cleaned