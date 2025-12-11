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
    
    assessment = await service.create_assessment(session, data.model_dump())
    return assessment


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
    assessment = await service.update_assessment(session, assessment_id, data.model_dump(exclude_unset=True))
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
    
    # ⭐ 关联查询问卷信息
    result_items = []
    for sub in submissions:
        questionnaire = await service.get_questionnaire(session, sub.questionnaire_id)
        item = schemas.SubmissionResponse(
            id=sub.id,
            code=sub.code,
            candidate_name=sub.candidate_name,
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
    
    return {
        "id": submission.id,
        "code": submission.code,  # ⭐ 修复：字段名是 code 不是 submission_code
        "candidate_name": submission.candidate_name or (candidate_info.get("name") if candidate_info else None),
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
    session: Session = Depends(get_session)
):
    """
    V42: 获取问卷的题目答案统计数据.
    
    返回每道题的选项分布统计，用于问卷统计页面的数据可视化。
    """
    stats = await service.get_question_answer_statistics(session, questionnaire_id)
    return stats


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


# ========== 公开API（候选人端） ==========

public_router = APIRouter(prefix="/api/public/assessment", tags=["public-assessment"])


@public_router.get("/{code}", response_model=schemas.PublicAssessmentInfo)
async def get_public_assessment_info(
    code: str,
    session: Session = Depends(get_session)
):
    """获取测评信息（候选人端）."""
    from datetime import datetime
    
    assessment = await service.get_assessment_by_code(session, code)
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在或已失效")
    
    questionnaire = await service.get_questionnaire(session, assessment.questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    now = datetime.now()
    valid = assessment.valid_from <= now <= assessment.valid_until
    expired = now > assessment.valid_until
    
    # ⭐ 如果没有配置字段，返回默认字段
    default_form_fields = [
        {"id": 1, "name": "candidate_name", "label": "姓名", "type": "text", "enabled": True, "required": True, "builtin": True, "icon": "ri-user-line"},
        {"id": 2, "name": "candidate_phone", "label": "手机号", "type": "tel", "enabled": True, "required": True, "builtin": True, "icon": "ri-phone-line"},
        {"id": 3, "name": "candidate_email", "label": "电子邮箱", "type": "email", "enabled": True, "required": False, "builtin": True, "icon": "ri-mail-line"},
        {"id": 4, "name": "target_position", "label": "应聘岗位", "type": "text", "enabled": True, "required": False, "builtin": True, "icon": "ri-briefcase-line"},
    ]
    
    form_fields_data = assessment.form_fields if assessment.form_fields else default_form_fields
    
    # ⭐ 获取问卷题目数据（用于前端 fallback）
    questions_data = questionnaire.questions_data.get("questions", []) if questionnaire.questions_data else []
    
    return schemas.PublicAssessmentInfo(
        name=questionnaire.name,
        type=questionnaire.type,
        questions_count=questionnaire.questions_count,
        estimated_minutes=questionnaire.estimated_minutes,
        valid=valid,
        expired=expired,
        description=assessment.description,
        form_fields=form_fields_data,  # ⭐ 返回字段配置（有默认值）
        page_texts=assessment.page_texts if assessment.page_texts else None,  # ⭐ 返回页面文案配置
        questions=questions_data,  # ⭐ 返回问卷题目数据
        # ⭐ 重复提交配置
        allow_repeat=assessment.allow_repeat if assessment.allow_repeat is not None else True,
        repeat_check_by=assessment.repeat_check_by or "phone",
        repeat_interval_hours=assessment.repeat_interval_hours or 0,
        max_submissions=assessment.max_submissions or 0,
    )


@public_router.post("/{code}/check-submit")
async def check_can_submit(
    code: str,
    data: dict,
    session: Session = Depends(get_session)
):
    """检查是否可以提交测评（候选人端）."""
    assessment = await service.get_assessment_by_code(session, code)
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在或已失效")
    
    phone = data.get("phone", "")
    name = data.get("name", "")
    
    result = await service.check_can_submit(session, assessment.id, phone, name)
    return result


@public_router.post("/{code}/start", response_model=schemas.PublicSubmissionStart)
async def start_assessment(
    code: str,
    data: schemas.SubmissionCreate,
    session: Session = Depends(get_session)
):
    """开始测评（候选人端）."""
    assessment = await service.get_assessment_by_code(session, code)
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在或已失效")
    
    questionnaire = await service.get_questionnaire(session, assessment.questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    # ⭐ 检查是否可以提交
    check_result = await service.check_can_submit(
        session, assessment.id, 
        data.candidate_phone, 
        data.candidate_name
    )
    if not check_result["can_submit"]:
        raise HTTPException(status_code=403, detail=check_result["reason"])
    
    # ⭐ 增加开始测评统计
    await service.increment_start_count(session, assessment.id)
    
    # 创建提交记录
    submission = await service.create_submission(
        session, assessment.id, data.model_dump(exclude={"assessment_code"})
    )
    
    # 返回题目
    questions = questionnaire.questions_data.get("questions", [])
    
    return schemas.PublicSubmissionStart(
        submission_code=submission.code,
        questions=questions
    )


@public_router.post("/submission/{submission_code}/submit", response_model=schemas.PublicSubmissionSuccess)
async def submit_assessment(
    submission_code: str,
    data: schemas.AnswerSubmit,
    session: Session = Depends(get_session)
):
    """提交答案（候选人端）."""
    submission = await service.submit_answers(session, submission_code, data.answers)
    
    return schemas.PublicSubmissionSuccess(
        success=True,
        submission_code=submission.code,
        submitted_at=submission.submitted_at or submission.started_at,
    )

