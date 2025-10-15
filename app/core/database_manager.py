# app/core/database_manager.py - Database management and base class
"""Database manager with proper lifecycle management for async engines.
Also provides Base class for SQLAlchemy models.
Follows best practices for FastAPI + SQLAlchemy async.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import Column, Table, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    __first_columns__ = ("id", "created_at", "updated_at", "created_by", "updated_by")

    @classmethod
    def __table_cls__(cls, *args, **kwargs):
        """Custom table creation to order columns consistently."""
        # args = (name, metadata, *cols_and_constraints)
        name, metadata, *cols_and_cons = args

        # Split columns from other objects (constraints/indexes/etc.)
        columns = [obj for obj in cols_and_cons if isinstance(obj, Column)]
        others = [obj for obj in cols_and_cons if not isinstance(obj, Column)]

        # Reorder: move columns in __first_columns__ to the front
        first_names = tuple(getattr(cls, "__first_columns__", Base.__first_columns__))
        first_set = set(first_names)
        first_cols = [c for c in columns if c.name in first_set]
        rest_cols = [c for c in columns if c.name not in first_set]

        # Create the Table exactly once
        return Table(name, metadata, *(first_cols + rest_cols + others), **kwargs)


class DatabaseManager:
    """Manages database engine and session lifecycle."""

    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.SessionLocal: async_sessionmaker | None = None

    async def initialize(self):
        """Initialize database engine and session maker.
        Should be called during app startup.
        """
        if settings.DATABASE_URL.startswith("sqlite"):
            # SQLite for development
            async_url = settings.DATABASE_URL
            if "aiosqlite" not in async_url:
                async_url = async_url.replace("sqlite:///", "sqlite+aiosqlite:///")

            self.engine = create_async_engine(
                async_url,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 20,
                },
                poolclass=StaticPool,  # Single connection for SQLite
                pool_pre_ping=True,
                echo=settings.SQL_LOG_LEVEL.upper() in ["DEBUG", "INFO"],
                future=True,
            )

            # Enable foreign keys for SQLite
            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            logger.info("SQLite async engine initialized for development")

        else:
            # PostgreSQL for production
            async_url = settings.DATABASE_URL
            if "asyncpg" not in async_url:
                async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")

            self.engine = create_async_engine(
                async_url,
                # Use default AsyncAdaptedQueuePool (best for async)
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=True,
                connect_args={
                    "server_settings": {
                        "application_name": "stab_payment_gateway_api",
                        "jit": "off",
                        "timezone": "UTC",  # Force UTC timezone for all connections
                    },
                    "command_timeout": 60,
                    "timeout": 10,
                },
                echo=settings.SQL_LOG_LEVEL.upper() in ["DEBUG", "INFO"],
                echo_pool=settings.SQL_POOL_LOG_ENABLED,
                future=True,
            )

            logger.info(
                f"PostgreSQL async engine initialized with pool_size={settings.DB_POOL_SIZE}"
            )

        # Create session factory
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def close(self):
        """Close database connections.
        Should be called during app shutdown.
        """
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session for dependency injection."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database transaction error: {e}")
                raise
            finally:
                await session.close()

    async def check_health(self) -> dict:
        """Check database health."""
        try:
            async with self.SessionLocal() as session:
                await session.execute(text("SELECT 1"))
                return {"healthy": True, "message": "Database is responsive"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"healthy": False, "message": str(e)}


# Global instance (will be initialized during startup)
db_manager = DatabaseManager()


# Compatibility functions for existing code
async def check_async_database_health():
    """Compatibility wrapper for check_async_database_health.
    DEPRECATED: Use db_manager.check_health() directly.
    """
    result = await db_manager.check_health()
    # Add pool_status for compatibility
    result["pool_status"] = {
        "size": 20,  # Default values
        "checked_out": 0,
        "overflow": 0,
        "total": 20,
    }
    return result


async def close_database_connections():
    """Compatibility wrapper for close_database_connections.
    DEPRECATED: Use db_manager.close() directly.
    """
    await db_manager.close()
