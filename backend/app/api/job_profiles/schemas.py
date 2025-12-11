"""岗位画像相关的Pydantic Schemas."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class DimensionBase(BaseModel):
    """能力维度基础模型."""
    
    name: str = Field(..., description="维度名称")
    weight: float = Field(..., ge=0, le=100, description="权重（0-100）")
    description: Optional[str] = Field(None, description="维度说明")
    
    class Config:
        from_attributes = True


class JobProfileCreate(BaseModel):
    """创建岗位画像."""
    
    name: str = Field(..., min_length=1, max_length=100, description="岗位名称")
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    description: Optional[str] = Field(None, description="岗位说明")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    dimensions: list[DimensionBase] = Field(..., min_items=1, description="能力维度列表")
    
    @validator("dimensions")
    def validate_dimensions_weight(cls, v):
        """验证维度权重总和为100."""
        total_weight = sum(dim.weight for dim in v)
        if not (99.99 <= total_weight <= 100.01):  # 允许浮点误差
            raise ValueError(f"维度权重总和必须为100，当前为{total_weight}")
        return v
    
    class Config:
        from_attributes = True


class JobProfileUpdate(BaseModel):
    """更新岗位画像."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="岗位名称")
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    description: Optional[str] = Field(None, description="岗位说明")
    tags: Optional[list[str]] = Field(None, description="标签列表")
    dimensions: Optional[list[DimensionBase]] = Field(None, min_items=1, description="能力维度列表")
    status: Optional[str] = Field(None, description="状态")
    
    @validator("dimensions")
    def validate_dimensions_weight(cls, v):
        """验证维度权重总和为100."""
        if v is not None:
            total_weight = sum(dim.weight for dim in v)
            if not (99.99 <= total_weight <= 100.01):
                raise ValueError(f"维度权重总和必须为100，当前为{total_weight}")
        return v
    
    class Config:
        from_attributes = True


class JobProfileResponse(BaseModel):
    """岗位画像响应."""
    
    id: int
    name: str
    department: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    dimensions: list[DimensionBase]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class JobProfileListResponse(BaseModel):
    """岗位画像列表响应."""
    
    items: list[JobProfileResponse]
    total: int
    skip: int = 0
    limit: int = 100
    
    class Config:
        from_attributes = True


class ProfileMatchCreate(BaseModel):
    """创建匹配记录（通常由系统自动创建）."""
    
    profile_id: int = Field(..., description="岗位画像ID")
    submission_id: int = Field(..., description="提交记录ID")
    match_score: float = Field(..., ge=0, le=100, description="匹配分数")
    dimension_scores: Optional[dict] = Field(None, description="各维度得分")
    ai_analysis: Optional[str] = Field(None, description="AI分析报告")
    
    class Config:
        from_attributes = True


class ProfileMatchResponse(BaseModel):
    """匹配记录响应."""
    
    id: int
    profile_id: int
    submission_id: int
    match_score: float
    dimension_scores: Optional[dict] = None
    ai_analysis: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MatchCandidatesRequest(BaseModel):
    """匹配候选人请求."""
    
    min_score: Optional[float] = Field(None, ge=0, le=100, description="最低匹配分数")
    limit: int = Field(20, ge=1, le=100, description="返回数量限制")
    
    class Config:
        from_attributes = True


class MatchCandidatesResponse(BaseModel):
    """匹配候选人响应."""
    
    matches: list[ProfileMatchResponse]
    total: int
    
    class Config:
        from_attributes = True

