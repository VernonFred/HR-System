"""add user role

Revision ID: add_user_role
Revises: add_users
Create Date: 2025-11-29
"""

from alembic import op
import sqlalchemy as sa

revision = "add_user_role"
down_revision = "add_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("role", sa.String(), server_default="user", nullable=False))


def downgrade() -> None:
    op.drop_column("user", "role")
