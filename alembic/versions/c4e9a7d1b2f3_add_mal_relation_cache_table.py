"""add mal relation cache table

Revision ID: c4e9a7d1b2f3
Revises: b8c2d1e4f9aa
Create Date: 2026-02-24 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c4e9a7d1b2f3"
down_revision: Union[str, Sequence[str], None] = "b8c2d1e4f9aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mal_relation_cache",
        sa.Column("provider_anime_id", sa.Integer(), nullable=False),
        sa.Column(
            "related_prequel_sequel_mal_ids",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("'{}'::integer[]"),
        ),
        sa.PrimaryKeyConstraint("provider_anime_id"),
    )
    op.alter_column("mal_relation_cache", "related_prequel_sequel_mal_ids", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("mal_relation_cache")
