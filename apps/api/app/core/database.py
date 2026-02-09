"""
Database Configuration
Async SQLAlchemy engine and session management
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from app.core.config import settings


# Create async engine with conditional pool settings
# SQLite doesn't support pool_size, max_overflow, etc.
def _create_engine() -> AsyncEngine:
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    
    if is_sqlite:
        # SQLite configuration - use StaticPool for async
        return create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL configuration with connection pooling
        return create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,
        )

engine: AsyncEngine = _create_engine()

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Automatically handles session cleanup on completion.
    
    Yields:
        AsyncSession: Database session
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


async def init_db() -> None:
    """
    Initialize database tables.
    Should only be used for development/testing.
    Use Alembic migrations for production.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Called on application shutdown.
    """
    await engine.dispose()
