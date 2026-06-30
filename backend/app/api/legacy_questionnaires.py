from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_user
from app.config_scoring import QUESTIONNAIRE_SCORING_CONFIG
from app.db import get_engine, get_session
from app.models import Question, SubmissionAnswer
from app.models_assessment import Questionnaire, Submission
from app.schemas import AnswerItem, SubmissionRequest, SubmissionResponse
from app.scoring import ScoringError, score_submission, validate_answers

router = APIRouter()

@router.get("/questionnaires", response_model=list[Questionnaire], tags=["questionnaires"])
def list_questionnaires(session: Session = Depends(get_session)) -> list[Questionnaire]:
    """List all questionnaires."""
    result = session.exec(select(Questionnaire).order_by(Questionnaire.id)).all()
    return result


@router.get(
    "/questionnaires/{code}",
    response_model=Questionnaire,
    tags=["questionnaires"],
)
def get_questionnaire(code: str, session: Session = Depends(get_session)) -> Questionnaire:
    """Get questionnaire by code."""
    q = session.exec(select(Questionnaire).where(Questionnaire.code == code)).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return q


@router.get(
    "/questionnaires/{code}/questions",
    response_model=list[Question],
    tags=["questionnaires"],
)
def list_questions(code: str, session: Session = Depends(get_session)) -> list[Question]:
    """List questions of a questionnaire by code."""
    q = session.exec(select(Questionnaire).where(Questionnaire.code == code)).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    rows = session.exec(
        select(Question).where(Question.questionnaire_id == q.id).order_by(Question.order)
    ).all()
    return rows


@router.post(
    "/submissions",
    response_model=SubmissionResponse,
    tags=["submissions"],
)
def submit_answers(
    payload: SubmissionRequest,
    user_id: int = Depends(get_current_user),
) -> SubmissionResponse:
    """提交并评分（当前简化算法，含必答校验；鉴权占位）."""
    engine = get_engine()
    with Session(engine) as session:
        qn = session.exec(
            select(Questionnaire).where(Questionnaire.code == payload.questionnaireCode)
        ).first()
        if not qn:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        # 鉴权占位：若需用户/候选人信息，可在此检查 payload.userId / candidateId
        # 如需强制登录，可在 get_current_user 中抛 401 或在此加判断 user_id/payload.userId
        _validate_weights(payload.weights)

        # 将答案转为 map，方便查找，并校验必答
        parsed_answers = []
        for a in payload.answers:
            try:
                parsed_answers.append(AnswerItem(questionId=int(a.get("questionId")), value=a.get("value")))
            except Exception:
                continue
        answers_map = {a.questionId: a.value for a in parsed_answers}
        q_rows = session.exec(
            select(Question).where(Question.questionnaire_id == qn.id)
        ).all()

        try:
            # 必答校验
            validate_answers(q_rows, {k: AnswerItem(questionId=k, value=v) for k, v in answers_map.items()})
            scoring_cfg = payload.scoring or QUESTIONNAIRE_SCORING_CONFIG.get(payload.questionnaireCode)
            scores, total = score_submission(
                q_rows,
                {k: AnswerItem(questionId=k, value=v) for k, v in answers_map.items()},
                weights=payload.weights,
                scoring_config=scoring_cfg,
            )
        except ScoringError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            )
        # 保存答案（仅保存已答题部分）
        answer_rows: list[SubmissionAnswer] = []
        for q in q_rows:
            if q.id not in answers_map:
                continue
            ans_val = answers_map[q.id]
            sc = next((s.score for s in scores if s.dimension == q.dimension), 0.0) if q.dimension else 0.0
            answer_rows.append(
                SubmissionAnswer(question_id=q.id, value=str(ans_val), score=sc)
            )

        submission_code = f"sub-{uuid4().hex[:8]}"
        submission = Submission(
            submission_code=submission_code,
            questionnaire_id=qn.id,
            total_score=total,
            summary="简化评分：基于答案匹配得分。",
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        # 回写 submission_id 到答案并批量保存
        for a in answer_rows:
            a.submission_id = submission.id
        session.add_all(answer_rows)
        session.commit()

        return SubmissionResponse(
            submissionId=submission_code,
            questionnaireCode=payload.questionnaireCode,
            scores=scores,
            totalScore=total,
            summary=submission.summary,
        )


def _score_question(q: Question, value: object, weights: Optional[dict] = None) -> float:
    """简化评分：yes/no 匹配正向得1分，choice 选 A 得1分，否则0；支持维度加权。"""
    base = 0.0
    v = str(value).lower()
    if q.answer_type == "yesno":
        if q.positive:
            base = 1.0 if v in {"yes", "true", "1"} else 0.0
        else:
            base = 1.0 if v in {"no", "false", "0"} else 0.0
    else:
        payload = q.payload or {}
        base = 1.0 if v == str(payload.get("optionA", "")).lower() else 0.0

    if weights and q.dimension:
        weight = float(weights.get(q.dimension, 1.0))
        return base * weight
    return base


def _validate_weights(weights: Optional[dict]) -> None:
    if not weights:
        return
    for k, v in weights.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid weight for dimension {k}",
            )
        if fv < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Weight for dimension {k} must be non-negative",
            )


# ---- Candidates / Analytics (从数据库获取) ----
