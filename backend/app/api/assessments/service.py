"""问卷/测评管理 - 业务逻辑."""
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from sqlmodel import Session, select, func, and_
import random
import string

from app.models_assessment import Questionnaire, Assessment, Submission
from app.models import Candidate
from app.professional_scoring import (
    score_professional_assessment,
    score_custom_questionnaire,
    ProfessionalScoringError
)
from app.custom_scoring import calculate_custom_questionnaire_score


# ========== 问卷管理 ==========

async def get_questionnaires(
    session: Session, skip: int = 0, limit: int = 100, category: Optional[str] = None
) -> Tuple[List[Questionnaire], int]:
    """获取问卷列表，支持按category过滤.
    
    Args:
        session: 数据库会话
        skip: 跳过数量
        limit: 返回数量
        category: 问卷分类过滤（professional/scored/survey/custom）
                  'custom' 表示获取所有非professional的问卷（scored + survey）
    """
    # 构建查询条件
    base_query = select(Questionnaire)
    count_query = select(func.count()).select_from(Questionnaire)
    
    if category:
        if category == 'custom':
            # ⭐ custom类别：获取所有非professional的问卷（scored + survey）
            base_query = base_query.where(Questionnaire.category.in_(['scored', 'survey']))
            count_query = count_query.where(Questionnaire.category.in_(['scored', 'survey']))
        else:
            base_query = base_query.where(Questionnaire.category == category)
            count_query = count_query.where(Questionnaire.category == category)
    
    total = session.scalar(count_query)
    statement = base_query.offset(skip).limit(limit).order_by(Questionnaire.created_at.desc())
    questionnaires = session.exec(statement).all()
    return list(questionnaires), total or 0


async def get_questionnaire(session: Session, questionnaire_id: int) -> Optional[Questionnaire]:
    """获取问卷详情."""
    return session.get(Questionnaire, questionnaire_id)


async def create_questionnaire(session: Session, data: dict) -> Questionnaire:
    """创建问卷."""
    questionnaire = Questionnaire(**data)
    session.add(questionnaire)
    session.commit()
    session.refresh(questionnaire)
    return questionnaire


async def update_questionnaire(
    session: Session, questionnaire_id: int, data: dict
) -> Optional[Questionnaire]:
    """更新问卷."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return None
    
    for key, value in data.items():
        if value is not None:
            setattr(questionnaire, key, value)
    
    questionnaire.updated_at = datetime.now()
    session.add(questionnaire)
    session.commit()
    session.refresh(questionnaire)
    return questionnaire


async def copy_questionnaire(session: Session, questionnaire_id: int) -> Optional[Questionnaire]:
    """复制问卷."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return None

    copied = Questionnaire(
        name=f"{questionnaire.name}（副本）",
        type=questionnaire.type,
        category=questionnaire.category,
        description=questionnaire.description,
        questions_count=questionnaire.questions_count,
        estimated_minutes=questionnaire.estimated_minutes,
        questions_data=questionnaire.questions_data,
        scoring_rules=questionnaire.scoring_rules,
        custom_type=questionnaire.custom_type,
        scoring_config=questionnaire.scoring_config,
        purpose=questionnaire.purpose,
        status=questionnaire.status,
    )
    session.add(copied)
    session.commit()
    session.refresh(copied)
    return copied


async def delete_questionnaire(session: Session, questionnaire_id: int) -> bool:
    """删除问卷."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return False
    
    session.delete(questionnaire)
    session.commit()
    return True


# ========== 测评管理 ==========

def generate_assessment_code() -> str:
    """生成测评唯一码."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ASSE-{timestamp}-{random_str}"


async def create_assessment(session: Session, data: dict) -> Assessment:
    """创建测评."""
    if "routing_config" in data:
        data["routing_config"] = await normalize_routing_config(session, data.get("routing_config"), strict=True)
    if data.get("anonymous_mode"):
        data["allow_repeat"] = False
    code = generate_assessment_code()
    assessment_data = {**data, "code": code}
    assessment = Assessment(**assessment_data)
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


async def get_assessments(
    session: Session, skip: int = 0, limit: int = 100
) -> Tuple[List[Assessment], int]:
    """获取测评列表."""
    total = session.scalar(select(func.count()).select_from(Assessment))
    statement = select(Assessment).offset(skip).limit(limit).order_by(Assessment.created_at.desc())
    assessments = session.exec(statement).all()
    return list(assessments), total or 0


