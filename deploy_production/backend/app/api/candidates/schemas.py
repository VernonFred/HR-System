"""候选人画像 - Pydantic Schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ========== 候选人画像响应 ==========

class DimensionScore(BaseModel):
    """能力维度得分."""
    name: str
    score: float = Field(ge=0, le=100, description="得分 0-100")
    weight: float = Field(ge=0, le=100, description="权重 0-100")
    description: Optional[str] = None
    weighted_score: float = Field(ge=0, le=100, description="加权得分")


class JobMatchInfo(BaseModel):
    """岗位匹配信息."""
    profile_id: int
    profile_name: str
    department: Optional[str] = None
    match_score: float = Field(ge=0, le=100, description="匹配分数")
    dimension_scores: List[DimensionScore]
    ai_analysis: Optional[str] = None
    matched_at: Optional[datetime] = None


class AssessmentInfo(BaseModel):
    """测评信息."""
    submission_id: int
    assessment_name: str
    questionnaire_name: str
    questionnaire_type: Optional[str] = None  # 问卷类型：EPQ/DISC/MBTI/CUSTOM等
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    score_percentage: Optional[float] = None
    grade: Optional[str] = None
    completed_at: Optional[datetime] = None
    personality_dimensions: Optional[List[Dict[str, Any]]] = None  # 该测评的人格维度数据


class CandidateBasicInfo(BaseModel):
    """候选人基本信息."""
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    gender: Optional[str] = None
    target_position: Optional[str] = None
    created_at: datetime


class PersonalityDimension(BaseModel):
    """人格特征维度."""
    key: str  # E, N, P, L 等
    label: str  # 外向性, 神经质 等
    score: float = Field(ge=0, le=100, description="得分 0-100")
    description: Optional[str] = None


class CompetencyScore(BaseModel):
    """岗位胜任力评分."""
    key: Optional[str] = None  # product_planning, user_insight 等
    label: str  # 产品规划能力, 用户洞察力 等
    score: float = Field(ge=0, le=100, description="得分 0-100")
    rationale: Optional[str] = Field(None, description="评分依据")


class TraitScore(BaseModel):
    """特质分数（来自不同测评）."""
    source: str = Field(description="测评类型: MBTI/EPQ/DISC")
    value: float = Field(description="分数值 0-100")


class TraitConsistencyCheck(BaseModel):
    """特质一致性检查."""
    trait: str = Field(description="特质名称，如：外向性、情绪稳定性")
    scores: List[TraitScore] = Field(description="各测评的分数")
    mean: float = Field(description="平均分")
    stdDev: float = Field(description="标准差，衡量离散程度")
    consistency: float = Field(ge=0, le=100, description="一致性得分 0-100")


class Contradiction(BaseModel):
    """测评矛盾点."""
    trait: str = Field(description="矛盾的特质")
    scores: List[float] = Field(description="冲突的分数列表")
    issue: str = Field(description="矛盾描述")


class CrossValidationData(BaseModel):
    """交叉验证数据（P1-1功能）."""
    consistency_score: float = Field(ge=0, le=100, description="整体一致性得分 0-100")
    confidence_level: str = Field(description="置信度等级：高/中/低")
    assessment_count: int = Field(ge=0, description="已完成测评数量")
    consistency_checks: List[TraitConsistencyCheck] = Field(default_factory=list, description="各维度一致性检查")
    contradictions: List[Contradiction] = Field(default_factory=list, description="矛盾点列表")


class CandidatePortrait(BaseModel):
    """候选人完整画像."""
    
    # 基本信息
    basic_info: CandidateBasicInfo
    
    # 测评信息
    assessments: List[AssessmentInfo]
    
    # 岗位匹配
    job_match: Optional[JobMatchInfo] = None
    
    # 综合评价
    overall_score: Optional[float] = Field(None, ge=0, le=100, description="综合得分")
    strengths: List[str] = Field(default_factory=list, description="优势亮点")
    improvements: List[str] = Field(default_factory=list, description="改进建议")
    
    # AI分析内容
    personality_dimensions: List[PersonalityDimension] = Field(default_factory=list, description="人格特征分布")
    competencies: List[CompetencyScore] = Field(default_factory=list, description="岗位胜任力（5-6个核心维度）")
    suitable_positions: List[str] = Field(default_factory=list, description="推荐岗位")
    unsuitable_positions: List[str] = Field(default_factory=list, description="不推荐岗位")
    ai_summary: Optional[str] = Field(None, description="AI综合评价")
    ai_summary_points: List[str] = Field(default_factory=list, description="AI综合评价要点（3条）")
    quick_tags: List[str] = Field(default_factory=list, description="快速标签（2-4字，用于头部展示）")
    
    # 🟢 P1-1: 交叉验证数据
    cross_validation: Optional[CrossValidationData] = Field(None, description="多测评交叉验证结果")
    
    # 🟢 P1-2: 降级标识
    is_fallback_analysis: bool = Field(default=False, description="是否为降级分析 (规则引擎生成)")
    analysis_method: str = Field(default="ai", description="分析方式: ai | fallback")
    fallback_reason: Optional[str] = Field(None, description="降级原因: ai_timeout | ai_error | ai_unavailable")
    
    # 元数据
    portrait_version: str = "1.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ========== 批量画像响应 ==========

class CandidatePortraitSummary(BaseModel):
    """候选人画像摘要（用于列表）."""
    candidate_id: int
    name: str
    target_position: Optional[str] = None
    overall_score: Optional[float] = None
    match_score: Optional[float] = None
    assessment_count: int
    has_job_match: bool


class CandidatePortraitListResponse(BaseModel):
    """候选人画像列表响应."""
    items: List[CandidatePortraitSummary]
    total: int

