from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.merchant import Merchant


class Psp(BaseModel):
    """PSP model - Minimal definition for payment gateway
    References psps table from stab_portal_api.
    """

    __tablename__ = "psps"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    merchants: Mapped[list["Merchant"]] = relationship(
        "Merchant", back_populates="psp", lazy="select"
    )

    def __repr__(self):
        return f"<Psp(id={self.id}, name={self.name})>"
