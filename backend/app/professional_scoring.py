"""
专业测评评分模块
实现 MBTI、DISC、EPQ 三种标准心理测评的评分算法
"""
from typing import Dict, List, Optional
from app.professional_scoring_standard import (
    _calculate_grade,
    score_disc,
    score_epq,
    score_mbti,
)


class ProfessionalScoringError(ValueError):
    """评分错误异常"""
    pass


# =====================================================
# MBTI 评分算法
# =====================================================

# =====================================================
# 统一评分入口
# =====================================================

def score_professional_assessment(
    questionnaire_type: str,
    answers: Dict[str, str],
    questions: List[Dict] = None
) -> Dict:
    """
    专业测评统一评分入口
    
    Args:
        questionnaire_type: 问卷类型 ('MBTI', 'DISC', 'EPQ')
        answers: 答案字典 {question_id: answer_value}
        questions: 题目列表，包含id和dimension等字段
    
    Returns:
        评分结果字典，包含各维度分数和总分
    """
    type_upper = questionnaire_type.upper()
    
    if type_upper == 'MBTI':
        return score_mbti(answers, questions)
    elif type_upper == 'DISC':
        return score_disc(answers, questions)
    elif type_upper == 'EPQ':
        return score_epq(answers, questions)
    else:
        raise ProfessionalScoringError(
            f"不支持的测评类型: {questionnaire_type}，仅支持 MBTI/DISC/EPQ"
        )


# =====================================================
# 自定义问卷简单评分
# =====================================================

def score_custom_questionnaire(
    answers: Dict[str, any],
    scoring_config: Optional[Dict] = None
) -> Dict:
    """
    自定义问卷评分
    
    支持：
    - 单选题/多选题：根据配置的分值计分
    - 量表题：直接取分值
    - 文本题：不计分
    
    Args:
        answers: 答案字典
        scoring_config: 评分配置
            {
                'questions': {
                    'q1': {'type': 'radio', 'scores': {'A': 5, 'B': 3, 'C': 1}},
                    'q2': {'type': 'scale', 'max': 10}
                },
                'full_score': 100,
                'grade_cutoffs': {'A': 90, 'B': 75, 'C': 60, 'D': 0}
            }
    
    Returns:
        评分结果
    """
    if not scoring_config:
        return {
            'total_score': 0,
            'grade': 'N/A',
            'message': '未配置评分规则'
        }
    
    questions_config = scoring_config.get('questions', {})
    full_score = scoring_config.get('full_score', 100)
    
    total_score = 0
    
    for question_id, answer in answers.items():
        q_config = questions_config.get(question_id, {})
        q_type = q_config.get('type', '')
        
        if q_type == 'radio':
            # 单选题：查找选项对应的分数
            scores = q_config.get('scores', {})
            total_score += scores.get(str(answer), 0)
        
        elif q_type == 'checkbox':
            # 多选题：累加所有选项的分数
            scores = q_config.get('scores', {})
            if isinstance(answer, list):
                for option in answer:
                    total_score += scores.get(str(option), 0)
        
        elif q_type == 'scale':
            # 量表题：直接取分值
            try:
                total_score += float(answer)
            except (ValueError, TypeError):
                pass
    
    # 转换为百分制
    percentage = int((total_score / full_score) * 100) if full_score > 0 else 0
    
    # 计算等级
    grade_cutoffs = scoring_config.get('grade_cutoffs', {})
    grade = _calculate_grade_from_cutoffs(percentage, grade_cutoffs)
    
    return {
        'total_score': total_score,
        'percentage': percentage,
        'grade': grade,
        'full_score': full_score
    }


def _calculate_grade_from_cutoffs(score: int, cutoffs: Dict[str, int]) -> str:
    """根据配置的分数线计算等级"""
    if not cutoffs:
        return _calculate_grade(score)
    
    sorted_grades = sorted(cutoffs.items(), key=lambda x: x[1], reverse=True)
    for grade, cutoff in sorted_grades:
        if score >= cutoff:
            return grade
    
    return sorted_grades[-1][0] if sorted_grades else 'D'

