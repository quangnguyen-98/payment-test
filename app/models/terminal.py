from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.store import Store


class Terminal(BaseModel):
    """Terminal model - Minimal definition for payment gateway
    References terminals table from stab_portal_api
    """

    __tablename__ = "terminals"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Foreign key to store
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"), nullable=True)

    # Relationships
    store: Mapped[Optional["Store"]] = relationship(
        "Store", back_populates="terminals", lazy="select"
    )

    def __repr__(self):
        return f"<Terminal(id={self.id}, name={self.name})>"
