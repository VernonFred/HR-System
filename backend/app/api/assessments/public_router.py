"""Public assessment entry and submission routes."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db import get_session
from app.api.assessments import schemas, service
from app.api.assessments import meeting_integration


# ========== 公开API（候选人端） ==========

public_router = APIRouter(prefix="/api/public/assessment", tags=["public-assessment"])


def _resolve_public_form_fields(raw_fields, *, use_default_fields: bool):
    """Normalize HR-configured entry fields without adding meeting-only fields."""
    default_form_fields = [
        {"id": 1, "name": "candidate_name", "label": "姓名", "type": "text", "enabled": True, "required": True, "builtin": True, "icon": "ri-user-line"},
        {"id": 2, "name": "candidate_phone", "label": "手机号", "type": "tel", "enabled": True, "required": True, "builtin": True, "icon": "ri-phone-line"},
        {"id": 3, "name": "candidate_email", "label": "电子邮箱", "type": "email", "enabled": True, "required": False, "builtin": True, "icon": "ri-mail-line"},
        {"id": 4, "name": "target_position", "label": "应聘岗位", "type": "text", "enabled": True, "required": False, "builtin": True, "icon": "ri-briefcase-line"},
    ]

    if raw_fields is None or raw_fields == {}:
        return default_form_fields if use_default_fields else []
    if isinstance(raw_fields, dict):
        fields = raw_fields.get("fields")
        if isinstance(fields, list):
            return fields
        return default_form_fields if use_default_fields and not raw_fields else []
    if isinstance(raw_fields, list):
        return raw_fields
    return default_form_fields if use_default_fields else []


@public_router.get("/{code}", response_model=schemas.PublicAssessmentInfo)
async def get_public_assessment_info(
    code: str,
    survey_token: Optional[str] = Query(None, alias="surveyToken"),
    participant_url: Optional[str] = Query(None, alias="participantUrl"),
    session: Session = Depends(get_session)
):
    """获取测评信息（候选人端）."""
    assessment = await service.get_assessment_by_code(session, code)
    if not assessment:
        raise HTTPException(status_code=404, detail="链接不存在或已失效")
    
    questionnaire = await service.get_questionnaire(session, assessment.questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    now = datetime.now()
    valid = assessment.valid_from <= now <= assessment.valid_until
    expired = now > assessment.valid_until
    
    has_meeting_context = bool(survey_token and participant_url)
    form_fields_data = _resolve_public_form_fields(
        assessment.form_fields,
        use_default_fields=not has_meeting_context,
    )

    meeting_identity = {}
    if survey_token and participant_url:
        meeting_identity = await meeting_integration.fetch_meeting_identity(participant_url, survey_token)

    entry_prefill = {}
    if not assessment.anonymous_mode:
        entry_prefill = meeting_integration.build_entry_prefill(form_fields_data, meeting_identity)

    if assessment.anonymous_mode and isinstance(form_fields_data, list):
        form_fields_data = [
            field
            for field in form_fields_data
            if not meeting_integration.is_identity_form_field(field)
        ]
    
    # ⭐ 获取问卷题目数据（用于前端 fallback）
    questions_data = questionnaire.questions_data.get("questions", []) if questionnaire.questions_data else []
    
    return schemas.PublicAssessmentInfo(
        name=assessment.name,  # 使用用户自定义的测评名称
        type=questionnaire.type,
        category=questionnaire.category,
        custom_type=questionnaire.custom_type,
        purpose=questionnaire.purpose,
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
        anonymous_mode=bool(assessment.anonymous_mode),
        entry_prefill=entry_prefill,
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
        raise HTTPException(status_code=404, detail="链接不存在或已失效")
    
    phone = data.get("phone", "")
    name = data.get("name", "")
    anonymous_device_id = data.get("anonymous_device_id", "")
    
    result = await service.check_can_submit(
        session,
        assessment.id,
        phone,
        name,
        anonymous_device_id=anonymous_device_id,
    )
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
        raise HTTPException(status_code=404, detail="链接不存在或已失效")
    
    # ⭐ 检查是否可以提交
    check_result = await service.check_can_submit(
        session, assessment.id, 
        data.candidate_phone, 
        data.candidate_name,
        anonymous_device_id=data.anonymous_device_id,
    )
    if not check_result["can_submit"]:
        raise HTTPException(status_code=403, detail=check_result["reason"])
    
    # ⭐ 增加开始测评统计
    await service.increment_start_count(session, assessment.id)

    payload = data.model_dump(exclude={"assessment_code", "survey_token", "participant_url", "callback_url"})

    custom_data = payload.get("custom_data")
    if not isinstance(custom_data, dict):
        custom_data = {}

    meeting_identity = {}
    if data.survey_token and data.participant_url:
        meeting_identity = await meeting_integration.fetch_meeting_identity(
            data.participant_url,
            data.survey_token,
        )
        if meeting_identity:
            custom_data["meeting_identity"] = meeting_identity

    if data.callback_url and data.survey_token:
        custom_data["__meeting_callback"] = {
            "callback_url": data.callback_url,
            "survey_token": data.survey_token,
        }

    payload["custom_data"] = custom_data

    # ⭐ 根据部门路由解析本次应使用的问卷
    try:
        target_questionnaire_id = await service.resolve_questionnaire_id(session, assessment, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    questionnaire = await service.get_questionnaire(session, target_questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    # 创建提交记录
    submission = await service.create_submission(
        session,
        assessment.id,
        payload,
        questionnaire_id_override=target_questionnaire_id
    )
    
    # 返回题目
    questions = questionnaire.questions_data.get("questions", [])
    
    return schemas.PublicSubmissionStart(
        submission_code=submission.code,
        questions=questions,
        questionnaire_name=questionnaire.name,
        questionnaire_type=questionnaire.type,
        category=questionnaire.category,
        custom_type=questionnaire.custom_type,
        purpose=questionnaire.purpose,
        questions_count=questionnaire.questions_count,
        estimated_minutes=questionnaire.estimated_minutes,
    )


@public_router.post("/submission/{submission_code}/submit", response_model=schemas.PublicSubmissionSuccess)
async def submit_assessment(
    submission_code: str,
    data: schemas.AnswerSubmit,
    session: Session = Depends(get_session)
):
    """提交答案（候选人端）."""
    try:
        submission = await service.submit_answers(session, submission_code, data.answers)
    except ValueError as e:
        detail = str(e)
        status_code = 403 if any(
            keyword in detail for keyword in ["重复提交", "最大提交次数", "距上次提交"]
        ) else 400
        raise HTTPException(status_code=status_code, detail=detail)

    callback_config = {}
    if isinstance(submission.custom_data, dict):
        callback_config = submission.custom_data.get("__meeting_callback") or {}
    callback_url = data.callback_url or callback_config.get("callback_url")
    survey_token = data.survey_token or callback_config.get("survey_token")
    try:
        await meeting_integration.send_completion_callback(
            callback_url,
            survey_token,
            submission.id,
            submission.submitted_at or submission.started_at,
        )
    except Exception:
        pass
    
    return schemas.PublicSubmissionSuccess(
        success=True,
        submission_code=submission.code,
        submitted_at=submission.submitted_at or submission.started_at,
    )
