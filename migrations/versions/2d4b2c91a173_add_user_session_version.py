"""add user session version

Revision ID: 2d4b2c91a173
Revises: c82d4e71f9a0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "2d4b2c91a173"
down_revision: Union[str, None] = "c82d4e71f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("session_version", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "session_version")
