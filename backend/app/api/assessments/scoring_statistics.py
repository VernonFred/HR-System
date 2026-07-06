"""评分问卷统计聚合."""
from typing import Any, Dict, List, Optional

from app.api.assessments.answer_export_service import COMPLETED_SUBMISSION_STATUSES
from app.api.assessments.statistics_normalizers import _normalize_submission_answers
from app.custom_scoring import normalize_scoring_config, score_question_answer
from app.models_assessment import Questionnaire, Submission


def _clean_number(value: Optional[float], precision: int = 1) -> Optional[float | int]:
    if value is None:
        return None
    rounded = round(float(value), precision)
    return int(rounded) if rounded.is_integer() else rounded


def _is_completed(submission: Submission) -> bool:
    return submission.status in COMPLETED_SUBMISSION_STATUSES


def _lookup_answer(answers: Dict[str, Any], question_id: Any, question_index: int) -> tuple[bool, Any]:
    keys = [question_id, str(question_id), str(question_index), str(question_index - 1)]
    for key in keys:
        if key in answers:
            return True, answers[key]
    return False, None


def _is_scoring_enabled(questionnaire: Questionnaire) -> bool:
    config = normalize_scoring_config(questionnaire.scoring_config, questionnaire.custom_type)
    is_scored = questionnaire.custom_type == "scored" or questionnaire.category == "scored"
    return is_scored and bool(config.get("enabled"))


def build_score_summary(questionnaire: Questionnaire, submissions: List[Submission]) -> Optional[Dict[str, Any]]:
    """生成问卷总分概览."""
    if not _is_scoring_enabled(questionnaire):
        return None

    scored_submissions = [
        submission
        for submission in submissions
        if _is_completed(submission) and submission.total_score is not None
    ]
    if not scored_submissions:
        return None

    scores = [float(submission.total_score or 0) for submission in scored_submissions]
    configured_max = normalize_scoring_config(
        questionnaire.scoring_config,
        questionnaire.custom_type,
    ).get("total_score", 100)
    max_scores = [
        float(submission.max_score)
        for submission in scored_submissions
        if submission.max_score is not None
    ]
    max_score = max(max_scores) if max_scores else float(configured_max or 100)

    percentages = [
        float(submission.score_percentage)
        for submission in scored_submissions
        if submission.score_percentage is not None
    ]
    if not percentages and max_score > 0:
        percentages = [score / max_score * 100 for score in scores]

    return {
        "scored_submission_count": len(scored_submissions),
        "max_score": _clean_number(max_score),
        "average_score": _clean_number(sum(scores) / len(scores)),
        "highest_score": _clean_number(max(scores)),
        "lowest_score": _clean_number(min(scores)),
        "average_percentage": _clean_number(sum(percentages) / len(percentages)) if percentages else None,
    }


def build_question_score_stats_map(
    questionnaire: Questionnaire,
    questions: List[Dict[str, Any]],
    submissions: List[Submission],
) -> Dict[str, Dict[str, Any]]:
    """生成每道题的得分统计，key 为题目 id."""
    if not _is_scoring_enabled(questionnaire):
        return {}

    config = normalize_scoring_config(questionnaire.scoring_config, questionnaire.custom_type)
    questionnaire_max = float(config.get("total_score", 100) or 100)
    completed = [submission for submission in submissions if _is_completed(submission)]
    raw_stats: Dict[str, Dict[str, Any]] = {}

    for question_index, question in enumerate(questions, start=1):
        question_id = question.get("id", str(question_index))
        details = []
        for submission in completed:
            answers = _normalize_submission_answers(submission.answers)
            found, answer = _lookup_answer(answers, question_id, question_index)
            if not found:
                continue
            score_detail = score_question_answer(question, answer)
            if score_detail.get("scoreable"):
                details.append(score_detail)

        if not details:
            continue

        raw_scores = [float(item["raw_score"]) for item in details]
        raw_max = max(float(item["raw_max_score"]) for item in details)
        raw_stats[str(question_id)] = {
            "count": len(details),
            "average_raw_score": sum(raw_scores) / len(raw_scores),
            "max_raw_score": raw_max,
        }

    total_raw_max = sum(item["max_raw_score"] for item in raw_stats.values())
    if total_raw_max <= 0:
        return {}

    stats_map: Dict[str, Dict[str, Any]] = {}
    for question_id, item in raw_stats.items():
        max_score = item["max_raw_score"] / total_raw_max * questionnaire_max
        average_score = item["average_raw_score"] / item["max_raw_score"] * max_score
        average_percentage = (
            item["average_raw_score"] / item["max_raw_score"] * 100
            if item["max_raw_score"] > 0
            else 0
        )
        stats_map[question_id] = {
            "scored_answer_count": item["count"],
            "average_raw_score": _clean_number(item["average_raw_score"]),
            "max_raw_score": _clean_number(item["max_raw_score"]),
            "average_score": _clean_number(average_score),
            "max_score": _clean_number(max_score),
            "average_percentage": _clean_number(average_percentage),
        }

    return stats_map
