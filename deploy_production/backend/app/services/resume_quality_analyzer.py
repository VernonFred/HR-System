"""
简历质量分析器

评估简历的完整度、逻辑性、岗位相关性
用于综合评分中的"简历质量"维度
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ResumeQualityAnalyzer:
    """简历质量分析器"""
    
    # 评分维度权重
    DIMENSION_WEIGHTS = {
        "completeness": 0.4,  # 完整度
        "logic": 0.3,         # 逻辑性
        "relevance": 0.3      # 岗位相关性
    }
    
    @classmethod
    def analyze_resume_quality(
        cls,
        resume_parsed_data: Optional[Dict[str, Any]],
        target_position: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析简历质量
        
        Args:
            resume_parsed_data: 简历解析数据 (来自AI解析)
            target_position: 目标岗位
            
        Returns:
            {
                "quality_score": 75.5,  # 质量得分 0-100
                "completeness": 80,     # 完整度得分
                "logic": 70,            # 逻辑性得分
                "relevance": 75,        # 相关性得分
                "strengths": [...],     # 简历优势
                "improvements": [...]   # 改进建议
            }
        """
        if not resume_parsed_data:
            return cls._empty_result()
        
        # 1. 完整度评分
        completeness_score = cls._score_completeness(resume_parsed_data)
        
        # 2. 逻辑性评分
        logic_score = cls._score_logic(resume_parsed_data)
        
        # 3. 岗位相关性评分
        relevance_score = cls._score_relevance(resume_parsed_data, target_position)
        
        # 4. 加权计算综合质量分
        quality_score = (
            completeness_score * cls.DIMENSION_WEIGHTS["completeness"] +
            logic_score * cls.DIMENSION_WEIGHTS["logic"] +
            relevance_score * cls.DIMENSION_WEIGHTS["relevance"]
        )
        
        # 5. 生成优势和改进建议
        strengths = cls._generate_strengths(
            completeness_score, logic_score, relevance_score, resume_parsed_data
        )
        improvements = cls._generate_improvements(
            completeness_score, logic_score, relevance_score
        )
        
        logger.info(f"📄 简历质量评分: {quality_score:.1f} (完整度{completeness_score:.0f}, 逻辑性{logic_score:.0f}, 相关性{relevance_score:.0f})")
        
        return {
            "quality_score": round(quality_score, 1),
            "completeness": round(completeness_score, 1),
            "logic": round(logic_score, 1),
            "relevance": round(relevance_score, 1),
            "strengths": strengths,
            "improvements": improvements
        }
    
    @classmethod
    def _score_completeness(cls, data: Dict[str, Any]) -> float:
        """
        完整度评分 (0-100)
        
        检查项:
        - 基本信息 (姓名、联系方式)
        - 教育经历
        - 工作经历
        - 技能列表
        - 项目经验
        """
        score = 0.0
        
        # 基本信息 (20分)
        basic_info = data.get("basic_info", {})
        if basic_info.get("name"):
            score += 5
        if basic_info.get("phone") or basic_info.get("email"):
            score += 10
        if basic_info.get("education"):
            score += 5
        
        # 教育经历 (20分)
        education = data.get("education", [])
        if isinstance(education, list) and len(education) >= 1:
            score += 10
            # 有详细信息（学校、专业、时间）
            if education[0].get("school") and education[0].get("major"):
                score += 10
        elif isinstance(education, dict):
            # 兼容单个对象格式
            if education.get("school"):
                score += 15
        
        # 工作经历 (30分)
        experiences = data.get("work_experience", [])
        if isinstance(experiences, list) and len(experiences) >= 1:
            score += 15
            # 有详细描述
            first_exp = experiences[0]
            desc = first_exp.get("description", "") if isinstance(first_exp, dict) else ""
            if desc and len(desc) > 50:
                score += 10
            # 有多段经历
            if len(experiences) >= 2:
                score += 5
        
        # 技能列表 (15分)
        skills = data.get("skills", [])
        if isinstance(skills, list):
            if len(skills) >= 3:
                score += 10
            if len(skills) >= 5:
                score += 5
        
        # 项目经验 (15分)
        projects = data.get("projects", [])
        if isinstance(projects, list):
            if len(projects) >= 1:
                score += 10
            if len(projects) >= 2:
                score += 5
        
        return min(score, 100)
    
    @classmethod
    def _score_logic(cls, data: Dict[str, Any]) -> float:
        """
        逻辑性评分 (0-100)
        
        检查项:
        - 时间连续性
        - 职业发展路径
        - 描述清晰度
        """
        score = 70.0  # 基础分
        
        experiences = data.get("work_experience", [])
        
        if not experiences or not isinstance(experiences, list):
            return 60.0
        
        # 职业发展路径 (±10分)
        # 如果岗位title有"高级"、"资深"、"主管"等晋升词汇
        has_progression = False
        for exp in experiences:
            if not isinstance(exp, dict):
                continue
            position = str(exp.get("position", "")).lower()
            if any(keyword in position for keyword in ["高级", "资深", "主管", "总监", "经理", "senior", "lead", "manager"]):
                has_progression = True
                break
        
        if has_progression:
            score += 10
        
        # 描述清晰度 (±10分)
        total_desc_length = 0
        valid_exps = 0
        for exp in experiences:
            if isinstance(exp, dict):
                desc = str(exp.get("description", ""))
                total_desc_length += len(desc)
                valid_exps += 1
        
        avg_desc_length = total_desc_length / valid_exps if valid_exps > 0 else 0
        
        if avg_desc_length > 100:
            score += 10
        elif avg_desc_length < 30:
            score -= 5
        
        return min(max(score, 0), 100)
    
    @classmethod
    def _score_relevance(
        cls,
        data: Dict[str, Any],
        target_position: Optional[str]
    ) -> float:
        """
        岗位相关性评分 (0-100)
        
        检查项:
        - 相关工作经验
        - 相关技能
        - 行业匹配度
        """
        if not target_position:
            return 75.0  # 无目标岗位时给中等分
        
        score = 50.0  # 基础分
        
        target_lower = target_position.lower()
        target_keywords = target_lower.split()
        
        # 工作经历相关性 (±20分)
        experiences = data.get("work_experience", [])
        if isinstance(experiences, list):
            for exp in experiences:
                if not isinstance(exp, dict):
                    continue
                
                position = str(exp.get("position", "")).lower()
                description = str(exp.get("description", "")).lower()
                
                # 岗位title匹配
                if any(keyword in position for keyword in target_keywords):
                    score += 10
                    break
                
                # 工作描述匹配
                if any(keyword in description for keyword in target_keywords):
                    score += 5
        
        # 技能相关性 (±15分)
        skills = data.get("skills", [])
        if isinstance(skills, list):
            skill_str = " ".join([str(s).lower() for s in skills if s])
            
            # 根据目标岗位检查关键技能
            if "产品" in target_lower or "pm" in target_lower:
                relevant_skills = ["产品", "原型", "axure", "需求", "prd", "用户研究"]
            elif "技术" in target_lower or "开发" in target_lower or "工程师" in target_lower:
                relevant_skills = ["python", "java", "前端", "后端", "算法", "数据库", "开发"]
            elif "运营" in target_lower:
                relevant_skills = ["运营", "推广", "用户增长", "数据分析", "活动策划"]
            elif "设计" in target_lower:
                relevant_skills = ["设计", "ui", "ux", "sketch", "figma", "photoshop"]
            else:
                relevant_skills = []
            
            matched_skills = sum(1 for skill in relevant_skills if skill in skill_str)
            score += min(matched_skills * 5, 15)
        
        # 行业经验 (±10分)
        industries = []
        if isinstance(experiences, list):
            for exp in experiences:
                if isinstance(exp, dict):
                    company = str(exp.get("company", "")).lower()
                    description = str(exp.get("description", "")).lower()
                    industries.append(company + " " + description)
        
        industry_str = " ".join(industries)
        if any(keyword in industry_str for keyword in ["互联网", "科技", "软件", "技术", "it"]):
            score += 5
        
        return min(max(score, 0), 100)
    
    @classmethod
    def _generate_strengths(
        cls,
        completeness: float,
        logic: float,
        relevance: float,
        data: Dict[str, Any]
    ) -> List[str]:
        """生成简历优势"""
        strengths = []
        
        if completeness >= 80:
            strengths.append("简历信息完整，包含详细的教育和工作经历")
        
        if logic >= 80:
            strengths.append("职业发展路径清晰，逻辑连贯")
        
        if relevance >= 80:
            strengths.append("工作经验与目标岗位高度相关")
        
        # 补充具体亮点
        experiences = data.get("work_experience", [])
        if isinstance(experiences, list) and len(experiences) >= 3:
            strengths.append(f"拥有{len(experiences)}段工作经历，经验丰富")
        
        skills = data.get("skills", [])
        if isinstance(skills, list) and len(skills) >= 5:
            strengths.append(f"掌握{len(skills)}项专业技能")
        
        if not strengths:
            strengths.append("简历整体质量良好")
        
        return strengths[:3]  # 最多3条
    
    @classmethod
    def _generate_improvements(
        cls,
        completeness: float,
        logic: float,
        relevance: float
    ) -> List[str]:
        """生成改进建议"""
        improvements = []
        
        if completeness < 70:
            improvements.append("建议补充教育背景或项目经验，提升简历完整度")
        
        if logic < 70:
            improvements.append("建议优化工作经历描述，突出职业发展轨迹")
        
        if relevance < 70:
            improvements.append("建议增加与目标岗位相关的技能和经验描述")
        
        if not improvements:
            improvements.append("简历质量良好，可进一步丰富项目成果描述")
        
        return improvements[:2]  # 最多2条
    
    @classmethod
    def _empty_result(cls) -> Dict[str, Any]:
        """无简历时的返回值"""
        return {
            "quality_score": 0,
            "completeness": 0,
            "logic": 0,
            "relevance": 0,
            "strengths": [],
            "improvements": ["建议上传简历以获得更准确的评估"]
        }

