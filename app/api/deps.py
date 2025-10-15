"""API Dependencies for dependency injection.

Contains dependencies used across API routes like database sessions,
authentication, pagination parameters, etc.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_manager import db_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in db_manager.get_session():
        yield session


async def get_current_user() -> str | None:
    """Get current user from authentication.

    For now, this is a placeholder. In a real implementation,
    you would decode JWT tokens or validate API keys here.
    """
    # TODO: Implement proper authentication
    return "system"  # Default user for now
