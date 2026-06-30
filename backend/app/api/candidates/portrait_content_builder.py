"""Helpers for shaping AI portrait content into response schema fields."""
from typing import Any, Dict, List, Tuple

from . import schemas


def build_summary_points(ai_analysis: Dict[str, Any]) -> List[str]:
    summary_points = ai_analysis.get("summary_points", [])

    if len(summary_points) >= 3:
        return summary_points[:3]
    if summary_points or not ai_analysis.get("summary"):
        return summary_points

    summary_text = ai_analysis.get("summary", "")
    paragraphs = [p.strip() for p in summary_text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        return paragraphs[:3]

    sentences: List[str] = []
    for para in (paragraphs if paragraphs else [summary_text]):
        sentences.extend([s.strip() + "。" for s in para.split("。") if s.strip()])

    if len(sentences) < 3:
        return paragraphs[:3] if paragraphs else [summary_text]

    merged_points: List[str] = []
    current_point = ""
    for sentence in sentences:
        if not current_point:
            current_point = sentence
        elif len(current_point + sentence) <= 120:
            current_point += sentence
        else:
            if current_point:
                merged_points.append(current_point)
            current_point = sentence

        if len(current_point) >= 80 and len(merged_points) < 2:
            merged_points.append(current_point)
            current_point = ""

    if current_point:
        merged_points.append(current_point)

    return merged_points[:3] if len(merged_points) >= 3 else merged_points


def build_competencies(ai_analysis: Dict[str, Any]) -> List[schemas.CompetencyScore]:
    ai_competencies = ai_analysis.get("competencies", [])[:6]

    if len(ai_competencies) < 5:
        default_competencies = [
            {"key": "communication", "label": "沟通协作能力", "score": 78, "rationale": "基于综合表现评估"},
            {"key": "execution", "label": "执行推进能力", "score": 80, "rationale": "基于任务完成度评估"},
            {"key": "learning", "label": "学习适应能力", "score": 82, "rationale": "基于开放性评估"},
            {"key": "problem_solving", "label": "问题解决能力", "score": 76, "rationale": "基于逻辑思维评估"},
            {"key": "teamwork", "label": "团队协作能力", "score": 75, "rationale": "基于协作表现评估"},
            {"key": "stress_tolerance", "label": "抗压能力", "score": 72, "rationale": "基于情绪稳定性评估"},
        ]
        existing_keys = {c.get("key") for c in ai_competencies}
        for item in default_competencies:
            if len(ai_competencies) >= 6:
                break
            if item["key"] not in existing_keys:
                ai_competencies.append(item)
                existing_keys.add(item["key"])

    return [
        schemas.CompetencyScore(
            key=comp.get("key"),
            label=comp.get("label", "未知能力"),
            score=float(comp.get("score", 0)),
            rationale=comp.get("rationale"),
        )
        for comp in ai_competencies
    ]


def build_quick_tags(ai_analysis: Dict[str, Any]) -> List[str]:
    valid_tags: List[str] = []
    for tag in ai_analysis.get("quick_tags", []):
        if isinstance(tag, str):
            tag = tag.strip()
            if 2 <= len(tag) <= 8:
                valid_tags.append(tag)

    if len(valid_tags) < 3:
        default_tags = ["待深入了解", "综合评估中", "详见分析"]
        return valid_tags + default_tags[len(valid_tags):3]
    return valid_tags[:3]
