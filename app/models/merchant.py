from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.psp import Psp
    from app.models.store import Store


class Merchant(BaseModel):
    """Merchant model - Minimal definition for payment gateway
    References merchants table from stab_portal_api
    """

    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Foreign key to PSP
    psp_id: Mapped[int | None] = mapped_column(ForeignKey("psps.id"), nullable=True, index=True)

    # Relationships
    psp: Mapped[Optional["Psp"]] = relationship("Psp", back_populates="merchants", lazy="select")

    stores: Mapped[list["Store"]] = relationship("Store", back_populates="merchant", lazy="select")

    def __repr__(self):
        return f"<Merchant(id={self.id}, name={self.name})>"
