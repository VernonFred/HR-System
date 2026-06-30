"""岗位画像API路由."""

from __future__ import annotations
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.db import get_session
from . import schemas, service

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/job-profiles", tags=["job-profiles"])


def _format_profile_response(profile) -> dict:
    """格式化岗位画像响应.
    
    Args:
        profile: JobProfile模型实例
        
    Returns:
        格式化的字典
    """
    return {
        "id": profile.id,
        "name": profile.name,
        "department": profile.department,
        "description": profile.description,
        "tags": json.loads(profile.tags) if profile.tags else [],
        "dimensions": json.loads(profile.dimensions) if profile.dimensions else [],
        "status": profile.status,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }


@router.post(
    "",
    response_model=schemas.JobProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建岗位画像"
)
async def create_job_profile(
    data: schemas.JobProfileCreate,
    session: Session = Depends(get_session)
):
    """创建新的岗位画像.
    
    - **name**: 岗位名称（必填）
    - **department**: 所属部门（可选）
    - **description**: 岗位说明（可选）
    - **tags**: 标签列表（可选）
    - **dimensions**: 能力维度列表（必填，权重总和必须为100）
    """
    try:
        profile = await service.create_job_profile(session, data)
        return _format_profile_response(profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建岗位画像失败: {str(e)}"
        )


@router.get(
    "",
    response_model=schemas.JobProfileListResponse,
    summary="获取岗位画像列表"
)
async def get_job_profiles(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=100, description="限制数量"),
    department: Optional[str] = Query(None, description="按部门过滤"),
    status_filter: Optional[str] = Query(None, description="按状态过滤"),
    session: Session = Depends(get_session)
):
    """获取岗位画像列表.
    
    支持分页和过滤：
    - **skip**: 跳过的数量（用于分页）
    - **limit**: 返回的最大数量
    - **department**: 按部门过滤
    - **status_filter**: 按状态过滤（active/inactive）
    """
    try:
        profiles, total = await service.get_job_profiles(
            session, skip, limit, department, status_filter
        )
        items = [_format_profile_response(p) for p in profiles]
        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取岗位画像列表失败: {str(e)}"
        )


@router.get(
    "/{profile_id}",
    response_model=schemas.JobProfileResponse,
    summary="获取单个岗位画像"
)
async def get_job_profile(
    profile_id: int,
    session: Session = Depends(get_session)
):
    """获取指定ID的岗位画像详情."""
    profile = await service.get_job_profile(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="岗位画像不存在"
        )
    return _format_profile_response(profile)


@router.put(
    "/{profile_id}",
    response_model=schemas.JobProfileResponse,
    summary="更新岗位画像"
)
async def update_job_profile(
    profile_id: int,
    data: schemas.JobProfileUpdate,
    session: Session = Depends(get_session)
):
    """更新指定ID的岗位画像.
    
    只需要提供要更新的字段，未提供的字段保持不变。
    """
    try:
        profile = await service.update_job_profile(session, profile_id, data)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="岗位画像不存在"
            )
        return _format_profile_response(profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新岗位画像失败: {str(e)}"
        )


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除岗位画像"
)
async def delete_job_profile(
    profile_id: int,
    session: Session = Depends(get_session)
):
    """删除指定ID的岗位画像.
    
    注意：删除画像会同时删除所有相关的匹配记录。
    """
    success = await service.delete_job_profile(session, profile_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="岗位画像不存在"
        )
    return None


@router.post(
    "/{profile_id}/match",
    response_model=schemas.MatchCandidatesResponse,
    summary="匹配候选人"
)
async def match_candidates(
    profile_id: int,
    request: schemas.MatchCandidatesRequest = schemas.MatchCandidatesRequest(),
    session: Session = Depends(get_session)
):
    """为岗位画像匹配候选人.
    
    系统会自动计算所有提交记录与该岗位画像的匹配度，
    并返回匹配度最高的候选人列表。
    
    - **min_score**: 最低匹配分数（可选）
    - **limit**: 返回数量限制（默认20）
    """
    try:
        matches = await service.match_candidates_to_profile(
            session,
            profile_id,
            request.min_score,
            request.limit
        )
        
        if not matches and not await service.get_job_profile(session, profile_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="岗位画像不存在"
            )
        
        return {
            "matches": matches,
            "total": len(matches)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"匹配候选人失败: {str(e)}"
        )


@router.get(
    "/{profile_id}/matches",
    response_model=schemas.MatchCandidatesResponse,
    summary="获取匹配记录"
)
async def get_profile_matches(
    profile_id: int,
    min_score: Optional[float] = Query(None, ge=0, le=100, description="最低匹配分数"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    session: Session = Depends(get_session)
):
    """获取岗位画像的已有匹配记录.
    
    返回之前计算过的匹配结果，不会重新计算。
    """
    try:
        # 检查画像是否存在
        profile = await service.get_job_profile(session, profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="岗位画像不存在"
            )
        
        matches = await service.get_profile_matches(
            session,
            profile_id,
            min_score,
            limit
        )
        
        return {
            "matches": matches,
            "total": len(matches)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取匹配记录失败: {str(e)}"
        )

from app.api.job_profiles.ai_router import router as ai_router
router.include_router(ai_router)
