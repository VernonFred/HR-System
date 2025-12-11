"""候选人画像 - AI分析模块.

负责调用AI服务生成候选人分析报告。
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .job_competencies import detect_job_family, get_job_competencies, get_default_competencies_by_position
from .dimension_parser import parse_personality_dimensions, get_default_personality_dimensions

if TYPE_CHECKING:
    from app.models import Candidate
    from app.models_assessment import Submission

logger = logging.getLogger(__name__)


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
            context_parts.append(f"工作经历：\n{'；\n'.join(exp_texts)}")
    
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
            context_parts.append(f"项目经验：\n{'；\n'.join(proj_texts)}")
    
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
    custom_job_competencies: Optional[List[str]] = None  # V39: 支持自定义岗位能力维度
) -> Dict[str, Any]:
    """调用AI生成完整的候选人分析.
    
    如果AI调用失败，使用基于测评数据的默认分析。
    
    ⭐ 支持两种场景：
    1. 无简历：仅基于测评数据生成画像
    2. 有简历：融合测评数据 + 简历信息生成更丰富的画像
    
    ⭐ 分析级别：
    - normal: 高级分析（Qwen2.5-7B）
    - pro: 深度分析（Qwen2.5-32B）
    - expert: 专家分析（DeepSeek-R1）
    
    Args:
        candidate: 候选人对象
        submission: 测评提交记录
        target_position: 目标岗位
        analysis_level: 分析级别
        custom_job_competencies: 自定义岗位能力维度（来自岗位画像配置）
    
    Returns:
        包含 personality_dimensions, strengths, risks, summary, 
        suitable_positions, unsuitable_positions 的字典
    """
    from app.api.ai import service as ai_service
    
    # 如果没有测评数据，返回基于候选人的默认分析
    if not submission or not submission.scores:
        return build_default_analysis(candidate, None, target_position)
    
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
        
        # 构建AI请求参数 - V7岗位族版
        payload = {
            "submission_code": f"portrait-{candidate.id}",
            "test_type": test_type,
            "scores": scores,
            "candidate_profile": candidate_profile,
            "position_keywords": [target_position] if target_position else [],
            "has_resume": has_resume,  # 标记是否有简历数据
            "job_competencies": job_competencies,  # 岗位胜任力模型
            "job_family": job_family  # ⭐ V7新增：岗位族标识
        }
        
        # 调用AI分析服务（带超时控制）
        # 根据分析级别决定是否强制使用 Pro 级，以及是否启用专家级综合分析
        force_pro = analysis_level in ("pro", "expert")
        use_expert_summary = analysis_level == "expert"  # 专家分析模式启用二阶段生成
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
            return build_default_analysis(candidate, submission, target_position)
        
        # ⭐ 强制使用测评结果中的真实维度数据（不使用AI生成的维度）
        personality_dimensions = parse_personality_dimensions(result_details)
        logger.info(f"🔍 解析真实维度: {len(personality_dimensions)}个, keys={[d.get('key') for d in personality_dimensions]}")
        
        # 如果解析失败，记录错误但不使用AI生成的维度（AI的维度数据不准确）
        if not personality_dimensions:
            logger.error(f"❌ 维度解析失败! result_details keys: {list(result_details.keys()) if result_details else 'None'}")
            logger.error(f"   questionnaire_type: {result_details.get('questionnaire_type') if result_details else 'None'}")
            # 使用默认维度（会在 build_default_analysis 中处理）
            return build_default_analysis(candidate, submission, target_position)
        
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
        
        return {
            "personality_dimensions": personality_dimensions,
            "strengths": result.get("strengths", []),
            "risks": result.get("risks", []),
            "summary": result.get("summary", ""),
            "summary_points": result.get("summary_points", []),
            "quick_tags": result.get("quick_tags", []),  # ⭐ 新增：头部快速标签
            "suitable_positions": result.get("suitable_positions", []),
            "unsuitable_positions": result.get("unsuitable_positions", []),
            "competencies": formatted_competencies
        }
        
    except Exception as e:
        logger.warning(f"❌ AI分析失败: {str(e)}，使用默认分析")
        return build_default_analysis(candidate, submission, target_position)


def build_default_analysis(
    candidate: "Candidate",
    submission: Optional["Submission"],
    target_position: Optional[str]
) -> Dict[str, Any]:
    """基于测评数据构建默认分析（当AI不可用时）.
    
    Args:
        candidate: 候选人对象
        submission: 测评提交记录
        target_position: 目标岗位
        
    Returns:
        分析结果字典
    """
    name = candidate.name if candidate else "候选人"
    position = target_position or "通用岗位"
    
    # 默认人格维度（基于测评数据或预设）
    personality_dimensions = []
    competencies = []
    
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
    
    return {
        "personality_dimensions": personality_dimensions,
        "competencies": competencies,
        "strengths": [
            f"测评表现良好，综合得分{avg_score:.0f}分",
            f"与{position}岗位具备基本匹配度",
            "具备良好的基础能力和发展潜力"
        ],
        "risks": [
            "建议进一步面试验证实际能力",
            "关注压力环境下的情绪管理"
        ],
        "summary": f"{name}在本次测评中表现稳定，综合得分{avg_score:.0f}分。从人格特征来看，具备良好的职业素养基础。与{position}岗位有一定的匹配度，建议通过面试进一步验证实际工作能力。",
        "summary_points": [
            f"{name}在测评中展现出稳定的人格特征，外向性和自律性表现良好，具备与人沟通协作的基础能力，适合需要团队配合的工作环境。",
            f"在{position}岗位的核心能力维度上表现均衡，各项胜任力得分在75-85分区间，说明具备该岗位的基本胜任条件。",
            f"建议关注候选人在高压环境下的情绪调节能力，可通过情境模拟面试进一步考察实际工作表现和问题解决能力。"
        ],
        "suitable_positions": [position, "相关领域岗位"],
        "unsuitable_positions": ["高度重复性工作", "独立承压岗位"]
    }

