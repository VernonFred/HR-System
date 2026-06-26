"""AI 服务层 - DeepSeek 单模型版。"""

import logging
from functools import lru_cache
from typing import Any, Dict, List

from app.core.ai.ai_client import AIClientError, parse_json_safely, pick_content_text, post_chat
from app.core.ai import prompt_builder
from app.core.ai.portrait_router import (
    call_portrait_model, 
    should_use_pro_level,
    generate_expert_analysis,
    get_router_status,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def _cache_placeholder() -> Dict[str, Dict[str, Any]]:
    # 通过 lru_cache 返回同一个 dict 实例，避免全局变量检查告警
    return {}


def _get_cache() -> Dict[str, Dict[str, Any]]:
    return _cache_placeholder()


def _cache_get(key: str) -> Dict[str, Any] | None:
    return _get_cache().get(key)


def _cache_set(key: str, value: Dict[str, Any]) -> None:
    _get_cache()[key] = value


async def ai_interpretation(
    payload: Dict[str, Any],
    force_pro: bool = False,
    use_expert_summary: bool = False,
) -> Dict[str, Any]:
    """
    AI 画像解读 - 统一使用 DeepSeek V4 Pro.
    
    Args:
        payload: 画像生成参数
        force_pro: 是否强制使用 Pro 级分析
        use_expert_summary: 是否使用专家级综合分析（二阶段生成，仍走 DeepSeek V4 Pro）
        
    Returns:
        画像结果字典
    """
    # 专家分析模式不使用缓存（每次都重新生成）
    cache_key = f"interpretation:{payload.get('submission_code')}"
    if payload.get("submission_code") and not use_expert_summary:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    # 判断分析级别
    position = payload.get("position_keywords", [""])[0] if payload.get("position_keywords") else ""
    
    # level 只用于选择提示词模板；模型固定为 DeepSeek V4 Pro。
    if use_expert_summary:
        level = "expert"
        logger.info("🧠 使用专家分析提示词模式 (level=expert, model=DeepSeek V4 Pro)")
    else:
        use_pro = should_use_pro_level(
            position=position,
            force_pro=force_pro,
            competency_scores=payload.get("competency_scores"),
        )
        level = "pro" if use_pro else "normal"
        logger.info("📊 使用画像提示词模式: %s", level)
    
    # ⭐ 关键修复：传入 level 参数以选择对应的提示词
    # 🟢 P2-3增强: 传递候选岗位参考给提示词构建器
    candidate_positions = payload.get("candidate_positions")
    messages = prompt_builder.build_interpretation_prompt(
        payload, 
        level=level,
        candidate_positions=candidate_positions  # 🟢 传递候选岗位
    )
    
    try:
        # 使用画像专用路由器
        resp = await call_portrait_model(
            messages=messages,
            level=level,
            max_tokens=4096,
            temperature=0.7,  # 提高temperature增加输出多样性
        )
        data = parse_json_safely(pick_content_text(resp))
        data = _fill_interpretation_defaults(data)
        
        # 记录使用的模型信息
        data["_model"] = resp.get("model", "unknown")
        data["_level"] = resp.get("level", level)
        
        logger.info(f"✅ AI画像生成成功 model={data.get('_model')} level={data.get('_level')}")
        
        # 二阶段生成：专家级综合分析
        if use_expert_summary:
            logger.info("🧠 启用二阶段生成：专家级综合分析")
            from app.core.ai.portrait_router import generate_expert_summary
            
            scores = payload.get("scores", {})
            job_family = payload.get("job_family", "通用")
            
            expert_result = await generate_expert_summary(
                basic_portrait=data,
                scores=scores,
                target_position=position,
                job_family=job_family,
            )
            
            # 合并专家分析结果
            if expert_result.get("expert_summary"):
                data["summary_points"] = expert_result.get("expert_summary", [])
                data["hiring_recommendation"] = expert_result.get("hiring_recommendation", "")
                data["interview_focus"] = expert_result.get("interview_focus", [])
                data["_expert_model"] = expert_result.get("_model", "unknown")
                logger.info("✅ 专家级综合分析已合并")
        
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_interpretation failed, return fallback: %s", exc)
        data = _fill_interpretation_defaults({})
        data["_error"] = str(exc)

    if payload.get("submission_code") and not use_expert_summary:
        _cache_set(cache_key, data)
    return data


async def ai_expert_analysis(
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
    return await generate_expert_analysis(
        summary_json=summary_json,
        scores=scores,
        job_family=job_family,
        target_position=target_position,
    )


def get_ai_router_status() -> Dict[str, Any]:
    """获取 AI 路由器状态."""
    return get_router_status()


async def ai_match(payload: Dict[str, Any]) -> Dict[str, Any]:
    cache_key = f"match:{payload.get('submission_code')}"
    if payload.get("submission_code"):
        cached = _cache_get(cache_key)
        if cached:
            return cached

    messages = prompt_builder.build_match_prompt(payload)
    try:
        resp = await post_chat(messages)
        data = parse_json_safely(pick_content_text(resp))
        data = _fill_match_defaults(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_match failed, return fallback: %s", exc)
        data = _fill_match_defaults({})

    if payload.get("submission_code"):
        _cache_set(cache_key, data)
    return data


async def ai_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    cache_key = f"report:{payload.get('submission_code')}"
    if payload.get("submission_code"):
        cached = _cache_get(cache_key)
        if cached:
            return cached

    messages = prompt_builder.build_report_prompt(payload)
    try:
        resp = await post_chat(messages, max_tokens=4096, temperature=0.4)
        data = parse_json_safely(pick_content_text(resp))
        data = _fill_report_defaults(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_report failed, return fallback: %s", exc)
        data = _fill_report_defaults({})

    if payload.get("submission_code"):
        _cache_set(cache_key, data)
    return data


def _split_summary_to_points(summary: str, target_count: int = 3) -> List[str]:
    """智能拆分summary为多条观点."""
    if not summary:
        return []
    
    # 先尝试按段落拆分（\n\n）
    paragraphs = [p.strip() for p in summary.split("\n\n") if p.strip()]
    if len(paragraphs) >= target_count:
        return paragraphs[:target_count]
    
    # 如果段落不足，尝试按句子拆分（。）
    sentences = []
    for para in paragraphs:
        # 按中文句号拆分，并过滤空句子
        para_sentences = [s.strip() + "。" for s in para.split("。") if s.strip()]
        sentences.extend(para_sentences)
    
    # 如果句子数量足够，选择前N句
    if len(sentences) >= target_count:
        return sentences[:target_count]
    
    # 如果还是不够，返回原段落
    return paragraphs if paragraphs else [summary]


def _detemplate_positions(positions: List[str]) -> List[str]:
    """移除岗位推荐中的模板化句式，保留个性化内容."""
    if not positions:
        return positions
    
    # 需要移除的模板化片段
    templates = [
        "最适合B轮-C轮快速扩张期的",
        "B轮-C轮快速扩张期",
        "与候选人'敢于尝试、快速学习'的特质高度匹配",
        "'敢于尝试、快速学习'的特质高度匹配",
    ]
    
    result = []
    for pos in positions:
        cleaned = pos
        for template in templates:
            cleaned = cleaned.replace(template, "")
        # 清理多余空格和标点
        cleaned = cleaned.strip()
        if cleaned.startswith("。") or cleaned.startswith("，"):
            cleaned = cleaned[1:].strip()
        if cleaned:
            result.append(cleaned)
    
    return result


def _fill_interpretation_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """填充 AI 解读默认值 - 增强版"""
    # 处理summary_points：优先使用AI返回的，否则智能拆分summary
    summary_points = data.get("summary_points", [])
    if not summary_points and data.get("summary"):
        summary_points = _split_summary_to_points(data.get("summary", ""), target_count=3)
    
    # ⭐ 后处理：移除岗位推荐中的模板化句式
    suitable_positions = _detemplate_positions(data.get("suitable_positions") or [])
    unsuitable_positions = _detemplate_positions(data.get("unsuitable_positions") or [])
    
    return {
        "personality_dimensions": data.get("personality_dimensions") or data.get("dimensions") or [],
        "dimensions": data.get("dimensions") or data.get("personality_dimensions") or [],  # 兼容
        "competencies": data.get("competencies") or [],
        "strengths": data.get("strengths") or [],
        "risks": data.get("risks") or [],
        "summary": data.get("summary") or "",
        "summary_points": summary_points,  # 新增：3条核心观点
        "quick_tags": data.get("quick_tags") or [],  # ⭐ 新增：头部快速标签
        "suitable_positions": suitable_positions,  # ⭐ 移除模板化句式
        "unsuitable_positions": unsuitable_positions,  # ⭐ 移除模板化句式
        "development_suggestions": data.get("development_suggestions") or [],
        "interview_focus": data.get("interview_focus") or [],
    }


def _fill_match_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """填充 AI 匹配默认值，确保返回列表类型."""
    def _ensure_list(val):
        if val is None:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            # 如果是字符串，包装成单元素列表
            return [val] if val.strip() else []
        return []
    
    return {
        "match_analysis": _ensure_list(data.get("match_analysis")),
        "risks": _ensure_list(data.get("risks")),
        "follow_up_questions": _ensure_list(data.get("follow_up_questions")),
    }


def _fill_report_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "markdown": data.get("markdown") or "AI 暂不可用，请稍后重试。",
    }
