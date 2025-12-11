from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models_spec import (
    Candidate,
    ResumeSummary,
    AssessmentConfig,
    AssessmentSession,
    Questionnaire,
    QuestionnaireResult,
    JobProfile,
    AIProfile,
)

router = APIRouter(prefix="/v2", tags=["v2"])


class PublicStartResponse(BaseModel):
    config: AssessmentConfig
    questionnaires: list[Questionnaire]
    job_profile: Optional[JobProfile] = None


class PublicSubmitResponse(BaseModel):
    status: str
    candidate_id: int
    session_id: int
    result_id: int
    match_score: Optional[float] = None
    dimension_scores: dict[str, Any] = {}
    overall_score: Optional[float] = None


class ResumeSummaryUpsert(BaseModel):
    candidate_id: int
    education: Optional[str] = None
    experiences: Optional[str] = None
    skills: Optional[list[str]] = None
    highlights: Optional[list[str]] = None


DEFAULT_DIMENSIONS = [
    {"key": "plan", "weight": 0.25},
    {"key": "comm", "weight": 0.2},
    {"key": "execute", "weight": 0.2},
    {"key": "pressure", "weight": 0.15},
    {"key": "insight", "weight": 0.2},
]


DEFAULT_QUESTIONNAIRE = {
    "name": "EPQ 核心量表",
    "description": "默认问卷（示例），可替换为真实发布配置",
    "type": "builtin",
    "dimensions": [
        {"key": "E", "name": "外向性"},
        {"key": "N", "name": "情绪稳定"},
        {"key": "O", "name": "开放性"},
        {"key": "C", "name": "自律性"},
    ],
    "questions": [],
}


def _ensure_default_job_profile(session: Session) -> JobProfile:
    job = session.exec(select(JobProfile)).first()
    if not job:
        job = JobProfile(name="默认岗位画像", dimensions=DEFAULT_DIMENSIONS)
        session.add(job)
        session.commit()
        session.refresh(job)
    return job


def _ensure_default_questionnaire(session: Session) -> Questionnaire:
    q = session.exec(select(Questionnaire)).first()
    if not q:
        q = Questionnaire(**DEFAULT_QUESTIONNAIRE)
        session.add(q)
        session.commit()
        session.refresh(q)
    return q


def _compute_match_score(dimension_scores: dict[str, float] | None, job_profile: JobProfile | None) -> Optional[float]:
    if not dimension_scores or not job_profile or not job_profile.dimensions:
        return None
    weights = job_profile.dimensions
    total_weight = sum(item.get("weight", 0) for item in weights)
    if total_weight <= 0:
        return None
    score_sum = 0.0
    for item in weights:
        key = item.get("key")
        weight = item.get("weight", 0)
        score = float(dimension_scores.get(key, 0) or 0)
        score_sum += score * weight
    return round(score_sum / total_weight, 2)


# --------- Questionnaire ---------
@router.get("/questionnaires", response_model=list[Questionnaire])
def list_questionnaires(session: Session = Depends(get_session)):
    return session.exec(select(Questionnaire)).all()


@router.post("/questionnaires", response_model=Questionnaire)
def create_questionnaire(payload: Questionnaire, session: Session = Depends(get_session)):
    payload.id = None
    session.add(payload)
    session.commit()
    session.refresh(payload)
    return payload


# --------- JobProfile ---------
@router.get("/job-profiles", response_model=list[JobProfile])
def list_job_profiles(session: Session = Depends(get_session)):
    return session.exec(select(JobProfile)).all()


@router.post("/job-profiles", response_model=JobProfile)
def create_job_profile(payload: JobProfile, session: Session = Depends(get_session)):
    payload.id = None
    session.add(payload)
    session.commit()
    session.refresh(payload)
    return payload


# --------- Assessment Config ---------
@router.get("/assessment-configs", response_model=list[AssessmentConfig])
def list_configs(session: Session = Depends(get_session)):
    return session.exec(select(AssessmentConfig)).all()


