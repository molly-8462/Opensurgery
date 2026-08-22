"""add user ban audit fields

Revision ID: 9b61e8f3a4c2
Revises: 7c4d2a90b816
Create Date: 2026-08-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b61e8f3a4c2"
down_revision: Union[str, None] = "7c4d2a90b816"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("banned_by_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("ban_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key("fk_users_banned_by", "users", ["banned_by_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_banned_by", type_="foreignkey")
        batch_op.drop_column("ban_reason")
        batch_op.drop_column("banned_by_id")
        batch_op.drop_column("banned_at")
