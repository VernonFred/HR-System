"""画像专用模型路由器 - DeepSeek 单模型调用。"""

import logging
from typing import Any, Dict, List, Optional

from .ai_client import AIClientError, post_chat, parse_json_safely
from .position_level import (
    PositionLevel, detect_position_level,
    get_level_display_name, get_level_description
)

logger = logging.getLogger(__name__)


def determine_analysis_level(
    position: Optional[str] = None,
    force_level: Optional[str] = None,
    resume_data: Optional[Dict[str, Any]] = None,
    competency_scores: Optional[Dict[str, int]] = None,
) -> str:
    """
    确定分析级别.
    
    现在默认直接使用 DeepSeek (pro)，仅在强制指定 expert 时仍使用 expert 流程。
    """
    # 强制指定级别（只接受 pro 或 expert）
    if force_level and force_level in ("pro", "expert"):
        logger.info(f"🎯 使用分析级别: {force_level}")
        return force_level
    
    # 默认使用 pro（现已映射到 DeepSeek）
    logger.info("📊 使用默认分析级别: pro (DeepSeek)")
    return "pro"


# 保留旧函数名以保持兼容性
def should_use_pro_level(
    position: str,
    force_pro: bool = False,
    competency_scores: Optional[Dict[str, int]] = None,
) -> bool:
    """兼容旧接口 - 判断是否使用 Pro 级."""
    level = determine_analysis_level(
        position=position,
        force_level="pro" if force_pro else None,
        competency_scores=competency_scores,
    )
    return level in ("pro", "expert")


