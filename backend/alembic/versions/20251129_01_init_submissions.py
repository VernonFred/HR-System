"""init submissions

Revision ID: init_submissions
Revises: 
Create Date: 2025-11-29
"""

from alembic import op
import sqlalchemy as sa

revision = "init_submissions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_code", sa.String(), nullable=False),
        sa.Column("questionnaire_id", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_code"),
    )
    op.create_index(op.f("ix_submission_submission_code"), "submission", ["submission_code"], unique=False)
    op.create_index(op.f("ix_submission_questionnaire_id"), "submission", ["questionnaire_id"], unique=False)

    op.create_table(
        "submissionanswer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_submissionanswer_submission_id"), "submissionanswer", ["submission_id"], unique=False)
    op.create_index(op.f("ix_submissionanswer_question_id"), "submissionanswer", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_submissionanswer_question_id"), table_name="submissionanswer")
    op.drop_index(op.f("ix_submissionanswer_submission_id"), table_name="submissionanswer")
    op.drop_table("submissionanswer")
    op.drop_index(op.f("ix_submission_questionnaire_id"), table_name="submission")
    op.drop_index(op.f("ix_submission_submission_code"), table_name="submission")
    op.drop_table("submission")
