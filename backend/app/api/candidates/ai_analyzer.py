"""候选人画像 - AI分析模块.

负责调用AI服务生成候选人分析报告。
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .job_competencies import detect_job_family, get_job_competencies, get_default_competencies_by_position
from .dimension_parser import parse_personality_dimensions, get_default_personality_dimensions

if TYPE_CHECKING:
    from app.models import Candidate
    from app.models_assessment import Questionnaire, Submission

logger = logging.getLogger(__name__)


def _submission_result_payload(submission: "Submission") -> Dict[str, Any]:
    """Return the result payload expected by fallback/cross-validation services."""
    for field_name in ("result_details", "scores", "answers"):
        value = getattr(submission, field_name, None)
        if isinstance(value, dict) and value:
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and parsed:
                return parsed
    return {}


def _position_items(value: Any) -> List[str]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else [value]
    result: List[str] = []
    seen = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        parts = [p.strip() for p in re.split(r"[\n、;；|]+", text) if p.strip()]
        if len(parts) == 1:
            comma_parts = [p.strip() for p in re.split(r"[,，]", text) if p.strip()]
            if len(comma_parts) > 1 and all(len(p) <= 18 for p in comma_parts):
                parts = comma_parts
        for part in parts:
            key = re.sub(r"\s+", "", part)
            if key and key not in seen:
                seen.add(key)
                result.append(part)
    return result


def _looks_like_default_positions(items: List[str]) -> bool:
    defaults = {"技术开发", "数据分析师", "项目管理", "运营专员"}
    normalized = {re.sub(r"\s+", "", item) for item in items}
    return len(normalized & defaults) >= 3


def _default_analysis_with_reason(
    candidate: "Candidate",
    submission: Optional["Submission"],
    target_position: Optional[str],
    session: Any = None,
    reason: str = "ai_invalid_response",
) -> Dict[str, Any]:
    result = build_default_analysis(candidate, submission, target_position, session)
    result["_fallback_reason"] = reason
    result["_is_default_analysis"] = True
    return result


def build_resume_context(candidate: "Candidate") -> str:
    """构建简历上下文信息，用于AI分析融合 - V3增强版.
    
    从候选人的 resume_parsed_data 中提取结构化信息，
    转换为自然语言描述供AI参考。
    
    V3增强：
    - 提供更详细的工作经历描述（包含职责）
    - 提供更详细的项目经验描述（包含成果）
    - 添加工作年限估算
    - 添加行业背景分析
    
    Args:
        candidate: 候选人对象
    
    Returns:
        简历上下文字符串，如果没有简历数据返回空字符串
    """
    if not candidate.resume_parsed_data:
        return ""
    
    parsed = candidate.resume_parsed_data
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except:
            return ""
    
    context_parts = []
    
    # ⭐ 目标岗位
    target_position = parsed.get("target_position", "")
    if target_position:
        context_parts.append(f"目标岗位：{target_position}")
    
    # ⭐ 教育背景 - 增强版
    education = parsed.get("education", [])
    if education:
        edu_texts = []
        for edu in education[:3]:  # 最多3条
            if isinstance(edu, dict):
                school = edu.get("school", "") or edu.get("university", "")
                degree = edu.get("degree", "")
                major = edu.get("major", "")
                start_date = edu.get("start_date", "")
                end_date = edu.get("end_date", "")
                
                if school:
                    edu_text = school
                    if degree:
                        edu_text += f" {degree}"
                    if major:
                        edu_text += f" {major}专业"
                    if start_date or end_date:
                        edu_text += f"（{start_date or '?'}-{end_date or '至今'}）"
                    edu_texts.append(edu_text)
        if edu_texts:
            context_parts.append(f"教育背景：{'；'.join(edu_texts)}")
    
    # ⭐ 工作经历 - 增强版（包含职责描述）
    experience = parsed.get("experience", [])
    if experience:
        exp_texts = []
        industries = set()  # 收集行业信息
        
        for i, exp in enumerate(experience[:4]):  # 最多4条
            if isinstance(exp, dict):
                company = exp.get("company", "")
                position = exp.get("position", "")
                description = exp.get("description", "")
                start_date = exp.get("start_date", "")
                end_date = exp.get("end_date", "")
                industry = exp.get("industry", "")
                
                if industry:
                    industries.add(industry)
                
                if company:
                    exp_text = f"【{company}】"
                    if position:
                        exp_text += f"担任{position}"
                    if start_date or end_date:
                        exp_text += f"（{start_date or '?'}-{end_date or '至今'}）"
                    # 添加职责描述（限制长度）
                    if description and i < 2:  # 只为前两条添加详细描述
                        desc_short = description[:150] if len(description) > 150 else description
                        exp_text += f"，主要负责：{desc_short}"
                    exp_texts.append(exp_text)
        
        if exp_texts:
            exp_joined = "；\n".join(exp_texts)
            context_parts.append(f"工作经历：\n{exp_joined}")
    
        # 添加行业背景
        if industries:
            context_parts.append(f"行业背景：{'、'.join(list(industries)[:3])}")
    
    # ⭐ 技能特长
    skills = parsed.get("skills", [])
    if skills:
        skill_list = skills[:15] if isinstance(skills, list) else []  # 最多15个技能
        if skill_list:
            context_parts.append(f"技能特长：{'、'.join(skill_list)}")
    
    # ⭐ 项目经验 - 增强版（包含成果描述）
    projects = parsed.get("projects", [])
    if projects:
        proj_texts = []
        for proj in projects[:3]:  # 最多3个项目
            if isinstance(proj, dict):
                name = proj.get("name", "")
                role = proj.get("role", "")
                description = proj.get("description", "")
                achievement = proj.get("achievement", "") or proj.get("result", "")
                
                if name:
                    proj_text = f"【{name}】"
                    if role:
                        proj_text += f"担任{role}"
                    if description:
                        desc_short = description[:100] if len(description) > 100 else description
                        proj_text += f"，{desc_short}"
                    if achievement:
                        ach_short = achievement[:80] if len(achievement) > 80 else achievement
                        proj_text += f"。成果：{ach_short}"
                    proj_texts.append(proj_text)
        if proj_texts:
            proj_joined = "；\n".join(proj_texts)
            context_parts.append(f"项目经验：\n{proj_joined}")
    
    # ⭐ 证书资质
    certificates = parsed.get("certificates", [])
    if certificates:
        cert_list = certificates[:5] if isinstance(certificates, list) else []
        if cert_list:
            context_parts.append(f"证书资质：{'、'.join(cert_list)}")
    
    # ⭐ 个人亮点/成就
    highlights = parsed.get("highlights", []) or parsed.get("achievements", [])
    if highlights:
        highlight_list = highlights[:5] if isinstance(highlights, list) else []
        if highlight_list:
            context_parts.append(f"核心亮点：{'；'.join(highlight_list)}")
    
    # ⭐ 简历摘要/自我评价
    summary = parsed.get("summary", "") or parsed.get("self_assessment", "")
    if summary and len(summary) > 10:
        context_parts.append(f"个人简介：{summary[:300]}")  # 增加长度限制
    
    return "\n".join(context_parts)


async def generate_ai_analysis(
    candidate: "Candidate",
    submission: Optional["Submission"],
    target_position: Optional[str],
    analysis_level: str = "pro",  # V5: 默认 pro
    custom_job_competencies: Optional[List[str]] = None,  # V39: 支持自定义岗位能力维度
    session = None  # 🟢 P2-3增强: 数据库会话，用于加载岗位画像
) -> Dict[str, Any]:
    """调用AI生成完整的候选人分析.
    
    如果AI调用失败，使用基于测评数据的默认分析。
    
    ⭐ 支持两种场景：
    1. 无简历：仅基于测评数据生成画像
    2. 有简历：融合测评数据 + 简历信息生成更丰富的画像
    
    ⭐ 分析模式：
    - 当前统一使用 pro 单模型画像生成。
    - 旧 analysis_level 参数仅保留兼容，函数内部会归一为 pro。
    
    Args:
        candidate: 候选人对象
        submission: 测评提交记录
        target_position: 目标岗位
        analysis_level: 画像分析模式（当前统一归一为 pro）
        custom_job_competencies: 自定义岗位能力维度（来自岗位画像配置）
    
    Returns:
        包含 personality_dimensions, strengths, risks, summary, 
        suitable_positions, unsuitable_positions 的字典
    """
    from app.api.ai import service as ai_service
    
    # 如果没有测评数据，返回基于候选人的默认分析
    if not submission or not submission.scores:
        return _default_analysis_with_reason(
            candidate,
            None,
            target_position,
            session,
            "no_assessment_scores",
        )
    
    try:
        # 解析测评分数
        scores = submission.scores if isinstance(submission.scores, dict) else json.loads(submission.scores or "{}")
        
        # 解析result_details获取更丰富的信息
        result_details = {}
        if submission.result_details:
            result_details = submission.result_details if isinstance(submission.result_details, dict) else json.loads(submission.result_details or "{}")
        
        # 确定测评类型（支持questionnaire_type和type两种字段）
        test_type = result_details.get("questionnaire_type") or result_details.get("type", "EPQ")
        
        # ⭐ 构建简历上下文（如果有简历数据）
        resume_context = build_resume_context(candidate)
        has_resume = bool(resume_context)
        if has_resume:
            logger.info(f"📄 候选人{candidate.name}有简历数据，将融合到AI分析中")
        
        # ⭐ 构建候选人画像描述（融合简历信息）- V3增强版
        candidate_profile = f"{candidate.name}，应聘{target_position or '未指定岗位'}"
        
        # 添加性别信息（如果有）
        if hasattr(candidate, 'gender') and candidate.gender:
            candidate_profile += f"\n性别：{candidate.gender}"
        
        # 添加简历信息
        if resume_context:
            candidate_profile += f"\n\n【简历信息】\n{resume_context}"
        
        # ⭐ 构建岗位胜任力模型（优先使用自定义配置，否则基于岗位类型动态调整）
        if custom_job_competencies and len(custom_job_competencies) > 0:
            job_competencies = custom_job_competencies
            logger.info(f"📋 使用岗位画像配置的能力维度: {job_competencies}")
        else:
            job_competencies = get_job_competencies(target_position)
        
        # ⭐ V7新增：检测岗位族
        job_family = detect_job_family(target_position)
        
        # 不在 AI 生成前注入默认岗位参考。
        # 之前这里用空胜任力计算岗位，容易把所有候选人都引向同一批默认岗位。
        candidate_positions_for_ai = None
        
        # 构建AI请求参数 - V7岗位族版
        # ⭐ 使用时间戳确保每次分析都是新的（禁用缓存以获得个性化结果）
        import time
        payload = {
            "submission_code": f"portrait-{candidate.id}-{int(time.time())}",
            "test_type": test_type,
            "scores": scores,
            "candidate_profile": candidate_profile,
            "position_keywords": [target_position] if target_position else [],
            "has_resume": has_resume,  # 标记是否有简历数据
            "job_competencies": job_competencies,  # 岗位胜任力模型
            "job_family": job_family,  # ⭐ V7新增：岗位族标识
            "candidate_positions": candidate_positions_for_ai  # 🟢 P2-3增强: 候选岗位参考
        }
        
        # 调用AI分析服务（带超时控制）
        # 单模型模式：统一使用默认深度提示词，不再触发专家二阶段生成。
        force_pro = True
        use_expert_summary = False
        analysis_level = "pro"
        logger.info(f"🤖 开始AI分析: {candidate.name}, 岗位: {target_position}, 级别: {analysis_level}, 专家综合: {use_expert_summary}")
        result = await ai_service.ai_interpretation(payload, force_pro=force_pro, use_expert_summary=use_expert_summary)
        
        # 验证AI返回结果 - V4-Lite版本使用 competencies 或 personality_dimensions
        has_valid_data = (
            result and (
                result.get("personality_dimensions") or 
                result.get("competencies") or
                result.get("summary_points")
            )
        )
        if not has_valid_data:
            logger.warning(f"⚠️ AI返回数据不完整，使用默认分析")
            return _default_analysis_with_reason(
                candidate,
                submission,
                target_position,
                session,
                "ai_invalid_response",
            )
        
        # ⭐ 强制使用测评结果中的真实维度数据（不使用AI生成的维度）
        personality_dimensions = parse_personality_dimensions(result_details)
        logger.info(f"🔍 解析真实维度: {len(personality_dimensions)}个, keys={[d.get('key') for d in personality_dimensions]}")
        
        # 如果解析失败，记录错误但不使用AI生成的维度（AI的维度数据不准确）
        if not personality_dimensions:
            logger.error(f"❌ 维度解析失败! result_details keys: {list(result_details.keys()) if result_details else 'None'}")
            logger.error(f"   questionnaire_type: {result_details.get('questionnaire_type') if result_details else 'None'}")
            # 使用默认维度（会在 build_default_analysis 中处理）
            return _default_analysis_with_reason(
                candidate,
                submission,
                target_position,
                session,
                "dimension_parse_failed",
            )
        
        # ⭐ 转换 competencies 格式（AI返回的是 name/level/score/evidence，前端需要 key/label/score）
        raw_competencies = result.get("competencies", [])
        formatted_competencies = []
        for idx, comp in enumerate(raw_competencies):
            if isinstance(comp, dict):
                formatted_competencies.append({
                    "key": comp.get("key", f"comp_{idx}"),
                    "label": comp.get("name", comp.get("label", "未知能力")),
                    "score": float(comp.get("score", 70)),
                    "description": comp.get("evidence", comp.get("description", ""))
                })
        
        if formatted_competencies:
            logger.info(f"✅ 岗位胜任力: {len(formatted_competencies)}个能力项")
        
        logger.info(f"🎯 最终返回维度: {len(personality_dimensions)}个, keys={[d.get('key') for d in personality_dimensions]}")
        
        # 🟢 P2-3增强: 保留AI的深度洞察分析
        # AI已经基于候选岗位参考进行了深度分析，直接使用AI的结果
        suitable_positions = _position_items(result.get("suitable_positions", []))
        unsuitable_positions = _position_items(result.get("unsuitable_positions", []))
        if (not suitable_positions or _looks_like_default_positions(suitable_positions)) and formatted_competencies:
            try:
                from app.services.job_recommender import JobRecommender
                suitable_positions = JobRecommender.recommend_positions(
                    competencies=formatted_competencies,
                    resume_keywords=None,
                    current_position=target_position,
                    top_n=4,
                    session=session,
                )
                logger.info(f"🎯 使用胜任力重新生成岗位推荐: {suitable_positions}")
            except Exception as e:
                logger.warning(f"⚠️ 胜任力岗位推荐失败，保留AI结果: {e}")
        if (not unsuitable_positions or _looks_like_default_positions(unsuitable_positions)) and formatted_competencies:
            try:
                from app.services.job_recommender import JobRecommender
                unsuitable_positions = JobRecommender.recommend_unsuitable_positions(formatted_competencies)
            except Exception as e:
                logger.warning(f"⚠️ 不适配岗位推荐失败，保留AI结果: {e}")
        
        logger.info(f"✅ AI岗位推荐: suitable={len(suitable_positions)}, unsuitable={len(unsuitable_positions)}")
        
        return {
            "personality_dimensions": personality_dimensions,
            "strengths": result.get("strengths", []),
            "risks": result.get("risks", []),
            "summary": result.get("summary", ""),
            "summary_points": result.get("summary_points", []),
            "quick_tags": result.get("quick_tags", []),
            "suitable_positions": suitable_positions,  # 🟢 P2-3增强: 使用AI的深度洞察
            "unsuitable_positions": unsuitable_positions,  # 🟢 P2-3增强: 使用AI的深度洞察
            "competencies": formatted_competencies
        }
        
    except Exception as e:
        logger.warning(f"❌ AI分析失败: {str(e)}，使用默认分析")
        return _default_analysis_with_reason(
            candidate,
            submission,
            target_position,
            session,
            "ai_error",
        )


def build_default_analysis(
    candidate: "Candidate",
    submission: Optional["Submission"],
    target_position: Optional[str],
    session = None  # 🟢 P2-3增强: 数据库会话，用于加载岗位画像
) -> Dict[str, Any]:
    """基于测评数据构建默认分析（当AI不可用时）.
    
    🟢 P1-2优化: 使用规则引擎分析，而非固定假数据
    
    Args:
        candidate: 候选人对象
        submission: 测评提交记录
        target_position: 目标岗位
        
    Returns:
        分析结果字典
    """
    from app.services.fallback_analyzer import FallbackAnalyzer
    from sqlmodel import Session, select
    from app.models_assessment import Questionnaire, Submission
    from app.db import get_engine
    
    name = candidate.name if candidate else "候选人"
    position = target_position or "通用岗位"
    
    # 🟢 P1-2: 获取候选人的所有测评记录
    submissions_data = []
    if candidate:
        with Session(get_engine()) as session:
            stmt = select(Submission).where(
                Submission.candidate_id == candidate.id
            ).order_by(Submission.submitted_at.desc())
            submissions = session.exec(stmt).all()
            
            for sub in submissions:
                questionnaire = session.get(Questionnaire, sub.questionnaire_id) if sub.questionnaire_id else None
                submissions_data.append({
                    'questionnaire': {
                        'type': questionnaire.type if questionnaire else 'UNKNOWN'
                    },
                    'result': _submission_result_payload(sub),
                    'score_percentage': sub.score_percentage
                })
    
    # 🟢 P1-2: 使用规则引擎生成分析
    if len(submissions_data) > 0:
        logger.info(f"🔧 使用规则引擎生成降级分析 (测评数量: {len(submissions_data)})")
        fallback_result = FallbackAnalyzer.analyze_candidate(submissions_data, target_position)
        
        # 解析人格维度 (从测评数据中提取)
        personality_dimensions = []
        competencies = fallback_result.get("competencies", [])
    else:
        # 无测评数据，使用基本默认值
        logger.warning("⚠️ 无测评数据，使用基本默认分析")
        fallback_result = {
            "strengths": [f"待完成专业测评以生成详细分析"],
            "risks": ["建议尽快完成测评"],
            "summary_points": [f"{name}尚未完成专业测评，建议先完成测评以获得准确的能力画像。"],
            "suitable_positions": [position],
            "quick_tags": ["待评估"]
        }
        personality_dimensions = []
        competencies = []
    
    # 默认人格维度（基于测评数据或预设）
    if submission and submission.result_details:
        result_details = submission.result_details if isinstance(submission.result_details, dict) else json.loads(submission.result_details or "{}")
        
        # 🔍 调试：打印result_details
        print(f"\n{'='*70}")
        print(f"build_default_analysis 收到的 result_details:")
        print(f"{'='*70}")
        print(f"Type: {type(result_details)}")
        print(f"Keys: {list(result_details.keys()) if isinstance(result_details, dict) else 'NOT A DICT'}")
        print(f"questionnaire_type: {result_details.get('questionnaire_type') if isinstance(result_details, dict) else 'N/A'}")
        if 'disc_dimensions' in result_details:
            print(f"disc_dimensions keys: {list(result_details['disc_dimensions'].keys())}")
        print(f"{'='*70}\n")
        
        # 使用维度解析模块解析人格维度
        personality_dimensions = parse_personality_dimensions(result_details)
        
        # 如果还没有，检查通用dimension_scores格式
        if not personality_dimensions:
            dim_scores = result_details.get("dimension_scores", [])
            for dim in dim_scores:
                if isinstance(dim, dict):
                    personality_dimensions.append({
                        "key": dim.get("key", ""),
                        "label": dim.get("label", ""),
                        "score": float(dim.get("score", 70)),
                        "description": dim.get("description", "")
                    })
    
    # 如果没有维度数据，使用默认维度
    if not personality_dimensions:
        personality_dimensions = get_default_personality_dimensions()
    
    # 获取默认胜任力
    competencies = get_default_competencies_by_position(position)
    
    # 计算平均分数
    avg_score = sum(d["score"] for d in personality_dimensions) / len(personality_dimensions) if personality_dimensions else 70
    
    # 🟢 P2-3增强: 降级场景下，使用简单的岗位推荐
    # 因为没有AI深度分析，这里使用算法推荐候选岗位名称
    from app.services.job_recommender import JobRecommender
    
    # 提取简历关键词
    resume_keywords = []
    if candidate and candidate.resume_parsed_data:
        parsed_data = candidate.resume_parsed_data
        if isinstance(parsed_data, dict):
            skills = parsed_data.get("skills", [])
            if isinstance(skills, list):
                resume_keywords.extend([str(s) for s in skills if s])
    
    # 使用算法推荐岗位（降级场景）
    suitable_positions = JobRecommender.recommend_positions(
        competencies=competencies,
        resume_keywords=resume_keywords if resume_keywords else None,
        current_position=target_position,
        top_n=4,
        session=session
    )
    
    unsuitable_positions = JobRecommender.recommend_unsuitable_positions(
        competencies=competencies
    )
    
    logger.info(f"🔧 降级场景岗位推荐: suitable={suitable_positions}, unsuitable={unsuitable_positions}")
    
    # 🟢 P1-2: 返回规则引擎的结果，或默认值
    return {
        "personality_dimensions": personality_dimensions,
        "competencies": competencies,
        "strengths": fallback_result.get("strengths", [f"综合测评得分{avg_score:.0f}分"]),
        "risks": fallback_result.get("risks", ["建议进一步面试验证"]),
        "summary": fallback_result.get("summary_points", [f"{name}综合表现稳定"])[0] if fallback_result.get("summary_points") else f"{name}综合表现稳定",
        "summary_points": fallback_result.get("summary_points", [
            f"{name}综合测评得分{avg_score:.0f}分，整体表现稳定",
            f"与{position}岗位具备基本匹配度",
            "建议通过面试进一步验证实际能力"
        ]),
        "quick_tags": fallback_result.get("quick_tags", ["综合评估"]),
        "suitable_positions": suitable_positions,  # 🟢 降级场景：算法推荐
        "unsuitable_positions": unsuitable_positions  # 🟢 降级场景：算法推荐
    }
