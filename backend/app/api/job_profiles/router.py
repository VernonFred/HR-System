"""岗位画像API路由."""

from __future__ import annotations
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from . import schemas, service, ai_helper
from app.api.resumes.extractors import extract_text_from_file, clean_text
from app.api.resumes import storage
import tempfile
import os

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
    "/",
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
    "/",
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


# ========== Phase 5: AI辅助功能 ==========

@router.post(
    "/analyze-resume",
    response_model=schemas.JobProfileCreate,
    summary="AI分析简历生成岗位画像建议"
)
async def analyze_resume_for_profile(
    file: UploadFile = File(...),
    job_title: str = Query(..., description="岗位名称"),
    department: Optional[str] = Query(None, description="部门名称"),
):
    """上传优秀员工简历，AI分析生成岗位画像配置建议.
    
    功能定位：
    - 仅作为辅助工具，不存储简历文件
    - 临时解析后即删除
    - 返回岗位画像配置建议
    
    流程：
    1. 上传简历文件（临时）
    2. 提取文本内容
    3. AI分析生成能力维度
    4. 返回配置建议
    5. 删除临时文件
    """
    temp_file_path = None
    try:
        # 1. 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # 2. 提取文本
        resume_text = extract_text_from_file(temp_file_path)
        if not resume_text:
            raise HTTPException(
                status_code=400,
                detail="无法提取简历文本，请确保文件格式正确（支持PDF/DOC/DOCX）"
            )
        
        # 3. 清洗文本
        clean_resume_text = clean_text(resume_text)
        
        # 4. AI分析
        result = await ai_helper.analyze_resume_for_job_profile(
            resume_text=clean_resume_text,
            job_title=job_title,
            department=department
        )
        
        # 5. 转换为 JobProfileCreate 格式
        profile_suggestion = schemas.JobProfileCreate(
            name=result["name"],
            department=result["department"],
            description=result["description"],
            tags=result["tags"],
            dimensions=[
                schemas.DimensionBase(
                    name=d["name"],
                    weight=d["weight"],
                    description=d.get("description", "")
                )
                for d in result["dimensions"]
            ]
        )
        
        return profile_suggestion
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI分析失败: {str(e)}"
        )
    finally:
        # 6. 删除临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning("删除临时文件失败: %s", e)


@router.post(
    "/analyze-resumes",
    response_model=schemas.JobProfileCreate,
    summary="AI分析多份简历生成岗位画像建议"
)
async def analyze_multiple_resumes_for_profile(
    files: list[UploadFile] = File(...),
    job_title: str = Query(..., description="岗位名称"),
    department: Optional[str] = Query(None, description="部门名称"),
):
    """上传多份优秀员工简历，AI分析共性特征生成岗位画像配置建议.
    
    功能定位：
    - 分析多份简历的共性特征
    - 提取岗位核心能力要求
    - 智能分配能力维度权重
    """
    temp_files = []
    resume_texts = []
    
    try:
        # 1. 处理所有上传的文件
        for file in files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_files.append(temp_file.name)
        
        # 2. 提取所有简历文本
        for temp_path in temp_files:
            text = extract_text_from_file(temp_path)
            if text:
                resume_texts.append(clean_text(text))
        
        if not resume_texts:
            raise HTTPException(
                status_code=400,
                detail="无法提取任何简历文本，请确保文件格式正确（支持PDF/DOC/DOCX）"
            )
        
        # 3. 合并简历文本进行分析
        combined_text = "\n\n---简历分隔---\n\n".join(resume_texts)
        analysis_prompt = f"以下是{len(resume_texts)}份优秀员工的简历，请分析他们的共性特征：\n\n{combined_text}"
        
        # 4. AI分析
        result = await ai_helper.analyze_resume_for_job_profile(
            resume_text=analysis_prompt,
            job_title=job_title,
            department=department
        )
        
        # 5. 转换为 JobProfileCreate 格式
        profile_suggestion = schemas.JobProfileCreate(
            name=result["name"],
            department=result["department"],
            description=result["description"] + f"（基于{len(resume_texts)}份优秀员工简历分析）",
            tags=result["tags"],
            dimensions=[
                schemas.DimensionBase(
                    name=d["name"],
                    weight=d["weight"],
                    description=d.get("description", "")
                )
                for d in result["dimensions"]
            ]
        )
        
        return profile_suggestion
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("多简历分析失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI分析失败: {str(e)}"
        )
    finally:
        # 6. 删除所有临时文件
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning("删除临时文件失败: %s", e)


class JDAnalysisRequest(BaseModel):
    """JD分析请求体."""
    jd_text: str


class DimensionConfigRequest(BaseModel):
    """能力维度配置请求体."""
    job_title: str
    description: Optional[str] = ""
    existing_dimensions: Optional[list] = []


class DimensionConfigResponse(BaseModel):
    """能力维度配置响应."""
    dimensions: list
    analysis: str


@router.post(
    "/ai-configure-dimensions",
    response_model=DimensionConfigResponse,
    summary="AI智能配置能力维度权重"
)
async def ai_configure_dimensions(
    request: DimensionConfigRequest,
):
    """AI智能配置能力维度和权重.
    
    功能：
    1. 如果已有维度，AI根据岗位特点智能分配权重
    2. 如果没有维度，AI根据岗位名称生成完整的维度配置
    """
    try:
        result = await ai_helper.configure_job_dimensions(
            job_title=request.job_title,
            description=request.description,
            existing_dimensions=request.existing_dimensions
        )
        
        return DimensionConfigResponse(
            dimensions=result["dimensions"],
            analysis=result.get("analysis", "AI配置完成")
        )
        
    except Exception as e:
        logger.error("AI配置维度失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI配置失败: {str(e)}"
        )


@router.post(
    "/analyze-jd",
    response_model=schemas.JobProfileCreate,
    summary="AI分析JD生成岗位画像建议"
)
async def analyze_jd_for_profile(
    job_title: str = Query(..., description="岗位名称"),
    department: Optional[str] = Query(None, description="部门名称"),
    body: Optional[JDAnalysisRequest] = None,
    jd_text: Optional[str] = Query(None, description="JD文本内容（兼容旧版）"),
):
    """分析JD文本，AI生成岗位画像配置建议.
    
    功能定位：
    - 辅助HR快速配置岗位画像
    - 基于JD文本分析
    - 不存储JD数据
    
    支持两种方式传递JD文本：
    1. POST body: {"jd_text": "..."}（推荐，适合长文本）
    2. Query参数: ?jd_text=...（兼容旧版）
    """
    # 优先使用 body 中的 jd_text，其次使用 query 参数
    actual_jd_text = (body.jd_text if body else None) or jd_text
    
    if not actual_jd_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少JD文本内容"
        )
    
    try:
        result = await ai_helper.analyze_jd_for_job_profile(
            jd_text=actual_jd_text,
            job_title=job_title,
            department=department
        )
        
        profile_suggestion = schemas.JobProfileCreate(
            name=result["name"],
            department=result["department"],
            description=result["description"],
            tags=result["tags"],
            dimensions=[
                schemas.DimensionBase(
                    name=d["name"],
                    weight=d["weight"],
                    description=d.get("description", "")
                )
                for d in result["dimensions"]
            ]
        )
        
        return profile_suggestion
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI分析失败: {str(e)}"
        )

