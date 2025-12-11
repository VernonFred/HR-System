"""
Seed questionnaires and questions from the existing questionnaires.js.

Usage:
    poetry run python scripts/seed_questionnaires.py

Prerequisites:
    - Node.js available (used to convert questionnaires.js to JSON)
    - DATABASE_URL set (PostgreSQL preferred; falls back to local sqlite)
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

from app.db import ensure_tables, get_engine
from app.models import Question, Questionnaire

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = ROOT / "scripts" / "export_questionnaires.js"


def load_questionnaire_data() -> dict:
    """Invoke Node helper to read questionnaires.js and return parsed JSON."""
    if not EXPORT_SCRIPT.exists():
        raise FileNotFoundError(f"Export script missing: {EXPORT_SCRIPT}")

    result = subprocess.run(
        ["node", str(EXPORT_SCRIPT), "--compact"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Node export failed (code {result.returncode}): {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def upsert_questionnaire(session: Session, code: str, payload: dict) -> Questionnaire:
    """Delete existing questionnaire (if any) and insert fresh data."""
    existing = session.exec(select(Questionnaire).where(Questionnaire.code == code)).first()
    if existing:
        session.exec(delete(Question).where(Question.questionnaire_id == existing.id))
        session.delete(existing)
        session.commit()

    q = Questionnaire(
        code=code,
        name=payload.get("name") or payload.get("id") or code,
        full_name=payload.get("fullName"),
        description=payload.get("description"),
        dimensions=payload.get("dimensions"),
        dimension_names=payload.get("dimensionNames"),
        dimension_descriptions=payload.get("dimensionDescriptions"),
        answer_type=payload.get("answerType"),
        question_count=payload.get("questionCount") or len(payload.get("questions", [])),
        estimated_time=payload.get("estimatedTime"),
        extra={
            "types": payload.get("types"),
        },
    )
    session.add(q)
    session.commit()
    session.refresh(q)
    return q


def insert_questions(session: Session, questionnaire_id: int, questions: list[dict], answer_type: str | None):
    """Insert questions for a questionnaire."""
    objs: list[Question] = []
    for idx, item in enumerate(questions, start=1):
        objs.append(
            Question(
                questionnaire_id=questionnaire_id,
                order=idx,
                text=item.get("text"),
                dimension=item.get("dimension"),
                answer_type=answer_type or item.get("answerType"),
                payload={k: v for k, v in item.items() if k not in {"text", "dimension", "positive"}},
                positive=item.get("positive"),
            )
        )
    session.add_all(objs)
    session.commit()


def main() -> None:
    ensure_tables()
    engine = get_engine()
    data = load_questionnaire_data()

    with Session(engine) as session:
        for code, payload in data.items():
            q = upsert_questionnaire(session, code, payload)
            insert_questions(session, q.id, payload.get("questions", []), payload.get("answerType"))
            print(f"Seeded questionnaire: {code} ({len(payload.get('questions', []))} questions)")


if __name__ == "__main__":
    main()
