"""候选人画像 - 维度解析模块.

负责解析测评结果中的人格维度数据（MBTI、DISC、EPQ等）。
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.models import JobProfile
from . import schemas

logger = logging.getLogger(__name__)


def clean_summary_point_prefix(point: str) -> str:
    """清理summary_point中的序号前缀.
    
    移除以下格式的前缀：
    - "第1条：" "第一条：" "第1条:" "第一条:"
    - "1. " "1、" "1：" "1:"
    - "第2条：" "第二条：" 等
    
    Args:
        point: 原始文本
        
    Returns:
        清理后的文本
    """
    if not point:
        return point
    
    # 匹配各种序号前缀模式
    patterns = [
        r'^第[一二三四五六七八九十\d]+条[：:]\s*',  # 第一条：、第1条：
        r'^[一二三四五六七八九十]+[、：:．.]\s*',     # 一、、一：
        r'^\d+[、：:．.]\s*',                        # 1、、1.
        r'^\([一二三四五六七八九十\d]+\)\s*',        # (一)、(1)
        r'^【[一二三四五六七八九十\d]+】\s*',        # 【一】、【1】
    ]
    
    cleaned = point
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned)
    
    return cleaned.strip()


def clean_summary_points(points: List[str]) -> List[str]:
    """清理所有summary_points的序号前缀.
    
    Args:
        points: 原始文本列表
        
    Returns:
        清理后的文本列表
    """
    return [clean_summary_point_prefix(p) for p in points if p]


def parse_mbti_dimensions(result_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析MBTI维度数据.
    
    Args:
        result_details: 测评结果详情
        
    Returns:
        人格维度列表
    """
    personality_dimensions = []
    # 优先使用 mbti_dimensions（真实格式），其次使用 dimensions（旧格式）
    mbti_dimensions = result_details.get("mbti_dimensions") or result_details.get("dimensions", {})
    
    if not mbti_dimensions or not isinstance(mbti_dimensions, dict):
        return []
    
    # 检查是否是真实格式（E-I, S-N等键）
    dimension_keys = list(mbti_dimensions.keys())
    is_real_format = any('-' in key for key in dimension_keys if isinstance(key, str))
    
    if is_real_format:
        # 真实格式：{\"E-I\": {\"tendency\": \"E\", \"label\": \"外向\", \"value\": 72}, ...}
        for key in ['E-I', 'S-N', 'T-F', 'J-P']:
            dim_data = mbti_dimensions.get(key, {})
            if dim_data:
                value = float(dim_data.get('value', 50))
                # label_map定义对立维度的中文标签
                label_map = {
                    'E-I': '外向-内向',
                    'S-N': '感觉-直觉',
                    'T-F': '思考-情感',
                    'J-P': '判断-知觉'
                }
                combined_label = label_map.get(key, key)
                personality_dimensions.append({
                    "key": key,
                    "label": combined_label,
                    "score": value,
                    "description": f"{key} 维度"
                })
    else:
        # 旧格式：单独的 E, I, S, N 等键
        mbti_pairs = [
            ('E', 'I', '外向-内向', 'Extraversion vs Introversion'),
            ('S', 'N', '感觉-直觉', 'Sensing vs Intuition'),
            ('T', 'F', '思考-情感', 'Thinking vs Feeling'),
            ('J', 'P', '判断-知觉', 'Judging vs Perceiving'),
        ]
        
        for key1, key2, label_cn, label_en in mbti_pairs:
            dim1 = mbti_dimensions.get(key1, {})
            dim2 = mbti_dimensions.get(key2, {})
            if dim1 or dim2:
                score1 = float(dim1.get("score", 50)) if dim1 else 50
                score2 = float(dim2.get("score", 50)) if dim2 else 50
                # 使用较高分数的维度作为主导
                if score1 >= score2:
                    main_key, main_score = key1, score1
                    desc = dim1.get("description", dim1.get("label", ""))
                else:
                    main_key, main_score = key2, score2
                    desc = dim2.get("description", dim2.get("label", ""))
                personality_dimensions.append({
                    "key": f"{key1}/{key2}",
                    "label": f"{label_cn} ({main_key})",
                    "score": main_score,
                    "description": desc or label_en
                })
    
    if personality_dimensions:
        logger.info(f"✅ 使用MBTI真实维度数据: {len(personality_dimensions)}个维度")
    
    return personality_dimensions


