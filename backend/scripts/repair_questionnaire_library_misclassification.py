"""Repair legacy custom questionnaires misclassified as professional.

Usage:
    python scripts/repair_questionnaire_library_misclassification.py --db hr.db
    python scripts/repair_questionnaire_library_misclassification.py --db hr.db --apply
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROFESSIONAL_TYPES = {"EPQ", "DISC", "MBTI"}
CUSTOM_TYPE_ALIASES = {
    "CUSTOM",
    "SURVEY",
    "QUESTIONNAIRE",
    "SCORED",
    "NON_SCORED",
    "CUSTOM_SURVEY",
}
SCORED_ALIASES = {"SCORED"}


@dataclass(frozen=True)
class RepairTarget:
    id: int
    name: str
    current_type: str | None
    current_category: str | None
    current_custom_type: str | None
    current_purpose: str | None
    current_library_category_id: int | None
    target_category: str
    target_custom_type: str
    target_purpose: str
    target_library_category_id: int | None


def _normalize(value: str | None) -> str:
    return (value or "").strip().upper()


def _is_scored(row: sqlite3.Row) -> bool:
    return (
        _normalize(row["type"]) in SCORED_ALIASES
        or (row["category"] or "").strip().lower() == "scored"
        or (row["custom_type"] or "").strip().lower() == "scored"
    )


def _resolve_uncategorized_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        """
        SELECT id
        FROM questionnaire_library_categories
        WHERE normalized_name = ? OR name = ?
        ORDER BY is_system DESC, sort_order DESC, id ASC
        LIMIT 1
        """,
        ("未分类", "未分类"),
    ).fetchone()
    return int(row["id"]) if row else None


def find_targets(
    conn: sqlite3.Connection,
    *,
    questionnaire_id: int | None = None,
) -> list[RepairTarget]:
    uncategorized_id = _resolve_uncategorized_id(conn)
    params: list[object] = []
    id_clause = ""
    if questionnaire_id is not None:
        id_clause = " AND id = ?"
        params.append(questionnaire_id)

    rows = conn.execute(
        f"""
        SELECT
            id, name, type, category, custom_type, purpose, library_category_id
        FROM questionnaires
        WHERE UPPER(COALESCE(type, '')) NOT IN ('EPQ', 'DISC', 'MBTI')
          AND (
            UPPER(COALESCE(type, '')) IN (
                'CUSTOM', 'SURVEY', 'QUESTIONNAIRE', 'SCORED',
                'NON_SCORED', 'CUSTOM_SURVEY'
            )
            OR LOWER(COALESCE(category, '')) IN ('survey', 'scored')
            OR LOWER(COALESCE(custom_type, '')) IN ('scored', 'non_scored')
          )
          {id_clause}
        ORDER BY id ASC
        """,
        params,
    ).fetchall()

    targets = []
    for row in rows:
        scored = _is_scored(row)
        target_category = "scored" if scored else "survey"
        target_custom_type = "scored" if scored else "non_scored"
        target_purpose = row["purpose"] or ("assessment" if scored else "survey")
        target_library_category_id = row["library_category_id"] or uncategorized_id
        if (
            _normalize(row["type"]) == "CUSTOM"
            and row["category"] == target_category
            and row["custom_type"] == target_custom_type
            and row["purpose"] == target_purpose
            and row["library_category_id"] == target_library_category_id
        ):
            continue
        targets.append(RepairTarget(
            id=int(row["id"]),
            name=row["name"],
            current_type=row["type"],
            current_category=row["category"],
            current_custom_type=row["custom_type"],
            current_purpose=row["purpose"],
            current_library_category_id=row["library_category_id"],
            target_category=target_category,
            target_custom_type=target_custom_type,
            target_purpose=target_purpose,
            target_library_category_id=target_library_category_id,
        ))
    return targets


def apply_targets(conn: sqlite3.Connection, targets: Iterable[RepairTarget]) -> int:
    count = 0
    for target in targets:
        cursor = conn.execute(
            """
            UPDATE questionnaires
            SET
                type = 'CUSTOM',
                category = ?,
                custom_type = ?,
                purpose = ?,
                library_category_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND UPPER(COALESCE(type, '')) NOT IN ('EPQ', 'DISC', 'MBTI')
            """,
            (
                target.target_category,
                target.target_custom_type,
                target.target_purpose,
                target.target_library_category_id,
                target.id,
            ),
        )
        count += cursor.rowcount
    conn.commit()
    return count


def print_targets(targets: Iterable[RepairTarget]) -> None:
    for target in targets:
        print(
            f"#{target.id} {target.name}: "
            f"type={target.current_type!r}, category={target.current_category!r}, "
            f"custom_type={target.current_custom_type!r}, purpose={target.current_purpose!r}, "
            f"library_category_id={target.current_library_category_id!r} -> "
            f"type='CUSTOM', category={target.target_category!r}, "
            f"custom_type={target.target_custom_type!r}, purpose={target.target_purpose!r}, "
            f"library_category_id={target.target_library_category_id!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="Path to SQLite database.")
    parser.add_argument("--questionnaire-id", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        targets = find_targets(conn, questionnaire_id=args.questionnaire_id)
        if not targets:
            print("No misclassified questionnaire candidates found.")
            return 0
        print_targets(targets)
        if not args.apply:
            print(f"Dry run only. Add --apply to update {len(targets)} rows.")
            return 0
        updated = apply_targets(conn, targets)
        print(f"Updated {updated} questionnaire rows.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
