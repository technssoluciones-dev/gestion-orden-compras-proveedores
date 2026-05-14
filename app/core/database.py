"""
ProcureFlow AI — Async Database Engine
SQLAlchemy 2.0 async session factory — Unit of Work pattern
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
import structlog

from app.core.config import settings
from app.domain.models.db_models import Base

logger = structlog.get_logger(__name__)

# ── Engine ──────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ── Session factory ─────────────────────────────────────────────────────────
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields an async DB session.

    Unit of Work pattern:
      - COMMIT automático al finalizar la request sin excepciones.
      - ROLLBACK automático si ocurre cualquier excepción.
      - Esto garantiza que los datos se persisten en escrituras (POST/PUT/PATCH/DELETE)
        sin necesidad de llamar commit() en cada service.

    NOTA: Para read-only requests el commit es un no-op (harmless).
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_db_tables() -> None:
    """Create all tables (use Alembic for production migrations)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_ready")


async def check_db_connection() -> bool:
    """Health check: verifica conectividad a la base de datos."""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return False
