"""问卷/测评管理 - API路由."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlmodel import Session

from app.db import get_session
from app.api.assessments import schemas, service
from app.api.assessments.meeting_integration import sanitize_custom_data
from app.api.assessments.questionnaire_parser import parse_questionnaire_file, parse_questionnaire_file_async
from app.models_assessment import Questionnaire

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


# ========== 问卷管理 ==========

@router.get("/questionnaires", response_model=schemas.QuestionnaireListResponse)
async def get_questionnaires(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = Query(
        None, description="问卷分类: professional/scored/survey/custom（custom 包含 scored 和 survey）"
    ),
    library_category_id: Optional[int] = Query(None, description="问卷库主分类ID"),
    tag_ids: Optional[List[int]] = Query(None, description="标签ID，可重复传入，标签间为 OR"),
    creator: Optional[str] = Query(None, description="创建人，按去除首尾空格后的文本精确匹配"),
    status: Optional[str] = Query(None, description="问卷状态"),
    custom_type: Optional[str] = Query(None, description="自定义问卷类型: scored/non_scored"),
    keyword: Optional[str] = Query(None, description="问卷名称或描述关键词"),
    sort: str = Query("updated_desc", description="updated_desc 或 created_desc"),
    session: Session = Depends(get_session)
):
    """获取问卷列表，支持问卷库分类、标签和创建人等组合过滤。"""
    try:
        questionnaires, total = await service.get_questionnaires(
            session,
            skip,
            limit,
            category=category,
            library_category_id=library_category_id,
            tag_ids=tag_ids,
            creator=creator,
            status=status,
            custom_type=custom_type,
            keyword=keyword,
            sort=sort,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return schemas.QuestionnaireListResponse(items=questionnaires, total=total)


@router.get(
    "/library/categories",
    response_model=List[schemas.QuestionnaireLibraryCategoryResponse],
)
async def get_library_categories(session: Session = Depends(get_session)):
    """获取问卷库主分类及其问卷数量。"""
    categories = await service.get_library_categories(session)
    return [
        schemas.QuestionnaireLibraryCategoryResponse(
            **schemas.QuestionnaireLibraryCategorySummary.model_validate(category).model_dump(),
            questionnaire_count=count,
        )
        for category, count in categories
    ]


@router.post(
    "/library/categories",
    response_model=schemas.QuestionnaireLibraryCategorySummary,
    status_code=201,
)
async def create_library_category(
    data: schemas.QuestionnaireLibraryCategoryCreate,
    session: Session = Depends(get_session),
):
    """创建可用于自定义问卷的主分类。"""
    try:
        return await service.create_library_category(session, data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put(
    "/library/categories/reorder",
    response_model=List[schemas.QuestionnaireLibraryCategorySummary],
)
async def reorder_library_categories(
    data: schemas.QuestionnaireLibraryCategoryReorder,
    session: Session = Depends(get_session),
):
    """在单个事务中更新全部主分类排序。"""
    try:
        return await service.reorder_library_categories(session, data.category_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put(
    "/library/categories/{category_id}",
    response_model=schemas.QuestionnaireLibraryCategorySummary,
)
async def update_library_category(
    category_id: int,
    data: schemas.QuestionnaireLibraryCategoryUpdate,
    session: Session = Depends(get_session),
):
    """更新主分类名称、排序或启用状态。"""
    try:
        category = await service.update_library_category(
            session, category_id, data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not category:
        raise HTTPException(status_code=404, detail="主分类不存在")
    return category


@router.get("/library/tags", response_model=List[schemas.QuestionnaireTagResponse])
async def get_questionnaire_tags(session: Session = Depends(get_session)):
    """获取问卷库标签及其问卷数量。"""
    tags = await service.get_questionnaire_tags(session)
    return [
        schemas.QuestionnaireTagResponse(
            **schemas.QuestionnaireTagSummary.model_validate(tag).model_dump(),
            questionnaire_count=count,
        )
        for tag, count in tags
    ]


@router.post("/library/tags", response_model=schemas.QuestionnaireTagSummary, status_code=201)
async def create_questionnaire_tag(
    data: schemas.QuestionnaireTagCreate,
    session: Session = Depends(get_session),
):
    """创建问卷库标签。"""
    try:
        return await service.create_questionnaire_tag(session, data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/library/tags/{tag_id}", response_model=schemas.QuestionnaireTagSummary)
async def update_questionnaire_tag(
    tag_id: int,
    data: schemas.QuestionnaireTagUpdate,
    session: Session = Depends(get_session),
):
    """更新标签名称或启用状态。"""
    try:
        tag = await service.update_questionnaire_tag(
            session, tag_id, data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    return tag


@router.post("/library/tags/{source_tag_id}/merge", response_model=schemas.QuestionnaireTagSummary)
async def merge_questionnaire_tags(
    source_tag_id: int,
    data: schemas.QuestionnaireTagMerge,
    session: Session = Depends(get_session),
):
    """将源标签关联迁移至目标标签并停用源标签。"""
    try:
        return await service.merge_questionnaire_tags(
            session, source_tag_id, data.target_tag_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/library/creators", response_model=List[str])
async def get_questionnaire_creator_options(session: Session = Depends(get_session)):
    """获取已编辑问卷中的创建人筛选项。"""
    return await service.get_questionnaire_creator_options(session)


@router.put("/questionnaires/bulk-library-category")
async def bulk_update_questionnaire_library_category(
    data: schemas.QuestionnaireBulkLibraryCategoryUpdate,
    session: Session = Depends(get_session),
):
    """批量更新问卷库主分类。"""
    try:
        updated_count = await service.bulk_update_questionnaire_library_category(
            session, data.questionnaire_ids, data.library_category_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"updated_count": updated_count}


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
    try:
        questionnaire = await service.create_questionnaire(session, data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
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
    try:
        questionnaire = await service.update_questionnaire(
            session, questionnaire_id, data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
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


@router.post("/questionnaires/{questionnaire_id}/recalculate-scores")
async def recalculate_questionnaire_scores(
    questionnaire_id: int,
    session: Session = Depends(get_session)
):
    """按当前评分配置重算评分问卷历史提交得分."""
    result = await service.recalculate_questionnaire_scores(session, questionnaire_id)
    if result is None:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return result


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
    questionnaire_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None, description="问卷分类: professional/scored/survey"),
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """获取提交记录列表，支持按问卷category过滤."""
    submissions, total = await service.get_submissions(
        session, assessment_id, status, skip, limit, category=category, questionnaire_id=questionnaire_id
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
            custom_data=sanitize_custom_data(sub.custom_data),
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
        "custom_data": sanitize_custom_data(submission.custom_data),
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
