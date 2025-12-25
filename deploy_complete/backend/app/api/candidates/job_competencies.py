"""候选人画像 - 岗位胜任力模型.

负责根据岗位类型生成对应的胜任力维度。
"""

from typing import List, Optional


def detect_job_family(target_position: Optional[str]) -> str:
    """根据目标岗位名称检测岗位族.
    
    岗位族映射关系：
    - dev: 研发技术类（前端/后端/测试/架构）
    - design: 设计创意类（UI/视觉/品牌/交互）
    - pm: 产品策划类（产品经理/解决方案）
    - ops: 运营增长类（活动运营/用户运营）
    - delivery: 项目交付类（实施工程师/项目经理）
    - support: 客户支持与服务类
    - hr_admin: 人事/行政/财务等职能类
    - edu: 教学/教务/班主任等教育类
    - sales: 销售/商务/渠道等销售类
    
    Args:
        target_position: 目标岗位名称
        
    Returns:
        岗位族标识
    """
    if not target_position:
        return "general"
    
    position_lower = target_position.lower()
    
    # 研发技术族
    if any(kw in position_lower for kw in ["工程师", "开发", "技术", "架构", "算法", "测试", "运维", "前端", "后端", "全栈", "程序员"]):
        return "dev"
    
    # 设计创意族
    if any(kw in position_lower for kw in ["设计", "ui", "ux", "视觉", "交互", "品牌", "创意", "美术"]):
        return "design"
    
    # 产品策划族
    if any(kw in position_lower for kw in ["产品", "需求", "策划", "解决方案", "pm", "规划"]):
        return "pm"
    
    # 运营增长族
    if any(kw in position_lower for kw in ["运营", "活动", "用户", "社群", "增长", "内容", "市场"]):
        return "ops"
    
    # 项目交付族
    if any(kw in position_lower for kw in ["实施", "项目", "交付", "客户", "部署", "集成", "顾问"]):
        return "delivery"
    
    # 客户支持族
    if any(kw in position_lower for kw in ["客服", "支持", "售后", "服务", "帮助"]):
        return "support"
    
    # 职能管理族
    if any(kw in position_lower for kw in ["人事", "行政", "财务", "法务", "hr", "招聘", "薪酬", "培训"]):
        return "hr_admin"
    
    # 教学教务族
    if any(kw in position_lower for kw in ["教学", "教务", "班主任", "教师", "老师", "培训", "讲师", "助教"]):
        return "edu"
    
    # 销售商务族
    if any(kw in position_lower for kw in ["销售", "商务", "渠道", "客户", "bd", "拓展", "大客户"]):
        return "sales"
    
    return "general"


def get_job_competencies(target_position: Optional[str]) -> List[str]:
    """根据目标岗位动态生成岗位胜任力模型.
    
    基于岗位类型返回最相关的胜任力维度，让AI分析更有针对性。
    
    Args:
        target_position: 目标岗位名称
        
    Returns:
        胜任力维度列表
    """
    if not target_position:
        # 通用胜任力模型
        return [
            "沟通协作能力", "结构化思维", "执行推进能力",
            "学习适应能力", "问题解决能力", "抗压能力"
        ]
    
    position_lower = target_position.lower()
    
    # 技术类岗位
    if any(kw in position_lower for kw in ["工程师", "开发", "技术", "架构", "算法", "测试", "运维"]):
        return [
            "技术能力", "问题解决能力", "学习适应能力",
            "沟通协作能力", "代码质量意识", "系统思维"
        ]
    
    # 产品类岗位
    if any(kw in position_lower for kw in ["产品", "需求", "用户体验", "ux", "ui"]):
        return [
            "用户洞察力", "需求分析能力", "沟通协作能力",
            "项目推进能力", "数据分析能力", "创新思维"
        ]
    
    # 设计类岗位
    if any(kw in position_lower for kw in ["设计", "视觉", "美工", "创意"]):
        return [
            "审美能力", "创意表达", "沟通协作能力",
            "细节把控", "学习适应能力", "抗压能力"
        ]
    
    # 运营类岗位
    if any(kw in position_lower for kw in ["运营", "内容", "活动", "社群", "新媒体"]):
        return [
            "用户思维", "内容创作能力", "数据分析能力",
            "沟通协作能力", "执行推进能力", "创新思维"
        ]
    
    # 销售/商务类岗位
    if any(kw in position_lower for kw in ["销售", "商务", "bd", "客户", "大客户"]):
        return [
            "客户关系能力", "沟通谈判能力", "抗压能力",
            "目标导向", "资源整合能力", "市场敏感度"
        ]
    
    # 市场类岗位
    if any(kw in position_lower for kw in ["市场", "品牌", "推广", "营销"]):
        return [
            "市场洞察力", "策划能力", "沟通协作能力",
            "创新思维", "数据分析能力", "执行推进能力"
        ]
    
    # 人力资源类岗位
    if any(kw in position_lower for kw in ["人事", "hr", "招聘", "培训", "薪酬", "绩效"]):
        return [
            "人际敏感度", "沟通协作能力", "组织协调能力",
            "政策理解力", "保密意识", "服务意识"
        ]
    
    # 财务类岗位
    if any(kw in position_lower for kw in ["财务", "会计", "审计", "税务", "出纳"]):
        return [
            "数据分析能力", "细节把控", "合规意识",
            "风险意识", "沟通协作能力", "学习适应能力"
        ]
    
    # 管理类岗位
    if any(kw in position_lower for kw in ["经理", "总监", "主管", "负责人", "leader"]):
        return [
            "团队管理能力", "战略思维", "决策能力",
            "沟通协作能力", "资源整合能力", "抗压能力"
        ]
    
    # 项目管理类岗位
    if any(kw in position_lower for kw in ["项目", "pmo", "实施"]):
        return [
            "项目管理能力", "沟通协作能力", "风险管理能力",
            "资源协调能力", "执行推进能力", "问题解决能力"
        ]
    
    # 教学教务类岗位
    if any(kw in position_lower for kw in ["教学", "教务", "班主任", "教师", "老师", "培训", "讲师"]):
        return [
            "课堂掌控力", "学生沟通能力", "耐心与细致度",
            "家校沟通能力", "情绪稳定性", "学习适应能力"
        ]
    
    # 默认通用胜任力模型
    return [
        "沟通协作能力", "结构化思维", "执行推进能力",
        "学习适应能力", "问题解决能力", "抗压能力"
    ]


