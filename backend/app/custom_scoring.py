"""自定义问卷评分算法."""
from typing import Dict, List, Any, Optional, Tuple


def calculate_custom_questionnaire_score(
    questionnaire: Dict[str, Any],
    answers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    计算自定义问卷的分数.
    
    Args:
        questionnaire: 问卷配置（包含scoring_config和questions_data）
        answers: 用户提交的答案列表
        
    Returns:
        {
            "total_score": 88,
            "max_score": 100,
            "score_percentage": 88.0,
            "grade": "A",
            "detailed_answers": [...]
        }
    """
    custom_type = questionnaire.get("custom_type", "non_scored")
    scoring_config = questionnaire.get("scoring_config", {})
    
    # 如果是信息收集问卷（未启用评分），直接返回
    if custom_type == "non_scored" or not scoring_config.get("enabled", False):
        return {
            "total_score": None,
            "max_score": None,
            "score_percentage": None,
            "grade": None,
            "detailed_answers": prepare_answers_without_scoring(answers, questionnaire)
        }
    
    # 评分问卷：计算分数
    method = scoring_config.get("method", "by_question")
    questions_data = questionnaire.get("questions_data", {})
    questions = questions_data.get("questions", [])
    questions_dict = {q["id"]: q for q in questions}
    
    total_earned = 0.0
    max_possible = scoring_config.get("total_score", 100)
    detailed_answers = []
    
    for answer in answers:
        q_id = answer.get("question_id")
        question = questions_dict.get(q_id)
        
        if not question:
            continue
        
        # 计算该题得分
        earned, max_score = calculate_question_score(
            question, 
            answer, 
            method
        )
        
        total_earned += earned
        
        # 保存详细答案
        detailed_answers.append({
            "question_id": q_id,
            "question_title": question.get("title", ""),
            "question_type": question.get("type", ""),
            "answer": answer.get("answer", {}),
            "scoring": {
                "earned_score": round(earned, 1),
                "max_score": max_score,
                "percentage": round((earned / max_score * 100) if max_score > 0 else 0, 1)
            } if max_score > 0 else None
        })
    
    # 计算得分率
    score_percentage = round((total_earned / max_possible * 100) if max_possible > 0 else 0, 1)
    
    # 判定等级
    grade = determine_grade(total_earned, scoring_config.get("grades", []))
    
    return {
        "total_score": round(total_earned, 1),
        "max_score": max_possible,
        "score_percentage": score_percentage,
        "grade": grade,
        "detailed_answers": detailed_answers
    }


def calculate_question_score(
    question: Dict[str, Any],
    answer: Dict[str, Any],
    method: str
) -> Tuple[float, float]:
    """
    计算单题得分.
    
    Args:
        question: 题目配置
        answer: 用户答案
        method: 评分方式 (by_question/by_option)
    
    Returns:
        (earned_score, max_score)
    """
    q_type = question.get("type", "")
    scoring = question.get("scoring", {})
    max_score = scoring.get("max_score", 0)
    
    # 文本题、日期题默认不计分
    if q_type in ["short_text", "long_text", "date"]:
        return 0, 0
    
    # 评分题、NPS题：直接使用用户打分
    if q_type in ["scale", "nps"]:
        user_score = answer.get("answer", {}).get("value", 0)
        scale_max = question.get("scale_max", 10)
        if isinstance(user_score, (int, float)) and scale_max > 0:
            earned = (float(user_score) / float(scale_max)) * max_score
            return earned, max_score
        return 0, max_score
    
    # 是否题
    if q_type == "yes_no":
        user_answer = answer.get("answer", {}).get("boolean", False)
        if method == "by_option":
            # 按选项加权
            option_scores = scoring.get("option_scores", {})
            earned = option_scores.get(str(user_answer), 0)
        else:
            # 按题目等分（"是"得满分）
            earned = max_score if user_answer else 0
        return earned, max_score
    
    # 单选题
    if q_type == "single_choice":
        selected = answer.get("answer", {}).get("value")
        
        if method == "by_option":
            # 按选项加权
            option_scores = scoring.get("option_scores", {})
            earned = option_scores.get(selected, 0)
        else:
            # 按题目等分（任意选项都得满分）
            earned = max_score if selected else 0
        
        return earned, max_score
    
    # 多选题
    if q_type == "multiple_choice":
        selected = answer.get("answer", {}).get("values", [])
        
        if method == "by_option":
            # 按选项加权：累加所选选项的分值
            option_scores = scoring.get("option_scores", {})
            earned = sum(option_scores.get(opt, 0) for opt in selected)
        else:
            # 按题目等分：按选对比例给分
            total_options = len(question.get("options", []))
            if total_options > 0:
                earned = (len(selected) / total_options) * max_score
            else:
                earned = 0
        
        return min(earned, max_score), max_score
    
    return 0, 0


def determine_grade(score: float, grades: List[Dict[str, Any]]) -> Optional[str]:
    """
    根据分数判定等级.
    
    Args:
        score: 总分
        grades: 等级配置列表
    
    Returns:
        等级名称 (如 "A", "B", "C")
    """
    if not grades:
        return None
    
    # 按最低分从高到低排序
    sorted_grades = sorted(grades, key=lambda g: g.get("min_score", 0), reverse=True)
    
    for grade in sorted_grades:
        min_score = grade.get("min_score", 0)
        max_score = grade.get("max_score", 100)
        if min_score <= score <= max_score:
            return grade.get("name", "N/A")
    
    return "N/A"


def prepare_answers_without_scoring(
    answers: List[Dict[str, Any]], 
    questionnaire: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    准备无评分的答案列表（信息收集问卷）.
    
    Args:
        answers: 用户答案列表
        questionnaire: 问卷配置
    
    Returns:
        详细答案列表（不含评分信息）
    """
    questions_data = questionnaire.get("questions_data", {})
    questions = questions_data.get("questions", [])
    questions_dict = {q["id"]: q for q in questions}
    
    detailed_answers = []
    for answer in answers:
        q_id = answer.get("question_id")
        question = questions_dict.get(q_id)
        
        if question:
            detailed_answers.append({
                "question_id": q_id,
                "question_title": question.get("title", ""),
                "question_type": question.get("type", ""),
                "answer": answer.get("answer", {}),
                "scoring": None  # 无评分
            })
    
    return detailed_answers


def validate_scoring_config(scoring_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    验证评分配置的有效性.
    
    Args:
        scoring_config: 评分配置
    
    Returns:
        (is_valid, error_message)
    """
    if not scoring_config.get("enabled", False):
        return True, None
    
    # 检查总分
    total_score = scoring_config.get("total_score")
    if not total_score or total_score <= 0:
        return False, "总分必须大于0"
    
    # 检查评分方式
    method = scoring_config.get("method")
    if method not in ["by_question", "by_option"]:
        return False, "评分方式必须是 by_question 或 by_option"
    
    # 检查等级配置
    grades = scoring_config.get("grades", [])
    if not grades:
        return False, "必须配置至少一个等级"
    
    # 检查等级分数范围是否合理
    for grade in grades:
        min_score = grade.get("min_score")
        max_score = grade.get("max_score")
        if min_score is None or max_score is None:
            return False, f"等级 {grade.get('name')} 缺少分数范围"
        if min_score > max_score:
            return False, f"等级 {grade.get('name')} 的最低分大于最高分"
    
    return True, None

