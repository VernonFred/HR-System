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


def test_scored_questionnaire_without_scores_does_not_default_to_zero_or_d():
    with _build_session() as session:
        questionnaire = Questionnaire(
            name="评分型课后问卷",
            type="custom",
            category="scored",
            custom_type="scored",
            purpose="survey",
            questions_count=1,
            estimated_minutes=3,
            questions_data={
                "questions": [
                    {
                        "id": "q1",
                        "text": "课程内容满意度",
                        "type": "radio",
                        "options": [
                            {"value": "1", "label": "1分"},
                            {"value": "2", "label": "2分"},
                            {"value": "3", "label": "3分"},
                            {"value": "4", "label": "4分"},
                            {"value": "5", "label": "5分"},
                        ],
                    }
                ]
            },
            scoring_rules={},
            scoring_config={"enabled": True, "totalScore": 100},
            status="active",
        )
        session.add(questionnaire)
        session.commit()
        session.refresh(questionnaire)

        now = datetime.now()
        assessment = Assessment(
            name="评分型课后问卷链接",
            code="ASSE-STATS-002",
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
                code="SUB-STATS-003",
                assessment_id=assessment.id,
                questionnaire_id=questionnaire.id,
                candidate_name="匿名",
                candidate_phone="",
                answers={"q1": "5分"},
                status="completed",
                submitted_at=now,
            ),
            Submission(
                code="SUB-STATS-004",
                assessment_id=assessment.id,
                questionnaire_id=questionnaire.id,
                candidate_name="匿名",
                candidate_phone="",
                answers={"q1": "4分"},
                status="completed",
                submitted_at=now,
            ),
        ]
        session.add_all(submissions)
        session.commit()

        stats = _run(service.get_question_answer_statistics(session, questionnaire.id))

        assert stats["total_submissions"] == 2
        assert stats["average_score"] is None
        assert stats["score_summary"] is None
        assert stats["scoring_enabled"] is True
        assert stats["score_status"] == "pending_recalculation"
        assert stats["scored_submission_count"] == 0
        assert stats["unscored_submission_count"] == 2
        assert stats["grade_distribution"] == {"A": 0, "B": 0, "C": 0, "D": 0}
        assert stats["grade_percentages"] == {"A": 0, "B": 0, "C": 0, "D": 0}
