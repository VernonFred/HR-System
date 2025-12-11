"""add v2 spec tables

Revision ID: 7c9ee2f45a87
Revises: 20251201_02_form_fields
Create Date: 2025-12-02 20:01:04.405455
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "7c9ee2f45a87"
down_revision = "20251201_02_form_fields"
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    inspector = inspect(conn)
    return name in inspector.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()

    # v2 candidates
    if not _has_table(conn, "candidates_v2"):
        op.create_table(
            "candidates_v2",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("phone", sa.String(), nullable=False, index=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("applied_position", sa.String(), nullable=True),
            sa.Column("extra_info", sa.JSON(), nullable=True),
            sa.Column("has_resume", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("resume_file_id", sa.String(), nullable=True),
            sa.Column("first_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("latest_assessment_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )

    if not _has_table(conn, "resume_summaries"):
        op.create_table(
            "resume_summaries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates_v2.id"), nullable=False, index=True),
            sa.Column("parsed_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("education", sa.Text(), nullable=True),
            sa.Column("experiences", sa.Text(), nullable=True),
            sa.Column("skills", sa.JSON(), nullable=True),
            sa.Column("highlights", sa.JSON(), nullable=True),
        )

    if not _has_table(conn, "job_profiles_v2"):
        op.create_table(
            "job_profiles_v2",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("dimensions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )

    if not _has_table(conn, "assessment_configs"):
        op.create_table(
            "assessment_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("questionnaire_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("job_profile_id", sa.Integer(), sa.ForeignKey("job_profiles_v2.id"), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )

    if not _has_table(conn, "assessment_sessions"):
        op.create_table(
            "assessment_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates_v2.id"), nullable=False, index=True),
            sa.Column("config_id", sa.Integer(), sa.ForeignKey("assessment_configs.id"), nullable=False, index=True),
            sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'in_progress'")),
            sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(conn, "questionnaires_v2"):
        op.create_table(
            "questionnaires_v2",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("type", sa.String(), nullable=False, server_default=sa.text("'custom'")),
            sa.Column("dimensions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("questions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )

    if not _has_table(conn, "questionnaire_results"):
        op.create_table(
            "questionnaire_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("assessment_sessions.id"), nullable=False, index=True),
            sa.Column("questionnaire_id", sa.Integer(), sa.ForeignKey("questionnaires_v2.id"), nullable=False, index=True),
            sa.Column("dimension_scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("overall_score", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )

    if not _has_table(conn, "ai_profiles"):
        op.create_table(
            "ai_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates_v2.id"), nullable=False, index=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("highlights", sa.JSON(), nullable=True),
            sa.Column("risks", sa.JSON(), nullable=True),
            sa.Column("recommended_positions", sa.JSON(), nullable=True),
            sa.Column("avoid_positions", sa.JSON(), nullable=True),
            sa.Column("last_generated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        )


def downgrade() -> None:
    conn = op.get_bind()
    for table in [
        "ai_profiles",
        "questionnaire_results",
        "questionnaires_v2",
        "assessment_sessions",
        "assessment_configs",
        "job_profiles_v2",
        "resume_summaries",
        "candidates_v2",
    ]:
        if _has_table(conn, table):
            op.drop_table(table)
