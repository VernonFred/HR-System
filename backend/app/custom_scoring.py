"""自定义问卷评分算法."""
import re
from typing import Dict, List, Any, Optional, Tuple


TEXT_QUESTION_TYPES = {"text", "textarea", "short_text", "long_text", "date"}
SINGLE_QUESTION_TYPES = {"radio", "single", "single_choice"}
MULTIPLE_QUESTION_TYPES = {"checkbox", "multiple", "multiple_choice"}
SCALE_QUESTION_TYPES = {"scale", "rating", "nps"}
YES_NO_QUESTION_TYPES = {"yesno", "yes_no"}
CHOICE_QUESTION_TYPES = {"choice"}


def normalize_scoring_config(
    scoring_config: Dict[str, Any] | None,
    custom_type: Optional[str] = None,
) -> Dict[str, Any]:
    """统一前后端新旧评分配置字段."""
    raw = scoring_config or {}
    total_score = raw.get("total_score", raw.get("totalScore", 100))
    passing_score = raw.get("passing_score", raw.get("passingScore", 60))
    enabled = raw.get("enabled")
    if enabled is None:
        enabled = custom_type == "scored" or any(
            key in raw for key in ("total_score", "totalScore", "grades", "gradeConfig")
        )

    grades = raw.get("grades")
    if grades is None and raw.get("gradeConfig"):
        grades = [
            {
                "name": item.get("grade") or item.get("name"),
                "label": item.get("label"),
                "min_score": item.get("minScore", item.get("min_score")),
                "max_score": item.get("maxScore", item.get("max_score")),
            }
            for item in raw.get("gradeConfig", [])
        ]

    return {
        "enabled": bool(enabled),
        "total_score": float(total_score or 100),
        "passing_score": float(passing_score or 60),
        "method": raw.get("method") or "auto",
        "grades": grades or [],
    }


def _extract_answer_value(answer: Any) -> Any:
    if isinstance(answer, dict) and "answer" in answer:
        answer = answer.get("answer")
    if isinstance(answer, dict):
        if "values" in answer:
            return answer.get("values")
        if "value" in answer:
            return answer.get("value")
        if "boolean" in answer:
            return answer.get("boolean")
        if "text" in answer:
            return answer.get("text")
    return answer


