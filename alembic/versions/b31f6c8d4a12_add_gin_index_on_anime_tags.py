"""add gin index on anime tags

Revision ID: b31f6c8d4a12
Revises: 9d1a6f2cbe44
Create Date: 2026-02-23 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b31f6c8d4a12"
down_revision: Union[str, Sequence[str], None] = "9d1a6f2cbe44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_anime_tags_gin", "anime", ["tags"], unique=False, postgresql_using="gin")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_anime_tags_gin", table_name="anime")
