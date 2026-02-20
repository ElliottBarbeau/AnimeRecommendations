"""add mean_score to users

Revision ID: a08e47b57fd7
Revises: a95b82a8119e
Create Date: 2026-02-20 17:59:16.350293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a08e47b57fd7'
down_revision: Union[str, Sequence[str], None] = 'a95b82a8119e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_stats",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mean_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stddev_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}

    if "mean_score" in user_columns:
        op.execute(
            sa.text(
                """
                INSERT INTO user_stats (user_id, mean_score, stddev_score, rating_count)
                SELECT id, COALESCE(mean_score, 0), 0, 0
                FROM users
                """
            )
        )
        op.drop_column("users", "mean_score")
    else:
        op.execute(
            sa.text(
                """
                INSERT INTO user_stats (user_id, mean_score, stddev_score, rating_count)
                SELECT id, 0, 0, 0
                FROM users
                """
            )
        )

    op.alter_column("user_stats", "mean_score", server_default=None)
    op.alter_column("user_stats", "stddev_score", server_default=None)
    op.alter_column("user_stats", "rating_count", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("users", sa.Column("mean_score", sa.Float(), nullable=False, server_default="0"))
    op.execute(
        sa.text(
            """
            UPDATE users
            SET mean_score = COALESCE(user_stats.mean_score, 0)
            FROM user_stats
            WHERE user_stats.user_id = users.id
            """
        )
    )
    op.alter_column("users", "mean_score", server_default=None)
    op.drop_table("user_stats")
