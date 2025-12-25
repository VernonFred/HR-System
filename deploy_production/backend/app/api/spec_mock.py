from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter(prefix="/spec", tags=["spec-mock"])

# --------- Mock Schemas (aligned with models_spec) ---------


class PersonalityDimension(BaseModel):
    key: str
    label: str
    score: float


class CompetencyScore(BaseModel):
    key: str
    label: str
    score: float


class CandidateProfileOut(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str] = None
    applied_position: Optional[str] = None
    has_resume: bool = False
    resume_education: Optional[str] = None
    resume_experiences: Optional[str] = None
    resume_skills: Optional[List[str]] = None
    resume_highlights: Optional[List[str]] = None
    latest_assessment_at: Optional[datetime] = None
    overall_match_score: float = 0
    tags: List[str] = []
    personality_dimensions: List[PersonalityDimension] = []
    competencies: List[CompetencyScore] = []
    ai_summary: Optional[str] = None
    highlights: List[str] = []
    risks: List[str] = []
    recommended_positions: List[str] = []
    avoid_positions: List[str] = []


class AssessmentConfigOut(BaseModel):
    id: int
    name: str
    questionnaire_ids: List[int]
    job_profile_id: Optional[int] = None
    description: Optional[str] = None


class QuestionnaireOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    type: str
    dimensions: List[dict]
    questions: List[dict]


class JobProfileOut(BaseModel):
    id: int
    name: str
    dimensions: List[dict]  # [{key, weight}]


# --------- Mock Data ---------

MOCK_CANDIDATES: List[CandidateProfileOut] = [
    CandidateProfileOut(
        id="1",
        name="张三",
        phone="138****1234",
        email="zhangsan@example.com",
        applied_position="产品经理",
        has_resume=True,
        resume_education="本科 · 计算机科学 · 211",
        resume_experiences="5年 ToB 产品经验，主导需求挖掘、规划与交付",
        resume_skills=["需求分析", "产品规划", "数据分析", "沟通协作"],
        resume_highlights=["3个0-1上线产品", "跨部门项目推进", "建立数据看板优化决策"],
        latest_assessment_at=datetime.utcnow(),
        overall_match_score=86,
        tags=["结构化分析", "执行力", "理性"],
        personality_dimensions=[
            PersonalityDimension(key="E", label="外向性", score=65),
            PersonalityDimension(key="N", label="情绪稳定性", score=72),
            PersonalityDimension(key="O", label="创新性", score=78),
            PersonalityDimension(key="C", label="自律性", score=82),
            PersonalityDimension(key="T", label="团队协作", score=74),
            PersonalityDimension(key="R", label="风险偏好", score=60),
        ],
        competencies=[
            CompetencyScore(key="plan", label="产品规划力", score=82),
            CompetencyScore(key="insight", label="用户洞察", score=78),
            CompetencyScore(key="comm", label="沟通协作", score=74),
            CompetencyScore(key="execute", label="执行力", score=80),
            CompetencyScore(key="pressure", label="抗压", score=70),
        ],
        ai_summary="逻辑与结构化突出，沟通理性直接，适合规划+落地结合的岗位。",
        highlights=[
            "结构化分析能力强",
            "规划视野成熟",
            "自驱力高，推进主动",
        ],
        risks=[
            "对低效流程容忍度低",
            "高压多任务下需节奏管理",
        ],
        recommended_positions=["ToB 产品经理", "产品策略", "数据/增长产品"],
        avoid_positions=["高度重复事务岗", "纯情绪劳动岗位"],
    )
]

MOCK_QUESTIONNAIRES: List[QuestionnaireOut] = [
    QuestionnaireOut(
        id=1,
        name="EPQ",
        description="艾森克人格问卷",
        type="builtin",
        dimensions=[
            {"key": "E", "name": "外向性"},
            {"key": "N", "name": "神经质"},
            {"key": "P", "name": "精神质"},
            {"key": "L", "name": "掩饰性"},
        ],
        questions=[],
    ),
    QuestionnaireOut(
        id=2,
        name="MBTI",
        description="MBTI 人格问卷",
        type="builtin",
        dimensions=[
            {"key": "EI", "name": "外倾-内倾"},
            {"key": "SN", "name": "实感-直觉"},
            {"key": "TF", "name": "思考-情感"},
            {"key": "JP", "name": "判断-知觉"},
        ],
        questions=[],
    ),
]

MOCK_ASSESS_CONFIGS: List[AssessmentConfigOut] = [
    AssessmentConfigOut(id=1, name="产品岗测评方案", questionnaire_ids=[1, 2], job_profile_id=1, description="EPQ+MBTI"),
]

MOCK_JOB_PROFILES: List[JobProfileOut] = [
    JobProfileOut(
        id=1,
        name="产品经理画像",
        dimensions=[
          {"key": "plan", "weight": 0.25},
          {"key": "comm", "weight": 0.2},
          {"key": "execute", "weight": 0.2},
          {"key": "pressure", "weight": 0.15},
          {"key": "insight", "weight": 0.2},
        ],
    )
]


# --------- Endpoints (mock responses) ---------


@router.get("/candidates", response_model=list[CandidateProfileOut])
def list_candidates_mock():
    return MOCK_CANDIDATES


@router.get("/candidates/{cid}", response_model=CandidateProfileOut)
def get_candidate_mock(cid: str):
    for c in MOCK_CANDIDATES:
        if c.id == cid:
            return c
    return MOCK_CANDIDATES[0]


@router.get("/questionnaires", response_model=list[QuestionnaireOut])
def list_questionnaires_mock():
    return MOCK_QUESTIONNAIRES


@router.get("/assessment-configs", response_model=list[AssessmentConfigOut])
def list_configs_mock():
    return MOCK_ASSESS_CONFIGS


@router.get("/job-profiles", response_model=list[JobProfileOut])
def list_job_profiles_mock():
    return MOCK_JOB_PROFILES


@router.post("/ai/profile", response_model=CandidateProfileOut)
def ai_profile_mock(payload: dict):
    # Echo back first mock with timestamp bump; in real impl, run AI and persist
    base = MOCK_CANDIDATES[0]
    return CandidateProfileOut(**base.dict(), ai_summary=base.ai_summary)
