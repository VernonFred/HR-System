"""问卷统计与逐人答题明细导出服务."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models_assessment import Questionnaire, Submission
from app.api.assessments.statistics_normalizers import (
    _normalize_questionnaire_questions,
    _normalize_submission_answers,
)


# ========== 统计相关 ==========

async def get_questionnaire_answer_export(
    session: Session,
    questionnaire_id: int,
) -> Optional[Dict[str, Any]]:
    """获取问卷逐人答题明细导出数据."""
    from app.api.assessments.answer_export_service import get_questionnaire_answer_export as _impl

    return await _impl(session, questionnaire_id)


async def get_submission_statistics(
    session: Session,
    category: Optional[str] = None,
    questionnaire_id: Optional[int] = None
) -> dict:
    """获取提交记录统计数据."""
    from sqlmodel import select, func

    # 构建查询基础
    base_query = select(Submission).where(Submission.status == "completed")

    # 如果指定了问卷ID
    if questionnaire_id:
        base_query = base_query.where(Submission.questionnaire_id == questionnaire_id)

    # 如果指定了category，需要先获取对应的问卷ID列表
    if category:
        q_statement = select(Questionnaire.id).where(Questionnaire.category == category)
        questionnaire_ids = session.exec(q_statement).all()
        if questionnaire_ids:
            base_query = base_query.where(Submission.questionnaire_id.in_(questionnaire_ids))
        else:
            return {
                "total_submissions": 0,
                "average_score": 0,
                "pass_rate": 0,
                "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0},
                "submissions": []
            }

    # 执行查询
    all_submissions = session.exec(base_query).all()

    # 计算统计数据
    total = len(all_submissions)

    if total == 0:
        return {
            "total_submissions": 0,
            "average_score": 0,
            "pass_rate": 0,
            "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0},
            "submissions": []
        }

    # 计算平均分（过滤掉 None 值）
    valid_scores = [s.total_score for s in all_submissions if s.total_score is not None]
    average_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

    # 计算合格率（假设60分及格）
    pass_count = len([s for s in valid_scores if s >= 60])
    pass_rate = (pass_count / len(valid_scores) * 100) if valid_scores else 0

    # 计算等级分布
    grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in all_submissions:
        grade = (s.grade or "D").upper()
        if grade in grade_distribution:
            grade_distribution[grade] += 1

    # 构建返回数据
    return {
        "total_submissions": total,
        "average_score": round(average_score, 2),
        "pass_rate": round(pass_rate, 2),
        "grade_distribution": grade_distribution,
        "grade_percentages": {
            grade: round(count / total * 100, 1) if total > 0 else 0
            for grade, count in grade_distribution.items()
        },
        "submissions": [
            {
                "id": s.id,
                "candidate_name": s.candidate_name,
                "candidate_phone": s.candidate_phone,
                "total_score": s.total_score,
                "grade": s.grade,
                "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None
            }
            for s in all_submissions[:100]  # 限制返回数量
        ]
    }


def _get_scale_label(score: int, scale_min: int, scale_max: int, min_label: str, max_label: str) -> str:
    """
    V46: 智能生成量表题的描述文本

    支持多种常见量表类型：满意度、同意度、频率、程度等
    """
    total_levels = scale_max - scale_min + 1
    position = score - scale_min  # 0-based position

    # 预定义的量表描述模板
    SCALE_TEMPLATES = {
        ('满意', 5): ['非常不满意', '不太满意', '一般', '比较满意', '非常满意'],
        ('满意', 4): ['不满意', '一般', '满意', '非常满意'],
        ('同意', 5): ['非常不同意', '不同意', '一般', '同意', '非常同意'],
        ('频率', 5): ['从不', '很少', '有时', '经常', '总是'],
        ('符合', 5): ['完全不符合', '不太符合', '一般', '比较符合', '完全符合'],
        ('重要', 5): ['非常不重要', '不太重要', '一般', '比较重要', '非常重要'],
    }

    labels = None
    for (keyword, levels), template in SCALE_TEMPLATES.items():
        if levels == total_levels and (keyword in min_label or keyword in max_label):
            labels = template
            break

    if not labels and min_label and max_label:
        if total_levels == 5:
            labels = [min_label, f'偏向{min_label[:2]}', '一般', f'偏向{max_label[:2]}', max_label]
        elif total_levels == 3:
            labels = [min_label, '一般', max_label]
        else:
            if score == scale_min:
                return f"{score}分 ({min_label})"
            elif score == scale_max:
                return f"{score}分 ({max_label})"
            return f"{score}分"

    if not labels:
        if total_levels == 5:
            labels = ['很低', '较低', '一般', '较高', '很高']
        else:
            return f"{score}分"

    if labels and 0 <= position < len(labels):
        return f"{score}分 ({labels[position]})"
    return f"{score}分"


async def get_question_answer_statistics(
    session: Session,
    questionnaire_id: int,
    trend_range: str = "week"
) -> dict:
    """
    V42: 获取问卷的题目答案统计数据.

    返回每道题的选项分布统计，用于问卷统计页面的数据可视化。
    """
    from sqlmodel import select
    from collections import Counter
    from datetime import datetime, timedelta, timezone
    import re

    # 获取问卷信息
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return {"error": "问卷不存在", "questions": []}

    submissions = _select_export_submissions(session, questionnaire_id)

    total_submissions = len(submissions)

    if total_submissions == 0:
        return {
            "questionnaire_id": questionnaire_id,
            "questionnaire_name": questionnaire.name,
            "questionnaire_type": questionnaire.type,
            "questionnaire_category": questionnaire.category,
            "total_submissions": 0,
            "completion_rate": 0,
            "average_score": None,
            "average_duration_minutes": None,
            "questions": [],
            "daily_trend": [],
            "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0}
        }

    questions_data = _normalize_questionnaire_questions(questionnaire)

    # 统计每道题的答案分布
    question_stats = []

    for q_idx, question in enumerate(questions_data):
        # 跳过非字典类型的项
        if not isinstance(question, dict):
            continue

        q_id = question.get("id", str(q_idx + 1))
        q_text = question.get("text", question.get("question", f"问题 {q_idx + 1}"))
        q_type = question.get("type", "single")  # single, multiple, text, rating
        options = question.get("options", [])

        # 收集所有答案
        answer_counts = Counter()
        text_answers = []
        answered_submission_count = 0
        total_selections = 0

        for sub in submissions:
            answers = _normalize_submission_answers(sub.answers)

            answer = answers.get(q_id) or answers.get(str(q_idx))

            if answer is None:
                continue

            if q_type in ("text", "textarea"):
                # 文本题收集答案
                if isinstance(answer, str) and answer.strip():
                    answered_submission_count += 1
                    text_answers.append(answer.strip())
            elif q_type in ("multiple", "checkbox") or isinstance(answer, list):
                # 多选题
                selected_answers = answer if isinstance(answer, list) else [answer]
                selected_answers = [
                    a for a in selected_answers
                    if a is not None and (not isinstance(a, str) or a.strip())
                ]
                if selected_answers:
                    answered_submission_count += 1
                    total_selections += len(selected_answers)
                for a in selected_answers:
                    answer_counts[str(a)] += 1
            else:
                # 单选题
                answered_submission_count += 1
                total_selections += 1
                answer_counts[str(answer)] += 1

        # 构建选项统计
        option_stats = []
        total_answers = answered_submission_count
        if q_type in ("text", "textarea"):
            total_selections = len(text_answers)
        elif total_selections == 0:
            total_selections = sum(answer_counts.values())
        text_summary = None
        percentage_denominator = total_answers or total_submissions

        if q_type == "text" or q_type == "textarea":
            # 文本题：智能聚合与分组
            empty_texts = {
                "无", "没有", "没有意见", "无意见", "无建议", "暂无", "无想法", "无改进",
                "没", "没意见", "没建议", "无所谓", "没有建议", "没有改进"
            }
            short_tag_max_len = 10

            def normalize_text(value: str) -> str:
                text = value.strip()
                text = re.sub(r"\s+", "", text)
                text = text.strip("，。,.!?！？；;：:、\"'“”‘’()（）[]【】{}")
                return text

            tag_counts = Counter()
            long_map = {}
            empty_count = 0

            for raw in text_answers:
                normalized = normalize_text(raw)
                if not normalized:
                    continue
                lower = normalized.lower()
                if lower in empty_texts:
                    empty_count += 1
                    continue
                if len(normalized) <= short_tag_max_len:
                    tag_counts[normalized] += 1
                    continue
                key = normalized
                if key in long_map:
                    long_map[key]["count"] += 1
                else:
                    long_map[key] = {"text": raw.strip(), "count": 1}

            tags = [{"text": t, "count": c} for t, c in tag_counts.most_common()]
            long_answers = sorted(
                long_map.values(),
                key=lambda item: (-item["count"], -len(item["text"]))
            )

            text_summary = {
                "tags": tags,
                "long_answers": long_answers,
                "empty_count": empty_count,
                "total_answers": len(text_answers)
            }
        elif q_type == "scale" or q_type == "rating":
            # V46: 量表题/评分题 - 根据 scale 配置生成选项统计
            scale_config = question.get("scale", {})
            scale_min = scale_config.get("min", 1)
            scale_max = scale_config.get("max", 5)
            min_label = scale_config.get("minLabel", "")
            max_label = scale_config.get("maxLabel", "")

            for score in range(scale_min, scale_max + 1):
                count = answer_counts.get(str(score), 0)
                percentage = round(count / percentage_denominator * 100, 1) if percentage_denominator > 0 else 0

                # 使用智能标签生成
                label = _get_scale_label(score, scale_min, scale_max, min_label, max_label)

                option_stats.append({
                    "index": score - scale_min,
                    "text": label,
                    "count": count,
                    "percentage": percentage
                })
        else:
            # 选择题：统计每个选项的选择次数
            for opt_idx, opt in enumerate(options):
                if isinstance(opt, dict):
                    opt_text = opt.get("text", opt.get("label", str(opt_idx)))
                    opt_value = str(opt.get("value", opt_idx))
                else:
                    opt_text = str(opt)
                    opt_value = str(opt_idx)

                # 确保 opt_text 是字符串
                if not isinstance(opt_text, str):
                    opt_text = str(opt_text)

                # 尝试匹配答案（可能是索引、值或文本）
                count = answer_counts.get(str(opt_idx), 0)
                count += answer_counts.get(opt_value, 0)
                if opt_text != opt_value and opt_text != str(opt_idx):
                    count += answer_counts.get(opt_text, 0)

                percentage = round(count / percentage_denominator * 100, 1) if percentage_denominator > 0 else 0

                option_stats.append({
                    "index": opt_idx,
                    "text": opt_text,
                    "count": count,
                    "percentage": percentage
                })

        question_stats.append({
            "id": q_id,
            "index": q_idx + 1,
            "text": q_text,
            "type": q_type,
            "total_answers": total_answers,
            "total_selections": total_selections,
            "options": option_stats,
            "text_summary": text_summary
        })

    # 计算平均分（仅评分问卷）
    average_score = None
    if questionnaire.category == "scored":
        valid_scores = [s.total_score for s in submissions if s.total_score is not None]
        if valid_scores:
            average_score = round(sum(valid_scores) / len(valid_scores), 1)

    # 计算平均用时
    average_duration = None
    durations = []
    for sub in submissions:
        if sub.started_at and sub.submitted_at:
            duration = (sub.submitted_at - sub.started_at).total_seconds() / 60
            if 0 < duration < 120:  # 排除异常值
                durations.append(duration)
    if durations:
        average_duration = round(sum(durations) / len(durations), 1)

    # 计算每日提交趋势（按本地时间统计）
    daily_trend = []
    local_tz = timezone(timedelta(hours=8))

    def to_local_date(dt: datetime) -> Optional[datetime.date]:
        if not dt:
            return None
        # SQLite 中的时间多数为本地时间（无时区），默认按本地时间处理
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=local_tz)
        return dt.astimezone(local_tz).date()

    today = datetime.now(local_tz).date()

    def build_week_days(base_date: datetime.date) -> list[datetime.date]:
        monday = base_date - timedelta(days=base_date.weekday())
        return [monday + timedelta(days=i) for i in range(7)]

    def build_month_days(base_date: datetime.date) -> list[datetime.date]:
        start = base_date - timedelta(days=29)
        return [start + timedelta(days=i) for i in range(30)]

    if trend_range == "month":
        days = build_month_days(today)
    elif trend_range == "week":
        days = build_week_days(today)
    else:
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    for day in days:
        count = sum(
            1
            for s in submissions
            if s.submitted_at and to_local_date(s.submitted_at) == day
        )
        daily_trend.append({
            "date": day.isoformat(),
            "count": count
        })

    # 等级分布
    grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
    for sub in submissions:
        grade = (sub.grade or "D").upper()
        if grade in grade_distribution:
            grade_distribution[grade] += 1

    return {
        "questionnaire_id": questionnaire_id,
        "questionnaire_name": questionnaire.name,
        "questionnaire_type": questionnaire.type,
        "questionnaire_category": questionnaire.category,
        "total_submissions": total_submissions,
        "completion_rate": 100,  # 只统计已完成的
        "average_score": average_score,
        "average_duration_minutes": average_duration,
        "questions": question_stats,
        "daily_trend": daily_trend,
        "grade_distribution": grade_distribution,
        "grade_percentages": {
            grade: round(count / total_submissions * 100, 1) if total_submissions > 0 else 0
            for grade, count in grade_distribution.items()
        }
    }
