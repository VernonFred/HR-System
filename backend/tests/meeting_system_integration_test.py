from datetime import datetime, timedelta
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.api.assessments.public_router import public_router
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


def _build_client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(public_router)

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def _create_questionnaire(session: Session) -> Questionnaire:
    questionnaire = Questionnaire(
        name="会议满意度问卷",
        type="custom",
        category="survey",
        custom_type="non_scored",
        questions_count=1,
        estimated_minutes=2,
        questions_data={
            "questions": [
                {
                    "id": "q1",
                    "text": "本次会议体验如何？",
                    "type": "radio",
                    "options": [{"value": "good", "label": "好"}],
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
    *,
    code: str = "ASSE-MEETING",
    anonymous_mode: bool = False,
    form_fields: list[dict] | None = None,
) -> Assessment:
    now = datetime.now()
    assessment = Assessment(
        name="会议问卷入口",
        code=code,
        questionnaire_id=questionnaire_id,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=7),
        form_fields=form_fields
        if form_fields is not None
        else [
            {"id": "candidate_name", "name": "candidate_name", "label": "姓名", "type": "text", "enabled": True, "required": True},
            {"id": "candidate_phone", "name": "candidate_phone", "label": "手机号", "type": "tel", "enabled": True, "required": True},
            {"id": "school", "name": "school", "label": "学校", "type": "text", "enabled": True, "required": False},
        ],
        page_texts={},
        link_type="temporary",
        allow_repeat=not anonymous_mode,
        repeat_check_by="phone",
        repeat_interval_hours=0,
        max_submissions=0,
        anonymous_mode=anonymous_mode,
        routing_config={},
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def test_normalize_meeting_identity_reads_meeting_profile_payload():
    from app.api.assessments.meeting_integration import normalize_meeting_identity

    identity = normalize_meeting_identity(
        {
            "activity_id": 1,
            "signup_id": 3,
            "profile_available": True,
            "profile": {
                "candidate_name": "赵六",
                "candidate_phone": "13600004444",
                "candidate_email": "zhao@example.com",
                "school": "第三中学",
                "department": "科研处",
                "title": "主任",
            },
        }
    )

    assert identity == {
        "candidate_name": "赵六",
        "candidate_phone": "13600004444",
        "candidate_email": "zhao@example.com",
        "school": "第三中学",
        "department": "科研处",
        "target_position": "主任",
    }


def test_meeting_url_allows_only_configured_hosts(monkeypatch):
    from app.api.assessments.meeting_integration import is_allowed_meeting_url

    monkeypatch.setenv("MEETING_SYSTEM_ALLOWED_HOSTS", "meeting.example,api.meeting.example")

    assert is_allowed_meeting_url("https://meeting.example/api/v1/survey/participant")
    assert is_allowed_meeting_url("https://api.meeting.example/api/v1/survey/callback")
    assert not is_allowed_meeting_url("https://169.254.169.254/latest/meta-data")
    assert not is_allowed_meeting_url("https://evil.example/api/v1/survey/participant")


def test_fetch_meeting_identity_posts_token_in_body(monkeypatch):
    from app.api.assessments import meeting_integration

    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "profile": {
                    "candidate_name": "赵六",
                    "candidate_phone": "13600004444",
                    "school": "第三中学",
                }
            }

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 5.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            calls.append({"url": url, "json": json, "headers": headers})
            return FakeResponse()

        async def get(self, *args, **kwargs):
            raise AssertionError("participant profile must not be fetched with GET")

    monkeypatch.setattr(meeting_integration.httpx, "AsyncClient", FakeClient)

    identity = _run(
        meeting_integration.fetch_meeting_identity(
            "https://meeting.qzmindspace.com/api/v1/survey/participant",
            "token-post",
        )
    )

    assert calls == [
        {
            "url": "https://meeting.qzmindspace.com/api/v1/survey/participant",
            "json": {"surveyToken": "token-post"},
            "headers": {
                "Authorization": "Bearer token-post",
                "X-Survey-Token": "token-post",
            },
        }
    ]
    assert identity["candidate_name"] == "赵六"
    assert identity["candidate_phone"] == "13600004444"
    assert identity["school"] == "第三中学"


def test_meeting_entry_without_configured_fields_does_not_add_identity_fields(monkeypatch):
    from app.api.assessments import meeting_integration

    async def fake_fetch_identity(participant_url: str, survey_token: str):
        return {
            "candidate_name": "张三",
            "candidate_phone": "13800001111",
            "school": "第一中学",
        }

    monkeypatch.setattr(meeting_integration, "fetch_meeting_identity", fake_fetch_identity)

    with _build_session() as session:
        questionnaire = _create_questionnaire(session)
        _create_assessment(session, questionnaire.id, code="ASSE-NO-FIELDS", form_fields={})
        client = _build_client(session)

        response = client.get(
            "/api/public/assessment/ASSE-NO-FIELDS",
            params={
                "surveyToken": "token-no-fields",
                "participantUrl": "https://meeting.example/participants/no-fields",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["form_fields"] == []
        assert body["entry_prefill"] == {}


def test_public_info_prefills_only_configured_entry_fields_from_meeting(monkeypatch):
    from app.api.assessments import meeting_integration

    async def fake_fetch_identity(participant_url: str, survey_token: str):
        assert participant_url == "https://meeting.example/participants/abc"
        assert survey_token == "token-123"
        return {
            "candidate_name": "张三",
            "candidate_phone": "13800001111",
            "school": "第一中学",
            "department": "教务处",
        }

    monkeypatch.setattr(meeting_integration, "fetch_meeting_identity", fake_fetch_identity)

    with _build_session() as session:
        questionnaire = _create_questionnaire(session)
        _create_assessment(session, questionnaire.id)
        client = _build_client(session)

        response = client.get(
            "/api/public/assessment/ASSE-MEETING",
            params={
                "surveyToken": "token-123",
                "participantUrl": "https://meeting.example/participants/abc",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["entry_prefill"] == {
            "candidate_name": "张三",
            "candidate_phone": "13800001111",
            "school": "第一中学",
        }
        assert "department" not in body["entry_prefill"]


def test_anonymous_meeting_entry_hides_identity_fields_but_stores_backend_identity(monkeypatch):
    from app.api.assessments import meeting_integration

    async def fake_fetch_identity(participant_url: str, survey_token: str):
        return {
            "candidate_name": "李四",
            "candidate_phone": "13900002222",
            "school": "第二中学",
            "department": "总务处",
        }

    monkeypatch.setattr(meeting_integration, "fetch_meeting_identity", fake_fetch_identity)

    with _build_session() as session:
        questionnaire = _create_questionnaire(session)
        _create_assessment(
            session,
            questionnaire.id,
            code="ASSE-MEETING-ANON",
            anonymous_mode=True,
            form_fields=[
                {"id": "candidate_name", "name": "candidate_name", "label": "姓名", "type": "text", "enabled": True, "required": True},
                {"id": "candidate_phone", "name": "candidate_phone", "label": "手机号", "type": "tel", "enabled": True, "required": True},
                {"id": "school", "name": "school", "label": "学校", "type": "text", "enabled": True, "required": False},
                {"id": "department", "name": "department", "label": "部门", "type": "text", "enabled": True, "required": False},
            ],
        )
        client = _build_client(session)

        info_response = client.get(
            "/api/public/assessment/ASSE-MEETING-ANON",
            params={
                "surveyToken": "anon-token",
                "participantUrl": "https://meeting.example/participants/anon",
            },
        )
        assert info_response.status_code == 200
        assert info_response.json()["form_fields"] == []
        assert info_response.json()["entry_prefill"] == {}

        start_response = client.post(
            "/api/public/assessment/ASSE-MEETING-ANON/start",
            json={
                "assessment_code": "ASSE-MEETING-ANON",
                "candidate_name": "",
                "candidate_phone": "",
                "anonymous_device_id": "device-1",
                "custom_data": {},
                "survey_token": "anon-token",
                "participant_url": "https://meeting.example/participants/anon",
                "callback_url": "https://meeting.example/callback",
            },
        )

        assert start_response.status_code == 200
        submission = session.exec(select(Submission)).one()
        assert submission.candidate_name == ""
        assert submission.candidate_phone == ""
        assert submission.custom_data["meeting_identity"] == {
            "candidate_name": "李四",
            "candidate_phone": "13900002222",
            "school": "第二中学",
            "department": "总务处",
        }
        assert submission.custom_data["__meeting_callback"] == {
            "callback_url": "https://meeting.example/callback",
            "survey_token": "anon-token",
        }


def test_submit_calls_meeting_callback_with_response_id_and_submitted_at(monkeypatch):
    from app.api.assessments import meeting_integration

    callback_calls = []

    async def fake_send_completion_callback(callback_url: str, survey_token: str, response_id: int, submitted_at):
        callback_calls.append(
            {
                "callback_url": callback_url,
                "survey_token": survey_token,
                "response_id": response_id,
                "submitted_at": submitted_at,
            }
        )
        return True

    monkeypatch.setattr(meeting_integration, "send_completion_callback", fake_send_completion_callback)

    with _build_session() as session:
        questionnaire = _create_questionnaire(session)
        assessment = _create_assessment(session, questionnaire.id)
        submission = Submission(
            code="SUB-MEETING-001",
            assessment_id=assessment.id,
            questionnaire_id=questionnaire.id,
            candidate_name="王五",
            candidate_phone="13700003333",
            custom_data={
                "__meeting_callback": {
                    "callback_url": "https://meeting.example/callback",
                    "survey_token": "token-callback",
                }
            },
            status="in_progress",
            started_at=datetime.now(),
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        client = _build_client(session)
        response = client.post(
            "/api/public/assessment/submission/SUB-MEETING-001/submit",
            json={"submission_code": "SUB-MEETING-001", "answers": {"q1": "good"}},
        )

        assert response.status_code == 200
        assert len(callback_calls) == 1
        assert callback_calls[0]["callback_url"] == "https://meeting.example/callback"
        assert callback_calls[0]["survey_token"] == "token-callback"
        assert callback_calls[0]["response_id"] == submission.id
        assert callback_calls[0]["submitted_at"] is not None


def test_submit_ignores_meeting_callback_failure(monkeypatch):
    from app.api.assessments import meeting_integration

    async def broken_send_completion_callback(*args, **kwargs):
        raise RuntimeError("meeting callback unavailable")

    monkeypatch.setattr(meeting_integration, "send_completion_callback", broken_send_completion_callback)

    with _build_session() as session:
        questionnaire = _create_questionnaire(session)
        assessment = _create_assessment(session, questionnaire.id)
        submission = Submission(
            code="SUB-MEETING-FAIL-CALLBACK",
            assessment_id=assessment.id,
            questionnaire_id=questionnaire.id,
            candidate_name="王五",
            candidate_phone="13700003333",
            custom_data={
                "__meeting_callback": {
                    "callback_url": "https://meeting.example/callback",
                    "survey_token": "token-callback",
                }
            },
            status="in_progress",
            started_at=datetime.now(),
        )
        session.add(submission)
        session.commit()

        client = _build_client(session)
        response = client.post(
            "/api/public/assessment/submission/SUB-MEETING-FAIL-CALLBACK/submit",
            json={"submission_code": "SUB-MEETING-FAIL-CALLBACK", "answers": {"q1": "good"}},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
