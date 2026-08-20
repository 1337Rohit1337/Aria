from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import check_db_connection
from app.redis_client import check_redis_connection
from app.api.routes import sessions, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Verifies critical dependencies (DB, Redis) before accepting traffic.
    """
    print("\n--- Starting Aria Agent Backend ---")
    
    # Verify Postgres connection
    db_ok = await check_db_connection()
    if db_ok:
        print("[+] PostgreSQL connected successfully.")
    else:
        print("[!] Warning: PostgreSQL connection failed.")

    # Verify Redis connection
    redis_ok = await check_redis_connection()
    if redis_ok:
        print("[+] Redis connected successfully.")
    else:
        print("[!] Warning: Redis connection failed.")

    print(f"[*] Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    print("-----------------------------------\n")

    yield  # Application serves incoming HTTP requests

    # Cleanup logic on server shutdown
    print("\n--- Shutting down Aria Agent Backend ---")


# Initialize FastAPI instance
app = FastAPI(
    title="Aria Agent API",
    description="Autonomous ReAct AI Productivity Agent Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Configuration — Allows React frontend to interact with backend
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


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check probe endpoint.
    Used by orchestrators (Docker/K8s) and monitoring tools to verify service status.
    """
    db_status = await check_db_connection()
    redis_status = await check_redis_connection()

    return {
        "status": "ok" if (db_status and redis_status) else "degraded",
        "postgres": db_status,
        "redis": redis_status,
        "debug": settings.DEBUG,
    }