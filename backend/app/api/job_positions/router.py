"""岗位管理 - API路由."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from pathlib import Path
import tempfile

from app.db import get_session
from app.api.job_positions import schemas, service
from app.api.job_positions.jd_extractor import extract_jd_text
from app.api.job_positions.jd_parser import parse_jd_with_ai

router = APIRouter(prefix="/api/job-positions", tags=["job-positions"])


# ========== 岗位管理 ==========

@router.post("", response_model=schemas.JobPositionResponse, status_code=201)
async def create_job_position(
    job_data: schemas.JobPositionCreate,
    session: Session = Depends(get_session)
):
    """创建岗位."""
    return await service.create_job_position(session, job_data)


@router.get("", response_model=schemas.JobPositionListResponse)
async def get_job_positions(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """获取岗位列表."""
    jobs, total = await service.get_job_positions(session, skip, limit)
    return schemas.JobPositionListResponse(items=jobs, total=total)


@router.get("/{job_id}", response_model=schemas.JobPositionDetailResponse)
async def get_job_position(
    job_id: int,
    session: Session = Depends(get_session)
):
    """获取岗位详情（包含画像列表）."""
    job = await service.get_job_position(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")
    
    # 获取该岗位的所有画像
    profiles = await service.get_job_profiles_by_position(session, job_id)
    
    # 转换为响应模型
    return schemas.JobPositionDetailResponse(
        **job.model_dump(),
        profiles=profiles
    )


@router.put("/{job_id}", response_model=schemas.JobPositionResponse)
async def update_job_position(
    job_id: int,
    job_data: schemas.JobPositionUpdate,
    session: Session = Depends(get_session)
):
    """更新岗位."""
    job = await service.update_job_position(session, job_id, job_data)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job_position(
    job_id: int,
    session: Session = Depends(get_session)
):
    """删除岗位."""
    success = await service.delete_job_position(session, job_id)
    if not success:
        raise HTTPException(status_code=404, detail="岗位不存在")


# ========== 岗位画像管理 ==========

@router.post("/profiles", response_model=schemas.JobProfileResponse, status_code=201)
async def create_job_profile(
    profile_data: schemas.JobProfileCreate,
    session: Session = Depends(get_session)
):
    """创建岗位画像."""
    return await service.create_job_profile(session, profile_data)


@router.get("/profiles/{profile_id}", response_model=schemas.JobProfileResponse)
async def get_job_profile(
    profile_id: int,
    session: Session = Depends(get_session)
):
    """获取岗位画像详情."""
    profile = await service.get_job_profile(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="岗位画像不存在")
    return profile


@router.put("/profiles/{profile_id}", response_model=schemas.JobProfileResponse)
async def update_job_profile(
    profile_id: int,
    profile_data: schemas.JobProfileUpdate,
    session: Session = Depends(get_session)
):
    """更新岗位画像基本信息."""
    profile = await service.update_job_profile(session, profile_id, profile_data)
    if not profile:
        raise HTTPException(status_code=404, detail="岗位画像不存在")
    return profile


@router.put("/profiles/{profile_id}/dimensions", response_model=List[schemas.DimensionWeightResponse])
async def update_dimension_weights(
    profile_id: int,
    dimensions: List[schemas.DimensionWeightCreate],
    session: Session = Depends(get_session)
):
    """更新岗位画像的维度权重配置."""
    return await service.update_dimension_weights(session, profile_id, dimensions)


# ========== AI功能 ==========

@router.post("/analyze-requirement", response_model=schemas.RequirementAnalysisResponse)
async def analyze_requirement(
    request: schemas.RequirementAnalysisRequest
):
    """分析岗位需求文案（AI）."""
    return await service.analyze_requirement(request.requirement_text)


@router.post("/{job_id}/suggest-dimensions", response_model=schemas.DimensionSuggestionResponse)
async def suggest_dimensions(
    job_id: int,
    request: schemas.DimensionSuggestionRequest,
    session: Session = Depends(get_session)
):
    """AI建议维度权重配置."""
    return await service.suggest_dimensions(
        session,
        job_id,
        request.requirement_analysis
    )


@router.post("/profiles/{profile_id}/match/{candidate_id}", response_model=schemas.CandidateMatchResponse)
async def match_candidate(
    profile_id: int,
    candidate_id: int,
    session: Session = Depends(get_session)
):
    """计算候选人与岗位的匹配度."""
    return await service.match_candidate(session, profile_id, candidate_id)


# ========== JD文件上传与解析 ==========

@router.post("/upload-jd")
async def upload_and_parse_jd(
    file: UploadFile = File(...)
):
    """
    上传JD文件并AI解析。
    
    支持格式: PDF, Word (.doc/.docx), TXT
    """
    # 验证文件格式
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
    file_ext = Path(file.filename or '').suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持: {', '.join(allowed_extensions)}"
        )
    
    # 保存到临时文件
    temp_file = None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tf:
            temp_file = tf.name
            content = await file.read()
            tf.write(content)
        
        # 提取文本
        jd_text = extract_jd_text(temp_file)
        
        if not jd_text or len(jd_text) < 20:
            raise HTTPException(
                status_code=400,
                detail="无法从文件中提取有效内容，请检查文件"
            )
        
        # AI解析
        parsed_data = await parse_jd_with_ai(jd_text)
        
        return {
            "success": True,
            "jd_text": jd_text[:500] + "..." if len(jd_text) > 500 else jd_text,  # 返回摘要
            "parsed_data": parsed_data,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
    
    finally:
        # 清理临时文件
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()


