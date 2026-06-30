"""问卷/测评管理 - API路由."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlmodel import Session

from app.db import get_session
from app.api.assessments import schemas, service
from app.api.assessments.questionnaire_parser import parse_questionnaire_file, parse_questionnaire_file_async
from app.models_assessment import Questionnaire

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


# ========== 问卷管理 ==========

@router.get("/questionnaires", response_model=schemas.QuestionnaireListResponse)
async def get_questionnaires(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = Query(None, description="问卷分类: professional/scored/survey"),
    session: Session = Depends(get_session)
):
    """获取问卷列表，支持按category过滤."""
    questionnaires, total = await service.get_questionnaires(session, skip, limit, category=category)
    return schemas.QuestionnaireListResponse(items=questionnaires, total=total)


@router.get("/questionnaires/{questionnaire_id}", response_model=schemas.QuestionnaireDetailResponse)
async def get_questionnaire(
    questionnaire_id: int,
    session: Session = Depends(get_session)
):
    """获取问卷详情."""
    questionnaire = await service.get_questionnaire(session, questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return questionnaire


@router.post("/questionnaires", response_model=schemas.QuestionnaireResponse, status_code=201)
async def create_questionnaire(
    data: schemas.QuestionnaireCreate,
    session: Session = Depends(get_session)
):
    """创建问卷."""
    questionnaire = await service.create_questionnaire(session, data.model_dump())
    return questionnaire


# ⭐ V43: 导入问卷（V45: 支持AI智能解析）
@router.post("/questionnaires/import", response_model=schemas.QuestionnaireImportResponse)
async def import_questionnaire(
    file: UploadFile = File(...),
    use_ai: bool = Query(True, description="是否使用AI智能解析"),
    session: Session = Depends(get_session)
):
    """
    导入问卷文件.
    
    支持格式：
    - JSON (.json)
    - Excel (.xlsx, .xls)
    - Word (.docx)
    - 纯文本 (.txt)
    
    V45新增：
    - use_ai=true（默认）：优先使用AI智能识别题目类型和选项
    - use_ai=false：仅使用规则匹配
    """
    try:
        content = await file.read()
        
        # V45: 使用异步解析（支持AI）
        metadata, questions = await parse_questionnaire_file_async(
            content, 
            file.filename or "unknown",
            file.content_type or "",
            use_ai=use_ai
        )
        
        parse_method = "AI智能解析" if use_ai else "规则匹配"
        return schemas.QuestionnaireImportResponse(
            success=True,
            message=f"成功解析 {len(questions)} 道题目（{parse_method}）",
            metadata=metadata,
            questions=questions
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.put("/questionnaires/{questionnaire_id}", response_model=schemas.QuestionnaireResponse)
async def update_questionnaire(
    questionnaire_id: int,
    data: schemas.QuestionnaireUpdate,
    session: Session = Depends(get_session)
):
    """更新问卷."""
    questionnaire = await service.update_questionnaire(
        session, questionnaire_id, data.model_dump(exclude_unset=True)
    )
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return questionnaire


@router.post("/questionnaires/{questionnaire_id}/copy", response_model=schemas.QuestionnaireResponse, status_code=201)
async def copy_questionnaire(
    questionnaire_id: int,
    session: Session = Depends(get_session)
):
    """复制问卷."""
    questionnaire = await service.copy_questionnaire(session, questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return questionnaire


@router.delete("/questionnaires/{questionnaire_id}", status_code=204)
async def delete_questionnaire(
    questionnaire_id: int,
    session: Session = Depends(get_session)
):
    """删除问卷."""
    success = await service.delete_questionnaire(session, questionnaire_id)
    if not success:
        raise HTTPException(status_code=404, detail="问卷不存在")


# ========== 测评管理 ==========

@router.post("", response_model=schemas.AssessmentResponse, status_code=201)
@router.post("/", response_model=schemas.AssessmentResponse, status_code=201)
async def create_assessment(
    data: schemas.AssessmentCreate,
    session: Session = Depends(get_session)
):
    """创建测评."""
    # 验证问卷是否存在
    questionnaire = await service.get_questionnaire(session, data.questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    try:
        assessment = await service.create_assessment(session, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return assessment


@router.get("", response_model=schemas.AssessmentListResponse)
@router.get("/", response_model=schemas.AssessmentListResponse)
async def get_assessments(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """获取测评列表."""
    assessments, total = await service.get_assessments(session, skip, limit)
    return schemas.AssessmentListResponse(items=assessments, total=total)


@router.put("/{assessment_id}", response_model=schemas.AssessmentResponse)
async def update_assessment(
    assessment_id: int,
    data: schemas.AssessmentUpdate,
    session: Session = Depends(get_session)
):
    """更新测评配置."""
    try:
        assessment = await service.update_assessment(session, assessment_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    return assessment


@router.delete("/{assessment_id}")
async def delete_assessment(
    assessment_id: int,
    force: bool = Query(False, description="是否强制删除（包括所有提交记录）"),
    session: Session = Depends(get_session)
):
    """
    删除测评（分发链接）.
    
    - 如果有提交记录且 force=False，返回警告信息，需要用户确认
    - 如果 force=True，删除分发链接及所有关联的提交记录
    """
    result = await service.delete_assessment(session, assessment_id, force_delete_submissions=force)
    
    if not result["success"]:
        if result.get("error") == "has_submissions":
            # 有提交记录，返回409冲突状态码，让前端处理确认
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "has_submissions",
                    "submission_count": result["submission_count"],
                    "message": result["message"]
                }
            )
        else:
            raise HTTPException(status_code=404, detail="测评不存在")
    
    return result


# ========== 提交记录管理 ==========

@router.get("/submissions", response_model=schemas.SubmissionListResponse)
async def get_submissions(
    assessment_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None, description="问卷分类: professional/scored/survey"),
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """获取提交记录列表，支持按问卷category过滤."""
    submissions, total = await service.get_submissions(
        session, assessment_id, status, skip, limit, category=category
    )
    
    def normalize_display_name(name: Optional[str], phone: Optional[str]) -> Optional[str]:
        trimmed_name = (name or "").strip()
        trimmed_phone = (phone or "").strip()
        if trimmed_phone:
            return trimmed_name or name
        if not trimmed_name or trimmed_name.lower() in {"匿名", "未知", "unknown", "n/a", "na", "null", "-", "--"}:
            return "匿名"
        return trimmed_name or name
    
    # ⭐ 关联查询问卷信息
    result_items = []
    for sub in submissions:
        questionnaire = await service.get_questionnaire(session, sub.questionnaire_id)
        display_name = normalize_display_name(sub.candidate_name, sub.candidate_phone)
        item = schemas.SubmissionResponse(
            id=sub.id,
            code=sub.code,
            candidate_name=display_name,
            candidate_phone=sub.candidate_phone,
            candidate_email=sub.candidate_email,  # V45: 返回邮箱
            gender=sub.gender,  # V45: 返回性别
            target_position=sub.target_position,  # V45: 返回应聘岗位
            questionnaire_id=sub.questionnaire_id,  # ⭐ 新增：返回问卷ID
            questionnaire_name=questionnaire.name if questionnaire else None,
            questionnaire_type=questionnaire.type if questionnaire else None,
            total_score=sub.total_score,
            grade=sub.grade,
            status=sub.status,
            started_at=sub.started_at,
            submitted_at=sub.submitted_at,
            max_score=sub.max_score,
            score_percentage=sub.score_percentage,
            result_details=sub.result_details,
            custom_data=sub.custom_data,
        )
        result_items.append(item)
    
    return schemas.SubmissionListResponse(items=result_items, total=total)


@router.get("/submissions/{submission_id}")
async def get_submission_detail(
    submission_id: int,
    session: Session = Depends(get_session)
):
    """获取单个提交记录详情（包含答案数据）."""
    submission = await service.get_submission_by_id(session, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    
    # 获取问卷信息
    questionnaire = await service.get_questionnaire(session, submission.questionnaire_id)
    
    # 获取答案数据（从 submission_answer 表）
    answers = await service.get_submission_answers(session, submission_id)
    
    # 获取候选人信息（从 candidates 表）
    candidate_info = await service.get_candidate_by_submission(session, submission_id)
    
    def normalize_display_name(name: Optional[str], phone: Optional[str]) -> Optional[str]:
        trimmed_name = (name or "").strip()
        trimmed_phone = (phone or "").strip()
        if trimmed_phone:
            return trimmed_name or name
        if not trimmed_name or trimmed_name.lower() in {"匿名", "未知", "unknown", "n/a", "na", "null", "-", "--"}:
            return "匿名"
        return trimmed_name or name

    display_name = normalize_display_name(submission.candidate_name, submission.candidate_phone)
    return {
        "id": submission.id,
        "code": submission.code,  # ⭐ 修复：字段名是 code 不是 submission_code
        "candidate_name": display_name or (candidate_info.get("name") if candidate_info else None),
        "candidate_phone": submission.candidate_phone or (candidate_info.get("phone") if candidate_info else None),
        "questionnaire_name": questionnaire.name if questionnaire else None,
        "questionnaire_type": questionnaire.type if questionnaire else None,
        "questions_data": questionnaire.questions_data if questionnaire else None,
        "total_score": submission.total_score,
        "max_score": submission.max_score or 100,
        "grade": submission.grade,
        "status": submission.status,
        "started_at": submission.started_at,
        "submitted_at": submission.submitted_at,
        "answers": submission.answers or answers,  # ⭐ 优先使用 submission.answers
        "result_details": submission.result_details,
        "custom_data": submission.custom_data,
    }


@router.delete("/submissions/{submission_id}")
async def delete_submission(
    submission_id: int,
    session: Session = Depends(get_session)
):
    """删除提交记录."""
    success = await service.delete_submission(session, submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    return {"message": "删除成功"}


# ========== 统计 API ==========

@router.get("/statistics")
async def get_submission_statistics(
    category: Optional[str] = Query(None, description="问卷分类: professional/scored/survey"),
    questionnaire_id: Optional[int] = Query(None, description="问卷ID"),
    session: Session = Depends(get_session)
):
    """获取提交记录统计数据."""
    stats = await service.get_submission_statistics(session, category, questionnaire_id)
    return stats


@router.get("/questionnaires/{questionnaire_id}/question-stats")
async def get_questionnaire_question_stats(
    questionnaire_id: int,
    trend_range: Optional[str] = Query("week", alias="range", description="趋势范围: week/month"),
    session: Session = Depends(get_session)
):
    """
    V42: 获取问卷的题目答案统计数据.
    
    返回每道题的选项分布统计，用于问卷统计页面的数据可视化。
    """
    stats = await service.get_question_answer_statistics(session, questionnaire_id, trend_range=trend_range)
    return stats


@router.get(
    "/questionnaires/{questionnaire_id}/answer-export",
    response_model=schemas.AnswerExportResponse,
)
async def get_questionnaire_answer_export(
    questionnaire_id: int,
    session: Session = Depends(get_session)
):
    """获取问卷逐人答题明细导出数据."""
    export_data = await service.get_questionnaire_answer_export(session, questionnaire_id)
    if not export_data:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return export_data


# ========== 导出 API ==========

@router.get("/export/excel")
async def export_submissions_excel(
    category: Optional[str] = Query(None, description="问卷分类"),
    questionnaire_id: Optional[int] = Query(None, description="问卷ID"),
    session: Session = Depends(get_session)
):
    """导出提交记录为Excel文件."""
    from fastapi.responses import StreamingResponse
    import io
    
    excel_data = await service.export_submissions_to_excel(session, category, questionnaire_id)
    
    # 创建响应
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=submissions_export.xlsx"
        }
    )


from app.api.assessments.public_router import public_router
