from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Column, DateTime, func
from sqlmodel import Field, SQLModel
from datetime import datetime


class User(SQLModel, table=True):
    """用户表（简化版，用于鉴权占位）."""

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="user")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class Questionnaire(SQLModel, table=True):
    """问卷定义表."""

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    full_name: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    dimension_names: Optional[dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    dimension_descriptions: Optional[dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    answer_type: Optional[str] = None
    question_count: Optional[int] = None
    estimated_time: Optional[int] = None
    extra: Optional[dict] = Field(default=None, sa_column=Column(JSON))

class Question(SQLModel, table=True):
    """问卷题目表，payload 兼容不同题型."""

    id: Optional[int] = Field(default=None, primary_key=True)
    questionnaire_id: int = Field(foreign_key="questionnaire.id", index=True)
    order: int
    text: str
    dimension: Optional[str] = None
    answer_type: Optional[str] = None
    payload: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    positive: Optional[bool] = None


class Submission(SQLModel, table=True):
    """提交记录（简化版，后续可扩展用户/候选人关联）."""

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_code: str = Field(index=True, unique=True)
    questionnaire_id: int = Field(foreign_key="questionnaire.id", index=True)
    total_score: float = 0
    summary: Optional[str] = None
    result_details: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # 完整的测评结果（MBTI/DISC/EPQ维度等）
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class SubmissionAnswer(SQLModel, table=True):
    """提交答案表."""

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id", index=True)
    question_id: int = Field(foreign_key="question.id", index=True)
    value: str
    score: float = 0


class JobPosition(SQLModel, table=True):
    """岗位表 - 基本岗位信息."""
    __tablename__ = "job_positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # 岗位名称，如"产品经理"
    department: Optional[str] = None  # 部门
    level: Optional[str] = None  # 级别：初级/中级/高级/专家
    description: Optional[str] = None  # 岗位描述
    status: str = Field(default="active")  # 状态：active/closed
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )


class JobProfile(SQLModel, table=True):
    """岗位画像配置表 - 存储岗位的画像配置（支持独立使用和关联岗位两种模式）."""
    __tablename__ = "job_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 基本信息（独立模式）
    name: str = Field(index=True)  # 岗位名称，如"产品经理"
    department: Optional[str] = None  # 所属部门
    description: Optional[str] = None  # 岗位说明
    tags: Optional[str] = None  # 标签，JSON数组格式
    
    # 能力维度配置
    dimensions: Optional[str] = None  # 能力维度，JSON数组格式，包含name/weight/description
    
    # 可选：关联岗位表（用于更复杂的场景）
    job_position_id: Optional[int] = Field(default=None, foreign_key="job_positions.id", index=True)
    
    # JD解析相关
    requirement_text: Optional[str] = None  # 导入的岗位需求文案
    ai_analysis: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # AI分析结果
    
    # 状态
    status: str = Field(default="active")  # active/inactive
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )


class JobDimensionWeight(SQLModel, table=True):
    """岗位维度权重配置表 - 存储各维度的权重和期望值."""
    __tablename__ = "job_dimension_weights"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_profile_id: int = Field(foreign_key="job_profiles.id", index=True)
    dimension_code: str  # 维度代码，如"E"(外向性)
    dimension_name: str  # 维度名称，如"外向性"
    weight: float = Field(default=0.0)  # 权重 0-1
    ideal_score: Optional[float] = None  # 理想分数
    min_score: Optional[float] = None  # 最低分数
    description: Optional[str] = None  # 维度说明
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class ProfileMatch(SQLModel, table=True):
    """岗位画像匹配记录表 - 存储候选人与岗位的匹配结果."""
    __tablename__ = "profile_matches"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="job_profiles.id", index=True)  # 岗位画像ID
    submission_id: int = Field(foreign_key="submission.id", index=True)  # 提交记录ID
    match_score: float = Field(default=0.0)  # 匹配分数 (0-100)
    dimension_scores: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # 各维度得分
    ai_analysis: Optional[str] = None  # AI分析报告
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class PortraitCache(SQLModel, table=True):
    """候选人画像缓存表 - 存储AI分析结果，避免重复调用.
    
    V38更新：支持按 analysis_level 分别缓存，同一候选人可有多条缓存（pro/expert）
    """
    __tablename__ = "portrait_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(index=True)  # 候选人ID
    analysis_level: str = Field(default="pro", index=True)  # 分析级别: pro/expert
    portrait_data: Optional[str] = None  # JSON格式的完整画像数据
    data_version: str = Field(default="")  # 数据版本标识（用于失效判断）
    ai_model: Optional[str] = None  # 使用的AI模型
    generation_time_ms: Optional[int] = None  # AI生成耗时（毫秒）
    is_default: bool = Field(default=False)  # 是否为默认分析（AI超时时使用）
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )
    
    # 注意：candidate_id + analysis_level 组合唯一


class Candidate(SQLModel, table=True):
    """候选人表 - 扩展以支持简历."""
    __tablename__ = "candidates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None  # V45: 性别
    position: Optional[str] = None  # 应聘岗位
    
    # 简历相关字段
    resume_file_path: Optional[str] = None  # 简历文件路径
    resume_original_name: Optional[str] = None  # 原始文件名
    resume_text: Optional[str] = None  # 简历文本内容（提取的）
    resume_parsed_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # AI解析的结构化数据
    resume_uploaded_at: Optional[datetime] = None  # 简历上传时间
    
    # 测评相关
    submission_id: Optional[int] = Field(default=None, foreign_key="submission.id")
    
    # 其他信息
    status: str = Field(default="new")  # 状态：new/screening/interviewing/hired/rejected
    notes: Optional[str] = None  # 备注
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )
