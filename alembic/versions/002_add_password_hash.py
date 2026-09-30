"""Add password_hash column, make api_key_hash nullable.

Revision ID: 002
Revises: 001
Create Date: 2026-09-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(128), nullable=False, server_default=""))
    op.alter_column("users", "api_key_hash", existing_type=sa.String(64), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "api_key_hash", existing_type=sa.String(64), nullable=False)
    op.drop_column("users", "password_hash")