async def get_assessment_by_code(session: Session, code: str) -> Optional[Assessment]:
    """根据code获取测评."""
    statement = select(Assessment).where(Assessment.code == code)
    return session.exec(statement).first()


async def normalize_routing_config(
    session: Session,
    raw_config: Optional[Dict[str, Any]],
    strict: bool = True
) -> Dict[str, Any]:
    """标准化并校验部门路由配置."""
    base_config: Dict[str, Any] = {
        "enabled": False,
        "department_field": "department",
        "fallback_to_default": True,
        "mappings": [],
    }

    if not isinstance(raw_config, dict):
        return base_config

    enabled = bool(raw_config.get("enabled", False))
    department_field = str(raw_config.get("department_field") or "department").strip() or "department"
    fallback_to_default = bool(raw_config.get("fallback_to_default", True))

    mappings: List[Dict[str, Any]] = []
    raw_mappings = raw_config.get("mappings")
    if isinstance(raw_mappings, list):
        for item in raw_mappings:
            if not isinstance(item, dict):
                continue

            department_value = str(item.get("department_value") or "").strip()
            questionnaire_id_raw = item.get("questionnaire_id")

            try:
                questionnaire_id = int(questionnaire_id_raw) if questionnaire_id_raw is not None else None
            except (TypeError, ValueError):
                questionnaire_id = None

            if not department_value or questionnaire_id is None:
                if strict and enabled:
                    raise ValueError("部门路由配置无效：请为每个映射填写部门和目标问卷")
                continue

            questionnaire = session.get(Questionnaire, questionnaire_id)
            if not questionnaire:
                if strict and enabled:
                    raise ValueError(f"部门路由配置无效：问卷ID {questionnaire_id} 不存在")
                continue

            mappings.append({
                "department_value": department_value,
                "questionnaire_id": questionnaire_id,
            })

    deduped_by_department: Dict[str, Dict[str, Any]] = {}
    for item in mappings:
        deduped_by_department[item["department_value"]] = item

    return {
        "enabled": enabled,
        "department_field": department_field,
        "fallback_to_default": fallback_to_default,
        "mappings": list(deduped_by_department.values()),
    }


async def resolve_questionnaire_id(
    session: Session,
    assessment: Assessment,
    submission_data: Dict[str, Any]
) -> int:
    """根据部门路由配置解析本次填写应该使用的问卷ID."""
    default_questionnaire_id = assessment.questionnaire_id
    routing_config = await normalize_routing_config(session, assessment.routing_config, strict=False)

    if not routing_config.get("enabled"):
        return default_questionnaire_id

    department_field = str(routing_config.get("department_field") or "department").strip() or "department"
    fallback_to_default = bool(routing_config.get("fallback_to_default", True))

    custom_data = submission_data.get("custom_data")
    raw_department = ""
    if isinstance(custom_data, dict):
        raw_department = custom_data.get(department_field) or ""
    if not raw_department:
        raw_department = submission_data.get(department_field) or ""

    department_value = str(raw_department).strip()
    if not department_value:
        return default_questionnaire_id

    mappings = routing_config.get("mappings") if isinstance(routing_config.get("mappings"), list) else []
    target_questionnaire_id: Optional[int] = None
    for item in mappings:
        if not isinstance(item, dict):
            continue
        if str(item.get("department_value") or "").strip() == department_value:
            try:
                target_questionnaire_id = int(item.get("questionnaire_id"))
            except (TypeError, ValueError):
                target_questionnaire_id = None
            break

    if target_questionnaire_id is None:
        if fallback_to_default:
            return default_questionnaire_id
        raise ValueError(f"部门“{department_value}”未配置对应问卷")

    target_questionnaire = session.get(Questionnaire, target_questionnaire_id)
    if target_questionnaire and target_questionnaire.status == "active":
        return target_questionnaire_id

    if fallback_to_default:
        return default_questionnaire_id
    raise ValueError(f"部门“{department_value}”对应问卷不可用")


# ========== 提交记录管理 ==========

