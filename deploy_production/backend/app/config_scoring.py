# 量表评分配置（业务化规则，可按需调整）
# - EPQ：单维满分 24，使用 0-24 区间映射，再按区间做等级。
# - MBTI / DISC：以 0-100 为基准，留出题型权重调节空间。

EPQ_SCORING = {
    # 单维满分 24，直接按 EPQ 规范计算
    "dim_max": {"E": 24, "N": 24, "P": 24, "L": 24},
    "dim_scale": {"E": [0, 24], "N": [0, 24], "P": [0, 24], "L": [0, 24]},
    # EPQ 多为是非题，保留可调权重
    "question_type_weights": {"yesno": 1.0, "choice": 0.8},
    # 等级按 0-24 区间划分
    "grade_cutoffs": {"A": 18, "B": 12, "C": 8},
    "grade_labels": {"A": "显著优势", "B": "平衡区间", "C": "需关注"},
}

MBTI_SCORING = {
    # MBTI 四维按百分制，保留上限 100
    "dim_max": {"EI": 100, "SN": 100, "TF": 100, "JP": 100},
    "dim_scale": {"EI": [0, 100], "SN": [0, 100], "TF": [0, 100], "JP": [0, 100]},
    # MBTI 常用单选题型，支持不同题型权重
    "question_type_weights": {"choice": 1.0, "yesno": 0.6},
    "grade_cutoffs": {"A": 80, "B": 65, "C": 50},
    "grade_labels": {"A": "高匹配", "B": "中性/待验证", "C": "需观察"},
}

DISC_SCORING = {
    "dim_max": {"D": 100, "I": 100, "S": 100, "C": 100},
    "dim_scale": {"D": [0, 100], "I": [0, 100], "S": [0, 100], "C": [0, 100]},
    # DISC 题型以选择/排序为主，这里为选择题留主导权重
    "question_type_weights": {"choice": 1.0, "yesno": 0.5},
    "grade_cutoffs": {"A": 78, "B": 62, "C": 48},
    "grade_labels": {"A": "优势画像", "B": "稳定区间", "C": "改进方向"},
}

QUESTIONNAIRE_SCORING_CONFIG = {
    "epq": EPQ_SCORING,
    "mbti": MBTI_SCORING,
    "disc": DISC_SCORING,
}
