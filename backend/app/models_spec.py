"""
规范化的数据模型定义（按最新产品规格）：
- Candidate 仅候选人端自动创建
- ResumeSummary / AIProfile 持久化保存
- AssessmentConfig / Session / Questionnaire / Result / JobProfile
说明：暂不替换现有业务模型，后续接口与迁移可基于此文件逐步落地。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Candidate(SQLModel, table=True):
    __tablename__ = "candidates_v2"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    phone: str = Field(index=True)
    email: Optional[str] = None
    applied_position: Optional[str] = None
    extra_info: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    has_resume: bool = Field(default=False)
    resume_file_id: Optional[str] = None
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    latest_assessment_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ResumeSummary(SQLModel, table=True):
    __tablename__ = "resume_summaries"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidates_v2.id", index=True)
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    education: Optional[str] = None
    experiences: Optional[str] = None
    skills: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    highlights: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))


class AssessmentConfig(SQLModel, table=True):
    __tablename__ = "assessment_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    questionnaire_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    job_profile_id: Optional[int] = Field(default=None, foreign_key="job_profiles_v2.id")
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AssessmentSession(SQLModel, table=True):
    __tablename__ = "assessment_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidates_v2.id", index=True)
    config_id: int = Field(foreign_key="assessment_configs.id", index=True)
    status: str = Field(default="in_progress")  # in_progress/completed
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class Questionnaire(SQLModel, table=True):
    __tablename__ = "questionnaires_v2"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    type: str = Field(default="custom")  # builtin/custom
    dimensions: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    questions: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QuestionnaireResult(SQLModel, table=True):
    __tablename__ = "questionnaire_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="assessment_sessions.id", index=True)
    questionnaire_id: int = Field(foreign_key="questionnaires_v2.id", index=True)
    dimension_scores: dict = Field(default_factory=dict, sa_column=Column(JSON))
    overall_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobProfile(SQLModel, table=True):
    __tablename__ = "job_profiles_v2"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    dimensions: list[dict] = Field(default_factory=list, sa_column=Column(JSON))  # [{key, weight}]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AIProfile(SQLModel, table=True):
    __tablename__ = "ai_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidates_v2.id", index=True)
    summary: Optional[str] = None
    highlights: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    risks: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    recommended_positions: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    avoid_positions: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    last_generated_at: datetime = Field(default_factory=datetime.utcnow)
