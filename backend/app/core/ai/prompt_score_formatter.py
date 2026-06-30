"""Assessment score prompt formatting helpers."""
from typing import Any, Dict


def _get_test_type_description(test_type: str) -> str:
    """获取测评类型的详细说明."""
    descriptions = {
        "DISC": """DISC 行为风格测评：
- D (Dominance/支配型)：结果导向、决断力强、喜欢挑战
- I (Influence/影响型)：热情开朗、善于社交、富有感染力
- S (Steadiness/稳健型)：耐心稳重、团队协作、追求和谐
- C (Conscientiousness/谨慎型)：严谨细致、追求品质、注重规则""",

        "EPQ": """EPQ 人格特质测评：
- E (外向性)：高分表示外向活泼，低分表示内向沉稳
- N (神经质/情绪稳定性)：低分表示情绪稳定，高分表示情绪敏感
- P (精神质/独立性)：反映独立性和坚韧程度
- L (掩饰性/自律性)：反映社会期望符合程度""",

        "MBTI": """MBTI 性格类型测评：
- E/I：外向/内向 - 能量来源
- S/N：感觉/直觉 - 信息获取方式
- T/F：思考/情感 - 决策方式
- J/P：判断/知觉 - 生活方式偏好"""
    }
    return descriptions.get(test_type, "人格特质测评")


def _score_to_level(score: int) -> str:
    """将分数转换为描述性级别."""
    if score >= 85:
        return "非常突出"
    elif score >= 75:
        return "较为明显"
    elif score >= 65:
        return "中等水平"
    elif score >= 55:
        return "相对一般"
    else:
        return "有待提升"


def _convert_scores_to_descriptive(test_type: str, scores: Dict[str, Any]) -> str:
    """
    将测评分数转换为描述性文本.

    ⚠️ 关键改进：生成更具差异化的描述，帮助AI区分不同候选人
    - 包含具体的量化级别(T分)而非仅用模糊描述
    - 添加行为预测描述，帮助AI进行个性化分析
    """
    if not scores:
        return "暂无测评数据"

    result_parts = []

    if test_type == "DISC":
        disc_labels = {
            "D": ("支配性", {
                "high": "决策果断、目标导向，喜欢掌控局面，可能显得强势",
                "mid": "适度主动，能在需要时展现领导力",
                "low": "更愿意配合他人，回避冲突，不喜欢强势主导"
            }),
            "I": ("影响性", {
                "high": "热情外向，善于社交和激励他人，喜欢成为焦点",
                "mid": "能够适应社交场合，表达能力适中",
                "low": "内向谨慎，偏好深度交流而非广泛社交"
            }),
            "S": ("稳健性", {
                "high": "耐心稳重，追求稳定，擅长团队协作和支持他人",
                "mid": "能适应变化，同时保持一定的稳定性",
                "low": "喜欢快节奏和变化，可能对重复性工作缺乏耐心"
            }),
            "C": ("谨慎性", {
                "high": "严谨细致，注重质量和规则，追求完美",
                "mid": "在细节和效率之间保持平衡",
                "low": "更看重速度和灵活性，不拘泥于细节"
            })
        }
        for key in ["D", "I", "S", "C"]:
            if key in scores:
                score = extract_score(scores[key])
                label, descs = disc_labels.get(key, (key, {"high": "", "mid": "", "low": ""}))
                level = _score_to_level(score)
                level_key = "high" if score >= 70 else ("mid" if score >= 45 else "low")
                desc = descs.get(level_key, "")
                result_parts.append(f"- {label}(T分{score})：{level}。{desc}")

    elif test_type == "EPQ":
        epq_labels = {
            "E": ("外向性", {
                "high": "非常活跃外向，喜欢社交活动，精力充沛",
                "mid": "介于内外向之间，能根据情境调整",
                "low": "安静内敛，偏好独处或小范围深度交流"
            }),
            "N": ("情绪稳定性", {
                "high": "情绪波动较大，对压力敏感，易焦虑紧张（⚠️风险点）",
                "mid": "情绪反应适中，整体较为稳定",
                "low": "情绪非常稳定，抗压能力强，冷静理性"
            }),
            "P": ("独立思考", {
                "high": "独立性强，不随波逐流，可能显得固执或难以妥协",
                "mid": "在独立与合作之间保持平衡",
                "low": "善于合作，重视和谐，易于与他人相处"
            }),
            "L": ("社会期望", {
                "high": "倾向于展现社会期望的形象，可能掩饰真实想法",
                "mid": "自我呈现适度真实",
                "low": "非常坦诚直接，较少在意社会评价"
            })
        }
        for key in ["E", "N", "P", "L"]:
            if key in scores:
                score = extract_score(scores[key])
                label, descs = epq_labels.get(key, (key, {"high": "", "mid": "", "low": ""}))
                level = _score_to_level(score)
                level_key = "high" if score >= 65 else ("mid" if score >= 45 else "low")
                desc = descs.get(level_key, "")
                result_parts.append(f"- {label}(T分{score})：{level}。{desc}")

    elif test_type == "MBTI":
        mbti_type = scores.get("type", "")
        if mbti_type:
            result_parts.append(f"- MBTI类型：{mbti_type}")
            # 添加类型解读
            mbti_desc = _get_mbti_type_description(mbti_type)
            if mbti_desc:
                result_parts.append(f"  → {mbti_desc}")
        for key, value in scores.items():
            if key != "type" and isinstance(value, (int, float)):
                score = int(value)
                level = _score_to_level(score)
                result_parts.append(f"- {key}维度偏好：{level}(偏好程度{score}%)")

    else:
        # 通用处理：胜任力维度
        for key, value in scores.items():
            score = extract_score(value)
            level = _score_to_level(score)
            result_parts.append(f"- {key}(T分{score})：{level}")

    return "\n".join(result_parts) if result_parts else "暂无测评数据"


