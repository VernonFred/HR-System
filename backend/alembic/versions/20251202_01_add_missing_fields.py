"""添加缺失字段: form_fields, candidate_id.

Revision ID: 20251202_01_add_missing_fields
Revises: 7c9ee2f45a87
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251202_01_add_missing_fields'
down_revision = '7c9ee2f45a87'
branch_labels = None
depends_on = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    """检查表是否有指定列"""
    inspector = inspect(conn)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()
    
    # 为 assessments 表添加 form_fields 字段（如果不存在）
    if not _has_column(conn, 'assessments', 'form_fields'):
        with op.batch_alter_table('assessments', schema=None) as batch_op:
            batch_op.add_column(sa.Column('form_fields', sa.JSON(), nullable=True))
        op.execute("UPDATE assessments SET form_fields = '{}' WHERE form_fields IS NULL")
    
    # 为 submissions 表添加 candidate_id 字段（如果不存在）
    if not _has_column(conn, 'submissions', 'candidate_id'):
        with op.batch_alter_table('submissions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('candidate_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    
    # 删除字段
    if _has_column(conn, 'submissions', 'candidate_id'):
        with op.batch_alter_table('submissions', schema=None) as batch_op:
            batch_op.drop_column('candidate_id')
    
    if _has_column(conn, 'assessments', 'form_fields'):
        with op.batch_alter_table('assessments', schema=None) as batch_op:
            batch_op.drop_column('form_fields')
