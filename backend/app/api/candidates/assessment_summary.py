"""候选人画像综合评价计算."""

import logging
from typing import Any, Dict, List, Optional

from app.api.candidates import schemas
from app.api.candidates.normalizers import _normalize_ai_insights
from app.services.resume_quality_analyzer import ResumeQualityAnalyzer

logger = logging.getLogger(__name__)


def _calculate_overall_assessment(
    assessments: List[schemas.AssessmentInfo],
    job_match: Optional[schemas.JobMatchInfo],
    ai_analysis: Optional[Dict[str, Any]] = None
) -> tuple[Optional[float], List[str], List[str]]:
    """计算综合评价.

    ⭐ V2优化: 多因子加权融合算法
    - 测评分(40%) + 岗位匹配(30%) + 完整度(15%) + 简历质量(15%)
    - 各维度权重可调整
    - 提供分数构成说明

    Args:
        assessments: 测评信息列表
        job_match: 岗位匹配信息
        ai_analysis: AI分析结果（包含candidate信息）

    Returns:
        (综合得分, 优势亮点, 改进建议)
    """
    strengths = []
    improvements = []

    # ⭐ 1. 测评加权平均分 (40%)
    # MBTI: 40%, DISC: 30%, EPQ: 30%
    assessment_weights = {
        "mbti": 0.40,
        "disc": 0.30,
        "epq": 0.30
    }

    assessment_score = 0
    actual_weight_sum = 0
    assessment_count = len(assessments)

    for a in assessments:
        # 检测测评类型
        test_type = None
        if a.questionnaire_type:
            test_type = a.questionnaire_type.lower()
        elif a.questionnaire_name:
            name_lower = a.questionnaire_name.lower()
            if "mbti" in name_lower:
                test_type = "mbti"
            elif "disc" in name_lower:
                test_type = "disc"
            elif "epq" in name_lower:
                test_type = "epq"

        if test_type and test_type in assessment_weights:
            weight = assessment_weights[test_type]
            score = a.score_percentage or a.total_score or 60
            assessment_score += score * weight
            actual_weight_sum += weight

    # 归一化 (如果只做了部分测评)
    if actual_weight_sum > 0:
        assessment_score = assessment_score / actual_weight_sum
    else:
        # 降级: 简单平均
        scores = [a.score_percentage or a.total_score or 60 for a in assessments if (a.score_percentage or a.total_score)]
        assessment_score = sum(scores) / len(scores) if scores else 60

    # ⭐ 2. 岗位匹配分 (30%)
    # 如果有匹配，使用匹配分；否则使用测评分
    match_score = job_match.match_score if job_match else assessment_score

    # ⭐ 3. 完整度加成 (15%)
    # 测评越全，加成越高
    completeness_bonus = 60  # 基准分

    if assessment_count == 1:
        completeness_bonus = 65  # 单测评
    elif assessment_count == 2:
        completeness_bonus = 75  # 双测评，有一定互补
    elif assessment_count >= 3:
        completeness_bonus = 85  # 三测评，数据全面

    # 如果有岗位匹配，额外加5分
    if job_match:
        completeness_bonus = min(completeness_bonus + 5, 95)

    # ⭐ 4. 简历质量分 (15%)
    # 🟢 P2-2: 使用ResumeQualityAnalyzer进行智能评分
    resume_score = 60  # 基准分
    has_resume = False

    if ai_analysis and ai_analysis.get("candidate"):
        candidate = ai_analysis["candidate"]
        # 使用实际字段判断是否已上传简历
        has_resume = bool(
            getattr(candidate, "resume_file_path", None)
            or getattr(candidate, "resume_original_name", None)
            or getattr(candidate, "resume_uploaded_at", None)
        )

        if has_resume:
            # 使用新的简历质量分析器
            resume_parsed_data = getattr(candidate, "resume_parsed_data", None)
            target_position = ai_analysis.get("target_position")

            if resume_parsed_data:
                try:
                    resume_analysis = ResumeQualityAnalyzer.analyze_resume_quality(
                        resume_parsed_data, target_position
                    )
                    resume_score = resume_analysis["quality_score"]
                    logger.info(f"📄 简历质量评分: {resume_score:.1f}")
                except Exception as e:
                    logger.warning(f"⚠️ 简历质量分析失败: {e}，使用默认分")
                    resume_score = 70  # 降级分数
            else:
                # 无解析数据时，使用简单评分
                resume_score = 70

    # ⭐ 综合计算
    overall_score = (
        assessment_score * 0.40 +
        match_score * 0.30 +
        completeness_bonus * 0.15 +
        resume_score * 0.15
    )

    overall_score = round(overall_score, 1)

    logger.debug(f"📊 综合评分: {overall_score:.1f} = "
                 f"测评({assessment_score:.1f}*0.4) + "
                 f"匹配({match_score:.1f}*0.3) + "
                 f"完整度({completeness_bonus:.1f}*0.15) + "
                 f"简历({resume_score:.1f}*0.15)")

    # ⭐ 生成优势和改进建议
    # 1. 基于测评表现
    if assessment_score >= 80:
        strengths.append(f"测评表现优秀（{assessment_score:.1f}分，{assessment_count}项测评）")
    elif assessment_score >= 60:
        strengths.append(f"测评表现良好（{assessment_score:.1f}分，{assessment_count}项测评）")
    else:
        improvements.append(f"测评得分偏低（{assessment_score:.1f}分），建议加强训练")

    # 2. 基于岗位匹配
    if job_match:
        if job_match.match_score >= 80:
            strengths.append(f"与{job_match.profile_name}岗位高度匹配（{job_match.match_score:.1f}分）")
        elif job_match.match_score >= 60:
            strengths.append(f"与{job_match.profile_name}岗位基本匹配（{job_match.match_score:.1f}分）")
        else:
            improvements.append(f"与{job_match.profile_name}岗位匹配度较低，建议补充经验")

        # 分析维度得分 (只取前2个极端)
        sorted_dims = sorted(job_match.dimension_scores, key=lambda d: d.score, reverse=True)
        if len(sorted_dims) > 0 and sorted_dims[0].score >= 85:
            strengths.append(f"{sorted_dims[0].name}表现突出（{sorted_dims[0].score:.1f}分）")
        if len(sorted_dims) > 0 and sorted_dims[-1].score < 60:
            improvements.append(f"{sorted_dims[-1].name}需要提升（{sorted_dims[-1].score:.1f}分）")

    # 3. 基于完整度
    if assessment_count >= 3:
        strengths.append(f"测评数据全面（完成{assessment_count}项测评）")

    # 4. 基于简历质量
    if has_resume and resume_score >= 85:
        strengths.append("简历内容完整详实")
    elif not has_resume:
        improvements.append("建议上传简历，提供更全面的背景信息")

    # 5. 如果有AI分析，追加AI生成的内容
    if ai_analysis:
        candidate = ai_analysis.get("candidate")
        candidate_name = getattr(candidate, "name", None)
        ai_strengths = _normalize_ai_insights(ai_analysis.get("strengths", []), candidate_name)
        ai_risks = _normalize_ai_insights(ai_analysis.get("risks", []), candidate_name)
        # 追加（不覆盖）AI分析的前2条
        if ai_strengths:
            strengths.extend(ai_strengths[:2])
        if ai_risks:
            improvements.extend(ai_risks[:2])

    # 6. 默认建议
    if not strengths:
        strengths.append("基础资料完整")

    if not improvements:
        improvements.append("继续保持，持续提升")

    return overall_score, strengths[:5], improvements[:5]  # 最多返回5条