def generate_submission_code() -> str:
    """生成提交记录唯一码."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.digits, k=3))
    return f"SUB-{timestamp}-{random_str}"


async def check_can_submit(
    session: Session, 
    assessment_id: int, 
    phone: str, 
    name: str = "",
    anonymous_device_id: Optional[str] = None,
) -> dict:
    """
    检查是否可以提交测评.
    
    返回:
        {
            "can_submit": bool,
            "reason": str,  # 如果不能提交，说明原因
            "submission_number": int,  # 这是第几次提交
            "previous_submissions": list  # 之前的提交记录摘要
        }
    """
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        return {"can_submit": False, "reason": "测评不存在", "submission_number": 0, "previous_submissions": []}

    normalized_device_id = (anonymous_device_id or "").strip()
    if assessment.anonymous_mode and not normalized_device_id:
        return {
            "can_submit": False,
            "reason": "匿名设备标识缺失，请刷新页面后重试",
            "submission_number": 0,
            "previous_submissions": [],
        }

    condition = _build_repeat_submission_condition(
        assessment,
        phone,
        name,
        anonymous_device_id=normalized_device_id,
    )
    statement = select(Submission).where(condition).order_by(Submission.submitted_at.desc())
    submissions = session.exec(statement).all()
    submission_count = len(submissions)
    
    # 获取之前提交的摘要
    previous_submissions = [
        {
            "code": sub.code,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "status": sub.status,
            "total_score": sub.total_score,
            "grade": sub.grade
        }
        for sub in submissions[:5]  # 只返回最近5条
    ]
    
    # 1. 检查是否允许重复
    if (assessment.anonymous_mode or not assessment.allow_repeat) and submission_count > 0:
        return {
            "can_submit": False, 
            "reason": "该测评不允许重复提交",
            "submission_number": submission_count,
            "previous_submissions": previous_submissions
        }
    
    # 2. 检查提交间隔
    if assessment.repeat_interval_hours > 0 and submissions:
        last_submission = submissions[0]
        if last_submission.submitted_at:
            hours_since = (datetime.now() - last_submission.submitted_at).total_seconds() / 3600
            if hours_since < assessment.repeat_interval_hours:
                remaining_hours = assessment.repeat_interval_hours - hours_since
                if remaining_hours < 1:
                    remaining_text = f"{int(remaining_hours * 60)}分钟"
                else:
                    remaining_text = f"{int(remaining_hours)}小时"
                return {
                    "can_submit": False, 
                    "reason": f"距上次提交不足{assessment.repeat_interval_hours}小时，请{remaining_text}后再试",
                    "submission_number": submission_count,
                    "previous_submissions": previous_submissions
                }
    
    # 3. 检查提交次数上限
    if assessment.max_submissions > 0 and submission_count >= assessment.max_submissions:
        return {
            "can_submit": False, 
            "reason": f"已达到最大提交次数({assessment.max_submissions}次)",
            "submission_number": submission_count,
            "previous_submissions": previous_submissions
        }
    
    return {
        "can_submit": True,
        "reason": "",
        "submission_number": submission_count + 1,
        "previous_submissions": previous_submissions
    }


def _build_repeat_submission_condition(
    assessment: Assessment,
    phone: str,
    name: str = "",
    anonymous_device_id: Optional[str] = None,
    exclude_submission_id: Optional[int] = None,
):
    """构建重复提交判断条件，只统计已完成提交。"""
    conditions = [
        Submission.assessment_id == assessment.id,
        Submission.status == "completed",
    ]

    if assessment.anonymous_mode:
        conditions.append(Submission.anonymous_device_id == (anonymous_device_id or "").strip())
    elif assessment.repeat_check_by == "phone_name":
        conditions.extend([
            Submission.candidate_phone == phone,
            Submission.candidate_name == name,
        ])
    else:
        conditions.append(Submission.candidate_phone == phone)

    if exclude_submission_id is not None:
        conditions.append(Submission.id != exclude_submission_id)

    return and_(*conditions)


def _format_repeat_interval_reason(repeat_interval_hours: int, last_submitted_at: datetime) -> Optional[str]:
    """返回提交间隔拦截原因；未触发间隔限制时返回 None。"""
    hours_since = (datetime.now() - last_submitted_at).total_seconds() / 3600
    if hours_since >= repeat_interval_hours:
        return None

    remaining_hours = repeat_interval_hours - hours_since
    if remaining_hours < 1:
        remaining_text = f"{int(remaining_hours * 60)}分钟"
    else:
        remaining_text = f"{int(remaining_hours)}小时"
    return f"距上次提交不足{repeat_interval_hours}小时，请{remaining_text}后再试"


async def _validate_submission_repeat_rules_before_complete(
    session: Session,
    submission: Submission,
) -> None:
    """最终提交前再次校验重复规则，防止多开页面绕过开始前检查。"""
    assessment = session.get(Assessment, submission.assessment_id)
    if not assessment:
        raise ValueError("测评不存在")

    if assessment.anonymous_mode and not (submission.anonymous_device_id or "").strip():
        raise ValueError("匿名设备标识缺失，请刷新页面后重试")

    condition = _build_repeat_submission_condition(
        assessment,
        submission.candidate_phone,
        submission.candidate_name,
        anonymous_device_id=submission.anonymous_device_id,
        exclude_submission_id=submission.id,
    )
    statement = select(Submission).where(condition).order_by(Submission.submitted_at.desc())
    completed_submissions = session.exec(statement).all()
    completed_count = len(completed_submissions)

    if (assessment.anonymous_mode or not assessment.allow_repeat) and completed_count > 0:
        raise ValueError("该测评不允许重复提交")

    if assessment.repeat_interval_hours > 0 and completed_submissions:
        last_submission = completed_submissions[0]
        if last_submission.submitted_at:
            interval_reason = _format_repeat_interval_reason(
                assessment.repeat_interval_hours,
                last_submission.submitted_at,
            )
            if interval_reason:
                raise ValueError(interval_reason)

    if assessment.max_submissions > 0 and completed_count >= assessment.max_submissions:
        raise ValueError(f"已达到最大提交次数({assessment.max_submissions}次)")


async def increment_view_count(session: Session, assessment_id: int) -> None:
    """增加浏览量统计."""
    assessment = session.get(Assessment, assessment_id)
    if assessment:
        assessment.view_count = (assessment.view_count or 0) + 1
        session.add(assessment)
        session.commit()


async def increment_start_count(session: Session, assessment_id: int) -> None:
    """增加开始测评数统计."""
    assessment = session.get(Assessment, assessment_id)
    if assessment:
        assessment.start_count = (assessment.start_count or 0) + 1
        session.add(assessment)
        session.commit()


async def create_submission(
    session: Session,
    assessment_id: int,
    data: dict,
    questionnaire_id_override: Optional[int] = None
) -> Submission:
    """创建提交记录（候选人开始测评）."""
    # 获取测评信息
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise ValueError("测评不存在")
    
    code = generate_submission_code()
    
    # ⭐ 提取 custom_data 中的关键字段（如果存在）
    custom_data = data.get("custom_data", {})
    if not isinstance(custom_data, dict):
        custom_data = {}
    
    # V45: 调试日志 - 查看传入的数据
    print(f"[create_submission] 传入数据: {data}")
    print(f"[create_submission] custom_data: {custom_data}")
    
    # ⭐ 提取应聘岗位（可能在 data、custom_data 或其他字段中）
    # 支持多种字段名：target_position, position, 应聘岗位, text（标签为应聘岗位的自定义字段）
    target_position = (
        data.get("target_position") or 
        data.get("position") or
        custom_data.get("target_position") or
        custom_data.get("position") or
        custom_data.get("text")  # 自定义字段可能用 "text" 作为 name
    )
    # 如果还没找到，遍历 custom_data 找包含"岗位"的值
    if not target_position:
        for key, value in custom_data.items():
            if value and isinstance(value, str) and len(value) < 50:  # 合理长度的岗位名
                # 如果 key 包含 position 或 text，可能是岗位字段
                if 'position' in key.lower() or key.startswith('text'):
                    target_position = value
                    break
    print(f"[create_submission] target_position: {target_position}")
    
    # ⭐ V45: 提取性别（可能在 data 或 custom_data 中）
    gender = data.get("gender") or custom_data.get("gender")
    print(f"[create_submission] gender: {gender}")
    
    # ⭐ 通过手机号+姓名双重校验查找候选人
    candidate_id = None
    candidate_name = data.get("candidate_name", "").strip()
    candidate_phone = data.get("candidate_phone", "").strip()
    
    if candidate_name and candidate_phone:
        # 查找匹配的候选人
        statement = select(Candidate).where(
            and_(
                Candidate.name == candidate_name,
                Candidate.phone == candidate_phone
            )
        )
        candidate = session.exec(statement).first()
        
        if candidate:
            candidate_id = candidate.id
            # 更新候选人的submission_id（关联最新的提交）
            # 这里暂不更新，因为一个候选人可能有多次测评
    
    submission_data = {
        **data,
        "code": code,
        "assessment_id": assessment_id,
        "questionnaire_id": questionnaire_id_override or assessment.questionnaire_id,
        "status": "in_progress",
        "candidate_id": candidate_id,  # ⭐ 关联候选人
        "target_position": target_position,  # ⭐ 确保应聘岗位字段正确保存
        "gender": gender,  # ⭐ V45: 确保性别字段正确保存
    }
    
    submission = Submission(**submission_data)
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission


async def get_submissions(
    session: Session,
    assessment_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None
) -> Tuple[List[Submission], int]:
    """获取提交记录列表，支持按问卷category过滤.
    
    Args:
        session: 数据库会话
        assessment_id: 测评ID（可选）
        status: 提交状态（可选）
        skip: 跳过数量
        limit: 返回数量
        category: 问卷分类过滤（professional/scored/survey/custom）
                  'custom' 表示获取所有非professional的问卷（scored + survey）
    """
    # 如果需要按category过滤，先获取符合条件的问卷ID列表
    questionnaire_ids = None
    if category:
        if category == 'custom':
            # ⭐ custom类别：获取所有非professional的问卷（scored + survey）
            q_statement = select(Questionnaire.id).where(Questionnaire.category.in_(['scored', 'survey']))
        else:
            q_statement = select(Questionnaire.id).where(Questionnaire.category == category)
        # ⭐ 修复：select(Questionnaire.id) 返回的是 int，不是对象
        questionnaire_ids = list(session.exec(q_statement).all())
        if not questionnaire_ids:
            return [], 0
    
    statement = select(Submission)
    count_statement = select(func.count()).select_from(Submission)
    
    if assessment_id:
        statement = statement.where(Submission.assessment_id == assessment_id)
        count_statement = count_statement.where(Submission.assessment_id == assessment_id)
    if status:
        statement = statement.where(Submission.status == status)
        count_statement = count_statement.where(Submission.status == status)
    if questionnaire_ids is not None:
        statement = statement.where(Submission.questionnaire_id.in_(questionnaire_ids))
        count_statement = count_statement.where(Submission.questionnaire_id.in_(questionnaire_ids))
    
    total = session.scalar(count_statement)
    
    statement = statement.offset(skip).limit(limit).order_by(Submission.started_at.desc())
    submissions = session.exec(statement).all()
    
    return list(submissions), total or 0


async def get_submission_by_id(session: Session, submission_id: int) -> Optional[Submission]:
    """根据ID获取单个提交记录."""
    statement = select(Submission).where(Submission.id == submission_id)
    return session.exec(statement).first()


async def get_submission_answers(session: Session, submission_id: int) -> dict:
    """获取提交记录的答案数据."""
    from app.models import SubmissionAnswer, Question
    
    # 查询答案记录
    statement = select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission_id)
    answer_records = session.exec(statement).all()
    
    # 构建答案字典: {question_id: {value, score}}
    answers = {}
    for ans in answer_records:
        # 获取题目信息
        question = session.get(Question, ans.question_id)
        answers[str(ans.question_id)] = {
            "value": ans.value,
            "score": ans.score,
            "question_text": question.text if question else None,
        }
    
    return answers


async def get_candidate_by_submission(session: Session, submission_id: int) -> Optional[dict]:
    """通过提交记录获取候选人信息."""
    from app.models import Candidate
    
    # 尝试通过 submission_id 关联查找候选人
    statement = select(Candidate).where(Candidate.submission_id == submission_id)
    candidate = session.exec(statement).first()
    
    if candidate:
        return {
            "name": candidate.name,
            "phone": candidate.phone,
        }
    
    return None


async def delete_submission(session: Session, submission_id: int) -> bool:
    """删除提交记录."""
    statement = select(Submission).where(Submission.id == submission_id)
    submission = session.exec(statement).first()
    
    if not submission:
        return False
    
    session.delete(submission)
    session.commit()
    return True


async def update_assessment(session: Session, assessment_id: int, data: dict) -> Optional[Assessment]:
    """更新测评配置."""
    assessment = session.get(Assessment, assessment_id)
    
    if not assessment:
        return None
    
    if "routing_config" in data:
        data["routing_config"] = await normalize_routing_config(session, data.get("routing_config"), strict=True)
    if data.get("anonymous_mode"):
        data["allow_repeat"] = False

    # 更新字段
    for key, value in data.items():
        if value is not None and hasattr(assessment, key):
            setattr(assessment, key, value)
    
    assessment.updated_at = datetime.now()
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    
    return assessment


async def delete_assessment(
    session: Session, 
    assessment_id: int,
    force_delete_submissions: bool = False
) -> dict:
    """
    删除测评（分发链接）.
    
    Args:
        session: 数据库会话
        assessment_id: 测评ID
        force_delete_submissions: 是否强制删除关联的提交记录
            - False: 如果有提交记录，返回错误信息，不删除
            - True: 删除分发链接及所有关联的提交记录
    
    Returns:
        dict: 包含删除结果的字典
    """
    assessment = session.get(Assessment, assessment_id)
    
    if not assessment:
        return {"success": False, "error": "测评不存在"}
    
    # 检查是否有关联的提交记录
    statement = select(Submission).where(Submission.assessment_id == assessment_id)
    submissions = session.exec(statement).all()
    submission_count = len(submissions)
    
    if submission_count > 0 and not force_delete_submissions:
        # 有提交记录但未强制删除，返回警告
        return {
            "success": False,
            "error": "has_submissions",
            "submission_count": submission_count,
            "message": f"该分发链接下有 {submission_count} 条提交记录，删除后数据将无法恢复。请确认是否继续删除？"
        }
    
    # 执行删除
    deleted_submissions = 0
    if submission_count > 0:
        for sub in submissions:
            session.delete(sub)
            deleted_submissions = submission_count
    
    session.delete(assessment)
    session.commit()
    
    return {
        "success": True,
        "deleted_submissions": deleted_submissions,
        "message": f"删除成功" + (f"，同时删除了 {deleted_submissions} 条提交记录" if deleted_submissions > 0 else "")
    }


async def submit_answers(session: Session, submission_code: str, answers: dict) -> Submission:
    """提交答案并计算得分."""
    statement = select(Submission).where(Submission.code == submission_code)
    submission = session.exec(statement).first()
    
    if not submission:
        raise ValueError("提交记录不存在")
    
    if submission.status == "completed":
        raise ValueError("该测评已完成，无法重复提交")

    await _validate_submission_repeat_rules_before_complete(session, submission)
    
    # 获取问卷信息
    questionnaire = session.get(Questionnaire, submission.questionnaire_id)
    if not questionnaire:
        raise ValueError("问卷不存在")
    
    # ⭐ 根据问卷类型调用对应的评分算法
    try:
        questionnaire_type = questionnaire.type.upper() if questionnaire.type else ''
        
        if questionnaire_type in ['MBTI', 'DISC', 'EPQ']:
            # 专业测评：使用专业评分算法
            # 获取题目数据以便评分算法能根据维度评分
            questions = questionnaire.questions_data.get('questions', [])
            result = score_professional_assessment(questionnaire_type, answers, questions)
            
            # 构建result_details用于前端展示
            if questionnaire_type == 'MBTI':
                result_details = {
                    'mbti_type': result.get('mbti_type'),
                    'mbti_description': result.get('mbti_description'),
                    'mbti_dimensions': result.get('mbti_dimensions')
                }
            elif questionnaire_type == 'DISC':
                result_details = {
                    'disc_type': result.get('disc_type'),
                    'disc_description': result.get('disc_description'),
                    'disc_dimensions': result.get('disc_dimensions')
                }
            elif questionnaire_type == 'EPQ':
                result_details = {
                    'personality_trait': result.get('personality_trait'),
                    'dimensions': result.get('dimensions')
                }
            
            submission.result_details = result_details
            submission.scores = result.get('raw_scores') or result.get('dimensions', {})
            submission.total_score = result.get('total_score', 0)
            submission.grade = result.get('grade', 'C')
            
        else:
            # 自定义问卷：使用新的评分算法
            questionnaire_dict = {
                "custom_type": questionnaire.custom_type,
                "scoring_config": questionnaire.scoring_config,
                "questions_data": questionnaire.questions_data
            }
            
            # 转换答案格式
            answers_list = []
            if isinstance(answers, dict):
                for q_id, answer_data in answers.items():
                    answers_list.append({
                        "question_id": q_id,
                        "answer": answer_data
                    })
            elif isinstance(answers, list):
                answers_list = answers
            
            # 使用新的评分算法
            result = calculate_custom_questionnaire_score(questionnaire_dict, answers_list)
            
            # 保存结果
            submission.result_details = {
                "custom_type": questionnaire.custom_type,
                "answers": result.get("detailed_answers", [])
            }
            submission.total_score = result.get("total_score")
            submission.max_score = result.get("max_score")
            submission.score_percentage = result.get("score_percentage")
            submission.grade = result.get("grade")
            submission.scores = {}  # 详细得分已在result_details中
        
        # 保存答案和状态
        submission.answers = answers
        submission.status = "completed"
        submission.submitted_at = datetime.now()
        
        # ⭐ 创建或关联候选人记录
        candidate = await _get_or_create_candidate(
            session, 
            submission.candidate_name,
            submission.candidate_phone,
            submission.candidate_email,
            submission.target_position,
            submission.gender  # V45: 传递性别
        )
        if candidate:
            submission.candidate_id = candidate.id
        
        session.add(submission)
        session.commit()
        session.refresh(submission)
        
    except ProfessionalScoringError as e:
        raise ValueError(f"评分失败: {str(e)}")
    except Exception as e:
        raise ValueError(f"提交失败: {str(e)}")
    
    return submission


async def _get_or_create_candidate(
    session: Session,
    name: str,
    phone: str,
    email: Optional[str] = None,
    position: Optional[str] = None,
    gender: Optional[str] = None  # V45: 添加性别参数
) -> Optional[Candidate]:
    """根据手机号获取或创建候选人记录.
    
    逻辑：
    1. 首先根据手机号查找已存在的候选人
    2. 如果存在，更新其信息（姓名、邮箱、岗位、性别）
    3. 如果不存在，创建新的候选人记录
    """
    if not phone:
        return None
    
    try:
        # 查找已存在的候选人
        statement = select(Candidate).where(Candidate.phone == phone)
        existing_candidate = session.exec(statement).first()
        
        if existing_candidate:
            # 更新候选人信息
            if name and name != existing_candidate.name:
                existing_candidate.name = name
            if email and email != existing_candidate.email:
                existing_candidate.email = email
            if position and position != existing_candidate.position:
                existing_candidate.position = position
            # V45: 更新性别
            if gender and gender != getattr(existing_candidate, 'gender', None):
                existing_candidate.gender = gender
            existing_candidate.updated_at = datetime.now()
            session.add(existing_candidate)
            return existing_candidate
        else:
            # 创建新候选人
            new_candidate = Candidate(
                name=name or "未知",
                phone=phone,
                email=email,
                position=position,
                gender=gender,  # V45: 保存性别
                status="completed"  # 已完成测评
            )
            session.add(new_candidate)
            session.flush()  # 获取ID但不提交
            return new_candidate
            
    except Exception as e:
        print(f"[候选人关联] 创建/更新候选人失败: {e}")
        return None


# ========== 统计与导出相关 ==========

async def get_questionnaire_answer_export(
    session: Session,
    questionnaire_id: int,
) -> Optional[Dict[str, Any]]:
    """获取问卷逐人答题明细导出数据."""
    from app.api.assessments.statistics_service import get_questionnaire_answer_export as _impl

    return await _impl(session, questionnaire_id)


async def get_submission_statistics(
    session: Session,
    category: Optional[str] = None,
    questionnaire_id: Optional[int] = None,
) -> dict:
    """获取提交记录统计数据."""
    from app.api.assessments.statistics_service import get_submission_statistics as _impl

    return await _impl(session, category, questionnaire_id)


async def get_question_answer_statistics(
    session: Session,
    questionnaire_id: int,
    trend_range: str = "week",
) -> dict:
    """获取问卷题目答案统计数据."""
    from app.api.assessments.statistics_service import get_question_answer_statistics as _impl

    return await _impl(session, questionnaire_id, trend_range=trend_range)


async def export_submissions_to_excel(
    session: Session,
    category: Optional[str] = None,
    questionnaire_id: Optional[int] = None,
) -> bytes:
    """导出提交记录为 Excel 文件."""
    from app.api.assessments.excel_export_service import export_submissions_to_excel as _impl

    return await _impl(session, category, questionnaire_id)
