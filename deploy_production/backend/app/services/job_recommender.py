"""
岗位推荐引擎

基于候选人的人格特质、能力维度、简历经验推荐最适合的岗位
优化现有的岗位推荐逻辑，提高准确度

🟢 P2-3增强: 支持从数据库动态读取岗位画像 + 内置默认岗位
"""

from typing import List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


class JobRecommender:
    """岗位推荐引擎"""
    
    # 🟢 内置默认岗位特征模型 (当数据库为空时使用)
    DEFAULT_JOB_PROFILES = {
        "产品经理": {
            "competencies": {
                "product_planning": 80,
                "user_insight": 80,
                "communication": 75,
                "execution": 70
            },
            "keywords": ["产品", "pm", "需求", "原型", "用户"],
            "category": "产品"
        },
        "技术开发": {
            "competencies": {
                "execution": 80,
                "learning": 80,
                "pressure_resistance": 70
            },
            "keywords": ["开发", "编程", "代码", "技术", "算法"],
            "category": "技术"
        },
        "运营专员": {
            "competencies": {
                "communication": 80,
                "user_insight": 75,
                "execution": 70
            },
            "keywords": ["运营", "推广", "用户增长", "活动"],
            "category": "运营"
        },
        "数据分析师": {
            "competencies": {
                "execution": 75,
                "learning": 80,
                "pressure_resistance": 70
            },
            "keywords": ["数据", "分析", "sql", "python", "统计"],
            "category": "数据"
        },
        "项目管理": {
            "competencies": {
                "execution": 85,
                "communication": 80,
                "pressure_resistance": 75
            },
            "keywords": ["项目", "管理", "协调", "pmp"],
            "category": "管理"
        },
        "UI/UX设计师": {
            "competencies": {
                "user_insight": 85,
                "learning": 75
            },
            "keywords": ["设计", "ui", "ux", "交互", "视觉"],
            "category": "设计"
        }
    }
    
    @classmethod
    def load_job_profiles_from_db(cls, session) -> Dict[str, Dict[str, Any]]:
        """
        从数据库加载岗位画像配置
        
        Args:
            session: 数据库会话
            
        Returns:
            岗位画像字典 {岗位名称: 岗位特征}
        """
        from app.models import JobProfile
        from sqlmodel import select
        
        try:
            # 查询所有激活状态的岗位画像
            stmt = select(JobProfile).where(JobProfile.status == "active")
            job_profiles = session.exec(stmt).all()
            
            if not job_profiles:
                logger.info("📦 数据库中无岗位画像，使用默认配置")
                return cls.DEFAULT_JOB_PROFILES
            
            # 转换为推荐引擎所需格式
            profiles_dict = {}
            for profile in job_profiles:
                # 解析 dimensions JSON字段
                dimensions = []
                if profile.dimensions:
                    if isinstance(profile.dimensions, str):
                        dimensions = json.loads(profile.dimensions)
                    elif isinstance(profile.dimensions, list):
                        dimensions = profile.dimensions
                
                # 构建胜任力要求字典
                competencies_dict = {}
                for dim in dimensions:
                    if isinstance(dim, dict):
                        # 能力维度映射
                        dim_name = dim.get("name", "")
                        ideal_score = dim.get("ideal_score") or dim.get("idealScore") or 75
                        
                        # 将中文维度名映射到代码
                        competency_key = cls._map_dimension_to_competency(dim_name)
                        if competency_key:
                            competencies_dict[competency_key] = ideal_score
                
                # 提取关键词 (从岗位名称和描述中)
                keywords = [profile.name]
                if profile.description:
                    # 简单提取：中文词汇分割
                    keywords.extend([word.strip() for word in profile.description.split() if len(word.strip()) > 1])
                
                # 提取部门作为类别
                category = profile.department or "通用"
                
                profiles_dict[profile.name] = {
                    "competencies": competencies_dict,
                    "keywords": keywords[:10],  # 限制关键词数量
                    "category": category
                }
            
            logger.info(f"📦 从数据库加载了 {len(profiles_dict)} 个岗位画像")
            return profiles_dict
            
        except Exception as e:
            logger.error(f"❌ 加载岗位画像失败: {e}，使用默认配置")
            return cls.DEFAULT_JOB_PROFILES
    
    @classmethod
    def _map_dimension_to_competency(cls, dimension_name: str) -> Optional[str]:
        """
        将岗位画像配置中的维度名映射到胜任力代码
        
        Args:
            dimension_name: 维度名称 (如 "产品规划能力")
            
        Returns:
            胜任力代码 (如 "product_planning")，如果无法映射则返回None
        """
        # 维度名称到代码的映射表
        mapping = {
            "产品规划": "product_planning",
            "产品规划能力": "product_planning",
            "用户洞察": "user_insight",
            "用户洞察力": "user_insight",
            "沟通协调": "communication",
            "沟通能力": "communication",
            "执行推进": "execution",
            "执行力": "execution",
            "学习能力": "learning",
            "抗压能力": "pressure_resistance",
            "压力承受": "pressure_resistance",
            "逻辑思维": "logic",
            "创新能力": "innovation",
        }
        
        # 精确匹配
        if dimension_name in mapping:
            return mapping[dimension_name]
        
        # 模糊匹配
        for key, value in mapping.items():
            if key in dimension_name:
                return value
        
        return None
    
    @classmethod
    def recommend_positions(
        cls,
        competencies: List[Dict[str, Any]],
        resume_keywords: Optional[List[str]] = None,
        current_position: Optional[str] = None,
        top_n: int = 4,
        session = None  # 🟢 新增: 数据库会话（可选）
    ) -> List[str]:
        """
        推荐岗位 (简化版，直接返回岗位名称列表)
        
        Args:
            competencies: 胜任力评分列表
            resume_keywords: 简历关键词
            current_position: 当前目标岗位
            top_n: 返回前N个推荐
            session: 数据库会话（如果提供，从数据库加载岗位画像）
            
        Returns:
            ["产品经理", "项目管理", ...] 岗位名称列表
        """
        # 🟢 动态加载岗位画像
        if session:
            job_profiles = cls.load_job_profiles_from_db(session)
        else:
            job_profiles = cls.DEFAULT_JOB_PROFILES
            logger.info("🔧 使用默认岗位画像配置")
        
        recommendations = []
        
        for job_name, job_profile in job_profiles.items():
            # 跳过当前岗位
            if current_position and job_name in current_position:
                continue
            
            # 计算匹配度
            match_score = cls._calculate_job_match(
                job_profile,
                competencies,
                resume_keywords
            )
            
            recommendations.append({
                "position": job_name,
                "match_score": match_score
            })
        
        # 按匹配度排序
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 返回前N个岗位名称
        top_positions = [rec["position"] for rec in recommendations[:top_n]]
        
        logger.info(f"🎯 岗位推荐: {top_positions}")
        
        return top_positions
    
    @classmethod
    def recommend_unsuitable_positions(
        cls,
        competencies: List[Dict[str, Any]]
    ) -> List[str]:
        """
        推荐不适合的岗位
        
        基于胜任力短板判断
        """
        unsuitable = []
        
        # 找出得分低的胜任力
        comp_dict = {c["key"]: c["score"] for c in competencies}
        
        # 如果沟通能力低，不适合客户接触类岗位
        if comp_dict.get("communication", 70) < 60:
            unsuitable.append("客户服务")
            unsuitable.append("销售岗位")
        
        # 如果执行能力低，不适合高强度执行岗位
        if comp_dict.get("execution", 70) < 60:
            unsuitable.append("项目执行")
        
        # 如果抗压能力低，不适合高压岗位
        if comp_dict.get("pressure_resistance", 70) < 60:
            unsuitable.append("高压环境岗位")
        
        # 如果学习能力低，不适合技术岗
        if comp_dict.get("learning", 70) < 60:
            unsuitable.append("快速迭代技术岗")
        
        # 默认不推荐岗位
        if not unsuitable:
            unsuitable = ["高度重复性工作", "纯体力劳动岗位"]
        
        return unsuitable[:3]  # 最多3个
    
    @classmethod
    def _calculate_job_match(
        cls,
        job_profile: Dict[str, Any],
        competencies: List[Dict[str, Any]],
        resume_keywords: Optional[List[str]]
    ) -> float:
        """
        计算岗位匹配度
        
        算法: 加权融合
        - 胜任力匹配 70%
        - 简历经验匹配 30%
        """
        # 1. 胜任力匹配度 (70%)
        comp_match = cls._match_competencies(
            job_profile.get("competencies", {}),
            competencies
        )
        
        # 2. 简历经验匹配度 (30%)
        resume_match = cls._match_resume(
            job_profile.get("keywords", []),
            resume_keywords or []
        )
        
        # 加权融合
        total_match = comp_match * 0.7 + resume_match * 0.3
        
        return total_match
    
    @classmethod
    def _match_competencies(
        cls,
        required_comps: Dict[str, float],
        candidate_comps: List[Dict[str, Any]]
    ) -> float:
        """匹配胜任力"""
        if not required_comps or not candidate_comps:
            return 60.0
        
        # 将候选人胜任力转为字典
        comp_dict = {c["key"]: c["score"] for c in candidate_comps}
        
        match_scores = []
        for key, required_score in required_comps.items():
            candidate_score = comp_dict.get(key, 60)
            # 计算匹配度: 越接近要求越好
            diff = abs(candidate_score - required_score)
            match = max(0, 100 - diff)
            match_scores.append(match)
        
        return sum(match_scores) / len(match_scores) if match_scores else 60.0
    
    @classmethod
    def _match_resume(
        cls,
        job_keywords: List[str],
        resume_keywords: List[str]
    ) -> float:
        """匹配简历经验"""
        if not job_keywords or not resume_keywords:
            return 50.0
        
        # 简单关键词匹配
        resume_str = " ".join([k.lower() for k in resume_keywords])
        
        matched_count = sum(
            1 for keyword in job_keywords
            if keyword.lower() in resume_str
        )
        
        match_rate = matched_count / len(job_keywords)
        return 50 + (match_rate * 50)  # 50-100分区间

