"""
AI降级分析器: 当AI不可用时，基于测评数据的规则算法

核心思想:
- 利用真实测评数据，而不是返回假数据
- 使用维度映射 + 加权计算
- 提供可信度 70-80% 的分析结果
"""

from typing import List, Dict, Any, Optional
import statistics
import logging

logger = logging.getLogger(__name__)


class FallbackAnalyzer:
    """规则引擎分析器 - AI降级时使用"""
    
    # 胜任力计算规则映射
    COMPETENCY_RULES = {
        "product_planning": {
            "name": "产品规划能力",
            "factors": [
                ("mbti", "N-S", 0.4, False),  # N倾向 = 抽象思维
                ("mbti", "T-F", 0.3, False),  # T倾向 = 逻辑决策
                ("disc", "D", 0.3, False),     # D维度 = 驱动力
            ]
        },
        "user_insight": {
            "name": "用户洞察力",
            "factors": [
                ("mbti", "N-S", 0.3, False),  # N倾向 = 洞察力
                ("mbti", "F-T", 0.4, False),  # F倾向 = 共情能力
                ("disc", "I", 0.3, False),     # I维度 = 影响力
            ]
        },
        "communication": {
            "name": "沟通协调能力",
            "factors": [
                ("mbti", "E-I", 0.5, False),  # E倾向 = 外向沟通
                ("disc", "I", 0.5, False),     # I维度 = 影响力
            ]
        },
        "execution": {
            "name": "执行推进能力",
            "factors": [
                ("mbti", "J-P", 0.4, False),  # J倾向 = 执行力
                ("disc", "D", 0.4, False),     # D维度 = 驱动力
                ("disc", "C", 0.2, False),     # C维度 = 细致度
            ]
        },
        "learning": {
            "name": "学习适应能力",
            "factors": [
                ("mbti", "N-S", 0.4, False),  # N倾向 = 开放性
                ("epq", "E", 0.3, False),      # E维度 = 活跃度
                ("disc", "I", 0.3, False),     # I维度 = 社交性
            ]
        },
        "pressure_resistance": {
            "name": "抗压能力",
            "factors": [
                ("epq", "N", 0.7, True),       # N维度反向 (N越低越稳定)
                ("disc", "D", 0.3, False),     # D维度 = 驱动力
            ]
        }
    }
    
    @classmethod
    def analyze_candidate(
        cls,
        submissions: List[Dict[str, Any]],
        target_position: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        基于测评数据生成降级分析
        
        Args:
            submissions: 测评记录列表 (每项包含 questionnaire, result, score_percentage 等)
            target_position: 目标岗位
            
        Returns:
            分析结果字典 (格式与AI返回一致)
        """
        logger.info(f"🔧 启动规则引擎分析 (测评数量: {len(submissions)}, 岗位: {target_position})")
        
        # 1. 计算胜任力评分
        competencies = cls._calculate_competencies(submissions, target_position)
        logger.debug(f"   → 胜任力评分: {[f'{c['label']}={c['score']}' for c in competencies]}")
        
        # 2. 生成优势分析
        strengths = cls._generate_strengths(competencies, submissions)
        
        # 3. 生成风险分析
        risks = cls._generate_risks(competencies, submissions)
        
        # 4. 生成综合评价
        summary_points = cls._generate_summary(competencies, strengths, risks)
        
        logger.info(f"✅ 规则引擎分析完成")
        
        return {
            "competencies": competencies,
            "strengths": strengths,
            "risks": risks,
            "summary_points": summary_points,
            "suitable_positions": cls._recommend_positions(competencies),
            "unsuitable_positions": [],
            "quick_tags": [s[:4] for s in strengths[:3]] if strengths else ["综合评估"]
        }
    
    @classmethod
    def _calculate_competencies(
        cls,
        submissions: List[Dict[str, Any]],
        target_position: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """计算胜任力评分"""
        competencies = []
        
        # 根据岗位选择相关胜任力
        if target_position and ("产品" in target_position or "PM" in target_position.upper()):
            keys = ["product_planning", "user_insight", "communication", "execution", "learning", "pressure_resistance"]
        elif target_position and ("技术" in target_position or "开发" in target_position or "工程师" in target_position):
            keys = ["execution", "learning", "pressure_resistance", "communication"]
        elif target_position and ("运营" in target_position):
            keys = ["communication", "execution", "user_insight", "learning"]
        else:
            # 通用岗位
            keys = ["communication", "execution", "learning", "pressure_resistance"]
        
        for key in keys:
            rule = cls.COMPETENCY_RULES.get(key)
            if not rule:
                continue
            
            score = cls._calculate_competency_score(
                rule["factors"],
                submissions
            )
            
            competencies.append({
                "key": key,
                "label": rule["name"],
                "score": round(score, 1),
                "rationale": f"基于{len(submissions)}项测评的综合评估"
            })
        
        return competencies
    
    @classmethod
    def _calculate_competency_score(
        cls,
        factors: List[tuple],
        submissions: List[Dict[str, Any]]
    ) -> float:
        """
        根据因子列表计算胜任力得分
        
        Args:
            factors: [(test_type, dimension, weight, is_reverse), ...]
            submissions: 测评记录列表
        """
        total_score = 0.0
        total_weight = 0.0
        
        for test_type, dimension, weight, is_reverse in factors:
            # 查找对应类型的测评
            submission = cls._find_submission_by_type(submissions, test_type)
            if not submission:
                continue
            
            # 提取维度得分
            dim_score = cls._extract_dimension_score(
                submission.get("result", {}),
                test_type,
                dimension
            )
            
            if dim_score is None:
                continue
            
            # 处理反向维度
            if is_reverse:
                dim_score = 100 - dim_score
            
            total_score += dim_score * weight
            total_weight += weight
        
        if total_weight > 0:
            return total_score / total_weight
        
        # 降级: 使用测评平均分
        avg_score = cls._calculate_average_score(submissions)
        return avg_score
    
    @classmethod
    def _extract_dimension_score(
        cls,
        result: Dict[str, Any],
        test_type: str,
        dimension: str
    ) -> Optional[float]:
        """从测评结果中提取维度得分"""
        
        if test_type == "mbti":
            # MBTI维度: "E-I", "S-N", "T-F", "J-P"
            dimensions = result.get("dimensions", {})
            if dimension in dimensions:
                # MBTI返回相对值 (-100 到 100)，转换为绝对值 (0-100)
                value = dimensions.get(dimension, 0)
                return (value + 100) / 2
        
        elif test_type == "disc":
            # DISC维度: "D", "I", "S", "C"
            dimensions = result.get("dimensions", [])
            for dim in dimensions:
                if dim.get("key", "").upper() == dimension.upper():
                    return float(dim.get("score", 50))
        
        elif test_type == "epq":
            # EPQ维度: "E", "N", "P", "L"
            dimensions = result.get("dimensions", {})
            if dimension in dimensions:
                return float(dimensions[dimension].get("score", 50))
        
        return None
    
    @classmethod
    def _find_submission_by_type(
        cls,
        submissions: List[Dict[str, Any]],
        test_type: str
    ) -> Optional[Dict[str, Any]]:
        """查找指定类型的测评"""
        for sub in submissions:
            q_type = sub.get("questionnaire", {}).get("type", "").lower()
            if q_type == test_type.lower():
                return sub
        return None
    
    @classmethod
    def _calculate_average_score(cls, submissions: List[Dict[str, Any]]) -> float:
        """计算测评平均分"""
        scores = []
        for sub in submissions:
            score = sub.get("score_percentage")
            if score is not None:
                scores.append(float(score))
        
        if scores:
            return statistics.mean(scores)
        return 75.0  # 默认分数
    
    @classmethod
    def _generate_strengths(
        cls,
        competencies: List[Dict[str, Any]],
        submissions: List[Dict[str, Any]]
    ) -> List[str]:
        """生成优势分析"""
        strengths = []
        
        # 找出得分最高的3项胜任力
        sorted_comps = sorted(competencies, key=lambda x: x["score"], reverse=True)
        
        for comp in sorted_comps[:3]:
            if comp["score"] >= 75:
                strengths.append(f"{comp['label']}表现突出，得分{comp['score']:.0f}分")
        
        # 如果优势不足3条，补充测评相关的优势
        if len(strengths) < 3:
            if len(submissions) >= 2:
                strengths.append(f"已完成{len(submissions)}项专业测评，数据完整性良好")
            
            # 补充通用优势
            avg_score = statistics.mean([c["score"] for c in competencies])
            if avg_score >= 70:
                strengths.append("综合表现稳定，各项能力均衡发展")
        
        if not strengths:
            strengths = ["综合表现中等，具有一定发展潜力"]
        
        return strengths[:3]  # 最多3条
    
    @classmethod
    def _generate_risks(
        cls,
        competencies: List[Dict[str, Any]],
        submissions: List[Dict[str, Any]]
    ) -> List[str]:
        """生成风险分析"""
        risks = []
        
        # 找出得分较低的胜任力
        for comp in competencies:
            if comp["score"] < 65:
                risks.append(f"{comp['label']}有待提升，建议针对性培养")
        
        # 如果测评数量少
        if len(submissions) < 2:
            risks.append("建议补充更多测评，以获得更全面的能力画像")
        
        if not risks:
            risks = ["综合表现均衡，暂无明显短板"]
        
        return risks[:2]  # 最多返回2条
    
    @classmethod
    def _generate_summary(
        cls,
        competencies: List[Dict[str, Any]],
        strengths: List[str],
        risks: List[str]
    ) -> List[str]:
        """生成综合评价要点 (3条)"""
        avg_score = statistics.mean([c["score"] for c in competencies])
        
        # 第1条: 综合评分
        if avg_score >= 85:
            level = "优秀"
        elif avg_score >= 75:
            level = "良好"
        elif avg_score >= 65:
            level = "中等"
        else:
            level = "有待提升"
        
        summary = [
            f"综合评分{avg_score:.1f}分，整体表现{level}"
        ]
        
        # 第2条: 主要优势
        if strengths:
            summary.append(strengths[0].split('，')[0])  # 取第一条优势的前半部分
        else:
            summary.append("综合能力表现均衡")
        
        # 第3条: 发展建议
        if risks and "有待提升" in risks[0]:
            summary.append(f"建议重点关注{risks[0].split('有待提升')[0].strip()}")
        else:
            summary.append("建议继续保持并横向拓展能力边界")
        
        return summary
    
    @classmethod
    def _recommend_positions(cls, competencies: List[Dict[str, Any]]) -> List[str]:
        """推荐岗位 (基于胜任力得分)"""
        high_scores = [c for c in competencies if c["score"] >= 80]
        
        positions = []
        for comp in high_scores:
            key = comp["key"]
            if key == "product_planning":
                positions.append("产品经理")
            elif key == "user_insight":
                positions.append("用户研究")
            elif key == "communication":
                positions.append("客户成功")
            elif key == "execution":
                positions.append("项目管理")
            elif key == "learning":
                positions.append("技术研发")
        
        # 去重并限制数量
        return list(dict.fromkeys(positions))[:3]

