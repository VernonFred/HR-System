"""
多测评交叉验证算法
用于分析候选人多个测评结果的一致性，提高画像可信度
"""

from typing import List, Dict, Any, Tuple
import statistics


class CrossValidationService:
    """交叉验证服务"""
    
    # 测评类型权重（用于加权平均）
    ASSESSMENT_WEIGHTS = {
        'MBTI': 40,
        'DISC': 30,
        'EPQ': 30
    }
    
    # 通用维度映射（不同测评的维度对应关系）
    DIMENSION_MAPPING = {
        '外向性': {
            'MBTI': 'E-I',
            'EPQ': 'E',
            'DISC': 'I'
        },
        '情绪稳定性': {
            'MBTI': 'T-F',
            'EPQ': 'N',
            'DISC': 'S'
        },
        '责任心': {
            'MBTI': 'J-P',
            'EPQ': 'P',
            'DISC': 'C'
        },
        '支配性': {
            'MBTI': 'E-I',
            'DISC': 'D'
        }
    }
    
    @classmethod
    def calculate_cross_validation(
        cls,
        submissions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算多测评交叉验证结果
        
        Args:
            submissions: 候选人的多个测评提交记录
            
        Returns:
            交叉验证结果，包括一致性得分、置信度等级、特质检查、矛盾点
        """
        if len(submissions) < 2:
            return {
                'consistency_score': 0,
                'confidence_level': '低',
                'assessment_count': len(submissions),
                'consistency_checks': [],
                'contradictions': []
            }
        
        # 提取各测评的维度数据
        assessment_data = cls._extract_assessment_data(submissions)
        
        # 对通用维度进行交叉检查
        consistency_checks = cls._check_dimension_consistency(assessment_data)
        
        # 识别矛盾点
        contradictions = cls._identify_contradictions(consistency_checks)
        
        # 计算整体一致性得分
        consistency_score = cls._calculate_consistency_score(consistency_checks)
        
        # 确定置信度等级
        confidence_level = cls._determine_confidence_level(
            consistency_score,
            len(submissions),
            len(contradictions)
        )
        
        return {
            'consistency_score': round(consistency_score, 1),
            'confidence_level': confidence_level,
            'assessment_count': len(submissions),
            'consistency_checks': consistency_checks,
            'contradictions': contradictions
        }
    
    @classmethod
    def _extract_assessment_data(
        cls,
        submissions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """提取各测评的维度数据"""
        assessment_data = []
        
        for sub in submissions:
            q_type = sub.get('questionnaire', {}).get('type', '').upper()
            if not q_type:
                continue
            
            # 获取该测评的维度分数
            dimensions = {}
            
            if q_type == 'MBTI':
                dimensions = cls._extract_mbti_dimensions(sub)
            elif q_type == 'EPQ':
                dimensions = cls._extract_epq_dimensions(sub)
            elif q_type == 'DISC':
                dimensions = cls._extract_disc_dimensions(sub)
            
            assessment_data.append({
                'type': q_type,
                'weight': cls.ASSESSMENT_WEIGHTS.get(q_type, 30),
                'dimensions': dimensions
            })
        
        return assessment_data
    
    @classmethod
    def _extract_mbti_dimensions(cls, submission: Dict[str, Any]) -> Dict[str, float]:
        """提取MBTI维度分数（转换为0-100）"""
        result = submission.get('result', {})
        dimensions = result.get('dimensions', {})
        
        # MBTI维度是相对值，转换为绝对值
        return {
            'E-I': cls._mbti_to_score(dimensions.get('E-I', 0)),
            'S-N': cls._mbti_to_score(dimensions.get('S-N', 0)),
            'T-F': cls._mbti_to_score(dimensions.get('T-F', 0)),
            'J-P': cls._mbti_to_score(dimensions.get('J-P', 0))
        }
    
    @classmethod
    def _mbti_to_score(cls, value: float) -> float:
        """将MBTI相对值(-100到100)转换为绝对分数(0-100)"""
        # 假设正值表示第一个字母倾向，负值表示第二个字母倾向
        # 将[-100, 100]映射到[0, 100]
        return (value + 100) / 2
    
    @classmethod
    def _extract_epq_dimensions(cls, submission: Dict[str, Any]) -> Dict[str, float]:
        """提取EPQ维度分数"""
        result = submission.get('result', {})
        dimensions = result.get('dimensions', {})
        
        return {
            'E': float(dimensions.get('E', {}).get('score', 50)),
            'N': float(dimensions.get('N', {}).get('score', 50)),
            'P': float(dimensions.get('P', {}).get('score', 50)),
            'L': float(dimensions.get('L', {}).get('score', 50))
        }
    
    @classmethod
    def _extract_disc_dimensions(cls, submission: Dict[str, Any]) -> Dict[str, float]:
        """提取DISC维度分数"""
        result = submission.get('result', {})
        dimensions = result.get('dimensions', [])
        
        disc_scores = {}
        for dim in dimensions:
            key = dim.get('key', '').upper()
            score = float(dim.get('score', 50))
            if key in ['D', 'I', 'S', 'C']:
                disc_scores[key] = score
        
        return disc_scores
    
    @classmethod
    def _check_dimension_consistency(
        cls,
        assessment_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """检查通用维度的一致性"""
        consistency_checks = []
        
        for trait, mapping in cls.DIMENSION_MAPPING.items():
            scores_list = []
            
            # 收集各测评中对应维度的分数
            for assessment in assessment_data:
                a_type = assessment['type']
                if a_type in mapping:
                    dim_key = mapping[a_type]
                    score = assessment['dimensions'].get(dim_key)
                    if score is not None:
                        scores_list.append({
                            'source': a_type,
                            'value': round(score, 1)
                        })
            
            # 如果至少有2个测评有该维度的数据，进行一致性检查
            if len(scores_list) >= 2:
                values = [s['value'] for s in scores_list]
                mean = statistics.mean(values)
                std_dev = statistics.stdev(values) if len(values) > 1 else 0
                
                # 一致性得分（标准差越小越一致，最高100分）
                # 假设标准差 > 20 为不一致，0-20映射到60-100
                consistency = max(0, min(100, 100 - (std_dev * 2)))
                
                consistency_checks.append({
                    'trait': trait,
                    'scores': scores_list,
                    'mean': round(mean, 1),
                    'stdDev': round(std_dev, 1),
                    'consistency': round(consistency, 1)
                })
        
        return consistency_checks
    
    @classmethod
    def _identify_contradictions(
        cls,
        consistency_checks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """识别矛盾点（一致性低的维度）"""
        contradictions = []
        
        for check in consistency_checks:
            # 一致性低于60分视为矛盾
            if check['consistency'] < 60:
                scores = check['scores']
                score_str = ' vs '.join([f"{s['source']} {s['value']}" for s in scores])
                
                contradictions.append({
                    'trait': check['trait'],
                    'scores': [s['value'] for s in scores],
                    'issue': f"不同测评结果差异较大 ({score_str})，标准差 {check['stdDev']}"
                })
        
        return contradictions
    
    @classmethod
    def _calculate_consistency_score(
        cls,
        consistency_checks: List[Dict[str, Any]]
    ) -> float:
        """计算整体一致性得分"""
        if not consistency_checks:
            return 0
        
        # 所有维度一致性的加权平均
        total_score = sum(check['consistency'] for check in consistency_checks)
        return total_score / len(consistency_checks)
    
    @classmethod
    def _determine_confidence_level(
        cls,
        consistency_score: float,
        assessment_count: int,
        contradiction_count: int
    ) -> str:
        """确定置信度等级"""
        # 综合考虑一致性得分、测评数量、矛盾点数量
        
        # 一致性得分占主导
        if consistency_score >= 80:
            level = '高'
        elif consistency_score >= 60:
            level = '中'
        else:
            level = '低'
        
        # 测评数量少或矛盾点多，降低置信度
        if assessment_count < 2:
            level = '低'
        elif contradiction_count >= 2:
            if level == '高':
                level = '中'
            elif level == '中':
                level = '低'
        
        return level

