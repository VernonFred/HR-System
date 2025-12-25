"""
AI 路由器 - 多模型分层路由版

支持：
1. 普通画像解读（自动选择 Normal/Pro 级）
2. 专家级深度分析（DeepSeek-R1）
3. 路由状态查询
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.ai.schemas import (
    InterpretationRequest,
    InterpretationResponse,
    MatchRequest,
    MatchResponse,
    ReportRequest,
    ReportResponse,
)
from app.api.ai import service
from app.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])


# =============================================================================
# 新增 Schema
# =============================================================================

class ExpertAnalysisRequest(BaseModel):
    """专家分析请求."""
    summary_json: Dict[str, Any]  # 已有的画像摘要
    scores: Dict[str, Any]        # 测评分数
    job_family: str               # 岗位族
    target_position: str          # 目标岗位


class ExpertAnalysisResponse(BaseModel):
    """专家分析响应."""
    expert_insights: List[Dict[str, Any]] = []
    interview_questions: List[str] = []
    hiring_suggestion: str = ""
    _model: Optional[str] = None
    _level: Optional[str] = None
    _error: Optional[str] = None


class ApiKeyStatusResponse(BaseModel):
    """API Key 状态."""
    available: bool
    expires: Optional[str] = None
    days_remaining: Optional[int] = None
    warning: Optional[str] = None


class RouterStatusResponse(BaseModel):
    """路由状态响应."""
    modelscope_available: bool
    api_key_status: ApiKeyStatusResponse
    models: List[Dict[str, Any]]
    fallback_available: bool
    routing_strategy: str


# =============================================================================
# 端点
# =============================================================================

@router.post("/interpretation", response_model=InterpretationResponse)
async def interpretation(
    payload: InterpretationRequest,
    force_pro: bool = Query(False, description="强制使用 Pro 级分析"),
    _user_id: int = Depends(get_current_user),
):
    """
    AI 画像解读 - 自动选择模型级别.
    
    路由逻辑：
    1. 普通岗位 → Qwen2.5-7B-Instruct
    2. 高级岗位/管理岗 → Qwen2.5-32B-Instruct
    3. force_pro=True → 强制使用 Pro 级
    """
    result = await service.ai_interpretation(payload.model_dump(), force_pro=force_pro)
    return InterpretationResponse(**result)


@router.post("/expert-analysis", response_model=ExpertAnalysisResponse)
async def expert_analysis(
    payload: ExpertAnalysisRequest,
    _user_id: int = Depends(get_current_user),
):
    """
    专家级深度分析 - 使用 DeepSeek-R1.
    
    输入已有的画像摘要，输出：
    - 3 条深度洞察
    - 面试追问建议
    - 是否建议录用的总结
    """
    result = await service.ai_expert_analysis(
        summary_json=payload.summary_json,
        scores=payload.scores,
        job_family=payload.job_family,
        target_position=payload.target_position,
    )
    return ExpertAnalysisResponse(**result)


@router.get("/router-status", response_model=RouterStatusResponse)
async def router_status(_user_id: int = Depends(get_current_user)):
    """
    获取 AI 路由器状态.
    
    返回：
    - ModelScope 是否可用
    - 可用模型列表
    - Fallback 策略
    """
    status = service.get_ai_router_status()
    return RouterStatusResponse(**status)


@router.post("/match", response_model=MatchResponse)
async def match(payload: MatchRequest, _user_id: int = Depends(get_current_user)):
    result = await service.ai_match(payload.model_dump())
    return MatchResponse(**result)


@router.post("/report", response_model=ReportResponse)
async def report(payload: ReportRequest, _user_id: int = Depends(get_current_user)):
    result = await service.ai_report(payload.model_dump())
    return ReportResponse(**result)
