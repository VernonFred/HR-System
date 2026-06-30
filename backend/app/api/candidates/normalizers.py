"""候选人画像文本字段归一化工具."""

import json
import re
from typing import Any, Dict, List, Optional

from app.models_assessment import Submission


def _merge_fragments(items: List[str]) -> List[str]:
    if not items:
        return []
    merged: List[str] = []
    buffer = ""
    end_punct = "。！？!?；;：:"
    for item in items:
        text = item.strip()
        if not text:
            continue
        if not buffer:
            buffer = text
            continue
        # 如果上一段没有结束标点，或任一段过短，则认为是同一句的分段
        if buffer[-1] not in end_punct or len(buffer) < 18 or len(text) < 10:
            joiner = "" if buffer.endswith(("，", "、", "；", ";", "：", ":")) else "，"
            buffer = f"{buffer}{joiner}{text}"
        else:
            merged.append(buffer)
            buffer = text
    if buffer:
        merged.append(buffer)
    return merged


def _normalize_list_field(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        if not items:
            return []
        # 如果是按单字符拆分的列表，先拼回字符串再按分隔符拆分
        single_char_ratio = sum(1 for item in items if len(item) == 1) / len(items)
        if len(items) >= 6 and single_char_ratio >= 0.8:
            merged = "".join(items)
            parts = re.split(r"[\n、;；|]+", merged)
            return _merge_fragments([p.strip() for p in parts if p and p.strip()])
        return _merge_fragments(items)
    if isinstance(value, str):
        parts = re.split(r"[\n、;；|]+", value)
        return _merge_fragments([p.strip() for p in parts if p and p.strip()])
    text = str(value).strip()
    return [text] if text else []


def _normalize_ai_insights(value: Any, candidate_name: Optional[str]) -> List[str]:
    items = _normalize_list_field(value)
    if not items:
        return []
    if all(len(item) == 1 for item in items):
        merged = "".join(items).strip()
        if candidate_name and merged == candidate_name:
            return []
        return [merged] if merged else []
    if candidate_name and len(items) == 1 and items[0] == candidate_name:
        return []
    return items


_GENERIC_RULE_INSIGHT_MARKERS = (
    "基础资料完整",
    "建议上传简历",
    "继续保持",
    "测评得分偏低",
    "建议补充更多测评",
    "数据完整性良好",
)


def _is_generic_rule_insight(text: str) -> bool:
    """识别规则引擎模板句，AI 有内容时不让这些句子抢占展示位."""
    return any(marker in text for marker in _GENERIC_RULE_INSIGHT_MARKERS)


def _combine_ai_first(ai_items: List[str], rule_items: List[str], max_items: int = 5) -> List[str]:
    result: List[str] = []
    seen = set()

    def add_item(item: str) -> None:
        text = str(item).strip()
        if not text:
            return
        key = re.sub(r"\s+", "", text)
        if key in seen:
            return
        seen.add(key)
        result.append(text)

    for item in ai_items:
        add_item(item)

    has_ai = len(result) > 0
    for item in rule_items:
        text = str(item).strip()
        if has_ai and _is_generic_rule_insight(text):
            continue
        add_item(text)
        if len(result) >= max_items:
            break

    return result[:max_items]


def _normalize_position_items(value: Any) -> List[str]:
    """岗位字段允许短词逗号分隔；长句保持原样，避免拆坏适配分析."""
    items = _normalize_list_field(value)
    expanded: List[str] = []

    for item in items:
        parts = [p.strip() for p in re.split(r"[\n、;；|]+", item) if p.strip()]
        if len(parts) == 1:
            comma_parts = [p.strip() for p in re.split(r"[,，]", item) if p.strip()]
            if len(comma_parts) > 1 and all(len(p) <= 18 for p in comma_parts):
                parts = comma_parts
        expanded.extend(parts)

    result: List[str] = []
    seen = set()
    for item in expanded:
        key = re.sub(r"\s+", "", item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _submission_result_payload(submission: Submission) -> Dict[str, Any]:
    """Return the result payload expected by fallback/cross-validation services."""
    for field_name in ("result_details", "scores", "answers"):
        value = getattr(submission, field_name, None)
        if isinstance(value, dict) and value:
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and parsed:
                return parsed
    return {}
