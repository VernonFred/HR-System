"""Assessment submission lifecycle helpers."""
from datetime import datetime
from typing import Any, Dict, Optional
import random
import string

from sqlmodel import Session, select, and_

from app.models import Candidate
from app.models_assessment import Assessment, Questionnaire, Submission
from app.professional_scoring import (
    ProfessionalScoringError,
    score_custom_questionnaire,
    score_professional_assessment,
)
from app.custom_scoring import calculate_custom_questionnaire_score
from app.api.assessments.repeat_rules import (
    _build_repeat_submission_condition,
    _validate_submission_repeat_rules_before_complete,
)


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
