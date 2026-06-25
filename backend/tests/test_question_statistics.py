from datetime import datetime, timedelta
import asyncio

from sqlmodel import SQLModel, Session, create_engine

from app.api.assessments import service
from app.models_assessment import Assessment, Questionnaire, Submission


def _run(coro):
    return asyncio.run(coro)


def _build_session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_multiple_choice_total_answers_counts_respondents_not_selected_options():
    with _build_session() as session:
        questionnaire = Questionnaire(
            name="产品培训问卷",
            type="custom",
            category="survey",
            custom_type="non_scored",
            questions_count=1,
            estimated_minutes=3,
            questions_data={
                "questions": [
                    {
                        "id": "q2",
                        "text": "哪些产品必须培训？",
                        "type": "checkbox",
                        "options": [
                            {"value": "A", "text": "产品A"},
                            {"value": "B", "text": "产品B"},
                        ],
                    }
                ]
            },
            scoring_rules={},
            scoring_config={},
            status="active",
        )
        session.add(questionnaire)
        session.commit()
        session.refresh(questionnaire)

        now = datetime.now()
        assessment = Assessment(
            name="产品培训问卷链接",
            code="ASSE-STATS-001",
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

        submissions = [
            Submission(
                code="SUB-STATS-001",
                assessment_id=assessment.id,
                questionnaire_id=questionnaire.id,
                candidate_name="匿名",
                candidate_phone="",
                answers={"q2": ["A", "B"]},
                status="completed",
                submitted_at=now,
            ),
            Submission(
                code="SUB-STATS-002",
                assessment_id=assessment.id,
                questionnaire_id=questionnaire.id,
                candidate_name="匿名",
                candidate_phone="",
                answers={"q2": ["A"]},
                status="completed",
                submitted_at=now,
            ),
        ]
        session.add_all(submissions)
        session.commit()

        stats = _run(service.get_question_answer_statistics(session, questionnaire.id))
        question = stats["questions"][0]

        assert stats["total_submissions"] == 2
        assert question["total_answers"] == 2
        assert question["total_selections"] == 3
        assert question["options"][0]["count"] == 2
        assert question["options"][0]["percentage"] == 100
        assert question["options"][1]["count"] == 1
        assert question["options"][1]["percentage"] == 50