def get_default_competencies_by_position(position: str) -> List[dict]:
    """根据岗位获取默认胜任力评分.
    
    当AI分析不可用时，提供基于岗位的默认胜任力评分。
    
    Args:
        position: 岗位名称
        
    Returns:
        胜任力评分列表
    """
    position_competencies = {
        "产品经理": [
            {"key": "product_planning", "label": "产品规划能力", "score": 85, "rationale": "基于测评表现评估"},
            {"key": "user_insight", "label": "用户洞察力", "score": 82, "rationale": "基于沟通能力评估"},
            {"key": "cross_dept", "label": "跨部门协作", "score": 80, "rationale": "基于团队协作评估"},
            {"key": "data_analysis", "label": "数据分析能力", "score": 78, "rationale": "基于逻辑思维评估"},
            {"key": "requirement", "label": "需求分析能力", "score": 83, "rationale": "基于综合能力评估"},
            {"key": "decision", "label": "决策判断力", "score": 76, "rationale": "基于独立思考评估"}
        ],
        "实施工程师": [
            {"key": "tech_understanding", "label": "技术理解能力", "score": 85, "rationale": "基于测评表现评估"},
            {"key": "problem_solving", "label": "问题解决能力", "score": 82, "rationale": "基于逻辑思维评估"},
            {"key": "client_comm", "label": "客户沟通能力", "score": 75, "rationale": "基于沟通能力评估"},
            {"key": "solution_delivery", "label": "方案交付能力", "score": 80, "rationale": "基于执行力评估"},
            {"key": "document", "label": "文档编写能力", "score": 78, "rationale": "基于条理性评估"},
            {"key": "project_mgmt", "label": "项目管理能力", "score": 72, "rationale": "基于组织能力评估"}
        ],
        "软件工程师": [
            {"key": "programming", "label": "编程能力", "score": 88, "rationale": "基于测评表现评估"},
            {"key": "system_design", "label": "系统设计能力", "score": 85, "rationale": "基于逻辑思维评估"},
            {"key": "problem_solving", "label": "问题解决能力", "score": 82, "rationale": "基于分析能力评估"},
            {"key": "team_collab", "label": "团队协作能力", "score": 70, "rationale": "基于沟通能力评估"},
            {"key": "learning", "label": "学习能力", "score": 90, "rationale": "基于开放性评估"},
            {"key": "code_quality", "label": "代码质量意识", "score": 80, "rationale": "基于严谨性评估"}
        ]
    }
    
    # 匹配岗位或使用默认
    for pos_key, comps in position_competencies.items():
        if pos_key in position:
            return comps
    
    # 默认通用胜任力
    return [
        {"key": "communication", "label": "沟通表达能力", "score": 80, "rationale": "基于综合评估"},
        {"key": "execution", "label": "执行落地能力", "score": 78, "rationale": "基于综合评估"},
        {"key": "learning", "label": "学习适应能力", "score": 82, "rationale": "基于综合评估"},
        {"key": "teamwork", "label": "团队协作能力", "score": 75, "rationale": "基于综合评估"},
        {"key": "problem_solving", "label": "问题解决能力", "score": 80, "rationale": "基于综合评估"},
        {"key": "stress_tolerance", "label": "抗压能力", "score": 72, "rationale": "基于综合评估"}
    ]

