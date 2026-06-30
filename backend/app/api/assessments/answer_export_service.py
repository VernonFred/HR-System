"""Questionnaire per-person answer export service."""
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models_assessment import Questionnaire, Submission
from app.api.assessments.statistics_normalizers import (
    _normalize_export_options,
    _normalize_questionnaire_questions,
    _normalize_submission_answers,
)


COMPLETED_SUBMISSION_STATUSES = ("completed", "已完成", "done", "submitted")


def _select_export_submissions(session: Session, questionnaire_id: int) -> List[Submission]:
    """优先选择已完成记录，缺失时回退到有答案的记录."""
    completed_query = (
        select(Submission)
        .where(
            Submission.questionnaire_id == questionnaire_id,
            Submission.status.in_(COMPLETED_SUBMISSION_STATUSES),
        )
        .order_by(Submission.submitted_at.desc(), Submission.id.desc())
    )
    submissions = list(session.exec(completed_query).all())
    if submissions:
        return submissions

    fallback_query = (
        select(Submission)
        .where(Submission.questionnaire_id == questionnaire_id)
        .order_by(Submission.submitted_at.desc(), Submission.id.desc())
    )
    all_submissions = list(session.exec(fallback_query).all())
    return [submission for submission in all_submissions if _normalize_submission_answers(submission.answers)]


async def get_questionnaire_answer_export(
    session: Session,
    questionnaire_id: int,
) -> Optional[Dict[str, Any]]:
    """获取问卷逐人答题明细导出数据."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return None

    questions = []
    for index, question in enumerate(_normalize_questionnaire_questions(questionnaire), start=1):
        questions.append({
            "id": question.get("id", str(index)),
            "index": index,
            "text": question.get("text") or question.get("question") or f"问题 {index}",
            "type": question.get("type"),
            "options": _normalize_export_options(question.get("options")),
        })

    submissions = []
    for submission in _select_export_submissions(session, questionnaire_id):
        submissions.append({
            "id": submission.id,
            "code": submission.code,
            "candidate_name": submission.candidate_name,
            "candidate_phone": submission.candidate_phone,
            "candidate_email": submission.candidate_email,
            "gender": submission.gender,
            "target_position": submission.target_position,
            "status": submission.status,
            "started_at": submission.started_at,
            "submitted_at": submission.submitted_at,
            "answers": _normalize_submission_answers(submission.answers),
        })

    return {
        "questionnaire_id": questionnaire_id,
        "questionnaire_name": questionnaire.name,
        "questions": questions,
        "submissions": submissions,
    }
