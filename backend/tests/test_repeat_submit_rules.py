from datetime import datetime, timedelta
import asyncio

import pytest
from sqlmodel import SQLModel, Session, create_engine

from app.api.assessments import service
from app.models_assessment import Assessment, Questionnaire


def _run(coro):
    return asyncio.run(coro)


def _build_session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _create_questionnaire(session: Session) -> Questionnaire:
    questionnaire = Questionnaire(
        name="匿名调查问卷",
        type="custom",
        category="survey",
        custom_type="non_scored",
        questions_count=1,
        estimated_minutes=3,
        questions_data={
            "questions": [
                {
                    "id": "q1",
                    "title": "是否参加培训？",
                    "text": "是否参加培训？",
                    "type": "single_choice",
                    "options": ["是", "否"],
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
    return questionnaire


def _create_assessment(
    session: Session,
    questionnaire_id: int,
    allow_repeat: bool = False,
    repeat_interval_hours: int = 24,
    max_submissions: int = 0,
) -> Assessment:
    now = datetime.now()
    assessment = Assessment(
        name="匿名调查链接",
        code=f"ASSE-REPEAT-{int(now.timestamp())}",
        questionnaire_id=questionnaire_id,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=7),
        form_fields=[],
        page_texts={},
        link_type="temporary",
        allow_repeat=allow_repeat,
        repeat_check_by="phone",
        repeat_interval_hours=repeat_interval_hours,
        max_submissions=max_submissions,
        routing_config={},
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def test_in_progress_submission_does_not_block_repeat_check():
    with _build_session() as session:
        questionnaire = _create_questionnaire(session)
        assessment = _create_assessment(session, questionnaire.id, allow_repeat=False)

        _run(
            service.create_submission(
                session,
                assessment.id,
                {
                    "candidate_name": "",
                    "candidate_phone": "",
                    "custom_data": {},
                },
                questionnaire_id_override=questionnaire.id,
            )
        )

        result = _run(service.check_can_submit(session, assessment.id, "", ""))

        assert result["can_submit"] is True
        assert result["submission_number"] == 1
        assert result["previous_submissions"] == []


def test_final_submit_rechecks_completed_repeat_rule():
    with _build_session() as session:
        questionnaire = _create_questionnaire(session)
        assessment = _create_assessment(session, questionnaire.id, allow_repeat=False)

        first = _run(
            service.create_submission(
                session,
                assessment.id,
                {
                    "candidate_name": "",
                    "candidate_phone": "",
                    "custom_data": {},
                },
                questionnaire_id_override=questionnaire.id,
            )
        )
        _run(service.submit_answers(session, first.code, {"q1": {"value": "是"}}))

        second = _run(
            service.create_submission(
                session,
                assessment.id,
                {
                    "candidate_name": "",
                    "candidate_phone": "",
                    "custom_data": {},
                },
                questionnaire_id_override=questionnaire.id,
            )
        )

        with pytest.raises(ValueError, match="不允许重复提交"):
            _run(service.submit_answers(session, second.code, {"q1": {"value": "否"}}))
