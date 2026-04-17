"""
Zylo — Main FastAPI Application

This is the single entry point. Each developer's router is mounted here.
Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from shared.config import settings
from shared.database import init_db, close_db
from shared.redis_client import close_redis

# ─── Import ALL routers (one per developer) ─────────
from rider_service.router import router as rider_router
from policy_service.router import router as policy_router
from premium_service.router import router as premium_router
from trigger_service.router import router as trigger_router
from claims_service.router import router as claims_router
from payout_service.router import router as payout_router
from admin_service.router import router as admin_router
from manual_claims.router import router as manual_claims_router

# ─── Import ALL models to ensure SQLAlchemy Registry is initialized ───
import rider_service.models
import policy_service.models
import trigger_service.models
import claims_service.models
import manual_claims.models


from trigger_service.scheduler import start_scheduler, stop_scheduler

# ─── Logging ─────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL),
)
logger = logging.getLogger("zylo")


# ─── Lifespan ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting Zylo API...")
    await init_db()
    logger.info("✅ Database initialized")
    
    # Load zones from DB into memory for trigger service
    from shared.zones import load_zones
    await load_zones()
    logger.info("✅ Zones loaded from DB")
    
    # Dev 3: Start trigger scheduler
    start_scheduler()
    
    yield
    
    # Dev 3: Stop trigger scheduler
    stop_scheduler()
    
    logger.info("🛑 Shutting down Zylo API...")
    await close_db()
    await close_redis()
    logger.info("✅ Connections closed")


# ─── App ─────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Parametric Income Protection for Delivery Riders",
    lifespan=lifespan,
)

uploads_dir = os.path.abspath(settings.UPLOAD_DIR)
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    message = first_error.get("msg", "Invalid request data")
    return JSONResponse(
        status_code=400,
        content={"detail": {"code": "VALIDATION_ERROR", "message": message}},
    )

# ─── CORS ────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Mount Routers ───────────────────────────────────
# Dev 1: Rider Service + Auth
app.include_router(rider_router, prefix="/api/riders", tags=["Riders (Dev 1)"])

# Dev 2: Policy Service
app.include_router(policy_router, prefix="/api/policies", tags=["Policies (Dev 2)"])

# Dev 2: Premium/Risk Service
app.include_router(premium_router, prefix="/api/risk", tags=["Premium (Dev 2)"])

# Dev 3: Trigger Service
app.include_router(trigger_router, prefix="/api/triggers", tags=["Triggers (Dev 3)"])

# Dev 4: Claims Service
app.include_router(claims_router, prefix="/api/claims", tags=["Claims (Dev 4)"])

# Dev 4: Payout Service
app.include_router(payout_router, prefix="/api/payouts", tags=["Payouts (Dev 4)"])

# Dev 5: Admin Service
app.include_router(admin_router, prefix="/api/admin", tags=["Admin (Dev 5)"])

# Dev 5: Manual Claims
app.include_router(manual_claims_router, prefix="/api/claims/manual", tags=["Manual Claims (Dev 5)"])


# ─── Health Check ────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check — verifies Postgres + Redis connectivity."""
    from shared.database import engine
    from shared.redis_client import get_redis

    pg_status = "disconnected"
    redis_status = "disconnected"

    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            pg_status = "connected"
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        pass

    try:
        redis = await get_redis()
        await redis.ping()
        redis_status = "connected"
    except Exception:
        pass

    from datetime import datetime, timezone
    from trigger_service.scheduler import get_cycle_count

    return {
        "status": "healthy" if pg_status == "connected" and redis_status == "connected" else "degraded",
        "postgres": pg_status,
        "redis": redis_status,
        "trigger_scheduler_cycles": get_cycle_count(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Zones (public) ─────────────────────────────────
@app.get("/api/zones", tags=["Zones"])
async def list_zones():
    """List available zones — public endpoint."""
    from sqlalchemy import text
    from shared.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Deduplicate at SQL level to ensure clean UI regardless of DB state
        result = await db.execute(text(
            "SELECT DISTINCT ON (lower(name), lower(city)) "
            "id, name, city, composite_risk_score, flood_risk_score, traffic_risk_score, store_risk_score, lat, lon "
            "FROM zones ORDER BY lower(name), lower(city), id"
        ))
        zones = [
            {
                "id": str(row[0]), 
                "name": row[1], 
                "city": row[2], 
                "risk_score": row[3],
                "flood_risk": row[4],
                "traffic_risk": row[5],
                "store_risk": row[6],
                "lat": row[7],
                "lon": row[8]
            }
            for row in result.fetchall()
        ]

    return {"zones": zones}


# ─── App Config (public) ─────────────────────────────
@app.get("/api/config", tags=["Config"])
async def get_config():
    """Return supported platforms and trigger types — single source of truth for frontends."""
    from shared.schemas import Platform, TriggerType

    PLATFORM_META = {"zepto": "⚡", "blinkit": "📦", "swiggy": "🛵"}
    TRIGGER_META = {
        "heavy_rain": "🌧️",
        "extreme_heat": "🌡️",
        "traffic_congestion": "🚗",
        "store_closure": "🏪",
        "platform_outage": "📱",
        "regulatory_curfew": "🚫",
        "gps_shadowban": "📍",
        "dark_store_queue": "🛒",
        "algorithmic_shock": "⚡",
        "community_signal": "📣",
    }

    platforms = [
        {"id": p.value, "name": p.value.capitalize(), "icon": PLATFORM_META.get(p.value, "🚀")}
        for p in Platform
    ]
    trigger_types = [
        {"type": t.value, "label": t.value.replace("_", " ").title(), "icon": TRIGGER_META.get(t.value, "⚠️")}
        for t in TriggerType
    ]

    return {"platforms": platforms, "trigger_types": trigger_types}
