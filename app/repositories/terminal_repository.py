"""Terminal Repository - Data access layer for terminal operations."""

from app.models.terminal import Terminal
from app.repositories.base_mixins import CRUDMixin


class TerminalRepository(CRUDMixin[Terminal]):
    """Repository class for Terminal entity."""

    def __init__(self, session, **kwargs):
        super().__init__(session, **kwargs)
        self.model = Terminal
        self.id_attr = Terminal.id
        self.tenant_attr = None  # No tenant for terminal

    async def exists(self, terminal_id: int) -> bool:
        """Check if terminal exists."""
        terminal = await self.get(terminal_id)
        return terminal is not None
