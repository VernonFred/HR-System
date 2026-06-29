from datetime import datetime, timedelta
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.api.assessments import service
from app.api.assessments.router import router as assessments_router
from app.db import get_session
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


def _create_questionnaire_with_assessment(session: Session, questionnaire_name: str = "满意度问卷"):
    questionnaire = Questionnaire(
        name=questionnaire_name,
        type="custom",
        category="survey",
        custom_type="non_scored",
        questions_count=3,
        estimated_minutes=5,
        questions_data={
            "questions": [
                {
                    "id": "q1",
                    "text": "你最喜欢的方案是？",
                    "type": "radio",
                    "options": [
                        {"value": "plan-a", "label": "方案A"},
                        {"text": "方案B", "value": "plan-b"},
                        {"label": "方案C"},
                    ],
                },
                {
                    "id": "q2",
                    "text": "你使用过哪些渠道？",
                    "type": "checkbox",
                    "options": [
                        {"value": "wechat", "text": "微信"},
                        {"value": "email", "label": "邮件"},
                    ],
                },
                {
                    "id": "q3",
                    "text": "其他建议",
                    "type": "text",
                },
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
        name=f"{questionnaire_name}链接",
        code=f"ASSE-{questionnaire.id}",
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
    return questionnaire, assessment


def test_answer_export_service_returns_question_mapping_and_raw_answers():
    with _build_session() as session:
        questionnaire, assessment = _create_questionnaire_with_assessment(session)
        other_questionnaire, other_assessment = _create_questionnaire_with_assessment(session, "其他问卷")
        now = datetime.now()

        session.add_all(
            [
                Submission(
                    code="SUB-EXPORT-001",
                    assessment_id=assessment.id,
                    questionnaire_id=questionnaire.id,
                    candidate_name="",
                    candidate_phone="",
                    candidate_email=None,
                    gender=None,
                    target_position="后端工程师",
                    answers={
                        "q1": "plan-b",
                        "q2": ["wechat", "email"],
                        "q3": "希望支持批量导出",
                    },
                    status="completed",
                    started_at=now - timedelta(minutes=8),
                    submitted_at=now - timedelta(minutes=3),
                ),
                Submission(
                    code="SUB-EXPORT-002",
                    assessment_id=assessment.id,
                    questionnaire_id=questionnaire.id,
                    candidate_name="张三",
                    candidate_phone="13800000000",
                    answers={"q1": "plan-a"},
                    status="in_progress",
                    started_at=now - timedelta(minutes=2),
                    submitted_at=None,
                ),
                Submission(
                    code="SUB-EXPORT-003",
                    assessment_id=other_assessment.id,
                    questionnaire_id=other_questionnaire.id,
                    candidate_name="李四",
                    candidate_phone="13900000000",
                    answers={"q1": "plan-a"},
                    status="completed",
                    started_at=now - timedelta(minutes=6),
                    submitted_at=now - timedelta(minutes=1),
                ),
            ]
        )
        session.commit()

        result = _run(service.get_questionnaire_answer_export(session, questionnaire.id))

        assert result is not None
        assert result["questionnaire_id"] == questionnaire.id
        assert result["questionnaire_name"] == "满意度问卷"
        assert result["questions"] == [
            {
                "id": "q1",
                "index": 1,
                "text": "你最喜欢的方案是？",
                "type": "radio",
                "options": [
                    {"index": 0, "value": "plan-a", "label": "方案A"},
                    {"index": 1, "value": "plan-b", "label": "方案B"},
                    {"index": 2, "value": "方案C", "label": "方案C"},
                ],
            },
            {
                "id": "q2",
                "index": 2,
                "text": "你使用过哪些渠道？",
                "type": "checkbox",
                "options": [
                    {"index": 0, "value": "wechat", "label": "微信"},
                    {"index": 1, "value": "email", "label": "邮件"},
                ],
            },
            {
                "id": "q3",
                "index": 3,
                "text": "其他建议",
                "type": "text",
                "options": [],
            },
        ]
        assert len(result["submissions"]) == 1
        submission = result["submissions"][0]
        assert submission["code"] == "SUB-EXPORT-001"
        assert submission["candidate_name"] == ""
        assert submission["candidate_phone"] == ""
        assert submission["target_position"] == "后端工程师"
        assert submission["answers"]["q1"] == "plan-b"
        assert submission["answers"]["q2"] == ["wechat", "email"]
        assert submission["answers"]["q3"] == "希望支持批量导出"


def test_answer_export_service_falls_back_to_answered_submissions_when_no_completed_status():
    with _build_session() as session:
        questionnaire, assessment = _create_questionnaire_with_assessment(session, "回退问卷")
        now = datetime.now()

        session.add_all(
            [
                Submission(
                    code="SUB-FALLBACK-001",
                    assessment_id=assessment.id,
                    questionnaire_id=questionnaire.id,
                    candidate_name="匿名",
                    candidate_phone="",
                    answers={"q1": "plan-a", "q2": ["wechat"]},
                    status="draft",
                    started_at=now - timedelta(minutes=5),
                    submitted_at=None,
                ),
                Submission(
                    code="SUB-FALLBACK-002",
                    assessment_id=assessment.id,
                    questionnaire_id=questionnaire.id,
                    candidate_name="王五",
                    candidate_phone="13700000000",
                    answers={},
                    status="draft",
                    started_at=now - timedelta(minutes=4),
                    submitted_at=None,
                ),
            ]
        )
        session.commit()

        result = _run(service.get_questionnaire_answer_export(session, questionnaire.id))

        assert result is not None
        assert [item["code"] for item in result["submissions"]] == ["SUB-FALLBACK-001"]
        assert result["submissions"][0]["answers"]["q2"] == ["wechat"]


def test_answer_export_route_returns_404_when_questionnaire_missing():
    app = FastAPI()
    app.include_router(assessments_router)

    with _build_session() as session:
        def override_get_session():
            yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)

        response = client.get("/api/assessments/questionnaires/9999/answer-export")

        assert response.status_code == 404
        assert response.json() == {"detail": "问卷不存在"}
