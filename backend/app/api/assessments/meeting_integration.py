"""Meeting system integration helpers for public assessment links."""
from datetime import datetime
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx


DEFAULT_ALLOWED_MEETING_HOSTS = {
    "113.240.112.71",
    "meeting.qzmindspace.com",
    "api.qzmindspace.com",
    "localhost",
    "127.0.0.1",
}

IDENTITY_FIELD_NAMES = {
    "name",
    "candidate_name",
    "phone",
    "candidate_phone",
    "mobile",
    "candidate_mobile",
    "email",
    "candidate_email",
    "school",
    "school_name",
    "department",
    "dept",
    "target_position",
    "position",
}


def _configured_allowed_hosts() -> set[str]:
    raw = os.getenv("MEETING_SYSTEM_ALLOWED_HOSTS", "")
    configured = {item.strip().lower() for item in raw.split(",") if item.strip()}
    return DEFAULT_ALLOWED_MEETING_HOSTS | configured


def is_allowed_meeting_url(value: Optional[str]) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    if host in _configured_allowed_hosts():
        return True
    return host.endswith(".qzmindspace.com")


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def normalize_meeting_identity(raw: Any) -> Dict[str, str]:
    """Normalize meeting participant data to the fields HR understands."""
    if not isinstance(raw, dict):
        return {}

    source = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if isinstance(source.get("participant"), dict):
        source = source["participant"]
    if isinstance(source.get("profile"), dict):
        source = source["profile"]

    identity = {
        "candidate_name": _first_non_empty(
            source.get("candidate_name"),
            source.get("name"),
            source.get("participant_name"),
            source.get("participantName"),
            source.get("姓名"),
        ),
        "candidate_phone": _first_non_empty(
            source.get("candidate_phone"),
            source.get("phone"),
            source.get("mobile"),
            source.get("participant_phone"),
            source.get("participantPhone"),
            source.get("手机号"),
        ),
        "candidate_email": _first_non_empty(
            source.get("candidate_email"),
            source.get("email"),
            source.get("邮箱"),
        ),
        "school": _first_non_empty(
            source.get("school"),
            source.get("school_name"),
            source.get("schoolName"),
            source.get("学校"),
        ),
        "department": _first_non_empty(
            source.get("department"),
            source.get("dept"),
            source.get("department_name"),
            source.get("departmentName"),
            source.get("部门"),
        ),
        "target_position": _first_non_empty(
            source.get("target_position"),
            source.get("title"),
            source.get("position"),
            source.get("岗位"),
        ),
    }
    return {key: value for key, value in identity.items() if value}


async def fetch_meeting_identity(participant_url: Optional[str], survey_token: Optional[str]) -> Dict[str, str]:
    """Fetch participant identity from the meeting system using only server-side calls."""
    if not is_allowed_meeting_url(participant_url) or not survey_token:
        return {}

    headers = {
        "Authorization": f"Bearer {survey_token}",
        "X-Survey-Token": survey_token,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                participant_url,
                json={"surveyToken": survey_token},
                headers=headers,
            )
            response.raise_for_status()
            return normalize_meeting_identity(response.json())
    except Exception:
        return {}


def is_identity_form_field(field: Any) -> bool:
    if not isinstance(field, dict):
        return False
    field_key = str(field.get("name") or field.get("id") or "").strip()
    label = str(field.get("label") or "").strip()
    normalized_key = field_key.lower()
    if normalized_key in IDENTITY_FIELD_NAMES:
        return True
    return any(text in label for text in ["姓名", "手机", "电话", "邮箱", "学校", "部门", "岗位"])


def _identity_value_for_field(field: Dict[str, Any], meeting_identity: Dict[str, str]) -> str:
    key = str(field.get("name") or field.get("id") or "").strip().lower()
    label = str(field.get("label") or "").strip()

    if key in {"name", "candidate_name"} or "姓名" in label:
        return meeting_identity.get("candidate_name", "")
    if key in {"phone", "candidate_phone", "mobile", "candidate_mobile"} or "手机" in label or "电话" in label:
        return meeting_identity.get("candidate_phone", "")
    if key in {"email", "candidate_email"} or "邮箱" in label:
        return meeting_identity.get("candidate_email", "")
    if key in {"school", "school_name"} or "学校" in label:
        return meeting_identity.get("school", "")
    if key in {"department", "dept"} or "部门" in label:
        return meeting_identity.get("department", "")
    if key in {"target_position", "position"} or "岗位" in label:
        return meeting_identity.get("target_position", "")
    return ""


def build_entry_prefill(form_fields: Any, meeting_identity: Dict[str, str]) -> Dict[str, str]:
    """Return prefill values only for fields configured by HR."""
    if not isinstance(form_fields, list) or not meeting_identity:
        return {}

    prefill: Dict[str, str] = {}
    for field in form_fields:
        if not isinstance(field, dict) or field.get("enabled") is False:
            continue
        field_name = str(field.get("name") or field.get("id") or "").strip()
        if not field_name:
            continue
        value = _identity_value_for_field(field, meeting_identity)
        if value:
            prefill[field_name] = value
    return prefill


def sanitize_custom_data(custom_data: Any) -> Dict[str, Any]:
    """Hide internal integration config while keeping backend-visible identity."""
    if not isinstance(custom_data, dict):
        return {}
    return {key: value for key, value in custom_data.items() if not str(key).startswith("__")}


async def send_completion_callback(
    callback_url: Optional[str],
    survey_token: Optional[str],
    response_id: Optional[int],
    submitted_at: Optional[datetime],
) -> bool:
    """Notify the meeting system that the HR response was submitted."""
    if not is_allowed_meeting_url(callback_url) or not survey_token or response_id is None or submitted_at is None:
        return False

    payload = {
        "surveyToken": survey_token,
        "response_id": response_id,
        "submitted_at": submitted_at.isoformat(),
    }
    headers = {
        "Authorization": f"Bearer {survey_token}",
        "X-Survey-Token": survey_token,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(callback_url, json=payload, headers=headers)
            response.raise_for_status()
        return True
    except Exception:
        return False
