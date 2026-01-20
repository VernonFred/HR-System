"""简历管理 - API路由."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlmodel import Session
from datetime import datetime

from app.db import get_session
from app.models import Candidate
from app.api.resumes import schemas, storage
from app.api.resumes.extractors import extract_text_from_file, clean_text
from app.api.resumes.parser import parse_resume_with_ai


router = APIRouter(prefix="/api/resumes", tags=["resumes"])


# ========== 单个简历上传 ==========

@router.post("/candidates/{candidate_id}/upload", response_model=schemas.ResumeUploadResponse)
async def upload_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """上传候选人简历（单个）."""
    # 检查候选人是否存在
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    # 如果已有简历，先删除旧文件
    if candidate.resume_file_path:
        storage.delete_resume_file(candidate.resume_file_path)
    
    # 保存新文件
    file_path, original_name, file_size = await storage.save_resume_file(candidate_id, file)
    
    # 更新数据库
    candidate.resume_file_path = file_path
    candidate.resume_original_name = original_name
    candidate.resume_uploaded_at = datetime.utcnow()
    # 重置解析状态和数据
    candidate.resume_text = None
    candidate.resume_parsed_data = None
    
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    
    # ⭐ 不再自动解析，由用户手动点击"开始解析"按钮触发
    # 这样可以让用户看到完整的流程：上传 -> 开始解析 -> 解析完成 -> 生成画像
    
    return schemas.ResumeUploadResponse(
        candidate_id=candidate.id,
        file_name=original_name,
        file_path=file_path,
        file_size=file_size,
        uploaded_at=candidate.resume_uploaded_at,
        parsing_status="pending"  # 上传后始终为 pending，等待用户手动解析
    )


# ========== 批量简历上传 ==========

@router.post("/batch-upload", response_model=schemas.BatchUploadResponse)
async def batch_upload_resumes(
    files: List[UploadFile] = File(...),
    candidate_ids: str = Form(...),  # 逗号分隔的候选人ID列表
    session: Session = Depends(get_session)
):
    """批量上传简历."""
    # 解析候选人ID列表
    try:
        ids = [int(id.strip()) for id in candidate_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="候选人ID格式错误")
    
    if len(files) != len(ids):
        raise HTTPException(
            status_code=400,
            detail=f"文件数量（{len(files)}）与候选人数量（{len(ids)}）不匹配"
        )
    
    results = []
    success_count = 0
    failed_count = 0
    
    for file, candidate_id in zip(files, ids):
        try:
            # 检查候选人
            candidate = session.get(Candidate, candidate_id)
            if not candidate:
                results.append(schemas.BatchUploadItem(
                    file_name=file.filename or "unknown",
                    success=False,
                    error="候选人不存在"
                ))
                failed_count += 1
                continue
            
            # 删除旧文件
            if candidate.resume_file_path:
                storage.delete_resume_file(candidate.resume_file_path)
            
            # 保存新文件
            file_path, original_name, file_size = await storage.save_resume_file(
                candidate_id, file
            )
            
            # 更新数据库
            candidate.resume_file_path = file_path
            candidate.resume_original_name = original_name
            candidate.resume_uploaded_at = datetime.utcnow()
            candidate.resume_text = None
            candidate.resume_parsed_data = None
            
            session.add(candidate)
            session.commit()
            
            results.append(schemas.BatchUploadItem(
                file_name=original_name,
                success=True,
                candidate_id=candidate_id,
                file_path=file_path
            ))
            success_count += 1
            
        except Exception as e:
            results.append(schemas.BatchUploadItem(
                file_name=file.filename or "unknown",
                success=False,
                error=str(e)
            ))
            failed_count += 1
            # 回滚当前候选人的更改
            session.rollback()
    
    return schemas.BatchUploadResponse(
        total=len(files),
        success_count=success_count,
        failed_count=failed_count,
        items=results
    )


# ========== 获取简历信息 ==========

@router.get("/candidates/{candidate_id}", response_model=schemas.ResumeInfoResponse)
async def get_resume_info(
    candidate_id: int,
    session: Session = Depends(get_session)
):
    """获取候选人的简历信息."""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    has_resume = bool(candidate.resume_file_path)
    
    return schemas.ResumeInfoResponse(
        candidate_id=candidate.id,
        has_resume=has_resume,
        file_name=candidate.resume_original_name,
        file_path=candidate.resume_file_path,
        uploaded_at=candidate.resume_uploaded_at,
        parsing_status="pending" if has_resume and not candidate.resume_parsed_data else "completed",
        parsed_data=candidate.resume_parsed_data,
        resume_text=candidate.resume_text
    )


# ========== 下载简历 ==========

@router.get("/candidates/{candidate_id}/download")
async def download_resume(
    candidate_id: int,
    session: Session = Depends(get_session)
):
    """下载候选人的简历文件."""
    candidate = session.get(Candidate, candidate_id)
    if not candidate or not candidate.resume_file_path:
        raise HTTPException(status_code=404, detail="简历文件不存在")
    
    file_path = storage.get_resume_file_path(candidate.resume_file_path)
    if not file_path:
        raise HTTPException(status_code=404, detail="简历文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=candidate.resume_original_name or "resume.pdf",
        media_type="application/octet-stream"
    )


# ========== 删除简历 ==========

@router.delete("/candidates/{candidate_id}")
async def delete_resume(
    candidate_id: int,
    session: Session = Depends(get_session)
):
    """删除候选人的简历."""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    if not candidate.resume_file_path:
        raise HTTPException(status_code=404, detail="该候选人没有简历")
    
    # 删除文件
    storage.delete_resume_file(candidate.resume_file_path)
    
    # 清空数据库记录
    candidate.resume_file_path = None
    candidate.resume_original_name = None
    candidate.resume_text = None
    candidate.resume_parsed_data = None
    candidate.resume_uploaded_at = None
    
    session.add(candidate)
    session.commit()
    
    return {"message": "简历已删除", "candidate_id": candidate_id}


# ========== 简历解析 ==========

from fastapi import Query

@router.post("/candidates/{candidate_id}/parse", response_model=schemas.ResumeParseResponse)
async def parse_resume(
    candidate_id: int,
    analysis_level: str = Query("pro", description="分析级别: pro(深度分析)/expert(专家分析)"),
    session: Session = Depends(get_session)
):
    """
    手动触发简历解析（使用AI模型）.
    
    **分析级别**：
    - pro: 深度分析（Qwen2.5-32B，默认）
    - expert: 专家分析（DeepSeek-R1）
    
    AI会提取简历结构化信息，并进行深度分析：
    - 核心优势识别
    - 职业轨迹分析
    - 工作风格推断
    - 潜在风险识别
    """
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    if not candidate.resume_file_path:
        raise HTTPException(status_code=404, detail="该候选人没有简历")
    
    # 验证分析级别
    if analysis_level not in ("pro", "expert"):
        analysis_level = "pro"
    
    try:
        # 1. 提取文本
        resume_text = extract_text_from_file(candidate.resume_file_path)
        if not resume_text:
            return schemas.ResumeParseResponse(
                candidate_id=candidate_id,
                status="failed",
                message="无法提取简历文本"
            )
        
        # 2. 清洗文本
        clean_resume_text = clean_text(resume_text)
        
        # 3. AI解析（使用指定的分析级别）
        print(f"📄 开始AI解析简历 candidate={candidate_id}, level={analysis_level}")
        parsed_data = await parse_resume_with_ai(clean_resume_text, analysis_level)
        # 如果AI/规则解析未能识别姓名，用候选人信息兜底
        if candidate.name:
            parsed_data.name = candidate.name
        if candidate.email:
            parsed_data.email = candidate.email
        if candidate.phone:
            parsed_data.phone = candidate.phone
        
        # 4. 保存到数据库
        candidate.resume_text = clean_resume_text
        candidate.resume_parsed_data = parsed_data.model_dump()
        
        # ⭐ 如果候选人没有岗位信息，从简历中获取并更新
        if not candidate.position and parsed_data.target_position:
            candidate.position = parsed_data.target_position
            print(f"📄 从简历更新候选人岗位: {parsed_data.target_position}")
        
        # ⭐ 更新候选人的 updated_at 以触发画像缓存失效
        candidate.updated_at = datetime.utcnow()
        
        session.add(candidate)
        session.commit()
        
        return schemas.ResumeParseResponse(
            candidate_id=candidate_id,
            status="success",
            message=f"简历解析成功（{analysis_level}级别）",
            parsed_data=parsed_data
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return schemas.ResumeParseResponse(
            candidate_id=candidate_id,
            status="failed",
            message=f"解析失败：{str(e)}"
        )


@router.post("/auto-parse-after-upload/{candidate_id}")
async def auto_parse_after_upload(
    candidate_id: int,
    session: Session = Depends(get_session)
):
    """上传后自动触发解析（内部调用）."""
    # 这个端点会在上传成功后被调用
    return await parse_resume(candidate_id, session)

