"""add user tag stats

Revision ID: e7b2f0f4d2aa
Revises: c3f4c8b27a11
Create Date: 2026-02-21 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7b2f0f4d2aa"
down_revision: Union[str, Sequence[str], None] = "c3f4c8b27a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_tag_stats",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "tag"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO user_tag_stats (user_id, tag, entry_count)
            SELECT uae.user_id, tag_value, COUNT(*)::integer
            FROM user_anime_entries AS uae
            CROSS JOIN LATERAL unnest(uae.tags) AS tag_value
            GROUP BY uae.user_id, tag_value
            """
        )
    )
    op.alter_column("user_tag_stats", "entry_count", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("user_tag_stats")
