"""add avg z score to user tag stats

Revision ID: c8a5f1d2e9b3
Revises: b31f6c8d4a12
Create Date: 2026-02-23 00:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8a5f1d2e9b3"
down_revision: Union[str, Sequence[str], None] = "b31f6c8d4a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_tag_stats",
        sa.Column("z_score_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_tag_stats",
        sa.Column("avg_z_score", sa.Float(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE user_tag_stats AS uts
            SET
                z_score_count = COALESCE(src.z_score_count, 0),
                avg_z_score = src.avg_z_score
            FROM (
                SELECT
                    uae.user_id,
                    tag_value AS tag,
                    COUNT(uae.z_score)::integer AS z_score_count,
                    AVG(uae.z_score)::double precision AS avg_z_score
                FROM user_anime_entries AS uae
                JOIN anime AS a
                    ON a.id = uae.anime_id
                CROSS JOIN LATERAL unnest(a.tags) AS tag_value
                WHERE uae.z_score IS NOT NULL
                GROUP BY uae.user_id, tag_value
            ) AS src
            WHERE uts.user_id = src.user_id
              AND uts.tag = src.tag
            """
        )
    )
    op.alter_column("user_tag_stats", "z_score_count", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_tag_stats", "avg_z_score")
    op.drop_column("user_tag_stats", "z_score_count")
