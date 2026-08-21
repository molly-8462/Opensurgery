"""add surgeon submission and removal lifecycle

Revision ID: 7c4d2a90b816
Revises: 645cd7ed22d8
Create Date: 2026-08-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c4d2a90b816"
down_revision: Union[str, None] = "645cd7ed22d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("surgeons") as batch_op:
        batch_op.add_column(sa.Column("lifecycle_status", sa.String(length=20), nullable=False, server_default="pending"))
        batch_op.add_column(sa.Column("submitted_by_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("removed_by_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("removal_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key("fk_surgeons_submitted_by", "users", ["submitted_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_surgeons_removed_by", "users", ["removed_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_surgeons_lifecycle_status", ["lifecycle_status"])
        batch_op.create_index("ix_surgeons_submitted_by_id", ["submitted_by_id"])
    op.execute("UPDATE surgeons SET lifecycle_status = 'published' WHERE is_published = true")


def downgrade() -> None:
    with op.batch_alter_table("surgeons") as batch_op:
        batch_op.drop_index("ix_surgeons_submitted_by_id")
        batch_op.drop_index("ix_surgeons_lifecycle_status")
        batch_op.drop_constraint("fk_surgeons_removed_by", type_="foreignkey")
        batch_op.drop_constraint("fk_surgeons_submitted_by", type_="foreignkey")
        batch_op.drop_column("removal_reason")
        batch_op.drop_column("removed_by_id")
        batch_op.drop_column("removed_at")
        batch_op.drop_column("submitted_by_id")
        batch_op.drop_column("lifecycle_status")
