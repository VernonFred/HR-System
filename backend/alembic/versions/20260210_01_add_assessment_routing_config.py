"""为 assessments 添加 routing_config 字段.

Revision ID: 20260210_01_add_assessment_routing_config
Revises: 20251202_01_add_missing_fields
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260210_01_add_assessment_routing_config"
down_revision = "20251202_01_add_missing_fields"
branch_labels = None
depends_on = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "assessments", "routing_config"):
        with op.batch_alter_table("assessments", schema=None) as batch_op:
            batch_op.add_column(sa.Column("routing_config", sa.JSON(), nullable=True))
        op.execute("UPDATE assessments SET routing_config = '{}' WHERE routing_config IS NULL")


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "assessments", "routing_config"):
        with op.batch_alter_table("assessments", schema=None) as batch_op:
            batch_op.drop_column("routing_config")
