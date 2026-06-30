"""Text-based questionnaire parser helpers."""
import re
from typing import Any, Dict, List, Tuple


def _parse_text(content: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """解析纯文本格式问卷."""
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('gbk', errors='ignore')
    
    lines = text.strip().split('\n')
    
    metadata = {"name": "导入的问卷", "description": "", "estimated_minutes": 15}
    questions = []
    current_question = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 第一行可能是标题
        if not questions and not current_question and not _looks_like_question(line):
            metadata["name"] = line
            continue
        
        if _looks_like_question(line):
            if current_question:
                questions.append(current_question)
            current_question = _create_question_from_text(line, len(questions) + 1)
        elif current_question and _looks_like_option(line):
            _add_option_to_question(current_question, line)
    
    if current_question:
        questions.append(current_question)
    
    # V45: 后处理 - 根据选项智能推断题目类型
    questions = _post_process_questions(questions)
    
    return metadata, questions


def _post_process_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """V45: 后处理题目列表，根据选项智能推断题目类型."""
    for q in questions:
        options = q.get("options", [])
        option_count = len(options)
        current_type = q.get("type", "single")
        
        # 如果已经明确识别了类型（非默认单选），跳过
        if current_type != "single":
            continue
        
        # 根据选项数量和内容推断类型
        if option_count == 0:
            # 无选项 → 文本题
            q["type"] = "text"
        elif option_count == 2:
            # 2个选项，检查是否是是非题
            opt_texts = [opt.get("text", "").lower() for opt in options]
            yesno_pairs = [
                ("是", "否"), ("对", "错"), ("有", "没有"), ("会", "不会"),
                ("同意", "不同意"), ("满意", "不满意"), ("yes", "no"),
                ("true", "false"), ("正确", "错误")
            ]
            is_yesno = any(
                (p[0] in opt_texts[0] and p[1] in opt_texts[1]) or
                (p[1] in opt_texts[0] and p[0] in opt_texts[1])
                for p in yesno_pairs
            )
            
            if is_yesno:
                q["type"] = "yesno"
            else:
                # 检查选项长度，较长的可能是二选一
                avg_len = sum(len(opt.get("text", "")) for opt in options) / 2
                if avg_len > 15:
                    q["type"] = "choice"
                # 否则保持单选
        elif option_count > 6:
            # 选项过多，可能是多选题
            q["type"] = "multiple"
    
    return questions


def _looks_like_question(text: str) -> bool:
    """判断文本是否像一个题目."""
    # 常见的题目开头模式
    patterns = [
        r'^[\d]+[\.、\)）]\s*',  # 1. 或 1、或 1) 或 1）
        r'^Q[\d]+[\.、:：]?\s*',  # Q1. 或 Q1
        r'^第[\d一二三四五六七八九十]+[题道][\.、:：]?\s*',  # 第1题
        r'^[\(（][\d]+[\)）]\s*',  # (1) 或 （1）
        r'^题目[\d]*[\.、:：]?\s*',  # 题目1. 或 题目：
    ]
    
    for pattern in patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    # 包含问号的可能是题目
    if '?' in text or '？' in text:
        return True
    
    # V45: 增强识别 - 常见的题目开头词
    question_starters = ['请问', '您认为', '你认为', '请选择', '请评价', '您对', '你对', 
                         '以下', '下列', '关于', '对于', '在您看来', '在你看来']
    for starter in question_starters:
        if text.startswith(starter):
            return True
    
    return False


def _looks_like_option(text: str) -> bool:
    """判断文本是否像一个选项."""
    # 常见的选项开头模式
    patterns = [
        r'^[A-Za-z][\.、\)）:：]\s*',  # A. 或 A、或 A) 或 A：
        r'^[\(（][A-Za-z][\)）]\s*',  # (A) 或 （A）
        r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*',  # 圆圈数字
        r'^[\-\*•·]\s*',  # 列表符号
        r'^选项[A-Za-z一二三四五六][\.、:：]?\s*',  # 选项A. 或 选项一
    ]
    
    for pattern in patterns:
        if re.match(pattern, text):
            return True
    
    # V45: 短文本（<40字）且不像题目，可能是选项
    if len(text) < 40 and not _looks_like_question(text):
        # 检查是否是常见的选项内容
        option_keywords = ['非常', '比较', '一般', '不太', '完全', '同意', '不同意',
                          '满意', '不满意', '经常', '偶尔', '从不', '总是', '有时']
        for kw in option_keywords:
            if text.startswith(kw):
                return True
    
    return False


def _create_question_from_text(text: str, index: int) -> Dict[str, Any]:
    """从文本创建题目结构."""
    # 移除题号前缀
    clean_text = re.sub(r'^[\d]+[\.、\)）]\s*', '', text)
    clean_text = re.sub(r'^Q[\d]+[\.、:：]?\s*', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'^第[\d一二三四五六七八九十]+[题道][\.、:：]?\s*', '', clean_text)
    clean_text = re.sub(r'^[\(（][\d]+[\)）]\s*', '', clean_text)
    clean_text = re.sub(r'^题目[\d]*[\.、:：]?\s*', '', clean_text)
    
    # 判断题目类型（V45增强）
    q_type = "single"  # 默认单选
    
    # 检测多选题
    if any(kw in text for kw in ['多选', '可多选', '多项选择', '选择所有', '可以选择多个', '至少选择']):
        q_type = "multiple"
    
    # 检测填空题/文本题
    elif any(kw in text for kw in ['请填写', '请输入', '简答', '填空', '请描述', '请说明', 
                                    '请写出', '请列举', '您的建议', '你的建议', '其他意见']):
        q_type = "text"
    
    # 检测多行文本题
    elif any(kw in text for kw in ['详细描述', '详细说明', '请详细', '具体说明', '补充说明']):
        q_type = "textarea"
    
    # 检测评分题/量表题
    elif any(kw in text for kw in ['评分', '打分', '分数', '1-5', '1-10', '评价程度', 
                                    '满意度', '认同程度', '从1到', '量表']):
        q_type = "rating"
    
    # 检测是非题
    elif any(kw in text for kw in ['是否', '是不是', '有没有', '对不对', '同不同意']):
        q_type = "yesno"
    
    return {
        "id": f"q{index}",
        "text": clean_text.strip(),
        "type": q_type,
        "options": [],
        "required": True,
        "score": 0 if q_type in ["text", "textarea", "rating"] else None
    }


def _add_option_to_question(question: Dict[str, Any], text: str) -> None:
    """向题目添加选项."""
    # 移除选项前缀
    clean_text = re.sub(r'^[A-Za-z][\.、\)）:：]\s*', '', text)
    clean_text = re.sub(r'^[\(（][A-Za-z][\)）]\s*', '', clean_text)
    clean_text = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', clean_text)
    clean_text = re.sub(r'^[\-\*•·]\s*', '', clean_text)
    
    option_index = len(question["options"])
    
    # 检测是否有分数标记
    score = 0
    score_match = re.search(r'[\(（](\d+)分[\)）]', clean_text)
    if score_match:
        score = int(score_match.group(1))
        clean_text = re.sub(r'[\(（]\d+分[\)）]', '', clean_text)
    
    # 🟢 检测是否为"其他"选项（允许用户自定义输入）
    allow_custom = False
    placeholder = None
    other_patterns = [
        r'其他.*(?:请注明|请填写|请说明|请写明)',
        r'其他.*[（(].*[)）].*[_＿]+',
        r'其他\s*[（(].*[)）]',
        r'其他\s*[_＿]{2,}',
    ]
    for pattern in other_patterns:
        if re.search(pattern, clean_text, re.IGNORECASE):
            allow_custom = True
            placeholder = "请填写具体内容..."
            break
    
    option_data = {
        "id": f"{question['id']}_opt{option_index}",
        "text": clean_text.strip(),
        "score": score
    }
    
    # 添加自定义输入字段
    if allow_custom:
        option_data["allow_custom"] = True
        option_data["placeholder"] = placeholder
    
    question["options"].append(option_data)
