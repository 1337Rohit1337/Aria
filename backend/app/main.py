from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import check_db_connection, engine
from app.redis_client import check_redis_connection
from app.agent.state import cleanup_stale_runs
from app.agent.embeddings import EmbeddingService
from app.api.routes import sessions, agent, notes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Loads models, verifies database, extension, cache dependencies,
    and resets stale agent states.
    """
    print("\n--- Starting Aria Agent Backend (Week 4) ---")
    
    # 1. Verify Postgres Connection
    db_ok = await check_db_connection()
    if db_ok:
        print("[+] PostgreSQL connected successfully.")
    else:
        print("[!] Warning: PostgreSQL connection failed.")

    # 2. Verify Redis Connection & Clean Stale Runs
    redis_ok = await check_redis_connection()
    if redis_ok:
        print("[+] Redis connected successfully.")
        # Clean up any runs stuck in 'running' state from previous crashes
        cleaned = await cleanup_stale_runs()
        if cleaned:
            print(f"[+] Cleaned up {cleaned} stale agent run(s) from Redis.")
    else:
        print("[!] Warning: Redis connection failed.")

    # 3. Eager-load local HuggingFace Embeddings Model
    print("[*] Loading embedding model (all-MiniLM-L6-v2) into system memory...")
    try:
        EmbeddingService.initialize()
        print("[+] Embedding model loaded successfully (384 dimensions).")
    except Exception as e:
        print(f"[!] Error: Failed to load embedding model: {e}")

    # 4. Verify pgvector extension is activated in PostgreSQL
    if db_ok:
        async with engine.begin() as conn:
            try:
                result = await conn.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                )
                row = result.fetchone()
                if row:
                    print(f"[+] pgvector extension active (v{row[0]}).")
                else:
                    print("[!] Warning: pgvector extension NOT installed. Long-term memory features will fail.")
            except Exception as e:
                print(f"[!] Error: Failed to check for pgvector extension: {e}")

    print(f"[*] Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    print("-------------------------------------------\n")

    yield  # Server is running and serving HTTP requests

    # Cleanup logic on server shutdown
    print("\n--- Shutting down Aria Agent Backend ---")
    await engine.dispose()
    print("[+] Database connections closed.")


# Initialize FastAPI instance
app = FastAPI(
    title="Aria Agent API",
    description="Autonomous ReAct AI Productivity Agent Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(notes.router, prefix="/notes", tags=["Notes"])


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check probe endpoint.
    Used by orchestrators (Docker/K8s) and monitoring tools.
    """
    db_status = await check_db_connection()
    redis_status = await check_redis_connection()

    return {
        "status": "ok" if (db_status and redis_status) else "degraded",
        "postgres": db_status,
        "redis": redis_status,
        "debug": settings.DEBUG,
    }