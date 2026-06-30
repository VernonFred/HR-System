"""Shared normalizers for assessment statistics/export services."""
from typing import Any, Dict, List

from app.models_assessment import Questionnaire


def _parse_json_object(raw_value: Any, default: Any) -> Any:
    """兼容历史字符串 JSON 字段."""
    if isinstance(raw_value, str):
        import json
        try:
            return json.loads(raw_value)
        except Exception:
            return default
    return raw_value if raw_value is not None else default


def _normalize_questionnaire_questions(questionnaire: Questionnaire) -> List[Dict[str, Any]]:
    """提取问卷题目列表，兼容历史结构."""
    questions_data = _parse_json_object(questionnaire.questions_data or [], [])
    if isinstance(questions_data, dict):
        questions_data = questions_data.get("questions", [])
    if not isinstance(questions_data, list):
        return []
    return [question for question in questions_data if isinstance(question, dict)]

def _normalize_export_options(raw_options: Any) -> List[Dict[str, Any]]:
    """标准化题目选项为 value/label 结构."""
    if not isinstance(raw_options, list):
        return []

    normalized_options: List[Dict[str, Any]] = []
    for option_index, option in enumerate(raw_options):
        if isinstance(option, dict):
            option_value = option.get("value")
            option_label = option.get("label") or option.get("text") or option.get("value")
            if option_value is None:
                option_value = option.get("label") or option.get("text")
            if option_label is not None:
                option_label = str(option_label)
            normalized_options.append({"index": option_index, "value": option_value, "label": option_label})
        else:
            normalized_options.append({"index": option_index, "value": option, "label": str(option)})
    return normalized_options


def _normalize_submission_answers(raw_answers: Any) -> Dict[str, Any]:
    """标准化提交答案结构."""
    answers = _parse_json_object(raw_answers or {}, {})
    return answers if isinstance(answers, dict) else {}
