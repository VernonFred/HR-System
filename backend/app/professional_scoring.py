"""
专业测评评分模块
实现 MBTI、DISC、EPQ 三种标准心理测评的评分算法
"""
from typing import Dict, List, Tuple, Optional
import statistics


class ProfessionalScoringError(ValueError):
    """评分错误异常"""
    pass


# =====================================================
# MBTI 评分算法
# =====================================================

def score_mbti(answers: Dict[str, str], questions: List[Dict] = None) -> Dict:
    """
    MBTI性格测试评分
    
    93道题，每道题选择A或B
    四个维度：E/I, S/N, T/F, J/P
    
    支持两种模式：
    1. 如果提供questions参数，根据题目的dimension字段评分
    2. 如果没有questions，按题号范围评分（兼容旧格式）
    
    答案格式支持：{"1": "A"} 或 {"mbti_1": "A"} 或 {1: "A"}
    """
    
    # 初始化维度计数器
    dimension_counts = {
        'EI': {'A': 0, 'B': 0},
        'SN': {'A': 0, 'B': 0},
        'TF': {'A': 0, 'B': 0},
        'JP': {'A': 0, 'B': 0}
    }
    
    # 如果提供了题目数据，根据题目的dimension字段评分
    if questions:
        for q in questions:
            q_id = str(q.get('id', ''))
            dimension = q.get('dimension', '')
            
            # 尝试多种答案key格式
            answer = (
                answers.get(q_id, '') or 
                answers.get(f'mbti_{q_id}', '') or 
                answers.get(int(q_id) if q_id.isdigit() else q_id, '')
            )
            answer = str(answer).upper()
            
            if dimension in dimension_counts and answer in ['A', 'B']:
                dimension_counts[dimension][answer] += 1
    else:
        # 兼容旧格式：尝试多种key格式
        for i in range(1, 94):  # 93道题
            # 尝试多种key格式
            answer = (
                answers.get(str(i), '') or 
                answers.get(f'mbti_{i}', '') or
                answers.get(i, '')
            )
            answer = str(answer).upper()
            
            if answer in ['A', 'B']:
                # 按题号范围分配维度
                if 1 <= i <= 23:
                    dimension_counts['EI'][answer] += 1
                elif 24 <= i <= 50:
                    dimension_counts['SN'][answer] += 1
                elif 51 <= i <= 73:
                    dimension_counts['TF'][answer] += 1
                elif 74 <= i <= 93:
                    dimension_counts['JP'][answer] += 1
    
    # 计算各维度倾向和百分比
    mbti_type = ""
    mbti_dimensions = {}
    
    for dim_code in ['EI', 'SN', 'TF', 'JP']:
        a_count = dimension_counts[dim_code]['A']
        b_count = dimension_counts[dim_code]['B']
        total = a_count + b_count
        
        if total == 0:
            # 如果某维度没有答案，使用默认值（50%）
            a_percentage = 50
        else:
            a_percentage = (a_count / total) * 100
        
        # 确定倾向（A选项代表E, S, T, J）
        dim_mapping = {
            'EI': ('E', 'I', '外向型', '内向型'),
            'SN': ('S', 'N', '感觉型', '直觉型'),
            'TF': ('T', 'F', '思考型', '情感型'),
            'JP': ('J', 'P', '判断型', '知觉型')
        }
        
        a_letter, b_letter, a_label, b_label = dim_mapping[dim_code]
        
        if a_percentage > 50:
            tendency = a_letter
            value = int(a_percentage)
            label = a_label
        else:
            tendency = b_letter
            value = int(100 - a_percentage)
            label = b_label
        
        mbti_type += tendency
        mbti_dimensions[dim_code] = {
            'tendency': tendency,
            'label': label,
            'value': value,
            'description': f'倾向于{label}'
        }
    
    # MBTI类型描述映射
    type_descriptions = {
        'INTJ': '建筑师 - 富有想象力和战略性的思考者',
        'INTP': '逻辑学家 - 具有创新性的发明家',
        'ENTJ': '指挥官 - 大胆、富有想象力且意志强大的领导者',
        'ENTP': '辩论家 - 聪明好奇的思想家',
        'INFJ': '提倡者 - 安静而神秘且充满灵感',
        'INFP': '调停者 - 诗意、善良且利他的人',
        'ENFJ': '主人公 - 具有魅力且鼓舞人心的领导者',
        'ENFP': '竞选者 - 热情、富有创造力和社交能力的自由人',
        'ISTJ': '物流师 - 实际且注重事实的个人',
        'ISFJ': '守卫者 - 非常专注且温暖的守护者',
        'ESTJ': '总经理 - 出色的管理者',
        'ESFJ': '执政官 - 极有同情心、受欢迎且乐于助人',
        'ISTP': '鉴赏家 - 大胆而实际的实验者',
        'ISFP': '探险家 - 灵活且富有魅力的艺术家',
        'ESTP': '企业家 - 聪明、精力充沛且善于察言观色',
        'ESFP': '表演者 - 自发的、精力充沛和热情的艺人'
    }
    
    # 计算平均分
    avg_score = sum(d['value'] for d in mbti_dimensions.values()) // 4
    
    return {
        'mbti_type': mbti_type,
        'mbti_description': type_descriptions.get(mbti_type, f'{mbti_type}人格类型'),
        'mbti_dimensions': mbti_dimensions,
        'total_score': avg_score,
        'grade': _calculate_grade(avg_score)
    }


