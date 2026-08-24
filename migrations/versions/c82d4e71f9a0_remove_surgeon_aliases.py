"""remove surgeon aliases

Revision ID: c82d4e71f9a0
Revises: 9b61e8f3a4c2
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c82d4e71f9a0"
down_revision: Union[str, None] = "9b61e8f3a4c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("surgeons") as batch_op:
        batch_op.drop_column("aliases")


def downgrade() -> None:
    with op.batch_alter_table("surgeons") as batch_op:
        batch_op.add_column(sa.Column("aliases", sa.Text(), nullable=True))