def _parse_score_text(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip()
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*分?", text)
    if match:
        return float(match.group(1))
    return None


def _option_score_candidates(option: Any, index: int) -> Tuple[list[str], Optional[float]]:
    if isinstance(option, dict):
        keys = [
            option.get("value"),
            option.get("label"),
            option.get("text"),
            option.get("id"),
            index,
            str(index),
        ]
        score = option.get("score")
        if score is None:
            score = _parse_score_text(option.get("label") or option.get("text") or option.get("value"))
    else:
        keys = [option, index, str(index)]
        score = _parse_score_text(option)
    try:
        score_value = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_value = None
    return [str(key) for key in keys if key not in (None, "")], score_value


def _build_option_score_map(question: Dict[str, Any]) -> Dict[str, float]:
    score_map: Dict[str, float] = {}
    for index, option in enumerate(question.get("options") or [], start=1):
        keys, score = _option_score_candidates(option, index)
        if score is None:
            continue
        for key in keys:
            score_map.setdefault(key, score)
    return score_map


def score_question_answer(question: Dict[str, Any], raw_answer: Any) -> Dict[str, Any]:
    """计算单题原始分，非评分题返回 scoreable=False."""
    q_type = question.get("type", "")
    answer_value = _extract_answer_value(raw_answer)

    if q_type in TEXT_QUESTION_TYPES or answer_value in (None, ""):
        return {"scoreable": False, "raw_score": None, "raw_max_score": None}

    option_scores = _build_option_score_map(question)

    if q_type in SCALE_QUESTION_TYPES:
        scale = question.get("scale") or {}
        raw_max = question.get("scale_max") or scale.get("max") or 10
        raw_score = _parse_score_text(answer_value)
        return {
            "scoreable": raw_score is not None,
            "raw_score": raw_score,
            "raw_max_score": float(raw_max),
        }

    values = answer_value if isinstance(answer_value, list) else [answer_value]
    selected_scores: list[float] = []
    for value in values:
        direct_score = _parse_score_text(value)
        if direct_score is not None:
            selected_scores.append(direct_score)
            continue
        mapped_score = option_scores.get(str(value))
        if mapped_score is not None:
            selected_scores.append(mapped_score)

    if not selected_scores:
        return {"scoreable": False, "raw_score": None, "raw_max_score": None}

    if q_type in MULTIPLE_QUESTION_TYPES and not _looks_like_rating_options(question):
        raw_max = sum(score for score in option_scores.values() if score > 0) or sum(selected_scores)
        raw_score = min(sum(selected_scores), raw_max)
    else:
        raw_max = max(option_scores.values()) if option_scores else max(selected_scores)
        raw_score = sum(selected_scores) / len(selected_scores)

    return {
        "scoreable": True,
        "raw_score": raw_score,
        "raw_max_score": raw_max,
    }


def _looks_like_rating_options(question: Dict[str, Any]) -> bool:
    options = question.get("options") or []
    if not options:
        return False
    scores = []
    for option in options:
        if not isinstance(option, dict):
            return False
        score = _parse_score_text(option.get("label") or option.get("text") or option.get("value"))
        if score is None:
            return False
        scores.append(score)
    return sorted(scores) == list(range(int(min(scores)), int(max(scores)) + 1))


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
    scoring_config = normalize_scoring_config(questionnaire.get("scoring_config", {}), custom_type)
    
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
    questions_data = questionnaire.get("questions_data", {})
    questions = questions_data.get("questions", [])
    questions_dict = {q["id"]: q for q in questions}

    max_possible = scoring_config.get("total_score", 100)
    scored_items = []
    detailed_answers = []
    
    for answer in answers:
        q_id = answer.get("question_id")
        question = questions_dict.get(q_id)
        
        if not question:
            continue
        score_detail = score_question_answer(question, answer.get("answer"))
        if score_detail["scoreable"]:
            scored_items.append(score_detail)

        detailed_answers.append({
            "question_id": q_id,
            "question_title": question.get("text", question.get("title", "")),
            "question_type": question.get("type", ""),
            "answer": answer.get("answer", {}),
            "scoring": score_detail if score_detail["scoreable"] else None,
        })

    total_raw = sum(item["raw_score"] for item in scored_items)
    max_raw = sum(item["raw_max_score"] for item in scored_items)
    if max_raw <= 0:
        return {
            "total_score": None,
            "max_score": max_possible,
            "score_percentage": None,
            "grade": None,
            "scored_question_count": 0,
            "detailed_answers": detailed_answers,
        }
    
    total_earned = total_raw / max_raw * max_possible
    score_percentage = round((total_earned / max_possible * 100) if max_possible > 0 else 0, 1)
    
    grade = determine_grade(total_earned, scoring_config.get("grades", []))

    for answer in detailed_answers:
        scoring = answer.get("scoring")
        if not scoring:
            continue
        raw_score = scoring["raw_score"]
        raw_max = scoring["raw_max_score"]
        earned_score = raw_score / max_raw * max_possible
        max_score = raw_max / max_raw * max_possible
        answer["scoring"] = {
            "raw_score": round(raw_score, 2),
            "raw_max_score": round(raw_max, 2),
            "earned_score": round(earned_score, 1),
            "max_score": round(max_score, 1),
            "percentage": round((raw_score / raw_max * 100) if raw_max > 0 else 0, 1),
        }
    
    return {
        "total_score": round(total_earned, 1),
        "max_score": max_possible,
        "score_percentage": score_percentage,
        "grade": grade,
        "scored_question_count": len(scored_items),
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
                "question_title": question.get("text", question.get("title", "")),
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
