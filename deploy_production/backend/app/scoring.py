from typing import Dict, Iterable, Tuple

from app.models import Question
from app.schemas import AnswerItem, SubmissionScore


class ScoringError(ValueError):
    pass


def validate_answers(required_questions: Iterable[Question], answers_map: Dict[int, AnswerItem]) -> None:
    missing = [q.id for q in required_questions if q.id not in answers_map]
    if missing:
        raise ScoringError(f"Missing required questions: {missing}")


def score_submission(
    questions: Iterable[Question],
    answers_map: Dict[int, AnswerItem],
    weights: dict | None = None,
    scoring_config: dict | None = None,
) -> Tuple[list[SubmissionScore], float]:
    """
    基于题目/维度的简化评分：
    - yes/no：匹配正向得1分，否则0
    - choice：选A得1分，否则0（支持 scoreA/scoreB，题型权重可调）
    - 维度得分 = (该维度得分 / 维度最大分) * 100 * 维度权重
    - 总分 = 维度得分的加权平均
    可选配置 scoring_config:
      - dim_max: {dim: max_score} 维度满分（缺省为该维度题目的满分之和）
      - question_type_weights: {yesno: 1.0, choice: 1.0} 题型权重
      - dim_scale: {dim: [min, max]} 将维度分数线性映射到指定区间（如 EPQ 0-24）
      - grade_cutoffs: {dim: {A:90,B:75,C:60}} 维度评分等级（前端可用）
    """
    dim_totals: Dict[str, float] = {}
    dim_max: Dict[str, float] = {}
    qtype_weights = scoring_config.get("question_type_weights", {}) if scoring_config else {}

    for q in questions:
        if q.id not in answers_map or not q.dimension:
            continue
        ans = answers_map[q.id]
        score, max_score = _score_question(q, ans.value, qtype_weights)
        dim_totals[q.dimension] = dim_totals.get(q.dimension, 0.0) + score
        dim_max[q.dimension] = dim_max.get(q.dimension, 0.0) + max_score

    dim_scores: Dict[str, float] = {}
    for dim, total in dim_totals.items():
        max_val = dim_max.get(dim, 0.0) or 1.0
        if scoring_config and scoring_config.get("dim_max", {}).get(dim):
            max_val = float(scoring_config["dim_max"][dim])
            if max_val <= 0:
                raise ScoringError(f"Invalid dim_max for {dim}")
        base_raw = (total / max_val) * 100.0
        base = _apply_scale(dim, base_raw, scoring_config)
        weight = float(weights.get(dim, 1.0)) if weights else 1.0
        if weight < 0:
            raise ScoringError(f"Weight for dimension {dim} must be non-negative")
        dim_scores[dim] = base * weight

    cutoffs = scoring_config.get("grade_cutoffs", {}) if scoring_config else {}
    labels = scoring_config.get("grade_labels", {}) if scoring_config else {}
    scores = [
        SubmissionScore(
            dimension=d,
            score=s,
            grade=_grade_from_score(s, cutoffs),
            grade_label=labels.get(_grade_from_score(s, cutoffs, default=None)),
        )
        for d, s in dim_scores.items()
    ]
    total_weight = sum(float(weights.get(dim, 1.0)) for dim in dim_scores.keys()) if weights else len(dim_scores)
    total_weight = total_weight or 1.0
    total = sum(s.score for s in scores) / total_weight
    return scores, total


def _score_question(q: Question, value: object, qtype_weights: dict | None = None) -> Tuple[float, float]:
    """基础得分与满分：支持 yes/no 与 choice 的显式分值."""
    v = str(value).lower()
    if q.answer_type == "yesno":
        if q.positive:
            base = 1.0 if v in {"yes", "true", "1"} else 0.0
        else:
            base = 1.0 if v in {"no", "false", "0"} else 0.0
        weight = _to_float(qtype_weights.get("yesno")) if qtype_weights else 1.0
        return base * weight, 1.0 * weight

    payload = q.payload or {}
    # 支持分值字段 scoreA/scoreB，缺省 1/0
    score_a = _to_float(payload.get("scoreA"), default=1.0)
    score_b = _to_float(payload.get("scoreB"), default=0.0)
    option_a = str(payload.get("optionA", "")).lower()
    option_b = str(payload.get("optionB", "")).lower()

    if option_a and v == option_a:
        return score_a, max(score_a, score_b, 1.0)
    if option_b and v == option_b:
        return score_b, max(score_a, score_b, 1.0)
    # 若选项未匹配，返回 0
    weight = _to_float(qtype_weights.get("choice")) if qtype_weights else 1.0
    return 0.0, max(score_a, score_b, 1.0) * weight


def _to_float(val, default: float) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _apply_scale(dim: str, value: float, scoring_config: dict | None) -> float:
    if not scoring_config:
        return value
    dim_scale = scoring_config.get("dim_scale", {}) if scoring_config else {}
    if dim not in dim_scale:
        return value
    try:
        min_v, max_v = dim_scale[dim]
        min_v = float(min_v)
        max_v = float(max_v)
    except Exception:
        return value
    # 线性映射到 [min_v, max_v]
    return min_v + (max_v - min_v) * (value / 100.0)


def _grade_from_score(score: float, cutoffs: dict) -> str | None:
    if not cutoffs:
        return None
    sorted_items = sorted(cutoffs.items(), key=lambda x: float(x[1]), reverse=True)
    for grade, minimum in sorted_items:
        if score >= float(minimum):
            return grade
    return list(cutoffs.keys())[-1] if cutoffs else None
