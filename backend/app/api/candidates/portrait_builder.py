"""Candidate portrait construction workflow."""
import asyncio
import json
import logging
import time
from typing import Dict, Optional

from fastapi import HTTPException, status as http_status
from sqlmodel import Session, select, and_

from app.models import Candidate, JobProfile, ProfileMatch
from app.models_assessment import Assessment, Questionnaire, Submission
from app.services.cross_validation import CrossValidationService
from app.services.job_recommender import JobRecommender

from . import schemas
from .assessment_summary import _calculate_overall_assessment
from .cache_manager import compute_data_version, get_cached_portrait, save_portrait_cache
from .dimension_mapping import calculate_dimension_score_from_assessments
from .dimension_parser import build_dimension_scores, clean_summary_points
from .ai_analyzer import build_default_analysis, generate_ai_analysis
from .match_record_service import _create_match_record
from .portrait_content_builder import build_competencies, build_quick_tags, build_summary_points
from .normalizers import (
    _combine_ai_first,
    _normalize_ai_insights,
    _normalize_list_field,
    _normalize_position_items,
    _submission_result_payload,
)

logger = logging.getLogger(__name__)


async def build_candidate_portrait(
    session: Session,
    candidate_id: int,
    force_refresh: bool = False,  # 强制刷新（跳过缓存）
    analysis_level: str = "pro"
) -> schemas.CandidatePortrait:
    """构建候选人完整画像.

    整合以下数据源：
    1. 候选人基本信息
    2. 测评记录（通过 candidate_id 关联）
    3. 岗位画像匹配（通过 target_position 关联）

    分析模式：
    - 当前统一使用 pro 单模型画像生成。
    - 旧的 expert 参数会在函数入口归一为 pro，避免生成重复缓存和重复话术。

    缓存策略：
    - 首次访问：调用AI分析，结果存入缓存
    - 再次访问：直接返回缓存（毫秒级响应）
    - 数据变更：自动失效缓存，重新分析

    Args:
        session: 数据库会话
        candidate_id: 候选人ID
        force_refresh: 是否强制刷新（跳过缓存）
        analysis_level: 画像分析模式（当前统一归一为 pro）

    Returns:
        完整的候选人画像
    """
    start_time = time.time()
    # 单模型模式下不再区分 pro/expert；旧请求统一复用默认画像缓存。
    analysis_level = "pro"

    # 1. 获取候选人基本信息
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="候选人不存在"
        )

    # 获取最新提交记录（用于计算版本）
    latest_sub_stmt = select(Submission).where(
        Submission.candidate_id == candidate_id
    ).order_by(Submission.submitted_at.desc())
    latest_submission_for_version = session.exec(latest_sub_stmt).first()

    # 获取关联的岗位画像（用于计算版本）
    job_profile_for_version = None
    if latest_submission_for_version and latest_submission_for_version.target_position:
        job_profile_for_version = session.exec(
            select(JobProfile).where(
                JobProfile.name == latest_submission_for_version.target_position
            )
        ).first()

    # 计算数据版本
    data_version = compute_data_version(candidate, latest_submission_for_version, job_profile_for_version)

    # 2. 检查缓存（除非强制刷新）- V38: 按级别缓存
    if not force_refresh:
        cached_portrait = get_cached_portrait(session, candidate_id, data_version, analysis_level)
        if cached_portrait:
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"⚡ 候选人{candidate_id}: 从{analysis_level}缓存返回画像 (耗时: {elapsed:.1f}ms)")
            return cached_portrait

    logger.info(f"🔄 候选人{candidate_id}: 开始生成新画像 (版本: {data_version})")

    # 获取岗位信息 - V5: 优先使用简历中的岗位（更准确）
    gender = None
    target_position = None
    resume_target_position = None

    # 1. 从简历中获取岗位（如果有简历）
    if candidate.resume_parsed_data:
        parsed = candidate.resume_parsed_data
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except:
                parsed = {}
        if isinstance(parsed, dict):
            resume_target_position = parsed.get("target_position", "")
            if resume_target_position:
                logger.info(f"📄 从简历中获取到岗位信息: {resume_target_position}")

    # 2. 从 candidate.position 获取（测评时填写的）
    candidate_position = getattr(candidate, 'position', None)

    # 3. 从 submission 获取（兼容旧数据）
    submission_position = None
    if candidate.submission_id:
        linked_submission = session.get(Submission, candidate.submission_id)
        if linked_submission:
            gender = getattr(linked_submission, 'gender', None)
            submission_position = getattr(linked_submission, 'target_position', None)

    # V5: 优先使用简历中的岗位，因为简历通常更准确
    # 如果简历岗位和测评岗位不同，记录日志
    if resume_target_position:
        target_position = resume_target_position
        if candidate_position and candidate_position != resume_target_position:
            logger.info(f"⚠️ 简历岗位({resume_target_position})与测评岗位({candidate_position})不一致，使用简历岗位")
    elif candidate_position:
        target_position = candidate_position
    elif submission_position:
        target_position = submission_position

    basic_info = schemas.CandidateBasicInfo(
        id=candidate.id,
        name=candidate.name,
        phone=candidate.phone or "",
        email=candidate.email,
        gender=gender,
        target_position=target_position,
        created_at=candidate.created_at
    )

    # 3. 获取所有测评记录
    statement = select(Submission).where(
        Submission.candidate_id == candidate_id
    ).order_by(Submission.submitted_at.desc())

    submissions = session.exec(statement).all()

    assessments_info = []
    latest_submission: Optional[Submission] = None

    for submission in submissions:
        if submission.status == "completed":
            # 获取测评和问卷名称
            assessment = session.get(Assessment, submission.assessment_id)
            questionnaire = session.get(Questionnaire, submission.questionnaire_id)

            # 解析该测评的人格维度数据
            submission_dims = []
            if submission.result_details:
                result_details = submission.result_details if isinstance(submission.result_details, dict) else json.loads(submission.result_details or "{}")
                from app.api.candidates.dimension_parser import parse_personality_dimensions
                submission_dims = parse_personality_dimensions(result_details)

            assessment_info = schemas.AssessmentInfo(
                submission_id=submission.id,
                assessment_name=assessment.name if assessment else "未知测评",
                questionnaire_name=questionnaire.name if questionnaire else "未知问卷",
                questionnaire_type=questionnaire.type if questionnaire else None,  # 添加问卷类型
                total_score=submission.total_score,
                max_score=submission.max_score,
                score_percentage=submission.score_percentage,
                grade=submission.grade,
                completed_at=submission.submitted_at,
                personality_dimensions=submission_dims  # 添加该测评的维度数据
            )
            assessments_info.append(assessment_info)

            # 保存最新的完成提交（用于匹配分析）
            if not latest_submission:
                latest_submission = submission

    # 3. 获取岗位匹配信息
    job_match_info = None
    job_profile = None  # V39: 在外部初始化，用于后续提取能力维度

    # ⭐ 确定用于岗位匹配的目标岗位（优先测评数据，其次简历数据）
    match_target_position = None
    if latest_submission and latest_submission.target_position:
        match_target_position = latest_submission.target_position
    elif target_position:  # 使用前面从简历中获取的岗位信息
        match_target_position = target_position
        logger.info(f"📄 使用简历中的岗位信息进行匹配: {match_target_position}")

    if latest_submission and match_target_position:
        # 通过 target_position 查找对应的岗位画像
        statement = select(JobProfile).where(
            and_(
                JobProfile.name == match_target_position,
                JobProfile.status == "active"
            )
        )
        job_profile = session.exec(statement).first()

        if job_profile:
            # 查找或创建匹配记录
            match_record = session.exec(
                select(ProfileMatch).where(
                    and_(
                        ProfileMatch.profile_id == job_profile.id,
                        ProfileMatch.submission_id == latest_submission.id
                    )
                )
            ).first()

            if not match_record:
                # 创建新的匹配记录（带超时控制）
                try:
                    match_record = await asyncio.wait_for(
                        _create_match_record(session, job_profile, latest_submission),
                        timeout=15.0  # 15秒超时
                )
                except asyncio.TimeoutError:
                    print(f"⚠️ 创建匹配记录超时(15s)")
                    match_record = None
                except Exception as e:
                    print(f"❌ 创建匹配记录失败: {e}")
                    match_record = None

            # 如果有有效的匹配记录，才构建job_match_info
            if match_record:
                # 构建维度得分
                dimension_scores = build_dimension_scores(
                    job_profile,
                    match_record.dimension_scores or {}
                )

                job_match_info = schemas.JobMatchInfo(
                    profile_id=job_profile.id,
                    profile_name=job_profile.name,
                    department=job_profile.department,
                    match_score=match_record.match_score if match_record.match_score is not None else 0.0,
                    dimension_scores=dimension_scores,
                    ai_analysis=match_record.ai_analysis,
                    matched_at=match_record.created_at
                )

    # ⭐ V39: 从岗位画像中提取能力维度名称，用于AI分析
    custom_job_competencies = None
    if job_profile:
        try:
            dimensions = json.loads(job_profile.dimensions) if job_profile.dimensions else []
            if dimensions:
                custom_job_competencies = [d.get("name", "") for d in dimensions if d.get("name")]
                logger.info(f"📋 从岗位画像获取能力维度: {custom_job_competencies}")
        except Exception as e:
            logger.warning(f"⚠️ 解析岗位画像维度失败: {e}")

    # 4. 调用AI生成完整分析（带超时控制）
    is_default_analysis = False  # 标记是否使用默认分析
    ai_model_used = "deepseek-v4-pro"  # 使用的AI模型
    fallback_reason = None  # 🟢 P1-2: 降级原因
    ai_start_time = time.time()

    timeout_seconds = 120.0

    logger.info(f"🎯 开始AI分析: 级别={analysis_level}, 超时={timeout_seconds}s")

    try:
        # 设置超时（根据分析级别调整）
        # V39: 传递自定义岗位能力维度
        ai_analysis = await asyncio.wait_for(
            generate_ai_analysis(
                candidate, latest_submission, target_position,
                analysis_level, custom_job_competencies, session  # 🟢 P2-3增强: 传入session
            ),
            timeout=timeout_seconds
        )
        logger.info(f"✅ AI分析完成 (级别={analysis_level})")
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ AI分析超时({timeout_seconds}s)，使用规则引擎降级分析")
        ai_analysis = build_default_analysis(candidate, latest_submission, target_position, session)  # 🟢 P2-3增强
        is_default_analysis = True
        ai_model_used = "fallback"  # 🟢 P1-2: 标识为降级
        fallback_reason = "ai_timeout"
    except Exception as e:
        logger.warning(f"⚠️ AI分析异常: {e}，使用规则引擎降级分析")
        ai_analysis = build_default_analysis(candidate, latest_submission, target_position, session)  # 🟢 P2-3增强
        is_default_analysis = True
        ai_model_used = "fallback"  # 🟢 P1-2: 标识为降级
        fallback_reason = "ai_error"

    if ai_analysis.get("_is_default_analysis") or ai_analysis.get("_fallback_reason"):
        is_default_analysis = True
        ai_model_used = "fallback"
        fallback_reason = ai_analysis.get("_fallback_reason") or fallback_reason or "ai_invalid_response"

    ai_generation_time = int((time.time() - ai_start_time) * 1000)  # 毫秒

    # 5. 计算综合评价（结合AI分析）
    # ⭐ 传入candidate信息用于简历质量评分
    ai_analysis_with_candidate = ai_analysis.copy() if ai_analysis else {}
    ai_analysis_with_candidate["candidate"] = candidate

    overall_score, strengths, improvements = _calculate_overall_assessment(
        assessments_info,
        job_match_info,
        ai_analysis_with_candidate
    )

    summary_points = build_summary_points(ai_analysis)
    competencies = build_competencies(ai_analysis)
    quick_tags = build_quick_tags(ai_analysis)

    # 🟢 P1-1: 计算多测评交叉验证数据
    cross_validation_data = None
    if len(submissions) >= 2:
        try:
            # 准备提交记录数据（需要转换为 dict）
            submission_dicts = []
            questionnaire_cache: Dict[int, Optional[Questionnaire]] = {}
            for sub in submissions:
                questionnaire = None
                if sub.questionnaire_id:
                    if sub.questionnaire_id not in questionnaire_cache:
                        questionnaire_cache[sub.questionnaire_id] = session.get(Questionnaire, sub.questionnaire_id)
                    questionnaire = questionnaire_cache.get(sub.questionnaire_id)

                sub_dict = {
                    'questionnaire': {
                        'type': questionnaire.type if questionnaire else 'UNKNOWN'
                    },
                    'result': _submission_result_payload(sub)
                }
                submission_dicts.append(sub_dict)

            # 调用交叉验证服务
            validation_result = CrossValidationService.calculate_cross_validation(submission_dicts)

            # 转换为 schema 格式
            cross_validation_data = schemas.CrossValidationData(
                consistency_score=validation_result['consistency_score'],
                confidence_level=validation_result['confidence_level'],
                assessment_count=validation_result['assessment_count'],
                consistency_checks=[
                    schemas.TraitConsistencyCheck(
                        trait=check['trait'],
                        scores=[
                            schemas.TraitScore(source=score['source'], value=score['value'])
                            for score in check['scores']
                        ],
                        mean=check['mean'],
                        stdDev=check['stdDev'],
                        consistency=check['consistency']
                    )
                    for check in validation_result['consistency_checks']
                ],
                contradictions=[
                    schemas.Contradiction(
                        trait=contr['trait'],
                        scores=contr['scores'],
                        issue=contr['issue']
                    )
                    for contr in validation_result['contradictions']
                ]
            )
            logger.info(f"🔍 候选人{candidate_id}: 交叉验证完成 (一致性: {validation_result['consistency_score']}, 置信度: {validation_result['confidence_level']})")
        except Exception as e:
            logger.error(f"⚠️ 候选人{candidate_id}: 交叉验证计算失败: {str(e)}")
            cross_validation_data = None

    ai_strengths = _normalize_ai_insights(ai_analysis.get("strengths", []), candidate.name)
    ai_risks = _normalize_ai_insights(ai_analysis.get("risks", []), candidate.name)
    ai_summary_points = _normalize_list_field(ai_analysis.get("summary_points", []))
    ai_quick_tags = _normalize_list_field(ai_analysis.get("quick_tags", []))
    ai_suitable_positions = _normalize_position_items(ai_analysis.get("suitable_positions", []))
    ai_unsuitable_positions = _normalize_position_items(ai_analysis.get("unsuitable_positions", []))
    display_strengths = _combine_ai_first(ai_strengths, strengths)
    display_improvements = _combine_ai_first(ai_risks, improvements)

    portrait = schemas.CandidatePortrait(
        basic_info=basic_info,
        assessments=assessments_info,
        job_match=job_match_info,
        overall_score=overall_score,
        strengths=display_strengths,
        improvements=display_improvements,
        personality_dimensions=[
            schemas.PersonalityDimension(**dim)
            for dim in ai_analysis.get("personality_dimensions", [])
        ],
        competencies=competencies,
        suitable_positions=ai_suitable_positions,
        unsuitable_positions=ai_unsuitable_positions,
        ai_summary=ai_analysis.get("summary"),
        ai_summary_points=clean_summary_points(summary_points) or ai_summary_points,  # 清理序号前缀
        quick_tags=quick_tags or ai_quick_tags,  # 快速标签
        cross_validation=cross_validation_data,  # 🟢 P1-1: 交叉验证数据
        # 🟢 P1-2: 降级标识
        is_fallback_analysis=is_default_analysis,
        analysis_method="fallback" if is_default_analysis else "ai",
        fallback_reason=fallback_reason if is_default_analysis else None
    )

    # 7. 保存到缓存 - V38: 按级别缓存
    total_time = int((time.time() - start_time) * 1000)
    save_portrait_cache(
        session=session,
        candidate_id=candidate_id,
        portrait=portrait,
        data_version=data_version,
        analysis_level=analysis_level,
        ai_model=ai_model_used,
        generation_time_ms=ai_generation_time,
        is_default=is_default_analysis
    )
    logger.info(f"🎉 候选人{candidate_id}: {analysis_level}画像生成完成 (总耗时: {total_time}ms, AI耗时: {ai_generation_time}ms)")

    return portrait
