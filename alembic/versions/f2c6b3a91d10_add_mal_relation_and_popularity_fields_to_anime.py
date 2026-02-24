"""add MAL relation and popularity fields to anime

Revision ID: f2c6b3a91d10
Revises: d4f7a2c1b8e6
Create Date: 2026-02-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f2c6b3a91d10"
down_revision: Union[str, Sequence[str], None] = "d4f7a2c1b8e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("anime", sa.Column("provider_popularity_rank", sa.Integer(), nullable=True))
    op.add_column("anime", sa.Column("provider_member_count", sa.Integer(), nullable=True))
    op.add_column(
        "anime",
        sa.Column(
            "related_prequel_sequel_mal_ids",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("'{}'::integer[]"),
        ),
    )
    op.alter_column("anime", "related_prequel_sequel_mal_ids", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("anime", "related_prequel_sequel_mal_ids")
    op.drop_column("anime", "provider_member_count")
    op.drop_column("anime", "provider_popularity_rank")