async def call_portrait_model(
    messages: List[Dict[str, Any]],
    level: str = "normal",
    max_tokens: int = 1536,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """调用画像专用模型，统一走 DeepSeek 单模型。"""
    try:
        result = await post_chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        result["level"] = "deepseek"
        return result
    except AIClientError as e:
        logger.error(f"❌ DeepSeek 模型调用失败: {e}")
        raise


async def generate_portrait(
    payload: Dict[str, Any],
    level: str = "pro",  # V5: 默认使用 pro
    use_expert_summary: bool = False,
) -> Dict[str, Any]:
    """
    生成候选人画像 - V5 版本.
    
    Args:
        payload: 画像生成参数
        level: 分析级别 (pro/expert)，默认 pro
        use_expert_summary: 是否使用专家级综合分析（二阶段生成）
        
    Returns:
        画像结果字典
    """
    from .prompt_builder import build_interpretation_prompt
    
    # V5: 确保 level 有效，默认使用 pro
    if level not in ("pro", "expert"):
        level = "pro"
    
    # 构建提示词（传入 level 以选择对应的 System Prompt）
    messages = build_interpretation_prompt(payload, level=level)
    
    # 使用指定级别的模型
    logger.info(f"📊 生成画像 (level={level})")
    print(f"📊 生成画像 (level={level})")
    result = await call_portrait_model(
        messages=messages,
        level=level,
        max_tokens=2048,  # V5: 增加 token 限制以支持更详细的输出
        temperature=0.3,
    )
    
    # 解析 JSON 结果
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = parse_json_safely(content)
    
    # 添加模型信息
    parsed["_model"] = result.get("model", "unknown")
    parsed["_level"] = result.get("level", level)
    
    # 第二阶段：如果启用专家级综合分析，使用 DeepSeek V4 Pro 增强
    if use_expert_summary:
        logger.info("🧠 第二阶段：启用专家级综合分析")
        scores = payload.get("scores", {})
        job_family = payload.get("job_family", "通用")
        position_keywords = payload.get("position_keywords", [])
        target_position = position_keywords[0] if position_keywords else "通用岗位"
        
        expert_result = await generate_expert_summary(
            basic_portrait=parsed,
            scores=scores,
            target_position=target_position,
            job_family=job_family,
        )
        
        # 合并专家分析结果
        if expert_result.get("expert_summary"):
            # 用专家级综合分析替换原有的 summary_points
            parsed["summary_points"] = expert_result.get("expert_summary", [])
            parsed["hiring_recommendation"] = expert_result.get("hiring_recommendation", "")
            parsed["interview_focus"] = expert_result.get("interview_focus", [])
            parsed["_expert_model"] = expert_result.get("_model", "unknown")
            logger.info("✅ 专家级综合分析已合并到画像")
        else:
            logger.warning("⚠️ 专家级综合分析生成失败，使用基础画像")
    
    return parsed


async def generate_expert_summary(
    basic_portrait: Dict[str, Any],
    scores: Dict[str, Any],
    target_position: str,
    job_family: str = "通用",
) -> Dict[str, Any]:
    """
    二阶段生成：使用 DeepSeek V4 Pro 生成更精准的综合分析.
    
    在「专家分析」模式下，第一阶段生成基础画像，
    第二阶段使用专家提示词生成高质量的综合分析。
    
    Args:
        basic_portrait: 第一阶段生成的基础画像
        scores: 测评分数
        target_position: 目标岗位
        job_family: 岗位族
        
    Returns:
        包含 expert_summary 和 expert_insights 的字典
    """
    import json
    
    # 提取基础画像中的关键信息
    strengths = basic_portrait.get("strengths", [])
    risks = basic_portrait.get("risks", [])
    competencies = basic_portrait.get("competencies", [])
    personality = basic_portrait.get("personality_dimensions", [])
    
    system_prompt = """你是一名资深人才测评专家，擅长综合分析候选人画像并给出精准、有洞察力的总结。

你的任务是：
1. 综合分析候选人的测评数据、优势和风险点
2. 给出 3 条精准、有深度的综合分析观点
3. 每条观点必须有具体的数据支撑和行为推断

输出要求：
- 不要简单复述已有信息，要有二阶推断
- 每条观点 80-120 字，信息密度高
- 语言专业但易懂，避免空洞的形容词
- 结合岗位需求分析匹配度"""

    user_prompt = f"""请对以下候选人进行深度综合分析：

【目标岗位】{target_position}（{job_family}）

【测评分数】
{json.dumps(scores, ensure_ascii=False, indent=2)}

【已识别优势】
{json.dumps(strengths, ensure_ascii=False)}

【已识别风险】
{json.dumps(risks, ensure_ascii=False)}

【胜任力评估】
{json.dumps(competencies, ensure_ascii=False)}

【人格特征】
{json.dumps(personality, ensure_ascii=False)}

请输出 JSON 格式：
{{
  "expert_summary": [
    "第一条综合分析观点（80-120字）",
    "第二条综合分析观点（80-120字）",
    "第三条综合分析观点（80-120字）"
  ],
  "hiring_recommendation": "是否建议录用及理由（50字以内）",
  "interview_focus": ["面试重点关注问题1", "面试重点关注问题2", "面试重点关注问题3"]
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        logger.info("🧠 二阶段生成：使用 DeepSeek V4 Pro 专家提示词生成综合分析")
        result = await call_portrait_model(
            messages=messages,
            level="expert",
            max_tokens=1024,
            temperature=0.4,
        )
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = parse_json_safely(content)
        
        parsed["_model"] = result.get("model", "unknown")
        parsed["_level"] = "expert"
        
        logger.info("✅ 专家级综合分析生成成功")
        return parsed
        
    except Exception as e:
        logger.error(f"❌ 专家级综合分析生成失败: {e}")
        return {
            "expert_summary": [],
            "hiring_recommendation": "",
            "interview_focus": [],
            "_error": str(e),
        }


async def generate_expert_analysis(
    summary_json: Dict[str, Any],
    scores: Dict[str, Any],
    job_family: str,
    target_position: str,
) -> Dict[str, Any]:
    """
    生成专家级深度分析.
    
    使用 DeepSeek V4 Pro 对已有的画像摘要进行深度推理，
    输出 3 条深度洞察或面试追问建议。
    
    Args:
        summary_json: 基础画像生成阶段产出的结构化摘要
        scores: 测评分数
        job_family: 岗位族
        target_position: 目标岗位
        
    Returns:
        专家分析结果
    """
    import json
    
    # 构建专家分析提示词
    system_prompt = """你是一名资深人才测评专家，擅长从候选人画像中发现深层洞察。

你的任务是：
1. 分析已有的画像摘要和测评数据
2. 找出 HR 和用人经理可能忽略的关键点
3. 给出 3 条深度洞察或面试追问建议

输出要求：
- 每条洞察必须有具体的行为证据支撑
- 面试追问建议要具体、可操作
- 语言专业但易懂"""

    user_prompt = f"""请分析以下候选人画像，给出专家级洞察：

【目标岗位】{target_position}（{job_family} 岗位族）

【已有画像摘要】
{json.dumps(summary_json, ensure_ascii=False, indent=2)}

【测评分数】
{json.dumps(scores, ensure_ascii=False, indent=2)}

请输出 JSON 格式：
{{
  "expert_insights": [
    {{
      "type": "洞察/追问/风险预警",
      "title": "标题（10字以内）",
      "content": "具体内容（50-100字）",
      "evidence": "支撑证据"
    }}
  ],
  "interview_questions": [
    "面试追问问题1",
    "面试追问问题2"
  ],
  "hiring_suggestion": "是否建议录用的总结（30字以内）"
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        result = await call_portrait_model(
            messages=messages,
            level="expert",
            max_tokens=1024,
            temperature=0.4,
        )
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = parse_json_safely(content)
        
        parsed["_model"] = result.get("model", "unknown")
        parsed["_level"] = "expert"
        
        return parsed
        
    except Exception as e:
        logger.error(f"❌ 专家分析生成失败: {e}")
        return {
            "expert_insights": [],
            "interview_questions": [],
            "hiring_suggestion": "分析生成失败，请稍后重试",
            "_error": str(e),
        }


def get_router_status() -> Dict[str, Any]:
    """获取路由器状态信息."""
    import os

    return {
        "modelscope_available": False,
        "api_key_status": {"available": bool(os.getenv("AI_API_KEY"))},
        "models": [{
            "model_id": os.getenv("AI_MODEL", "deepseek-v4-pro"),
            "level": "deepseek",
            "api_base": os.getenv("AI_API_BASE", "https://api.deepseek.com"),
            "available": bool(os.getenv("AI_API_KEY")),
        }],
        "fallback_available": False,
        "routing_strategy": "DeepSeek only",
    }