# =====================================================
# DISC 评分算法
# =====================================================

def score_disc(answers: Dict[str, str], questions: List[Dict] = None) -> Dict:
    """
    DISC行为风格测评评分
    
    支持两种格式：
    1. 量表题格式（1-5分）：根据题目的 dimension 字段累加分数
    2. 选择题格式（A/B/C/D）：A=D, B=I, C=S, D=C
    
    28道题，每个维度7道题
    量表评分规则：每题1-5分，每个维度最高35分
    """
    
    dimension_totals = {'D': 0, 'I': 0, 'S': 0, 'C': 0}
    question_counts = {'D': 0, 'I': 0, 'S': 0, 'C': 0}
    
    # 构建题目ID到维度的映射
    question_dimension_map = {}
    if questions:
        for q in questions:
            q_id = str(q.get('id', '')).replace('disc_', '')
            dimension = q.get('dimension', '')
            if dimension in ['D', 'I', 'S', 'C']:
                question_dimension_map[q_id] = dimension
                # 也支持带前缀的ID
                question_dimension_map[f"disc_{q_id}"] = dimension
    
    # 如果没有题目信息，使用默认映射（1-7=D, 8-14=I, 15-21=S, 22-28=C）
    if not question_dimension_map:
        for i in range(1, 8):
            question_dimension_map[str(i)] = 'D'
        for i in range(8, 15):
            question_dimension_map[str(i)] = 'I'
        for i in range(15, 22):
            question_dimension_map[str(i)] = 'S'
        for i in range(22, 29):
            question_dimension_map[str(i)] = 'C'
    
    # DISC选项映射（用于选择题格式）
    option_to_dimension = {'A': 'D', 'B': 'I', 'C': 'S', 'D': 'C'}
    
    # 遍历所有答案
    for key, value in answers.items():
        # 清理key
        clean_key = str(key).replace('disc_', '')
        
        # 尝试获取维度
        dimension = question_dimension_map.get(clean_key) or question_dimension_map.get(str(key))
        
        if dimension:
            # 量表题格式：值是数字1-5
            try:
                score = int(value)
                if 1 <= score <= 5:
                    dimension_totals[dimension] += score
                    question_counts[dimension] += 1
                    continue
            except (ValueError, TypeError):
                pass
        
        # 选择题格式：值是A/B/C/D
        answer = str(value).upper()
        if answer in option_to_dimension:
            dimension_totals[option_to_dimension[answer]] += 1
            question_counts[option_to_dimension[answer]] += 1
    
    # 计算每个维度的百分比（相对于最大可能分）
    # 量表题：每个维度7题，每题最高5分，最高35分
    max_per_dimension = 35
    
    disc_dimensions = {}
    labels = {'D': '支配型', 'I': '影响型', 'S': '稳健型', 'C': '谨慎型'}
    
    for dim in ['D', 'I', 'S', 'C']:
        raw = dimension_totals[dim]
        # 计算百分比
        pct = int((raw / max_per_dimension * 100)) if max_per_dimension > 0 else 0
        pct = min(pct, 100)  # 确保不超过100
        disc_dimensions[dim] = {
            'label': labels[dim],
            'value': pct,
            'raw_score': raw
    }
    
    # 确定主导风格（得分最高的维度）
    dominant = max(dimension_totals.items(), key=lambda x: x[1])[0]
    
    style_descriptions = {
        'D': 'D型 - 支配型：直接、果断、以结果为导向',
        'I': 'I型 - 影响型：外向、热情、善于社交',
        'S': 'S型 - 稳健型：耐心、可靠、支持他人',
        'C': 'C型 - 谨慎型：精确、分析、注重细节'
        }
    
    # 计算综合分（使用主导维度百分比作为总分）
    total_score = disc_dimensions[dominant]['value']
    
    return {
        'disc_type': dominant + '型',
        'disc_description': style_descriptions.get(dominant, ''),
        'disc_dimensions': disc_dimensions,
        'raw_scores': dimension_totals,
        'total_score': total_score,
        'grade': _calculate_grade(total_score)
    }


# =====================================================
# EPQ 评分算法
# =====================================================

