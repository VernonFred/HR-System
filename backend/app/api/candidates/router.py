"""候选人画像API路由."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session
from typing import Optional

from app.db import get_session
from . import schemas, service
from .cache_manager import get_available_analysis_levels, compute_data_version
from app.models import Candidate
from app.models_assessment import Submission


router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get(
    "/{candidate_id}/portrait",
    response_model=schemas.CandidatePortrait,
    summary="获取候选人完整画像"
)
async def get_candidate_portrait(
    candidate_id: int,
    refresh: bool = Query(False, description="强制刷新（跳过缓存）"),
    analysis_level: str = Query("pro", description="分析级别: pro(深度分析，默认)/expert(专家分析)"),
    session: Session = Depends(get_session)
):
    """获取候选人的完整画像数据.
    
    整合以下信息：
    - 基本信息（姓名、电话、应聘岗位等）
    - 测评记录（所有已完成的测评）
    - 岗位匹配（基于 target_position 关联岗位画像）
    - 综合评价（优势、建议、综合得分）
    
    **分析级别 V5**：
    - pro: 深度分析（Qwen2.5-32B，默认，交叉分析测评与简历）
    - expert: 专家分析（DeepSeek-R1，专家级推理与发展建议）
    
    **缓存策略**：
    - 首次访问：调用AI分析，结果存入缓存
    - 再次访问：直接返回缓存数据（毫秒级响应）
    - 数据变更：自动失效缓存，重新分析
    - refresh=true：强制重新分析（跳过缓存）
    
    **数据来源**：
    1. Candidate 表 - 基本信息
    2. Submission 表 - 测评记录（通过 candidate_id 关联）
    3. JobProfile 表 - 岗位画像（通过 target_position 匹配）
    4. ProfileMatch 表 - 匹配记录和得分
    5. PortraitCache 表 - 画像缓存
    """
    try:
        portrait = await service.build_candidate_portrait(
            session, 
            candidate_id,
            force_refresh=refresh,
            analysis_level=analysis_level
        )
        return portrait
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成候选人画像失败: {str(e)}"
        )


@router.get(
    "/portraits",
    response_model=schemas.CandidatePortraitListResponse,
    summary="获取候选人画像列表"
)
async def get_candidate_portraits(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=100, description="限制数量"),
    target_position: Optional[str] = Query(None, description="按应聘岗位过滤"),
    session: Session = Depends(get_session)
):
    """获取候选人画像摘要列表.
    
    支持分页和过滤：
    - **skip**: 跳过的数量（用于分页）
    - **limit**: 返回的最大数量
    - **target_position**: 按应聘岗位过滤
    
    返回简化的画像摘要，包含关键指标。
    """
    try:
        summaries, total = await service.get_candidate_portraits_summary(
            session, skip, limit, target_position
        )
        return {
            "items": summaries,
            "total": total
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取候选人画像列表失败: {str(e)}"
        )


@router.get(
    "/{candidate_id}/portrait-cache-status",
    summary="获取候选人画像缓存状态"
)
async def get_portrait_cache_status(
    candidate_id: int,
    session: Session = Depends(get_session)
):
    """获取候选人已缓存的画像分析级别.
    
    返回每个分析级别是否有有效缓存：
    - pro: 深度分析缓存
    - expert: 专家分析缓存
    
    用于前端切换查看时判断是否需要重新生成。
    """
    from sqlmodel import select
    
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    # 获取最新测评
    latest_submission = session.exec(
        select(Submission)
        .where(Submission.candidate_id == candidate_id)
        .order_by(Submission.submitted_at.desc())
    ).first()
    
    # 计算当前数据版本
    current_version = compute_data_version(candidate, latest_submission, None)
    
    # 获取已缓存的级别
    cache_status = get_available_analysis_levels(session, candidate_id, current_version)
    
    return {
        "candidate_id": candidate_id,
        "data_version": current_version,
        "cached_levels": cache_status
    }
