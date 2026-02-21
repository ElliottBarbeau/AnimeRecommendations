"""add tags to user anime entries

Revision ID: c3f4c8b27a11
Revises: 7f8d2a9c4e31
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3f4c8b27a11"
down_revision: Union[str, Sequence[str], None] = "7f8d2a9c4e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user_anime_entries",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.alter_column("user_anime_entries", "tags", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_anime_entries", "tags")
