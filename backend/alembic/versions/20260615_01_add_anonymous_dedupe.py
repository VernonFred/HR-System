"""添加匿名问卷同设备防重复字段.

Revision ID: 20260615_01_add_anonymous_dedupe
Revises: 20260210_01_add_assessment_routing_config
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260615_01_add_anonymous_dedupe"
down_revision = "20260210_01_add_assessment_routing_config"
branch_labels = None
depends_on = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "assessments", "anonymous_mode"):
        with op.batch_alter_table("assessments", schema=None) as batch_op:
            batch_op.add_column(sa.Column("anonymous_mode", sa.Boolean(), nullable=True))
        op.execute("UPDATE assessments SET anonymous_mode = 0 WHERE anonymous_mode IS NULL")

    if not _has_column(conn, "submissions", "anonymous_device_id"):
        with op.batch_alter_table("submissions", schema=None) as batch_op:
            batch_op.add_column(sa.Column("anonymous_device_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, "submissions", "anonymous_device_id"):
        with op.batch_alter_table("submissions", schema=None) as batch_op:
            batch_op.drop_column("anonymous_device_id")

    if _has_column(conn, "assessments", "anonymous_mode"):
        with op.batch_alter_table("assessments", schema=None) as batch_op:
            batch_op.drop_column("anonymous_mode")
