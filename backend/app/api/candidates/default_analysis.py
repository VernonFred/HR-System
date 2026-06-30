"""Rule-based fallback analysis for candidate portraits."""
import json
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from .dimension_parser import parse_personality_dimensions, get_default_personality_dimensions
from .job_competencies import get_default_competencies_by_position

if TYPE_CHECKING:
    from app.models import Candidate
    from app.models_assessment import Submission

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
