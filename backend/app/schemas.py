from typing import List, Optional

from sqlmodel import SQLModel


class SubmissionRequest(SQLModel):
    questionnaireCode: str
    answers: list[dict]  # {questionId, value}
    userId: Optional[int] = None
    candidateId: Optional[int] = None
    # 可选：维度权重或配置，后续可扩展
    weights: Optional[dict] = None
    # 可选：答案来源（web/mobile/qr），用于审计
    source: Optional[str] = None
    # 可选：评分配置：dim_max（维度满分）、question_type_weights（题型权重）
    scoring: Optional[dict] = None


class AnswerItem(SQLModel):
    questionId: int
    value: str | int | float | bool


class SubmissionScore(SQLModel):
    dimension: str
    score: float
    grade: Optional[str] = None
    grade_label: Optional[str] = None


class SubmissionResponse(SQLModel):
    submissionId: str
    questionnaireCode: str
    scores: list[SubmissionScore]
    totalScore: float
    summary: str | None = None


class CandidateOut(SQLModel):
    id: int
    name: str
    position: str
    phone: str
    score: float
    status: str
    grade: Optional[str] = None
    level: Optional[str] = None
    tags: Optional[list[str]] = None
    updated_at: Optional[str] = None
    dimensions: Optional[list[SubmissionScore]] = None
    # ⭐ 新增：提交类型标签（用于人员画像页面显示）
    # professional: 专业测评（EPQ/MBTI/DISC）
    # survey: 问卷调查（scored/survey类型问卷）
    submission_types: Optional[list[str]] = None
    # 性别：男/女
    gender: Optional[str] = None


class CandidateListResponse(SQLModel):
    items: list[CandidateOut]
    page: int
    pageSize: int
    total: int


class PositionBucket(SQLModel):
    name: str
    value: float


class RadarSeries(SQLModel):
    name: str
    value: list[float]


class RadarIndicator(SQLModel):
    name: str
    max: float


class TrendSeries(SQLModel):
    name: str
    data: list[float]


class AnalyticsSummary(SQLModel):
    positionDistribution: list[PositionBucket]
    matchDistribution: list[PositionBucket]
    radarIndicators: list[RadarIndicator]
    radarSeries: list[RadarSeries]
    personalityPie: list[PositionBucket]
    dimensionTrendLabels: list[str]
    dimensionTrendSeries: list[TrendSeries]
    gradeCutoffs: Optional[dict] = None
    totalCandidates: Optional[int] = None
    avgScore: Optional[float] = None
