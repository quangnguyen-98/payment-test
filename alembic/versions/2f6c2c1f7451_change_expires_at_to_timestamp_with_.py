"""change_expires_at_to_timestamp_with_timezone

Revision ID: 2f6c2c1f7451
Revises: 
Create Date: 2025-09-19 09:13:14.568345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f6c2c1f7451"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change expires_at column from TIMESTAMP to TIMESTAMP WITH TIME ZONE
    op.alter_column(
        'payments',
        'expires_at',
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using='expires_at AT TIME ZONE \'UTC\'',  # Convert existing data to UTC
        existing_type=sa.TIMESTAMP(timezone=False),
        existing_nullable=True
    )


def downgrade() -> None:
    # Revert expires_at column from TIMESTAMP WITH TIME ZONE to TIMESTAMP
    op.alter_column(
        'payments',
        'expires_at',
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using='expires_at AT TIME ZONE \'UTC\'',  # Convert back to naive timestamp
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=True
    )