def score_epq(answers: Dict[str, str], questions: List[Dict] = None) -> Dict:
    """
    EPQ艾森克人格问卷评分
    
    支持两个版本：
    - EPQ简版：48道题，每个维度12题
    - EPQ完整版：88道题，E:21题, N:24题, P:23题, L:20题
    
    根据题目的dimension字段来确定维度，而非固定题号范围
    
    支持答案格式：{"1": "A"} 或 {"1": "是"} 或 {"epq_1": "yes"}
    """
    
    # 初始化各维度计数
    dimension_counts = {
        'E': {'yes': 0, 'total': 0},
        'N': {'yes': 0, 'total': 0},
        'P': {'yes': 0, 'total': 0},
        'L': {'yes': 0, 'total': 0}
    }
    
    # 如果有题目数据，根据题目的dimension字段来计分
    if questions:
        for q in questions:
            q_id = str(q.get('id', ''))
            dimension = q.get('dimension', '').upper()
            
            if dimension not in dimension_counts:
                continue
            
            # 获取用户答案
            answer = (
                answers.get(q_id, '') or
                answers.get(f'epq_{q_id}', '') or
                answers.get(int(q_id) if q_id.isdigit() else q_id, '')
            )
            answer = str(answer).lower().strip()
            
            if not answer:
                continue
            
            dimension_counts[dimension]['total'] += 1
            
            # 判断是否为"是"类答案（正向计分）
            # 支持: A, 是, yes, true, 1, y
            is_yes = answer in ['a', 'yes', 'true', '1', '是', 'y']
            
            # 检查题目是否为反向计分
            reverse = q.get('reverse', False)
            if reverse:
                is_yes = not is_yes
            
            if is_yes:
                dimension_counts[dimension]['yes'] += 1
    else:
        # 兼容旧逻辑：如果没有题目数据，尝试按题号范围分配
        # 48题版本的范围
        dimension_ranges_48 = {
            'E': (1, 12),
            'N': (13, 24),
            'P': (25, 36),
            'L': (37, 48)
        }
        # 88题版本的范围
        dimension_ranges_88 = {
            'E': (1, 21),
            'N': (22, 45),
            'P': (46, 68),
            'L': (69, 88)
        }
        
        # 检测是48题还是88题版本
        max_question_id = 0
        for key in answers.keys():
            try:
                q_id = int(str(key).replace('epq_', ''))
                max_question_id = max(max_question_id, q_id)
            except:
                pass
        
        dimension_ranges = dimension_ranges_88 if max_question_id > 48 else dimension_ranges_48
        
        for dim_code, (start, end) in dimension_ranges.items():
            for order in range(start, end + 1):
                answer = (
                    answers.get(str(order), '') or
                    answers.get(f'epq_{order}', '') or
                    answers.get(order, '')
                )
                answer = str(answer).lower().strip()
                
                if answer:
                    dimension_counts[dim_code]['total'] += 1
                    is_yes = answer in ['a', 'yes', 'true', '1', '是', 'y']
                    if is_yes:
                        dimension_counts[dim_code]['yes'] += 1
    
    # 计算各维度结果
    dimension_results = {}
    
    for dim_code in ['E', 'N', 'P', 'L']:
        yes_count = dimension_counts[dim_code]['yes']
        total_count = dimension_counts[dim_code]['total']
        
        # 计算原始分和T分
        raw_score = yes_count
        if total_count > 0:
            # 使用更合理的T分计算：基于该维度的总题数
            mean = total_count / 2  # 均值为题数的一半
            std = total_count / 4   # 标准差约为题数的1/4
            t_score = int((raw_score - mean) / std * 10 + 50) if std > 0 else 50
        else:
            t_score = 50  # 默认中等水平
        
        t_score = max(20, min(80, t_score))  # 限制在20-80范围
        
        # 确定水平
        if t_score >= 60:
            level = '高'
        elif t_score >= 40:
            level = '中'
        else:
            level = '低'
        
        dimension_results[dim_code] = {
            'value': raw_score,
            't_score': t_score,
            'level': level,
            'label': _get_epq_label(dim_code),
            'total_questions': total_count  # 添加总题数用于调试
        }
    
    # 确定人格类型
    e_level = dimension_results['E']['level']
    n_level = dimension_results['N']['level']
    
    if e_level == '高' and n_level == '低':
        personality_trait = '外向稳定型'
    elif e_level == '高' and n_level == '高':
        personality_trait = '外向不稳定型'
    elif e_level == '低' and n_level == '低':
        personality_trait = '内向稳定型'
    else:
        personality_trait = '内向不稳定型'
    
    # 计算总分（T分平均）
    avg_t_score = sum(d['t_score'] for d in dimension_results.values()) // 4
    
    return {
        'personality_trait': personality_trait,
        'dimensions': dimension_results,
        'total_score': avg_t_score,
        'grade': _calculate_grade(avg_t_score)
    }


def _get_epq_label(dim_code: str) -> str:
    """获取EPQ维度标签"""
    labels = {
        'E': '外向性',
        'N': '神经质',
        'P': '精神质',
        'L': '掩饰性'
    }
    return labels.get(dim_code, dim_code)


def _calculate_grade(score: int) -> str:
    """根据分数计算等级"""
    if score >= 90:
        return 'A'
    elif score >= 75:
        return 'B'
    elif score >= 60:
        return 'C'
    else:
        return 'D'


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

