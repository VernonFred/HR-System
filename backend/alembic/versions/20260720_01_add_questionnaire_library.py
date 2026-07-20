"""Add questionnaire library categories and tags.

Revision ID: 20260720_01_questionnaire_lib
Revises: 20260615_01_add_anonymous_dedupe
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260720_01_questionnaire_lib"
down_revision = "20260615_01_add_anonymous_dedupe"
branch_labels = None
depends_on = None


CATEGORY_TABLE = "questionnaire_library_categories"
TAG_TABLE = "questionnaire_tags"
LINK_TABLE = "questionnaire_tag_links"

SEED_CATEGORIES = [
    ("培训学习", 1, False),
    ("会议活动", 2, False),
    ("员工体验", 3, False),
    ("组织文化", 4, False),
    ("对外招聘", 5, False),
    ("其他", 6, False),
    ("未分类", 7, True),
]


def _has_table(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def _has_column(conn, table_name: str, column_name: str) -> bool:
    if not _has_table(conn, table_name):
        return False
    return column_name in {column["name"] for column in inspect(conn).get_columns(table_name)}


def _has_index(conn, table_name: str, index_name: str) -> bool:
    if not _has_table(conn, table_name):
        return False
    return index_name in {index["name"] for index in inspect(conn).get_indexes(table_name)}


def _has_foreign_key(conn, table_name: str, constraint_name: str) -> bool:
    if not _has_table(conn, table_name):
        return False
    return constraint_name in {
        foreign_key["name"] for foreign_key in inspect(conn).get_foreign_keys(table_name)
    }


def _normalize_legacy_custom_questionnaires(conn) -> None:
    """Map historical survey/scored aliases back to the custom questionnaire model."""
    conn.execute(sa.text(
        """
        UPDATE questionnaires
        SET
            type = 'CUSTOM',
            category = CASE
                WHEN LOWER(COALESCE(custom_type, '')) = 'scored'
                  OR LOWER(COALESCE(category, '')) = 'scored'
                  OR UPPER(COALESCE(type, '')) = 'SCORED'
                THEN 'scored'
                ELSE 'survey'
            END,
            custom_type = CASE
                WHEN LOWER(COALESCE(custom_type, '')) = 'scored'
                  OR LOWER(COALESCE(category, '')) = 'scored'
                  OR UPPER(COALESCE(type, '')) = 'SCORED'
                THEN 'scored'
                ELSE 'non_scored'
            END,
            purpose = CASE
                WHEN purpose IS NOT NULL AND TRIM(purpose) <> '' THEN purpose
                WHEN LOWER(COALESCE(custom_type, '')) = 'scored'
                  OR LOWER(COALESCE(category, '')) = 'scored'
                  OR UPPER(COALESCE(type, '')) = 'SCORED'
                THEN 'assessment'
                ELSE 'survey'
            END
        WHERE UPPER(COALESCE(type, '')) NOT IN ('EPQ', 'DISC', 'MBTI')
          AND (
            UPPER(COALESCE(type, '')) IN (
                'CUSTOM', 'SURVEY', 'QUESTIONNAIRE', 'SCORED',
                'NON_SCORED', 'CUSTOM_SURVEY'
            )
            OR LOWER(COALESCE(category, '')) IN ('survey', 'scored')
            OR LOWER(COALESCE(custom_type, '')) IN ('scored', 'non_scored')
          )
        """
    ))


def _mark_professional_questionnaires(conn) -> None:
    """Only technical professional questionnaires belong to the professional area."""
    conn.execute(sa.text(
        """
        UPDATE questionnaires
        SET category = 'professional', custom_type = NULL, purpose = NULL
        WHERE UPPER(COALESCE(type, '')) IN ('EPQ', 'DISC', 'MBTI')
        """
    ))


def upgrade() -> None:
    conn = op.get_bind()

    # Older Alembic revisions predate fields that were historically created by
    # SQLModel.create_all. Add them here so a database built only from migrations
    # matches the current Questionnaire ORM model.
    compatibility_columns = {
        "category": sa.Column(
            "category", sa.String(length=20), nullable=False, server_default="survey"
        ),
        "custom_type": sa.Column("custom_type", sa.String(length=20), nullable=True),
        "scoring_config": sa.Column(
            "scoring_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        "purpose": sa.Column("purpose", sa.String(length=20), nullable=True),
    }
    missing_compatibility_columns = [
        column
        for name, column in compatibility_columns.items()
        if not _has_column(conn, "questionnaires", name)
    ]
    if missing_compatibility_columns:
        with op.batch_alter_table("questionnaires", schema=None) as batch_op:
            for column in missing_compatibility_columns:
                batch_op.add_column(column)

    _normalize_legacy_custom_questionnaires(conn)
    _mark_professional_questionnaires(conn)

    if not _has_table(conn, CATEGORY_TABLE):
        op.create_table(
            CATEGORY_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("normalized_name", sa.String(length=255), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("normalized_name", name="uq_questionnaire_library_categories_normalized_name"),
        )
        op.create_index(
            "ix_questionnaire_library_categories_normalized_name",
            CATEGORY_TABLE,
            ["normalized_name"],
        )

    if not _has_table(conn, TAG_TABLE):
        op.create_table(
            TAG_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("normalized_name", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("normalized_name", name="uq_questionnaire_tags_normalized_name"),
        )
        op.create_index("ix_questionnaire_tags_normalized_name", TAG_TABLE, ["normalized_name"])

    if not _has_column(conn, "questionnaires", "library_category_id"):
        with op.batch_alter_table("questionnaires", schema=None) as batch_op:
            batch_op.add_column(sa.Column(
                "library_category_id",
                sa.Integer(),
                nullable=True,
            ))
            batch_op.create_foreign_key(
                "fk_questionnaires_library_category_id",
                CATEGORY_TABLE,
                ["library_category_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index(
                "ix_questionnaires_library_category_id",
                ["library_category_id"],
            )

    if not _has_table(conn, LINK_TABLE):
        op.create_table(
            LINK_TABLE,
            sa.Column(
                "questionnaire_id",
                sa.Integer(),
                sa.ForeignKey("questionnaires.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "tag_id",
                sa.Integer(),
                sa.ForeignKey(f"{TAG_TABLE}.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )
    if not _has_index(conn, LINK_TABLE, "ix_questionnaire_tag_links_tag_id"):
        op.create_index(
            "ix_questionnaire_tag_links_tag_id",
            LINK_TABLE,
            ["tag_id"],
        )

    category_rows = conn.execute(sa.text(
        f"SELECT normalized_name FROM {CATEGORY_TABLE}"
    )).scalars().all()
    existing_names = set(category_rows)
    category_table = sa.table(
        CATEGORY_TABLE,
        sa.column("name", sa.String()),
        sa.column("normalized_name", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_system", sa.Boolean()),
    )
    missing_rows = [
        {
            "name": name,
            "normalized_name": name,
            "sort_order": sort_order,
            "is_active": True,
            "is_system": is_system,
        }
        for name, sort_order, is_system in SEED_CATEGORIES
        if name not in existing_names
    ]
    if missing_rows:
        op.bulk_insert(category_table, missing_rows)

    conn.execute(sa.text(
        f"""
        UPDATE questionnaires
        SET library_category_id = (
            SELECT id FROM {CATEGORY_TABLE} WHERE normalized_name = :uncategorized
        )
        WHERE UPPER(type) = 'CUSTOM'
          AND category IN ('scored', 'survey')
          AND library_category_id IS NULL
        """
    ), {"uncategorized": "未分类"})
    conn.execute(sa.text(
        """
        UPDATE questionnaires
        SET custom_type = CASE
            WHEN category = 'scored' THEN 'scored'
            WHEN category = 'survey' THEN 'non_scored'
            ELSE custom_type
        END
        WHERE UPPER(type) = 'CUSTOM'
          AND category IN ('scored', 'survey')
          AND custom_type IS NULL
        """
    ))


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, LINK_TABLE):
        op.drop_table(LINK_TABLE)

    if _has_column(conn, "questionnaires", "library_category_id"):
        has_foreign_key = _has_foreign_key(
            conn, "questionnaires", "fk_questionnaires_library_category_id"
        )
        has_index = _has_index(
            conn, "questionnaires", "ix_questionnaires_library_category_id"
        )
        with op.batch_alter_table("questionnaires", schema=None) as batch_op:
            if has_foreign_key:
                batch_op.drop_constraint(
                    "fk_questionnaires_library_category_id", type_="foreignkey"
                )
            if has_index:
                batch_op.drop_index("ix_questionnaires_library_category_id")
            batch_op.drop_column("library_category_id")

    if _has_table(conn, TAG_TABLE):
        op.drop_table(TAG_TABLE)
    if _has_table(conn, CATEGORY_TABLE):
        op.drop_table(CATEGORY_TABLE)
