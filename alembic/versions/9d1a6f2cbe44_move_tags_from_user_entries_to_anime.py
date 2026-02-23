"""move tags from user anime entries to anime

Revision ID: 9d1a6f2cbe44
Revises: e7b2f0f4d2aa
Create Date: 2026-02-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9d1a6f2cbe44"
down_revision: Union[str, Sequence[str], None] = "e7b2f0f4d2aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "anime",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE anime AS a
            SET tags = src.tags
            FROM (
                SELECT
                    uae.anime_id,
                    COALESCE(array_agg(DISTINCT tag_value ORDER BY tag_value), '{}'::text[]) AS tags
                FROM user_anime_entries AS uae
                CROSS JOIN LATERAL unnest(uae.tags) AS tag_value
                GROUP BY uae.anime_id
            ) AS src
            WHERE a.id = src.anime_id
            """
        )
    )
    op.alter_column("anime", "tags", server_default=None)
    op.drop_column("user_anime_entries", "tags")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "user_anime_entries",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE user_anime_entries AS uae
            SET tags = COALESCE(a.tags, '{}'::text[])
            FROM anime AS a
            WHERE a.id = uae.anime_id
            """
        )
    )
    op.alter_column("user_anime_entries", "tags", server_default=None)
    op.drop_column("anime", "tags")
