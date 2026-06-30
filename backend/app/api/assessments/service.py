"""问卷/测评管理 - 业务逻辑."""
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from sqlmodel import Session, select, func
import random
import string

from app.models_assessment import Questionnaire, Assessment, Submission
from app.api.assessments.routing_service import normalize_routing_config, resolve_questionnaire_id
from app.api.assessments.submission_service import (
    check_can_submit,
    create_submission,
    generate_submission_code,
    submit_answers,
)


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


# ========== 提交记录管理 ==========

# ========== 提交记录管理 ==========

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


# ========== 统计与导出相关 ==========

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
