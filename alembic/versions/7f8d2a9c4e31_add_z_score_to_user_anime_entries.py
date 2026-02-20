"""add z_score to user anime entries

Revision ID: 7f8d2a9c4e31
Revises: a08e47b57fd7
Create Date: 2026-02-20 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f8d2a9c4e31"
down_revision: Union[str, Sequence[str], None] = "a08e47b57fd7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("user_anime_entries", sa.Column("z_score", sa.Float(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE user_anime_entries AS uae
            SET z_score = CASE
                WHEN uae.score IS NULL OR uae.score <= 0 THEN NULL
                WHEN us.stddev_score > 0 THEN ROUND(((uae.score::double precision - us.mean_score) / us.stddev_score)::numeric, 4)::double precision
                ELSE 0
            END
            FROM user_stats AS us
            WHERE us.user_id = uae.user_id
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_anime_entries", "z_score")
