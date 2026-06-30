"""Assessment department routing helpers."""
from typing import Any, Dict, List, Optional
from sqlmodel import Session

from app.models_assessment import Assessment, Questionnaire


async def normalize_routing_config(
    session: Session,
    raw_config: Optional[Dict[str, Any]],
    strict: bool = True
) -> Dict[str, Any]:
    """标准化并校验部门路由配置."""
    base_config: Dict[str, Any] = {
        "enabled": False,
        "department_field": "department",
        "fallback_to_default": True,
        "mappings": [],
    }

    if not isinstance(raw_config, dict):
        return base_config

    enabled = bool(raw_config.get("enabled", False))
    department_field = str(raw_config.get("department_field") or "department").strip() or "department"
    fallback_to_default = bool(raw_config.get("fallback_to_default", True))

    mappings: List[Dict[str, Any]] = []
    raw_mappings = raw_config.get("mappings")
    if isinstance(raw_mappings, list):
        for item in raw_mappings:
            if not isinstance(item, dict):
                continue

            department_value = str(item.get("department_value") or "").strip()
            questionnaire_id_raw = item.get("questionnaire_id")

            try:
                questionnaire_id = int(questionnaire_id_raw) if questionnaire_id_raw is not None else None
            except (TypeError, ValueError):
                questionnaire_id = None

            if not department_value or questionnaire_id is None:
                if strict and enabled:
                    raise ValueError("部门路由配置无效：请为每个映射填写部门和目标问卷")
                continue

            questionnaire = session.get(Questionnaire, questionnaire_id)
            if not questionnaire:
                if strict and enabled:
                    raise ValueError(f"部门路由配置无效：问卷ID {questionnaire_id} 不存在")
                continue

            mappings.append({
                "department_value": department_value,
                "questionnaire_id": questionnaire_id,
            })

    deduped_by_department: Dict[str, Dict[str, Any]] = {}
    for item in mappings:
        deduped_by_department[item["department_value"]] = item

    return {
        "enabled": enabled,
        "department_field": department_field,
        "fallback_to_default": fallback_to_default,
        "mappings": list(deduped_by_department.values()),
    }


async def resolve_questionnaire_id(
    session: Session,
    assessment: Assessment,
    submission_data: Dict[str, Any]
) -> int:
    """根据部门路由配置解析本次填写应该使用的问卷ID."""
    default_questionnaire_id = assessment.questionnaire_id
    routing_config = await normalize_routing_config(session, assessment.routing_config, strict=False)

    if not routing_config.get("enabled"):
        return default_questionnaire_id

    department_field = str(routing_config.get("department_field") or "department").strip() or "department"
    fallback_to_default = bool(routing_config.get("fallback_to_default", True))

    custom_data = submission_data.get("custom_data")
    raw_department = ""
    if isinstance(custom_data, dict):
        raw_department = custom_data.get(department_field) or ""
    if not raw_department:
        raw_department = submission_data.get(department_field) or ""

    department_value = str(raw_department).strip()
    if not department_value:
        return default_questionnaire_id

    mappings = routing_config.get("mappings") if isinstance(routing_config.get("mappings"), list) else []
    target_questionnaire_id: Optional[int] = None
    for item in mappings:
        if not isinstance(item, dict):
            continue
        if str(item.get("department_value") or "").strip() == department_value:
            try:
                target_questionnaire_id = int(item.get("questionnaire_id"))
            except (TypeError, ValueError):
                target_questionnaire_id = None
            break

    if target_questionnaire_id is None:
        if fallback_to_default:
            return default_questionnaire_id
        raise ValueError(f"部门“{department_value}”未配置对应问卷")

    target_questionnaire = session.get(Questionnaire, target_questionnaire_id)
    if target_questionnaire and target_questionnaire.status == "active":
        return target_questionnaire_id

    if fallback_to_default:
        return default_questionnaire_id
    raise ValueError(f"部门“{department_value}”对应问卷不可用")