def _get_mbti_type_description(mbti_type: str) -> str:
    """获取MBTI类型的简短描述."""
    descriptions = {
        "INTJ": "战略家型：独立、深思熟虑、追求效率和长期规划",
        "INTP": "逻辑学家型：分析能力强、追求理论和创新",
        "ENTJ": "指挥官型：果断、有领导力、善于组织和执行",
        "ENTP": "辩论家型：思维敏捷、喜欢挑战、善于创新",
        "INFJ": "提倡者型：富有洞察力、理想主义、关注他人",
        "INFP": "调停者型：理想主义、富有同理心、追求意义",
        "ENFJ": "主人公型：有魅力、善于激励他人、注重和谐",
        "ENFP": "竞选者型：热情、创造力强、善于发现可能性",
        "ISTJ": "物流师型：可靠、务实、重视责任和传统",
        "ISFJ": "守卫者型：体贴、可靠、善于照顾他人",
        "ESTJ": "总经理型：务实、有组织、注重效率和规则",
        "ESFJ": "执政官型：友善、热心、重视和谐与合作",
        "ISTP": "鉴赏家型：灵活、务实、善于解决问题",
        "ISFP": "探险家型：温和、敏感、追求美和自由",
        "ESTP": "企业家型：精力充沛、务实、喜欢冒险",
        "ESFP": "表演者型：热情、自发、喜欢成为焦点",
    }
    return descriptions.get(mbti_type.upper(), "")


def extract_score(score_data: Any) -> int:
    """从各种格式中提取分数值.

    优先级：t_score > score > value > Score > Value
    EPQ测评结果中使用t_score作为标准化分数(0-100)
    """
    if isinstance(score_data, (int, float)):
        return int(score_data)
    if isinstance(score_data, dict):
        # 优先使用t_score（EPQ等测评的标准化分数）
        for key in ["t_score", "score", "value", "Score", "Value"]:
            if key in score_data and score_data[key] is not None:
                return int(score_data[key])
    return 50


def _format_scores(test_type: str, scores: Dict[str, Any]) -> str:
    """格式化测评分数为文本描述."""
    if not scores:
        return "无测评数据"

    result_parts = []

    if test_type == "DISC":
        dims = {"D": "支配型", "I": "影响型", "S": "稳健型", "C": "谨慎型"}
        for key, label in dims.items():
            score = extract_score(scores.get(key, scores.get(key.lower(), 50)))
            result_parts.append(f"{key}({label}): {score}分")

    elif test_type == "EPQ":
        dims = {"E": "外向性", "N": "情绪稳定性", "P": "独立性", "L": "自律性"}
        for key, label in dims.items():
            score = extract_score(scores.get(key, scores.get(key.lower(), 50)))
            result_parts.append(f"{key}({label}): {score}分")

    elif test_type == "MBTI":
        # MBTI 显示各维度倾向
        for pair in [("E", "I"), ("S", "N"), ("T", "F"), ("J", "P")]:
            score1 = extract_score(scores.get(pair[0], 50))
            score2 = extract_score(scores.get(pair[1], 50))
            dominant = pair[0] if score1 >= score2 else pair[1]
            result_parts.append(f"{pair[0]}/{pair[1]}: 倾向{dominant} ({max(score1, score2)}分)")

    else:
        for key, value in scores.items():
            score = extract_score(value)
            result_parts.append(f"{key}: {score}分")

    return "\n".join(result_parts)
