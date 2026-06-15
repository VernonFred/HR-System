from datetime import datetime, timedelta
import asyncio

from sqlmodel import SQLModel, Session, create_engine

from app.api.assessments import service
from app.models_assessment import Assessment, Questionnaire


def _run(coro):
    return asyncio.run(coro)


def _build_session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _create_questionnaire(session: Session, qid: int, name: str, status: str = "active") -> Questionnaire:
    q = Questionnaire(
        id=qid,
        name=name,
        type="custom",
        category="survey",
        questions_count=2,
        estimated_minutes=5,
        questions_data={"questions": [{"id": "1", "text": f"{name}-Q1"}]},
        scoring_rules={},
        status=status,
    )
    session.add(q)
    session.commit()
    session.refresh(q)
    return q


def _create_assessment(
    session: Session,
    questionnaire_id: int,
    routing_config: dict | None = None,
    allow_repeat: bool = True,
) -> Assessment:
    now = datetime.now()
    assessment = Assessment(
        name="入口测评",
        code=f"ASSE-TEST-{questionnaire_id}-{int(now.timestamp())}",
        questionnaire_id=questionnaire_id,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=7),
        form_fields=[],
        page_texts={},
        link_type="temporary",
        allow_repeat=allow_repeat,
        repeat_check_by="phone",
        repeat_interval_hours=0,
        max_submissions=0,
        routing_config=routing_config or {},
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def test_resolve_questionnaire_id_with_empty_routing_config_returns_default():
    with _build_session() as session:
        q_default = _create_questionnaire(session, 1, "问卷A")
        _create_questionnaire(session, 2, "问卷B")
        assessment = _create_assessment(session, questionnaire_id=q_default.id)

        resolved = _run(
            service.resolve_questionnaire_id(
                session,
                assessment,
                {"custom_data": {"department": "技术部"}},
            )
        )

        assert resolved == q_default.id


def test_resolve_questionnaire_id_routes_to_target_questionnaire():
    with _build_session() as session:
        q_default = _create_questionnaire(session, 1, "问卷A")
        q_target = _create_questionnaire(session, 2, "问卷B")
        assessment = _create_assessment(
            session,
            questionnaire_id=q_default.id,
            routing_config={
                "enabled": True,
                "department_field": "department",
                "fallback_to_default": True,
                "mappings": [{"department_value": "技术部", "questionnaire_id": q_target.id}],
            },
        )

        resolved = _run(
            service.resolve_questionnaire_id(
                session,
                assessment,
                {"custom_data": {"department": "技术部"}},
            )
        )

        assert resolved == q_target.id


def test_resolve_questionnaire_id_fallbacks_when_department_not_mapped():
    with _build_session() as session:
        q_default = _create_questionnaire(session, 1, "问卷A")
        q_target = _create_questionnaire(session, 2, "问卷B")
        assessment = _create_assessment(
            session,
            questionnaire_id=q_default.id,
            routing_config={
                "enabled": True,
                "department_field": "department",
                "fallback_to_default": True,
                "mappings": [{"department_value": "技术部", "questionnaire_id": q_target.id}],
            },
        )

        resolved = _run(
            service.resolve_questionnaire_id(
                session,
                assessment,
                {"custom_data": {"department": "销售部"}},
            )
        )

        assert resolved == q_default.id


def test_resolve_questionnaire_id_fallbacks_when_target_questionnaire_inactive():
    with _build_session() as session:
        q_default = _create_questionnaire(session, 1, "问卷A")
        q_inactive = _create_questionnaire(session, 3, "问卷C", status="inactive")
        assessment = _create_assessment(
            session,
            questionnaire_id=q_default.id,
            routing_config={
                "enabled": True,
                "department_field": "department",
                "fallback_to_default": True,
                "mappings": [{"department_value": "销售部", "questionnaire_id": q_inactive.id}],
            },
        )

        resolved = _run(
            service.resolve_questionnaire_id(
                session,
                assessment,
                {"custom_data": {"department": "销售部"}},
            )
        )

        assert resolved == q_default.id


def test_repeat_submit_rule_keeps_effect_with_routing():
    with _build_session() as session:
        q_default = _create_questionnaire(session, 1, "问卷A")
        q_target = _create_questionnaire(session, 2, "问卷B")
        assessment = _create_assessment(
            session,
            questionnaire_id=q_default.id,
            allow_repeat=False,
            routing_config={
                "enabled": True,
                "department_field": "department",
                "fallback_to_default": True,
                "mappings": [{"department_value": "技术部", "questionnaire_id": q_target.id}],
            },
        )

        first_submission = _run(
            service.create_submission(
                session,
                assessment.id,
                {
                    "candidate_name": "张三",
                    "candidate_phone": "13800001111",
                    "custom_data": {"department": "技术部"},
                },
                questionnaire_id_override=q_target.id,
            )
        )
        _run(service.submit_answers(session, first_submission.code, {"1": {"value": "已完成"}}))

        check_result = _run(service.check_can_submit(session, assessment.id, "13800001111", "张三"))
        assert check_result["can_submit"] is False
