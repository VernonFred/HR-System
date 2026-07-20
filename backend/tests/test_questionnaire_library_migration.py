from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from scripts.repair_questionnaire_library_misclassification import (
    apply_targets,
    find_targets,
)


PREVIOUS_REVISION = "20260615_01_add_anonymous_dedupe"
LIBRARY_REVISION = "20260720_01_questionnaire_lib"
SEED_NAMES = [
    "培训学习",
    "会议活动",
    "员工体验",
    "组织文化",
    "对外招聘",
    "其他",
    "未分类",
]


def test_questionnaire_library_revision_fits_default_alembic_version_column():
    assert len(LIBRARY_REVISION) <= 32


def _alembic_config(database_url: str) -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_questionnaire_library_migration_supports_pristine_alembic_database(
    tmp_path, monkeypatch
):
    database_url = f"sqlite:///{tmp_path / 'questionnaire-library.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config(database_url)

    command.upgrade(config, PREVIOUS_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        previous_columns = {
            column["name"] for column in inspect(connection).get_columns("questionnaires")
        }
        assert "category" not in previous_columns
    engine.dispose()

    command.upgrade(config, LIBRARY_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        questionnaire_columns = {
            column["name"] for column in inspect(connection).get_columns("questionnaires")
        }
        assert {
            "category",
            "custom_type",
            "scoring_config",
            "purpose",
            "library_category_id",
        }.issubset(questionnaire_columns)
        assert "ix_questionnaire_tag_links_tag_id" in {
            index["name"] for index in inspect(connection).get_indexes("questionnaire_tag_links")
        }
        seeds = connection.execute(text(
            "SELECT name, is_system FROM questionnaire_library_categories ORDER BY sort_order"
        )).all()
        assert [name for name, _ in seeds] == SEED_NAMES
        assert seeds[-1] == ("未分类", 1)
    engine.dispose()

    command.downgrade(config, PREVIOUS_REVISION)
    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "questionnaire_library_categories" not in inspector.get_table_names()
    assert "questionnaire_tags" not in inspector.get_table_names()
    assert "questionnaire_tag_links" not in inspector.get_table_names()
    assert "library_category_id" not in {
        column["name"] for column in inspector.get_columns("questionnaires")
    }
    engine.dispose()


def test_questionnaire_library_migration_backfills_deployed_legacy_data(
    tmp_path, monkeypatch
):
    database_url = f"sqlite:///{tmp_path / 'questionnaire-library-backfill.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config(database_url)

    command.upgrade(config, PREVIOUS_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        # Production databases historically received these ORM fields through
        # SQLModel.create_all even though the old Alembic chain omitted them.
        connection.execute(text(
            "ALTER TABLE questionnaires ADD COLUMN category VARCHAR(20) "
            "NOT NULL DEFAULT 'survey'"
        ))
        connection.execute(text(
            "ALTER TABLE questionnaires ADD COLUMN custom_type VARCHAR(20)"
        ))
        connection.execute(text(
            """
            INSERT INTO questionnaires (
                name, type, questions_count, estimated_minutes,
                questions_data, scoring_rules, status, created_at, updated_at, category
            ) VALUES
                ('历史评分问卷', 'custom', 0, 15, '{}', '{}', 'active',
                 '2026-07-20 00:00:00', '2026-07-20 00:00:00', 'scored'),
                ('历史调查问卷', 'custom', 0, 15, '{}', '{}', 'active',
                 '2026-07-20 00:00:00', '2026-07-20 00:00:00', 'survey'),
                ('历史别名调查问卷', 'survey', 0, 15, '{}', '{}', 'active',
                 '2026-07-20 00:00:00', '2026-07-20 00:00:00', 'survey'),
                ('迁移误判调查问卷', 'survey', 0, 15, '{}', '{}', 'active',
                 '2026-07-20 00:00:00', '2026-07-20 00:00:00', 'professional'),
                ('历史专业测评', 'MBTI', 0, 15, '{}', '{}', 'active',
                 '2026-07-20 00:00:00', '2026-07-20 00:00:00', 'survey')
            """
        ))
    engine.dispose()

    command.upgrade(config, LIBRARY_REVISION)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        backfill = connection.execute(text(
            """
            SELECT q.name, q.type, c.name, q.custom_type, q.category, q.purpose
            FROM questionnaires q
            LEFT JOIN questionnaire_library_categories c ON c.id = q.library_category_id
            ORDER BY q.id
            """
        )).all()
        assert backfill == [
            ("历史评分问卷", "CUSTOM", "未分类", "scored", "scored", "assessment"),
            ("历史调查问卷", "CUSTOM", "未分类", "non_scored", "survey", "survey"),
            ("历史别名调查问卷", "CUSTOM", "未分类", "non_scored", "survey", "survey"),
            ("迁移误判调查问卷", "CUSTOM", "未分类", "non_scored", "survey", "survey"),
            ("历史专业测评", "MBTI", None, None, "professional", None),
        ]
    engine.dispose()


def test_questionnaire_library_repair_script_restores_legacy_survey_alias():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE questionnaire_library_categories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            normalized_name TEXT,
            sort_order INTEGER,
            is_system INTEGER
        );
        CREATE TABLE questionnaires (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            category TEXT,
            custom_type TEXT,
            purpose TEXT,
            library_category_id INTEGER,
            updated_at TEXT
        );
        INSERT INTO questionnaire_library_categories
            (id, name, normalized_name, sort_order, is_system)
        VALUES (7, '未分类', '未分类', 7, 1);
        INSERT INTO questionnaires
            (id, name, type, category, custom_type, purpose, library_category_id)
        VALUES
            (23, '暑假售前类课程选课', 'survey', 'professional', NULL, NULL, NULL),
            (24, 'MBTI专业测评', 'MBTI', 'professional', NULL, NULL, NULL);
        """
    )

    targets = find_targets(conn, questionnaire_id=23)

    assert len(targets) == 1
    target = targets[0]
    assert target.target_category == "survey"
    assert target.target_custom_type == "non_scored"
    assert target.target_purpose == "survey"
    assert target.target_library_category_id == 7

    assert apply_targets(conn, targets) == 1
    fixed = conn.execute(
        """
        SELECT type, category, custom_type, purpose, library_category_id
        FROM questionnaires
        WHERE id = 23
        """
    ).fetchone()
    assert tuple(fixed) == ("CUSTOM", "survey", "non_scored", "survey", 7)
    assert find_targets(conn, questionnaire_id=24) == []
    conn.close()
