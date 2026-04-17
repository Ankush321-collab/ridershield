"""
Database session management — used by ALL services.

Usage in any router:
    from shared.database import get_db

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Rider))
        ...
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from shared.config import settings

# ─── Async Engine (for FastAPI endpoints) ───────────
engine_kwargs = {
    "echo": settings.DEBUG,
}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Base Model (all ORM models inherit from this) ──
class Base(DeclarativeBase):
    pass


# ─── Dependency Injection ───────────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency — yields a DB session per request.
    Usage:  db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── Startup / Shutdown ─────────────────────────────
async def init_db():
    """Create all tables on startup (dev only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose engine on shutdown."""
    await engine.dispose()
