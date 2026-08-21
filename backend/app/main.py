"""
Aria — FastAPI Application Entry Point.
Performs health verification checks on PostgreSQL & Redis,
pre-loads the local sentence-transformer embedding model,
and verifies the presence of the pgvector database extension on startup.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import check_db_connection, engine
from app.redis_client import check_redis_connection
from app.agent.embeddings import EmbeddingService
from app.api.routes import sessions, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Loads models, verifies database, extension, and cache dependencies.
    """
    print("\n--- Starting Aria Agent Backend (Week 2) ---")
    
    # 1. Verify Postgres Connection
    db_ok = await check_db_connection()
    if db_ok:
        print("[+] PostgreSQL connected successfully.")
    else:
        print("[!] Warning: PostgreSQL connection failed.")

    # 2. Verify Redis Connection
    redis_ok = await check_redis_connection()
    if redis_ok:
        print("[+] Redis connected successfully.")
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

    yield  # Server serves HTTP requests

    # Cleanup logic on server shutdown
    print("\n--- Shutting down Aria Agent Backend ---")
    await engine.dispose()
    print("[+] Database connections closed.")
    """
    Handles application startup and shutdown events.
    Loads models, verifies database, extension, and cache dependencies.
    """
    print("\n--- Starting Aria Agent Backend (Week 2) ---")
    
    # 1. Verify Postgres Connection
    db_ok = await check_db_connection()
    if db_ok:
        print("[+] PostgreSQL connected successfully.")
    else:
        print("[!] Warning: PostgreSQL connection failed.")

    # 2. Verify Redis Connection
    redis_ok = await check_redis_connection()
    if redis_ok:
        print("[+] Redis connected successfully.")
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
        async with async_engine.begin() as conn:
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

    yield  # Server serves HTTP requests

    # Cleanup logic on server shutdown
    print("\n--- Shutting down Aria Agent Backend ---")
    await async_engine.dispose()
    print("[+] Database connections closed.")


# Initialize FastAPI instance
app = FastAPI(
    title="Aria Agent API",
    description="Autonomous ReAct AI Productivity Agent Backend",
    version="0.2.0",
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

# Include API Routers (clean prefix mapping)
app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])


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