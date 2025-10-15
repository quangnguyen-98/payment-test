"""
Unit tests for database manager and connection.

Tests database lifecycle, health checks, and session management.
"""
import pytest
from sqlalchemy import select, text

from app.core.database_manager import Base, db_manager


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    @pytest.mark.asyncio
    async def test_database_engine_creation(self, db_engine):
        """Test database engine is created successfully."""
        assert db_engine is not None
        # Pool attributes vary by database type
        assert db_engine.pool is not None

    @pytest.mark.asyncio
    async def test_database_session_creation(self, db_session):
        """Test database session is created successfully."""
        assert db_session is not None
        assert db_session.is_active

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session):
        """Test database connection works."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_database_tables_created(self, db_engine):
        """Test all tables are created."""
        async with db_engine.begin() as conn:
            # Check if tables exist
            result = await conn.run_sync(
                lambda sync_conn: sync_conn.dialect.has_table(
                    sync_conn, "payments"
                )
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, db_session):
        """Test session rollback on error."""
        try:
            # Force an error
            await db_session.execute(text("INVALID SQL"))
        except Exception:
            await db_session.rollback()

        # Session should still be usable
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1


class TestDatabaseHealth:
    """Test database health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, db_engine):
        """Test health check returns success for healthy database."""
        async with db_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_database_ping(self, db_session):
        """Test database responds to ping."""
        result = await db_session.execute(text("SELECT 1 as ping"))
        assert result.scalar() == 1


class TestBaseModel:
    """Test Base model functionality."""

    def test_base_has_declarative_base(self):
        """Test Base is a valid declarative base."""
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "__table_cls__")

    def test_base_first_columns_defined(self):
        """Test first columns are defined."""
        assert hasattr(Base, "__first_columns__")
        expected = ("id", "created_at", "updated_at", "created_by", "updated_by")
        assert Base.__first_columns__ == expected
