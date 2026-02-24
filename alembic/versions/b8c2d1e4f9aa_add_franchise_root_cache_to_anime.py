"""add franchise root cache to anime

Revision ID: b8c2d1e4f9aa
Revises: f2c6b3a91d10
Create Date: 2026-02-24 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c2d1e4f9aa"
down_revision: Union[str, Sequence[str], None] = "f2c6b3a91d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("anime", sa.Column("franchise_root_mal_id", sa.Integer(), nullable=True))
    op.create_index("ix_anime_franchise_root_mal_id", "anime", ["franchise_root_mal_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_anime_franchise_root_mal_id", table_name="anime")
    op.drop_column("anime", "franchise_root_mal_id")
