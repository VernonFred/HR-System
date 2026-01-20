"""候选人画像 - 业务逻辑主入口.

整合以下模块：
- cache_manager: 画像缓存管理
- dimension_parser: 人格维度解析
- job_competencies: 岗位胜任力模型
- ai_analyzer: AI分析调用
"""

import asyncio
import json
import logging
import time
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import Session, select, and_, func
from fastapi import HTTPException, status as http_status

from app.models import Candidate, JobProfile, ProfileMatch, PortraitCache
from app.models_assessment import Submission, Assessment, Questionnaire
from . import schemas

# 导入拆分后的模块
from .cache_manager import (
    compute_data_version,
    get_cached_portrait,
    save_portrait_cache,
)
from .dimension_parser import (
    clean_summary_points,
    build_dimension_scores,
)
from .ai_analyzer import (
    generate_ai_analysis,
    build_default_analysis,
)
from .dimension_mapping import calculate_dimension_score_from_assessments
from app.services.cross_validation import CrossValidationService
from app.services.resume_quality_analyzer import ResumeQualityAnalyzer  # 🟢 P2-2


def _normalize_list_field(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[\n,，、;；|]+", value)
        return [p.strip() for p in parts if p and p.strip()]
    text = str(value).strip()
    return [text] if text else []
from app.services.job_recommender import JobRecommender  # 🟢 P2-3

logger = logging.getLogger(__name__)


async def build_candidate_portrait(
    session: Session,
    candidate_id: int,
    force_refresh: bool = False,  # 强制刷新（跳过缓存）
    analysis_level: str = "pro"  # V5: 分析级别默认 pro (32B)
) -> schemas.CandidatePortrait:
    """构建候选人完整画像.
    
    整合以下数据源：
    1. 候选人基本信息
    2. 测评记录（通过 candidate_id 关联）
    3. 岗位画像匹配（通过 target_position 关联）
    
    分析级别：
    - normal: 高级分析（Qwen2.5-7B，适合大多数岗位）
    - pro: 深度分析（Qwen2.5-32B，更深入的洞察）
    - expert: 专家分析（DeepSeek-R1，专家级推理）
    
    缓存策略：
    - 首次访问：调用AI分析，结果存入缓存
    - 再次访问：直接返回缓存（毫秒级响应）
    - 数据变更：自动失效缓存，重新分析
    
    Args:
        session: 数据库会话
        candidate_id: 候选人ID
        force_refresh: 是否强制刷新（跳过缓存）
        analysis_level: 分析级别
        
    Returns:
        完整的候选人画像
    """
    start_time = time.time()
    
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
    ai_model_used = "Qwen/Qwen3-8B"  # 使用的AI模型
    fallback_reason = None  # 🟢 P1-2: 降级原因
    ai_start_time = time.time()
    
    # 根据分析级别设置超时时间
    timeout_map = {
        "normal": 60.0,   # 高级分析：60秒
        "pro": 120.0,     # 深度分析：120秒
        "expert": 180.0,  # 专家分析：180秒
    }
    timeout_seconds = timeout_map.get(analysis_level, 90.0)
    
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
    
    # 6. 构建完整画像
    # 获取summary_points，优先使用AI返回的
    summary_points = ai_analysis.get("summary_points", [])
    
    # 如果已有3条点，直接使用（不再因为字数不足而清空）
    # 只有当点数不足3条时，才尝试从summary补充
    if len(summary_points) < 3 and ai_analysis.get("summary"):
        # 尝试从summary补充
        pass  # 进入下面的智能拆分逻辑
    elif len(summary_points) >= 3:
        # 已有足够的点，截取前3条
        summary_points = summary_points[:3]
    
    # 智能拆分summary为3条观点（每条80-100字）
    if not summary_points and ai_analysis.get("summary"):
        summary_text = ai_analysis.get("summary", "")
        
        # 先按段落拆分
        paragraphs = [p.strip() for p in summary_text.split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            summary_points = paragraphs[:3]
        else:
            # 如果段落不足，按句子拆分并智能合并
            sentences = []
            for para in (paragraphs if paragraphs else [summary_text]):
                para_sentences = [s.strip() + "。" for s in para.split("。") if s.strip()]
                sentences.extend(para_sentences)
            
            # 智能合并句子，确保每条80-100字
            if len(sentences) >= 3:
                merged_points = []
                current_point = ""
                for sentence in sentences:
                    # 如果当前点为空或加上新句子不超过120字，则合并
                    if not current_point:
                        current_point = sentence
                    elif len(current_point + sentence) <= 120:
                        current_point += sentence
                    else:
                        # 当前点已足够，保存并开始新点
                        if current_point:
                            merged_points.append(current_point)
                        current_point = sentence
                    
                    # 如果当前点达到80字以上，考虑保存
                    if len(current_point) >= 80 and len(merged_points) < 2:
                        merged_points.append(current_point)
                        current_point = ""
                
                # 保存最后一个点
                if current_point:
                    merged_points.append(current_point)
                
                summary_points = merged_points[:3] if len(merged_points) >= 3 else merged_points
            else:
                # 句子太少，直接使用段落或整个summary
                summary_points = paragraphs[:3] if paragraphs else [summary_text]
    
    # 提取岗位胜任力（确保5-6个）
    ai_competencies = ai_analysis.get("competencies", [])[:6]
    
    # 如果AI返回的不足5个，补充默认胜任力
    if len(ai_competencies) < 5:
        default_competencies = [
            {"key": "communication", "label": "沟通协作能力", "score": 78, "rationale": "基于综合表现评估"},
            {"key": "execution", "label": "执行推进能力", "score": 80, "rationale": "基于任务完成度评估"},
            {"key": "learning", "label": "学习适应能力", "score": 82, "rationale": "基于开放性评估"},
            {"key": "problem_solving", "label": "问题解决能力", "score": 76, "rationale": "基于逻辑思维评估"},
            {"key": "teamwork", "label": "团队协作能力", "score": 75, "rationale": "基于协作表现评估"},
            {"key": "stress_tolerance", "label": "抗压能力", "score": 72, "rationale": "基于情绪稳定性评估"},
        ]
        # 补充缺失的胜任力（避免重复key）
        existing_keys = {c.get("key") for c in ai_competencies}
        for dc in default_competencies:
            if len(ai_competencies) >= 6:
                break
            if dc["key"] not in existing_keys:
                ai_competencies.append(dc)
                existing_keys.add(dc["key"])
    
    competencies = [
        schemas.CompetencyScore(
            key=comp.get("key"),
            label=comp.get("label", "未知能力"),
            score=float(comp.get("score", 0)),
            rationale=comp.get("rationale")
        ) for comp in ai_competencies
    ]
    
    # 获取 quick_tags（用于头部展示的短标签）
    # 注意：quick_tags 必须是 AI 生成的简短标签，不能从 strengths 中截取
    quick_tags = ai_analysis.get("quick_tags", [])
    
    # 验证 quick_tags 格式：每个标签应该是 3-6 个字的简短标签
    valid_tags = []
    for tag in quick_tags:
        if isinstance(tag, str):
            tag = tag.strip()
            # 如果标签太长（超过8个字），说明可能是截断的文字，跳过
            if 2 <= len(tag) <= 8:
                valid_tags.append(tag)
    
    # 如果没有有效的 quick_tags，使用默认标签
    if len(valid_tags) < 3:
        # 使用通用的默认标签，而不是从 strengths 截取
        default_tags = ["待深入了解", "综合评估中", "详见分析"]
        quick_tags = valid_tags + default_tags[len(valid_tags):3]
    else:
        quick_tags = valid_tags[:3]
    
    # 🟢 P1-1: 计算多测评交叉验证数据
    cross_validation_data = None
    if len(submissions) >= 2:
        try:
            # 准备提交记录数据（需要转换为 dict）
            submission_dicts = []
            for sub in submissions:
                sub_dict = {
                    'questionnaire': {
                        'type': sub.questionnaire.type if sub.questionnaire else 'UNKNOWN'
                    },
                    'result': sub.result if isinstance(sub.result, dict) else {}
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
    
    ai_strengths = _normalize_list_field(ai_analysis.get("strengths", []))
    ai_risks = _normalize_list_field(ai_analysis.get("risks", []))
    ai_summary_points = _normalize_list_field(ai_analysis.get("summary_points", []))
    ai_quick_tags = _normalize_list_field(ai_analysis.get("quick_tags", []))
    ai_suitable_positions = _normalize_list_field(ai_analysis.get("suitable_positions", []))
    ai_unsuitable_positions = _normalize_list_field(ai_analysis.get("unsuitable_positions", []))

    portrait = schemas.CandidatePortrait(
        basic_info=basic_info,
        assessments=assessments_info,
        job_match=job_match_info,
        overall_score=overall_score,
        strengths=strengths or ai_strengths,
        improvements=improvements or ai_risks,
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
        ai_strengths = ai_analysis.get("strengths", [])
        ai_risks = ai_analysis.get("risks", [])
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


async def get_candidate_portraits_summary(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    target_position: Optional[str] = None
) -> tuple[List[schemas.CandidatePortraitSummary], int]:
    """获取候选人画像摘要列表.
    
    Args:
        session: 数据库会话
        skip: 跳过数量
        limit: 限制数量
        target_position: 应聘岗位过滤
        
    Returns:
        (画像摘要列表, 总数)
    """
    # 构建查询
    statement = select(Candidate)
    
    if target_position:
        statement = statement.where(Candidate.target_position == target_position)
    
    # 获取总数
    count_statement = select(func.count()).select_from(Candidate)
    if target_position:
        count_statement = count_statement.where(Candidate.target_position == target_position)
    
    total = session.exec(count_statement).one()
    
    # 获取候选人列表
    statement = statement.offset(skip).limit(limit).order_by(Candidate.created_at.desc())
    candidates = session.exec(statement).all()
    
    # 构建摘要列表
    summaries = []
    for candidate in candidates:
        # 统计测评数量
        assessment_count = session.exec(
            select(func.count()).select_from(Submission).where(
                and_(
                    Submission.candidate_id == candidate.id,
                    Submission.status == "completed"
                )
            )
        ).one()
        
        # 获取最新匹配记录
        latest_match = session.exec(
            select(ProfileMatch).join(Submission).where(
                Submission.candidate_id == candidate.id
            ).order_by(ProfileMatch.created_at.desc())
        ).first()
        
        # 计算综合得分（简化）
        overall_score = None
        if latest_match:
            overall_score = latest_match.match_score
        
        summary = schemas.CandidatePortraitSummary(
            candidate_id=candidate.id,
            name=candidate.name,
            target_position=candidate.target_position,
            overall_score=overall_score,
            match_score=latest_match.match_score if latest_match else None,
            assessment_count=assessment_count,
            has_job_match=latest_match is not None
        )
        summaries.append(summary)
    
    return summaries, total
