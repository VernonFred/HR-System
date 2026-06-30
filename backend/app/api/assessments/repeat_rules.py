"""问卷提交重复校验规则."""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select, and_

from app.models_assessment import Assessment, Submission


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
