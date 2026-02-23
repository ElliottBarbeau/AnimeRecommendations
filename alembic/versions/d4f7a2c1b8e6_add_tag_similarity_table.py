"""add tag similarity table

Revision ID: d4f7a2c1b8e6
Revises: c8a5f1d2e9b3
Create Date: 2026-02-23 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4f7a2c1b8e6"
down_revision: Union[str, Sequence[str], None] = "c8a5f1d2e9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tag_similarity",
        sa.Column("source_tag", sa.String(), nullable=False),
        sa.Column("related_tag", sa.String(), nullable=False),
        sa.Column("cooccurrence_count", sa.Integer(), nullable=False),
        sa.Column("jaccard_score", sa.Float(), nullable=False),
        sa.CheckConstraint("source_tag <> related_tag", name="ck_tag_similarity_no_self"),
        sa.PrimaryKeyConstraint("source_tag", "related_tag"),
    )
    op.create_index("ix_tag_similarity_related_tag", "tag_similarity", ["related_tag"], unique=False)

    op.execute(
        sa.text(
            """
            WITH tag_instances AS (
                SELECT
                    a.id AS anime_id,
                    tag_value AS tag
                FROM anime AS a
                CROSS JOIN LATERAL unnest(a.tags) AS tag_value
                WHERE tag_value IS NOT NULL
                  AND btrim(tag_value) <> ''
            ),
            tag_counts AS (
                SELECT
                    tag,
                    COUNT(DISTINCT anime_id)::integer AS anime_count
                FROM tag_instances
                GROUP BY tag
            ),
            pair_counts AS (
                SELECT
                    ti1.tag AS tag_a,
                    ti2.tag AS tag_b,
                    COUNT(DISTINCT ti1.anime_id)::integer AS cooccurrence_count
                FROM tag_instances AS ti1
                JOIN tag_instances AS ti2
                    ON ti1.anime_id = ti2.anime_id
                   AND ti1.tag < ti2.tag
                GROUP BY ti1.tag, ti2.tag
            ),
            pair_scores AS (
                SELECT
                    pc.tag_a,
                    pc.tag_b,
                    pc.cooccurrence_count,
                    (
                        pc.cooccurrence_count::double precision
                        / NULLIF((tc_a.anime_count + tc_b.anime_count - pc.cooccurrence_count), 0)
                    ) AS jaccard_score
                FROM pair_counts AS pc
                JOIN tag_counts AS tc_a
                    ON tc_a.tag = pc.tag_a
                JOIN tag_counts AS tc_b
                    ON tc_b.tag = pc.tag_b
            )
            INSERT INTO tag_similarity (source_tag, related_tag, cooccurrence_count, jaccard_score)
            SELECT tag_a, tag_b, cooccurrence_count, jaccard_score
            FROM pair_scores
            UNION ALL
            SELECT tag_b, tag_a, cooccurrence_count, jaccard_score
            FROM pair_scores
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_tag_similarity_related_tag", table_name="tag_similarity")
    op.drop_table("tag_similarity")