def parse_disc_dimensions(result_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析DISC维度数据.
    
    Args:
        result_details: 测评结果详情
        
    Returns:
        人格维度列表
    """
    personality_dimensions = []
    disc_dimensions = result_details.get("disc_dimensions", {})
    
    if not disc_dimensions:
        return []
    
    disc_descriptions = {
        'D': '结果导向、决断力强',
        'I': '热情开朗、善于社交',
        'S': '耐心稳重、团队协作',
        'C': '严谨细致、追求品质'
    }
    
    for key in ['D', 'I', 'S', 'C']:
        dim_data = disc_dimensions.get(key, {})
        if dim_data:
            personality_dimensions.append({
                "key": key,
                "label": f"{key} {dim_data.get('label', '')}",
                "score": float(dim_data.get("value", 50)),
                "description": disc_descriptions.get(key, "")
            })
    
    if personality_dimensions:
        logger.info(f"✅ 使用DISC真实维度数据: {len(personality_dimensions)}个维度")
    
    return personality_dimensions


def parse_epq_dimensions(result_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析EPQ维度数据.
    
    Args:
        result_details: 测评结果详情
        
    Returns:
        人格维度列表
    """
    personality_dimensions = []
    # 优先使用 epq_dimensions（真实格式），其次使用 dimensions（旧格式）
    epq_dimensions = result_details.get("epq_dimensions") or result_details.get("dimensions", {})
    
    if not epq_dimensions or not isinstance(epq_dimensions, dict):
        return []
    
    # 检查是否是EPQ格式（有E/N/P/L四个维度）
    epq_keys = ['E', 'N', 'P', 'L']
    if not any(k in epq_dimensions for k in epq_keys):
        return []
    
    epq_labels = {
        'E': '外向性',
        'N': '神经质',
        'P': '精神质',
        'L': '掩饰性'
    }
    epq_descriptions = {
        'E': '倾向于独立思考和深度工作，适合需要专注的岗位',
        'N': '情绪稳定，能够在压力下保持冷静和理性',
        'P': '独立、坚韧，不随波逐流，适合需要自主决策的场景',
        'L': '行为真实，较少刻意迎合社会期望'
    }
    
    for key in epq_keys:
        dim_data = epq_dimensions.get(key, {})
        if dim_data and isinstance(dim_data, dict):
            # 优先使用 t_score（标准化分数），其次是 score，最后是 value
            score_val = dim_data.get("t_score", dim_data.get("score", dim_data.get("value", 50)))
            personality_dimensions.append({
                "key": key,
                "label": f"{epq_labels.get(key, key)} {key}",
                "score": float(score_val) if score_val else 50,
                "description": dim_data.get("description", epq_descriptions.get(key, ""))
            })
    
    if personality_dimensions:
        logger.info(f"✅ 使用EPQ真实维度数据: {len(personality_dimensions)}个维度")
    
    return personality_dimensions


def parse_personality_dimensions(result_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析人格维度数据（自动检测测评类型）.
    
    优先顺序：
    1. MBTI
    2. DISC
    3. EPQ
    
    Args:
        result_details: 测评结果详情
        
    Returns:
        人格维度列表
    """
    # 支持两种字段：questionnaire_type（真实格式）和 type（旧格式）
    test_type = (result_details.get("questionnaire_type") or result_details.get("type", "")).upper()
    
    # 1. 检查是否有MBTI真实数据
    if test_type == "MBTI" or result_details.get("personality_type"):
        dimensions = parse_mbti_dimensions(result_details)
        if dimensions:
            return dimensions
    
    # 2. 检查是否有DISC真实数据
    dimensions = parse_disc_dimensions(result_details)
    if dimensions:
        return dimensions
    
    # 3. 检查是否有EPQ真实数据（EPQ保存在 'epq_dimensions' 或 'dimensions' 字段中，且不是MBTI）
    if test_type != "MBTI":
        dimensions = parse_epq_dimensions(result_details)
        if dimensions:
            return dimensions
    
    return []


def build_dimension_scores(
    job_profile: JobProfile,
    dimension_scores_data: Any
) -> List[schemas.DimensionScore]:
    """构建维度得分列表.
    
    dimension_scores_data 可能是：
    - 列表格式: [{"name": "xxx", "score": 85, "weight": 100, "weighted_score": 85}]
    - 字典格式: {"维度名": {"score": 85, "weighted_score": 85}}
    
    Args:
        job_profile: 岗位画像
        dimension_scores_data: 维度得分数据
        
    Returns:
        维度得分列表
    """
    # 如果是列表格式（数据库存储格式），直接使用
    if isinstance(dimension_scores_data, list):
        result = []
        for item in dimension_scores_data:
            result.append(schemas.DimensionScore(
                name=item.get("name", ""),
                score=float(item.get("score", 0)),
                weight=float(item.get("weight", 0)),
                description=item.get("description"),
                weighted_score=float(item.get("weighted_score", 0))
            ))
        return result
    
    # 如果是字典格式，从job_profile获取维度定义
    dimension_scores_dict = dimension_scores_data if isinstance(dimension_scores_data, dict) else {}
    dimensions = json.loads(job_profile.dimensions) if job_profile.dimensions else []
    result = []
    
    for dim in dimensions:
        dim_name = dim.get("name", "")
        dim_weight = float(dim.get("weight", 0))
        dim_desc = dim.get("description")
        
        score_data = dimension_scores_dict.get(dim_name, {})
        score = float(score_data.get("score", 0)) if isinstance(score_data, dict) else 0
        weighted_score = float(score_data.get("weighted_score", 0)) if isinstance(score_data, dict) else 0
        
        result.append(schemas.DimensionScore(
            name=dim_name,
            score=score,
            weight=dim_weight,
            description=dim_desc,
            weighted_score=weighted_score
        ))
    
    return result


def get_default_personality_dimensions() -> List[Dict[str, Any]]:
    """获取默认的人格维度数据（EPQ格式）.
    
    Returns:
        默认人格维度列表
    """
    return [
        {"key": "E", "label": "外向性", "score": 75, "description": "社交活跃，善于表达"},
        {"key": "N", "label": "神经质", "score": 50, "description": "情绪稳定，抗压良好"},
        {"key": "P", "label": "精神质", "score": 65, "description": "独立思考，注重效率"},
        {"key": "L", "label": "掩饰性", "score": 80, "description": "自律性强，表现真诚"}
    ]

