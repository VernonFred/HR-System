"""候选人画像 - 维度映射模块.

定义测评维度与岗位维度的映射关系，用于计算岗位匹配度。
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# 维度映射表：岗位维度 → (测评类型, 测评维度, 权重, 是否反向)
DIMENSION_MAPPING: Dict[str, List[Tuple[str, str, float, bool]]] = {
    # 逻辑思维能力
    "逻辑思维": [
        ("mbti", "T-F", 0.7, False),   # MBTI的T倾向代表逻辑思维
        ("disc", "C", 0.3, False),      # DISC的C维度代表谨慎分析
    ],
    "逻辑思维能力": [
        ("mbti", "T-F", 0.7, False),
        ("disc", "C", 0.3, False),
    ],
    "分析能力": [
        ("mbti", "T-F", 0.6, False),
        ("mbti", "N-S", 0.2, False),   # N倾向代表抽象思维
        ("disc", "C", 0.2, False),
    ],
    "数据分析": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "N-S", 0.3, False),
        ("disc", "C", 0.2, False),
    ],
    "数据分析能力": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "N-S", 0.3, False),
        ("disc", "C", 0.2, False),
    ],
    
    # 沟通能力
    "沟通能力": [
        ("mbti", "E-I", 0.4, False),   # E倾向代表外向沟通
        ("disc", "I", 0.6, False),      # I维度代表影响力
    ],
    "沟通表达": [
        ("mbti", "E-I", 0.4, False),
        ("disc", "I", 0.6, False),
    ],
    "沟通表达能力": [
        ("mbti", "E-I", 0.4, False),
        ("disc", "I", 0.6, False),
    ],
    "表达能力": [
        ("mbti", "E-I", 0.5, False),
        ("disc", "I", 0.5, False),
    ],
    "客户沟通": [
        ("mbti", "E-I", 0.3, False),
        ("disc", "I", 0.5, False),
        ("disc", "S", 0.2, False),      # S维度代表稳健关系
    ],
    "客户沟通能力": [
        ("mbti", "E-I", 0.3, False),
        ("disc", "I", 0.5, False),
        ("disc", "S", 0.2, False),
    ],
    
    # 团队协作
    "团队协作": [
        ("mbti", "F-T", 0.5, False),   # F倾向代表情感共鸣
        ("disc", "S", 0.5, False),      # S维度代表稳定协作
    ],
    "团队协作能力": [
        ("mbti", "F-T", 0.5, False),
        ("disc", "S", 0.5, False),
    ],
    "协作能力": [
        ("mbti", "F-T", 0.5, False),
        ("disc", "S", 0.5, False),
    ],
    "跨部门协作": [
        ("mbti", "F-T", 0.4, False),
        ("mbti", "E-I", 0.2, False),
        ("disc", "I", 0.2, False),
        ("disc", "S", 0.2, False),
    ],
    
    # 执行能力
    "执行能力": [
        ("mbti", "J-P", 0.4, False),   # J倾向代表执行力
        ("disc", "D", 0.6, False),      # D维度代表驱动力
    ],
    "执行落地": [
        ("mbti", "J-P", 0.4, False),
        ("disc", "D", 0.6, False),
    ],
    "执行落地能力": [
        ("mbti", "J-P", 0.4, False),
        ("disc", "D", 0.6, False),
    ],
    "执行力": [
        ("mbti", "J-P", 0.4, False),
        ("disc", "D", 0.6, False),
    ],
    "方案交付": [
        ("mbti", "J-P", 0.5, False),
        ("disc", "D", 0.3, False),
        ("disc", "C", 0.2, False),
    ],
    "方案交付能力": [
        ("mbti", "J-P", 0.5, False),
        ("disc", "D", 0.3, False),
        ("disc", "C", 0.2, False),
    ],
    
    # 情绪稳定性
    "情绪稳定": [
        ("epq", "N", 1.0, True),       # N维度反向 (N越低越稳定)
    ],
    "情绪稳定性": [
        ("epq", "N", 1.0, True),
    ],
    "抗压能力": [
        ("epq", "N", 0.7, True),       # N维度反向
        ("disc", "D", 0.3, False),
    ],
    "压力管理": [
        ("epq", "N", 0.7, True),
        ("disc", "D", 0.3, False),
    ],
    
    # 责任心
    "责任心": [
        ("disc", "C", 0.6, False),
        ("epq", "P", 0.4, True),       # P维度反向 (P越低越有责任心)
    ],
    "责任感": [
        ("disc", "C", 0.6, False),
        ("epq", "P", 0.4, True),
    ],
    
    # 学习适应能力
    "学习能力": [
        ("mbti", "N-S", 0.5, False),   # N倾向代表开放性
        ("epq", "E", 0.3, False),      # E维度代表活跃度
        ("disc", "I", 0.2, False),
    ],
    "学习适应": [
        ("mbti", "N-S", 0.5, False),
        ("epq", "E", 0.3, False),
        ("disc", "I", 0.2, False),
    ],
    "学习适应能力": [
        ("mbti", "N-S", 0.5, False),
        ("epq", "E", 0.3, False),
        ("disc", "I", 0.2, False),
    ],
    "适应能力": [
        ("mbti", "N-S", 0.5, False),
        ("epq", "E", 0.3, False),
        ("disc", "I", 0.2, False),
    ],
    
    # 创新能力
    "创新能力": [
        ("mbti", "N-S", 0.6, False),   # N倾向代表创新思维
        ("mbti", "P-J", 0.4, False),   # P倾向代表灵活性
    ],
    "创新思维": [
        ("mbti", "N-S", 0.6, False),
        ("mbti", "P-J", 0.4, False),
    ],
    
    # 领导力
    "领导力": [
        ("disc", "D", 0.5, False),     # D维度代表支配性
        ("mbti", "E-I", 0.3, False),
        ("disc", "I", 0.2, False),
    ],
    "管理能力": [
        ("disc", "D", 0.5, False),
        ("mbti", "J-P", 0.3, False),
        ("mbti", "T-F", 0.2, False),
    ],
    
    # 决策能力
    "决策能力": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "J-P", 0.3, False),
        ("disc", "D", 0.2, False),
    ],
    "决策判断": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "J-P", 0.3, False),
        ("disc", "D", 0.2, False),
    ],
    "决策判断力": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "J-P", 0.3, False),
        ("disc", "D", 0.2, False),
    ],
    
    # 技术能力
    "技术能力": [
        ("mbti", "T-F", 0.6, False),
        ("mbti", "N-S", 0.2, False),
        ("disc", "C", 0.2, False),
    ],
    "技术理解": [
        ("mbti", "T-F", 0.6, False),
        ("mbti", "N-S", 0.2, False),
        ("disc", "C", 0.2, False),
    ],
    "技术理解能力": [
        ("mbti", "T-F", 0.6, False),
        ("mbti", "N-S", 0.2, False),
        ("disc", "C", 0.2, False),
    ],
    "编程能力": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "N-S", 0.3, False),
        ("disc", "C", 0.2, False),
    ],
    "系统设计": [
        ("mbti", "N-S", 0.5, False),
        ("mbti", "T-F", 0.4, False),
        ("disc", "C", 0.1, False),
    ],
    "系统设计能力": [
        ("mbti", "N-S", 0.5, False),
        ("mbti", "T-F", 0.4, False),
        ("disc", "C", 0.1, False),
    ],
    
    # 产品能力
    "产品规划": [
        ("mbti", "N-S", 0.5, False),
        ("mbti", "J-P", 0.3, False),
        ("disc", "D", 0.2, False),
    ],
    "产品规划能力": [
        ("mbti", "N-S", 0.5, False),
        ("mbti", "J-P", 0.3, False),
        ("disc", "D", 0.2, False),
    ],
    "用户洞察": [
        ("mbti", "N-S", 0.4, False),
        ("mbti", "F-T", 0.3, False),
        ("disc", "I", 0.3, False),
    ],
    "用户洞察力": [
        ("mbti", "N-S", 0.4, False),
        ("mbti", "F-T", 0.3, False),
        ("disc", "I", 0.3, False),
    ],
    "需求分析": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "N-S", 0.3, False),
        ("disc", "C", 0.2, False),
    ],
    "需求分析能力": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "N-S", 0.3, False),
        ("disc", "C", 0.2, False),
    ],
    
    # 其他通用能力
    "问题解决": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "N-S", 0.3, False),
        ("disc", "D", 0.2, False),
    ],
    "问题解决能力": [
        ("mbti", "T-F", 0.5, False),
        ("mbti", "N-S", 0.3, False),
        ("disc", "D", 0.2, False),
    ],
    "文档编写": [
        ("mbti", "J-P", 0.5, False),
        ("disc", "C", 0.5, False),
    ],
    "文档编写能力": [
        ("mbti", "J-P", 0.5, False),
        ("disc", "C", 0.5, False),
    ],
    "项目管理": [
        ("mbti", "J-P", 0.4, False),
        ("disc", "D", 0.4, False),
        ("disc", "C", 0.2, False),
    ],
    "项目管理能力": [
        ("mbti", "J-P", 0.4, False),
        ("disc", "D", 0.4, False),
        ("disc", "C", 0.2, False),
    ],
    "代码质量": [
        ("disc", "C", 0.6, False),
        ("mbti", "J-P", 0.4, False),
    ],
    "代码质量意识": [
        ("disc", "C", 0.6, False),
        ("mbti", "J-P", 0.4, False),
    ],
}


def extract_dimension_score(
    result_details: dict,
    test_type: str,
    dimension_key: str
) -> Optional[float]:
    """
    从测评结果中提取维度得分.
    
    Args:
        result_details: 测评结果详情（JSON解析后的字典）
        test_type: 测评类型 (mbti/disc/epq)
        dimension_key: 维度键名 (如 "E-I", "D", "N")
    
    Returns:
        0-100的得分，如果找不到则返回None
    
    Examples:
        >>> extract_dimension_score(result_details, "mbti", "E-I")
        65.0  # 外向分数
        
        >>> extract_dimension_score(result_details, "disc", "D")
        72.0  # D维度分数
    """
    if not result_details:
        return None
    
    try:
        if test_type == "mbti":
            # MBTI维度: "E-I", "S-N", "T-F", "J-P"
            mbti_dims = result_details.get("mbti_dimensions", [])
            for dim in mbti_dims:
                if dim.get("key") == dimension_key:
                    # 返回左侧倾向的分数 (E, S, T, J)
                    left_score = dim.get("leftScore")
                    if left_score is not None:
                        return float(left_score)
            return None
        
        elif test_type == "disc":
            # DISC维度: "D", "I", "S", "C"
            disc_dims = result_details.get("disc_dimensions", [])
            for dim in disc_dims:
                if dim.get("key") == dimension_key:
                    score = dim.get("score")
                    if score is not None:
                        return float(score)
            return None
        
        elif test_type == "epq":
            # EPQ维度: "E", "N", "P", "L"
            epq_dims = result_details.get("epq_dimensions", [])
            for dim in epq_dims:
                if dim.get("key") == dimension_key:
                    score = dim.get("score")
                    if score is not None:
                        return float(score)
            return None
        
        else:
            logger.warning(f"未知的测评类型: {test_type}")
            return None
    
    except Exception as e:
        logger.error(f"提取维度得分失败: test_type={test_type}, dimension_key={dimension_key}, error={e}")
        return None


def calculate_dimension_score_from_assessments(
    job_dim_name: str,
    candidate_assessments: List[dict]
) -> float:
    """
    基于候选人的测评数据计算岗位维度得分.
    
    Args:
        job_dim_name: 岗位维度名称 (如 "逻辑思维")
        candidate_assessments: 候选人的测评记录列表，每项包含:
            - test_type: 测评类型 (mbti/disc/epq)
            - result_details: 测评结果详情
            - score_percentage: 测评总分百分比
    
    Returns:
        0-100的得分
    
    Algorithm:
        1. 查找该岗位维度的映射关系
        2. 遍历映射关系，提取对应的测评维度得分
        3. 按权重加权平均
        4. 如果没有映射或提取失败，使用测评平均分降级
    """
    # 获取映射关系
    mapping = DIMENSION_MAPPING.get(job_dim_name)
    
    if not mapping:
        # 没有映射，使用测评平均分
        logger.debug(f"岗位维度 '{job_dim_name}' 没有映射关系，使用测评平均分")
        return _calculate_average_assessment_score(candidate_assessments)
    
    total_score = 0.0
    total_weight = 0.0
    
    for test_type, test_dim, weight, is_reverse in mapping:
        # 查找候选人该类型的测评
        assessment = _find_assessment_by_type(candidate_assessments, test_type)
        if not assessment:
            continue
        
        # 提取维度得分
        result_details = assessment.get("result_details", {})
        if isinstance(result_details, str):
            try:
                result_details = json.loads(result_details)
            except json.JSONDecodeError:
                result_details = {}
        
        dim_score = extract_dimension_score(result_details, test_type, test_dim)
        
        if dim_score is None:
            continue
        
        # 处理反向维度 (如EPQ的N维度: 分数越低越好)
        if is_reverse:
            dim_score = 100 - dim_score
        
        total_score += dim_score * weight
        total_weight += weight
    
    if total_weight > 0:
        final_score = total_score / total_weight
        logger.debug(f"岗位维度 '{job_dim_name}' 计算得分: {final_score:.1f} (基于映射)")
        return final_score
    
    # 降级: 使用测评平均分
    fallback_score = _calculate_average_assessment_score(candidate_assessments)
    logger.debug(f"岗位维度 '{job_dim_name}' 映射失败，使用测评平均分: {fallback_score:.1f}")
    return fallback_score


def _find_assessment_by_type(
    assessments: List[dict],
    test_type: str
) -> Optional[dict]:
    """
    从测评列表中查找指定类型的测评.
    
    Args:
        assessments: 测评列表
        test_type: 测评类型 (mbti/disc/epq)
    
    Returns:
        测评记录字典，如果找不到则返回None
    """
    for assessment in assessments:
        if assessment.get("test_type") == test_type:
            return assessment
    return None


def _calculate_average_assessment_score(assessments: List[dict]) -> float:
    """
    计算测评的平均分数.
    
    Args:
        assessments: 测评列表
    
    Returns:
        平均分 (0-100)，如果没有测评则返回60.0
    """
    if not assessments:
        return 60.0
    
    scores = []
    for assessment in assessments:
        score = assessment.get("score_percentage")
        if score is not None:
            scores.append(float(score))
    
    if scores:
        return sum(scores) / len(scores)
    
    return 60.0  # 默认及格分

