"""add job positions and profiles

Revision ID: 20251130_01_job_positions
Revises: add_user_role
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20251130_01_job_positions'
down_revision = 'add_user_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建岗位表
    op.create_table(
        'job_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('department', sa.String(), nullable=True),
        sa.Column('level', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_positions_name'), 'job_positions', ['name'], unique=False)

    # 创建岗位画像配置表
    op.create_table(
        'job_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_position_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('requirement_text', sa.String(), nullable=True),
        sa.Column('ai_analysis', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['job_position_id'], ['job_positions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_profiles_job_position_id'), 'job_profiles', ['job_position_id'], unique=False)

    # 创建岗位维度权重表
    op.create_table(
        'job_dimension_weights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_profile_id', sa.Integer(), nullable=False),
        sa.Column('dimension_code', sa.String(), nullable=False),
        sa.Column('dimension_name', sa.String(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('ideal_score', sa.Float(), nullable=True),
        sa.Column('min_score', sa.Float(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['job_profile_id'], ['job_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_dimension_weights_job_profile_id'), 'job_dimension_weights', ['job_profile_id'], unique=False)

    # 创建候选人表
    op.create_table(
        'candidates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('resume_file_path', sa.String(), nullable=True),
        sa.Column('resume_original_name', sa.String(), nullable=True),
        sa.Column('resume_text', sa.String(), nullable=True),
        sa.Column('resume_parsed_data', sa.JSON(), nullable=True),
        sa.Column('resume_uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submission.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_name'), 'candidates', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_candidates_name'), table_name='candidates')
    op.drop_table('candidates')
    op.drop_index(op.f('ix_job_dimension_weights_job_profile_id'), table_name='job_dimension_weights')
    op.drop_table('job_dimension_weights')
    op.drop_index(op.f('ix_job_profiles_job_position_id'), table_name='job_profiles')
    op.drop_table('job_profiles')
    op.drop_index(op.f('ix_job_positions_name'), table_name='job_positions')
    op.drop_table('job_positions')

