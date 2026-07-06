"""评分问卷历史提交重算服务."""
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.api.assessments.answer_export_service import COMPLETED_SUBMISSION_STATUSES
from app.api.assessments.scoring_statistics import build_score_summary
from app.custom_scoring import calculate_custom_questionnaire_score
from app.models_assessment import Questionnaire, Submission


def _answers_to_list(answers: Any) -> List[Dict[str, Any]]:
    if isinstance(answers, dict):
        return [
            {"question_id": str(question_id), "answer": answer}
            for question_id, answer in answers.items()
        ]
    if isinstance(answers, list):
        return answers
    return []


def _clean_score(value: Any) -> Optional[float | int]:
    if value is None:
        return None
    rounded = round(float(value), 1)
    return int(rounded) if rounded.is_integer() else rounded


async def recalculate_questionnaire_scores(
    session: Session,
    questionnaire_id: int,
) -> Optional[Dict[str, Any]]:
    """按当前评分配置重算指定问卷的已完成提交."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return None

    statement = select(Submission).where(Submission.questionnaire_id == questionnaire_id)
    submissions = list(session.exec(statement).all())
    questionnaire_dict = {
        "custom_type": questionnaire.custom_type,
        "scoring_config": questionnaire.scoring_config,
        "questions_data": questionnaire.questions_data,
    }
    updated_count = 0
    skipped_count = 0

    for submission in submissions:
        if submission.status not in COMPLETED_SUBMISSION_STATUSES:
            skipped_count += 1
            continue

        answers_list = _answers_to_list(submission.answers)
        result = calculate_custom_questionnaire_score(questionnaire_dict, answers_list)
        submission.result_details = {
            "custom_type": questionnaire.custom_type,
            "answers": result.get("detailed_answers", []),
        }
        submission.total_score = _clean_score(result.get("total_score"))
        submission.max_score = _clean_score(result.get("max_score"))
        submission.score_percentage = _clean_score(result.get("score_percentage"))
        submission.grade = result.get("grade")
        submission.scores = {}
        session.add(submission)
        updated_count += 1

    session.commit()
    refreshed = list(session.exec(statement).all())
    summary = build_score_summary(questionnaire, refreshed) or {}

    return {
        "questionnaire_id": questionnaire_id,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "average_score": summary.get("average_score"),
        "score_summary": summary,
    }
