"""岗位管理 - Pydantic schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ========== 岗位基础模型 ==========

class JobPositionBase(BaseModel):
    """岗位基础信息."""
    name: str
    department: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"


class JobPositionCreate(JobPositionBase):
    """创建岗位."""
    pass


class JobPositionUpdate(BaseModel):
    """更新岗位."""
    name: Optional[str] = None
    department: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class JobPositionResponse(JobPositionBase):
    """岗位响应."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ========== 维度权重模型 ==========

class DimensionWeightBase(BaseModel):
    """维度权重基础."""
    dimension_code: str
    dimension_name: str
    weight: float  # 0-1
    ideal_score: Optional[float] = None
    min_score: Optional[float] = None
    description: Optional[str] = None


class DimensionWeightCreate(DimensionWeightBase):
    """创建维度权重."""
    pass


class DimensionWeightResponse(DimensionWeightBase):
    """维度权重响应."""
    id: int
    job_profile_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== 岗位画像模型 ==========

class JobProfileBase(BaseModel):
    """岗位画像基础."""
    name: str = "默认画像"
    requirement_text: Optional[str] = None


class JobProfileCreate(JobProfileBase):
    """创建岗位画像."""
    job_position_id: int
    dimensions: Optional[List[DimensionWeightCreate]] = None


class JobProfileUpdate(BaseModel):
    """更新岗位画像."""
    name: Optional[str] = None
    requirement_text: Optional[str] = None
    ai_analysis: Optional[dict] = None


class JobProfileResponse(JobProfileBase):
    """岗位画像响应."""
    id: int
    job_position_id: int
    ai_analysis: Optional[dict] = None
    dimensions: List[DimensionWeightResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ========== AI分析相关 ==========

class RequirementAnalysisRequest(BaseModel):
    """需求文案分析请求."""
    requirement_text: str


class RequirementAnalysisResponse(BaseModel):
    """需求文案分析响应."""
    key_abilities: List[dict]  # [{"name": "沟通能力", "importance": "高"}]
    personality_preferences: List[str]  # ["外向型", "高尽责性"]
    experience_requirements: Optional[str] = None
    education_requirements: Optional[str] = None
    summary: str


class DimensionSuggestionRequest(BaseModel):
    """维度权重建议请求."""
    job_position_id: int
    requirement_analysis: Optional[dict] = None


class DimensionSuggestionResponse(BaseModel):
    """维度权重建议响应."""
    dimensions: List[DimensionWeightCreate]
    explanation: str


class CandidateMatchRequest(BaseModel):
    """候选人匹配请求."""
    candidate_id: int


class CandidateMatchResponse(BaseModel):
    """候选人匹配响应."""
    match_score: float  # 0-100
    dimension_scores: List[dict]  # 各维度匹配情况
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    suitable: bool


# ========== 列表和详情 ==========

class JobPositionListResponse(BaseModel):
    """岗位列表响应."""
    items: List[JobPositionResponse]
    total: int


class JobPositionDetailResponse(JobPositionResponse):
    """岗位详情响应（包含画像）."""
    profiles: List[JobProfileResponse] = []

