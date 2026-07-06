from datetime import datetime, timedelta
import asyncio

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.api.assessments import service
from app.custom_scoring import calculate_custom_questionnaire_score
from app.models_assessment import Assessment, Questionnaire, Submission


def _run(coro):
    return asyncio.run(coro)


def _build_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _score_question(question_id: str, text: str) -> dict:
    return {
        "id": question_id,
        "type": "radio",
        "text": text,
        "required": True,
        "options": [
            {"value": "opt1", "label": "1分"},
            {"value": "opt2", "label": "2分"},
            {"value": "opt3", "label": "3分"},
            {"value": "opt4", "label": "4分"},
            {"value": "opt5", "label": "5分"},
        ],
    }


def _direction_question() -> dict:
    return {
        "id": "q3",
        "type": "radio",
        "text": "后续课程方向",
        "required": True,
        "options": [
            {"value": "hr", "label": "人事类课程"},
            {"value": "admin", "label": "行政类课程"},
        ],
    }


def _editor_scoring_config() -> dict:
    return {
        "totalScore": 100,
        "passingScore": 60,
        "gradeConfig": [
            {"grade": "A", "label": "优秀", "minScore": 90, "maxScore": 100},
            {"grade": "B", "label": "良好", "minScore": 75, "maxScore": 89},
            {"grade": "C", "label": "中等", "minScore": 60, "maxScore": 74},
            {"grade": "D", "label": "待提升", "minScore": 0, "maxScore": 59},
        ],
    }


def test_custom_scoring_accepts_editor_config_and_raw_score_answers():
    questionnaire = {
        "custom_type": "scored",
        "scoring_config": _editor_scoring_config(),
        "questions_data": {
            "questions": [
                _score_question("q1", "课程内容"),
                _score_question("q2", "讲师表现"),
                _direction_question(),
            ]
        },
    }

    result = calculate_custom_questionnaire_score(
        questionnaire,
        [
            {"question_id": "q1", "answer": "5分"},
            {"question_id": "q2", "answer": "3分"},
            {"question_id": "q3", "answer": "人事类课程"},
        ],
    )

    assert result["total_score"] == 80
    assert result["max_score"] == 100
    assert result["score_percentage"] == 80
    assert result["grade"] == "B"
    assert result["scored_question_count"] == 2
    assert result["detailed_answers"][0]["scoring"]["raw_score"] == 5
    assert result["detailed_answers"][1]["scoring"]["raw_score"] == 3
    assert result["detailed_answers"][2]["scoring"] is None


def test_recalculate_questionnaire_scores_updates_completed_submissions_and_stats():
    with _build_session() as session:
        questionnaire = Questionnaire(
            name="课后培训问卷",
            type="CUSTOM",
            category="scored",
            custom_type="scored",
            purpose="survey",
            questions_count=3,
            estimated_minutes=5,
            questions_data={
                "questions": [
                    _score_question("q1", "课程内容"),
                    _score_question("q2", "讲师表现"),
                    _direction_question(),
                ]
            },
            scoring_config=_editor_scoring_config(),
            scoring_rules={},
            status="active",
        )
        session.add(questionnaire)
        session.commit()
        session.refresh(questionnaire)

        now = datetime.now()
        assessment = Assessment(
            name="课后培训问卷链接",
            code="ASSE-SCORED-001",
            questionnaire_id=questionnaire.id,
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=7),
            form_fields=[],
            page_texts={},
            routing_config={},
        )
        session.add(assessment)
        session.commit()
        session.refresh(assessment)

        completed_one = Submission(
            code="SUB-SCORED-001",
            assessment_id=assessment.id,
            questionnaire_id=questionnaire.id,
            candidate_name="匿名",
            candidate_phone="",
            answers={"q1": "5分", "q2": "3分", "q3": "人事类课程"},
            status="completed",
            started_at=now - timedelta(minutes=5),
            submitted_at=now,
        )
        completed_two = Submission(
            code="SUB-SCORED-002",
            assessment_id=assessment.id,
            questionnaire_id=questionnaire.id,
            candidate_name="匿名",
            candidate_phone="",
            answers={"q1": "2分", "q2": "4分", "q3": "行政类课程"},
            status="completed",
            started_at=now - timedelta(minutes=4),
            submitted_at=now,
        )
        in_progress = Submission(
            code="SUB-SCORED-003",
            assessment_id=assessment.id,
            questionnaire_id=questionnaire.id,
            candidate_name="匿名",
            candidate_phone="",
            answers={"q1": "5分"},
            status="in_progress",
            started_at=now,
        )
        session.add_all([completed_one, completed_two, in_progress])
        session.commit()

        result = _run(service.recalculate_questionnaire_scores(session, questionnaire.id))

        assert result["updated_count"] == 2
        assert result["skipped_count"] == 1
        assert result["average_score"] == 70

        refreshed = {
            sub.code: session.get(Submission, sub.id)
            for sub in [completed_one, completed_two, in_progress]
        }
        assert refreshed["SUB-SCORED-001"].total_score == 80
        assert refreshed["SUB-SCORED-001"].score_percentage == 80
        assert refreshed["SUB-SCORED-001"].grade == "B"
        assert refreshed["SUB-SCORED-002"].total_score == 60
        assert refreshed["SUB-SCORED-002"].grade == "C"
        assert refreshed["SUB-SCORED-003"].total_score is None

        stats = _run(service.get_question_answer_statistics(session, questionnaire.id))

        assert stats["average_score"] == 70
        assert stats["score_summary"] == {
            "scored_submission_count": 2,
            "max_score": 100,
            "average_score": 70,
            "highest_score": 80,
            "lowest_score": 60,
            "average_percentage": 70,
        }
        assert stats["questions"][0]["score_stats"] == {
            "scored_answer_count": 2,
            "average_raw_score": 3.5,
            "max_raw_score": 5,
            "average_score": 35,
            "max_score": 50,
            "average_percentage": 70,
        }
        assert stats["questions"][2]["score_stats"] is None
