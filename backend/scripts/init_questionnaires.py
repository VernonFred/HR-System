"""初始化测评系统默认数据."""
import asyncio
from datetime import datetime
from sqlmodel import Session, select

from app.db import get_engine
from app.models_assessment import Questionnaire


# EPQ人格测评问卷数据
EPQ_QUESTIONS = {
    "questions": [
        {
            "id": 1,
            "text": "你在社交场合中通常感到精力充沛",
            "options": [
                {"label": "A", "text": "非常同意", "score": 4},
                {"label": "B", "text": "同意", "score": 3},
                {"label": "C", "text": "不同意", "score": 2},
                {"label": "D", "text": "非常不同意", "score": 1},
            ],
            "dimension": "E",
        },
        {
            "id": 2,
            "text": "你更喜欢一个人独处而不是参加派对",
            "options": [
                {"label": "A", "text": "非常同意", "score": 4},
                {"label": "B", "text": "同意", "score": 3},
                {"label": "C", "text": "不同意", "score": 2},
                {"label": "D", "text": "非常不同意", "score": 1},
            ],
            "dimension": "E",
        },
        # ... 实际应该有88道题
    ]
}

EPQ_SCORING_RULES = {
    "dimensions": {
        "E": {"name": "外向性", "max_score": 24},
        "N": {"name": "神经质", "max_score": 24},
        "P": {"name": "精神质", "max_score": 24},
        "L": {"name": "掩饰性", "max_score": 24},
    },
    "grading": {
        "A": {"min": 80, "label": "优秀"},
        "B": {"min": 60, "label": "良好"},
        "C": {"min": 40, "label": "一般"},
        "D": {"min": 0, "label": "需改进"},
    },
}

# DISC性格分析问卷数据
DISC_QUESTIONS = {
    "questions": [
        {
            "id": 1,
            "text": "我喜欢主导和控制局面",
            "options": [
                {"label": "A", "text": "非常同意", "score": 4},
                {"label": "B", "text": "同意", "score": 3},
                {"label": "C", "text": "不同意", "score": 2},
                {"label": "D", "text": "非常不同意", "score": 1},
            ],
            "dimension": "D",
        },
        {
            "id": 2,
            "text": "我善于影响和说服他人",
            "options": [
                {"label": "A", "text": "非常同意", "score": 4},
                {"label": "B", "text": "同意", "score": 3},
                {"label": "C", "text": "不同意", "score": 2},
                {"label": "D", "text": "非常不同意", "score": 1},
            ],
            "dimension": "I",
        },
    ]
}

DISC_SCORING_RULES = {
    "dimensions": {
        "D": {"name": "支配型", "max_score": 28},
        "I": {"name": "影响型", "max_score": 28},
        "S": {"name": "稳健型", "max_score": 28},
        "C": {"name": "谨慎型", "max_score": 28},
    }
}

# MBTI性格测试问卷数据
MBTI_QUESTIONS = {
    "questions": [
        {
            "id": 1,
            "text": "在聚会中，你更倾向于",
            "options": [
                {"label": "A", "text": "主动与很多人交谈", "score": 1, "dimension": "E"},
                {"label": "B", "text": "与少数人深入交流", "score": 1, "dimension": "I"},
            ],
            "dimension": "EI",
        },
        {
            "id": 2,
            "text": "你更相信",
            "options": [
                {"label": "A", "text": "实际经验", "score": 1, "dimension": "S"},
                {"label": "B", "text": "直觉感受", "score": 1, "dimension": "N"},
            ],
            "dimension": "SN",
        },
    ]
}

MBTI_SCORING_RULES = {
    "dimensions": {
        "EI": {"name": "外向/内向", "options": ["E", "I"]},
        "SN": {"name": "实感/直觉", "options": ["S", "N"]},
        "TF": {"name": "思考/情感", "options": ["T", "F"]},
        "JP": {"name": "判断/知觉", "options": ["J", "P"]},
    }
}


DEFAULT_QUESTIONNAIRES = [
    {
        "name": "EPQ人格测评",
        "type": "EPQ",
        "questions_count": 88,
        "estimated_minutes": 15,
        "questions_data": EPQ_QUESTIONS,
        "scoring_rules": EPQ_SCORING_RULES,
        "description": "艾森克人格问卷，评估外向性、神经质、精神质和掩饰性四个维度",
        "status": "active",
    },
    {
        "name": "DISC性格分析",
        "type": "DISC",
        "questions_count": 28,
        "estimated_minutes": 10,
        "questions_data": DISC_QUESTIONS,
        "scoring_rules": DISC_SCORING_RULES,
        "description": "DISC行为风格测评，评估支配型、影响型、稳健型、谨慎型四种风格",
        "status": "active",
    },
    {
        "name": "MBTI性格测试",
        "type": "MBTI",
        "questions_count": 93,
        "estimated_minutes": 20,
        "questions_data": MBTI_QUESTIONS,
        "scoring_rules": MBTI_SCORING_RULES,
        "description": "迈尔斯-布里格斯类型指标，识别16种人格类型",
        "status": "active",
    },
]


def init_questionnaires():
    """初始化问卷数据."""
    engine = get_engine()
    
    with Session(engine) as session:
        # 检查是否已有问卷
        statement = select(Questionnaire)
        existing = session.exec(statement).first()
        
        if existing:
            print("✅ 问卷数据已存在，跳过初始化")
            return
        
        print("📝 开始初始化问卷数据...")
        
        for q_data in DEFAULT_QUESTIONNAIRES:
            questionnaire = Questionnaire(**q_data)
            session.add(questionnaire)
            print(f"   ✓ 创建问卷: {q_data['name']}")
        
        session.commit()
        print("✅ 问卷数据初始化完成！")


if __name__ == "__main__":
    init_questionnaires()