@router.post("/assessment-configs", response_model=AssessmentConfig)
def create_config(payload: AssessmentConfig, session: Session = Depends(get_session)):
    payload.id = None
    session.add(payload)
    session.commit()
    session.refresh(payload)
    return payload


# --------- Candidate (只读) ---------
@router.get("/candidates", response_model=list[Candidate])
def list_candidates(session: Session = Depends(get_session)):
    return session.exec(select(Candidate)).all()


@router.get("/candidates/{cid}")
def get_candidate(cid: int, session: Session = Depends(get_session)):
    cand = session.get(Candidate, cid)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # 汇总 resume 与 ai 画像
    resume = session.exec(select(ResumeSummary).where(ResumeSummary.candidate_id == cand.id)).first()
    ai = session.exec(select(AIProfile).where(AIProfile.candidate_id == cand.id)).first()
    return {
        "candidate": cand,
        "resume": resume,
        "ai_profile": ai,
    }


# --------- Resume Summary ---------
@router.get("/resume/summary/{candidate_id}", response_model=Optional[ResumeSummary])
def get_resume_summary(candidate_id: int, session: Session = Depends(get_session)):
    return session.exec(select(ResumeSummary).where(ResumeSummary.candidate_id == candidate_id)).first()


@router.post("/resume/summary", response_model=ResumeSummary)
def upsert_resume_summary(payload: ResumeSummaryUpsert, session: Session = Depends(get_session)):
    cand = session.get(Candidate, payload.candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    existing = session.exec(select(ResumeSummary).where(ResumeSummary.candidate_id == payload.candidate_id)).first()
    if existing:
        existing.education = payload.education
        existing.experiences = payload.experiences
        existing.skills = payload.skills
        existing.highlights = payload.highlights
        session.add(existing)
        session.commit()
        session.refresh(existing)
        cand.has_resume = True
        session.add(cand)
        session.commit()
        return existing
    summary = ResumeSummary(
        candidate_id=payload.candidate_id,
        education=payload.education,
        experiences=payload.experiences,
        skills=payload.skills,
        highlights=payload.highlights,
    )
    session.add(summary)
    cand.has_resume = True
    session.add(cand)
    session.commit()
    session.refresh(summary)
    return summary


# --------- 公共测评接口 ---------
class PublicStartRequest(BaseModel):
    # 占位：后续可扩展 config_id、channel、meta 等
    config_id: Optional[int] = Field(default=None)
    metadata: Optional[dict] = Field(default=None)


@router.post("/public/assessments/start")
def public_start(payload: PublicStartRequest, session: Session = Depends(get_session)) -> PublicStartResponse:
    """
    返回测评配置与问卷/画像信息。
    - 如果没有任何配置/问卷/画像，自动创建默认示例，保证前端可联调。
    """
    default_job = _ensure_default_job_profile(session)
    default_q = _ensure_default_questionnaire(session)

    config: Optional[AssessmentConfig] = None
    if payload.config_id:
        config = session.get(AssessmentConfig, payload.config_id)

    if not config:
        config = AssessmentConfig(
            name="默认测评配置",
            questionnaire_ids=[default_q.id],
            job_profile_id=default_job.id,
            description="占位配置，缺省用于本地联调",
        )
        session.add(config)
        session.commit()
        session.refresh(config)

    questionnaires: list[Questionnaire] = []
    for qid in config.questionnaire_ids or []:
        q = session.get(Questionnaire, qid)
        if q:
            questionnaires.append(q)
    if not questionnaires:
        questionnaires = [default_q]

    job_profile = session.get(JobProfile, config.job_profile_id) if config.job_profile_id else default_job

    return PublicStartResponse(config=config, questionnaires=questionnaires, job_profile=job_profile)


class PublicSubmitPayload(BaseModel):
    name: str
    phone: str
    applied_position: Optional[str] = None
    config_id: Optional[int] = None
    questionnaire_id: Optional[int] = None
    dimension_scores: Optional[dict] = None
    overall_score: Optional[float] = None


@router.post("/public/assessments/submit")
def public_submit(payload: PublicSubmitPayload, session: Session = Depends(get_session)) -> PublicSubmitResponse:
    """
    自动建档 + 创建测评 Session + 保存维度分。
    - 手机号去重合并候选人
    - 维度分计算：如果未提供 overall_score，则使用维度平均
    - 匹配度：基于 job_profile 权重和维度分
    """
    if not payload.name or not payload.phone:
        raise HTTPException(status_code=400, detail="name and phone required")

    # 自动建档（手机号合并）
    cand = session.exec(select(Candidate).where(Candidate.phone == payload.phone)).first()
    if not cand:
        cand = Candidate(
            name=payload.name,
            phone=payload.phone,
            applied_position=payload.applied_position,
            first_seen_at=datetime.utcnow(),
        )
        session.add(cand)
        session.commit()
        session.refresh(cand)
    else:
        cand.applied_position = payload.applied_position or cand.applied_position
        cand.updated_at = datetime.utcnow()
        session.add(cand)
        session.commit()

    # 创建 Session + Result
    session_row = AssessmentSession(
        candidate_id=cand.id,
        config_id=payload.config_id or 0,
        status="completed",
        completed_at=datetime.utcnow(),
    )
    session.add(session_row)
    session.commit()
    session.refresh(session_row)

    dimension_scores = payload.dimension_scores or {}
    overall_score = payload.overall_score
    if overall_score is None and dimension_scores:
        vals = [float(v) for v in dimension_scores.values() if v is not None]
        overall_score = round(sum(vals) / len(vals), 2) if vals else None

    result = QuestionnaireResult(
        session_id=session_row.id,
        questionnaire_id=payload.questionnaire_id or 0,
        dimension_scores=dimension_scores,
        overall_score=overall_score,
    )
    session.add(result)
    cand.latest_assessment_at = datetime.utcnow()
    session.commit()

    # 计算匹配度
    job_profile = None
    if payload.config_id:
        cfg = session.get(AssessmentConfig, payload.config_id)
        if cfg and cfg.job_profile_id:
            job_profile = session.get(JobProfile, cfg.job_profile_id)
    if not job_profile:
        job_profile = _ensure_default_job_profile(session)

    match_score = _compute_match_score(dimension_scores, job_profile)

    return PublicSubmitResponse(
        status="ok",
        candidate_id=cand.id,
        session_id=session_row.id,
        result_id=result.id,
        match_score=match_score,
        dimension_scores=dimension_scores,
        overall_score=overall_score,
    )


# --------- Assessment results ---------
@router.get("/assessment-sessions/{session_id}/results", response_model=list[QuestionnaireResult])
def get_results_by_session(session_id: int, session: Session = Depends(get_session)):
    return session.exec(select(QuestionnaireResult).where(QuestionnaireResult.session_id == session_id)).all()


# --------- AI Profile 占位 ---------
@router.post("/ai/profile", response_model=AIProfile)
def generate_ai_profile(payload: dict, session: Session = Depends(get_session)):
    cand_id = payload.get("candidate_id")
    if not cand_id:
        raise HTTPException(status_code=400, detail="candidate_id required")
    existing = session.exec(select(AIProfile).where(AIProfile.candidate_id == cand_id)).first()
    if existing:
        session.delete(existing)
        session.commit()
    ai = AIProfile(
        candidate_id=cand_id,
        summary=payload.get("summary"),
        highlights=payload.get("highlights"),
        risks=payload.get("risks"),
        recommended_positions=payload.get("recommended_positions"),
        avoid_positions=payload.get("avoid_positions"),
        last_generated_at=datetime.utcnow(),
    )
    session.add(ai)
    session.commit()
    session.refresh(ai)
    return ai
