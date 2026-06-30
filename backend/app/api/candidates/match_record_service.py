"""Candidate job-profile match record generation."""
import json
import logging

from sqlmodel import Session, select, and_

from app.models import JobProfile, ProfileMatch
from app.models_assessment import Questionnaire, Submission
from .dimension_mapping import calculate_dimension_score_from_assessments

logger = logging.getLogger(__name__)


async def _create_match_record(
    session: Session,
    job_profile: JobProfile,
    submission: Submission
) -> ProfileMatch:
    """创建岗位匹配记录.

    ⭐ V2优化: 基于维度映射的智能匹配算法
    - 不再使用统一的总分百分比
    - 建立测评维度↔岗位维度的映射关系
    - 真正利用测评的维度数据

    Args:
        session: 数据库会话
        job_profile: 岗位画像
        submission: 测评提交记录 (可能只是最新的一条)

    Returns:
        匹配记录
    """
    # 解析岗位画像的能力维度
    dimensions = json.loads(job_profile.dimensions) if job_profile.dimensions else []

    # ⭐ 获取候选人的所有测评记录（用于跨测评计算）
    candidate_id = submission.candidate_id
    all_submissions_stmt = select(Submission).where(
        and_(
            Submission.candidate_id == candidate_id,
            Submission.status == "completed"
        )
    )
    all_submissions = session.exec(all_submissions_stmt).all()

    # 构建测评数据列表（供维度映射算法使用）
    candidate_assessments = []
    for sub in all_submissions:
        # 获取问卷信息，判断测评类型
        questionnaire = session.get(Questionnaire, sub.questionnaire_id)
        test_type = None
        if questionnaire and questionnaire.type:
            # 统一转小写
            test_type = questionnaire.type.lower()

        # 解析result_details
        result_details = sub.result_details
        if isinstance(result_details, str):
            try:
                result_details = json.loads(result_details)
            except json.JSONDecodeError:
                result_details = {}

        candidate_assessments.append({
            "test_type": test_type,
            "result_details": result_details,
            "score_percentage": sub.score_percentage
        })

    logger.info(f"🔍 岗位匹配: 候选人{candidate_id}有{len(candidate_assessments)}项测评, "
                f"测评类型: {[a['test_type'] for a in candidate_assessments]}")

    # ⭐ 基于维度映射计算各维度得分
    dimension_scores = {}
    total_weighted_score = 0.0
    total_weight = 0.0

    for dim in dimensions:
        dim_name = dim.get("name", "")
        dim_weight = float(dim.get("weight", 0))

        # ⭐ 核心: 使用维度映射算法计算得分
        dim_score = calculate_dimension_score_from_assessments(
            dim_name,
            candidate_assessments
        )

        dimension_scores[dim_name] = {
            "score": round(dim_score, 1),
            "weight": dim_weight,
            "weighted_score": dim_score * (dim_weight / 100)
        }

        total_weighted_score += dim_score * (dim_weight / 100)
        total_weight += dim_weight

    # 计算总匹配分数
    if total_weight > 0:
        match_score = total_weighted_score / (total_weight / 100)
    else:
        # 降级: 使用测评平均分
        scores = [a["score_percentage"] for a in candidate_assessments if a["score_percentage"]]
        match_score = sum(scores) / len(scores) if scores else 60.0

    match_score = round(match_score, 1)

    # 生成AI分析（占位，可以后续增强）
    ai_analysis = f"候选人在 {job_profile.name} 岗位的综合匹配度为 {match_score}分。"

    # 添加维度分析
    if dimension_scores:
        top_dims = sorted(dimension_scores.items(), key=lambda x: x[1]["score"], reverse=True)[:3]
        top_names = [f"{name}({score['score']}分)" for name, score in top_dims]
        ai_analysis += f" 优势维度: {', '.join(top_names)}。"

    logger.info(f"✅ 岗位匹配: {job_profile.name} 匹配度={match_score}, "
                f"维度数={len(dimension_scores)}")

    # 创建匹配记录
    match_record = ProfileMatch(
        profile_id=job_profile.id,
        submission_id=submission.id,
        match_score=match_score,
        dimension_scores=dimension_scores,
        ai_analysis=ai_analysis
    )

    session.add(match_record)
    session.commit()
    session.refresh(match_record)

    return match_record
