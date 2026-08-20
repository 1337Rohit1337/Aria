import json
from datetime import datetime
import redis.asyncio as aioredis
from app.config import settings


# Create Redis connection pool
# decode_responses=True  returns strings instead of bytes
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=10,
)


def get_redis_client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)


# FastAPI dependency
async def get_redis() -> aioredis.Redis:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


# Helper: store agent state
async def set_agent_state(session_id: str, state: dict, ttl: int = 3600) -> None:
    client = get_redis_client()
    key = f"agent_run:{session_id}"
    await client.setex(key, ttl, json.dumps(state, default=str))
    await client.aclose()


# Helper: retrieve agent state
async def get_agent_state(session_id: str) -> dict | None:
    client = get_redis_client()
    key = f"agent_run:{session_id}"
    data = await client.get(key)
    await client.aclose()
    if data:
        return json.loads(data)
    return None


# Helper: delete agent state
async def delete_agent_state(session_id: str) -> None:
    client = get_redis_client()
    key = f"agent_run:{session_id}"
    await client.delete(key)
    await client.aclose()


# Called on startup to verify Redis is reachable
async def check_redis_connection() -> bool:
    try:
        client = get_redis_client()
        await client.ping()
        await client.aclose()
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False