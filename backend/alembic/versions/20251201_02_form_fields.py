"""添加表单字段配置.

Revision ID: 20251201_02_form_fields
Revises: 20251201_01_assessments
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20251201_02_form_fields'
down_revision = '20251201_01_assessments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 为 assessments 表添加 form_fields 字段
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('form_fields', sa.JSON(), nullable=True))
    
    # 为 submissions 表添加 custom_data 和 gender 字段
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('custom_data', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('gender', sa.String(10), nullable=True))
    
    # 为现有记录设置默认值
    op.execute("UPDATE assessments SET form_fields = '{}' WHERE form_fields IS NULL")
    op.execute("UPDATE submissions SET custom_data = '{}' WHERE custom_data IS NULL")


def downgrade() -> None:
    # 删除字段
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.drop_column('gender')
        batch_op.drop_column('custom_data')
    
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_column('form_fields')

