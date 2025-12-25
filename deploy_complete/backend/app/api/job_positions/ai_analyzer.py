"""岗位管理 - AI分析模块."""
from typing import Optional
from app.api.job_positions import schemas
from app.models import Candidate, JobProfile


async def analyze_job_requirement(
    requirement_text: str,
) -> schemas.RequirementAnalysisResponse:
    """
    AI分析岗位需求文案。
    
    TODO: 接入真实AI模型（如OpenAI GPT、百度文心、阿里通义等）
    """
    # Mock数据 - 实际应调用AI API
    mock_result = schemas.RequirementAnalysisResponse(
        key_abilities=[
            {"name": "沟通协调能力", "importance": "高"},
            {"name": "项目管理能力", "importance": "高"},
            {"name": "数据分析能力", "importance": "中"},
            {"name": "团队协作能力", "importance": "高"},
            {"name": "问题解决能力", "importance": "中"},
        ],
        personality_preferences=["外向型", "高尽责性", "开放性强", "情绪稳定"],
        experience_requirements="3-5年相关工作经验",
        education_requirements="本科及以上学历，计算机或相关专业优先",
        summary="该岗位需要候选人具备较强的沟通协调和项目管理能力，性格上偏好外向、尽责、开放的类型。"
        "同时需要一定的数据分析能力和问题解决能力。要求3-5年工作经验，本科及以上学历。",
    )
    return mock_result


async def suggest_dimension_weights_ai(
    job_id: int, requirement_analysis: Optional[dict] = None
) -> schemas.DimensionSuggestionResponse:
    """
    AI建议维度权重配置。
    
    根据岗位需求分析结果，建议各个测评维度的权重和理想分数。
    
    TODO: 接入真实AI模型
    """
    # Mock数据
    mock_dimensions = [
        schemas.DimensionWeightCreate(
            dimension_code="E",
            dimension_name="外向性",
            weight=0.25,
            ideal_score=18.0,
            min_score=12.0,
            description="该岗位需要较强的社交能力",
        ),
        schemas.DimensionWeightCreate(
            dimension_code="N",
            dimension_name="神经质",
            weight=0.15,
            ideal_score=8.0,
            min_score=5.0,
            description="情绪稳定性要求中等",
        ),
        schemas.DimensionWeightCreate(
            dimension_code="P",
            dimension_name="精神质",
            weight=0.10,
            ideal_score=6.0,
            min_score=3.0,
            description="创新思维需求中等",
        ),
        schemas.DimensionWeightCreate(
            dimension_code="C",
            dimension_name="尽责性",
            weight=0.30,
            ideal_score=20.0,
            min_score=15.0,
            description="该岗位需要高度的责任心和执行力",
        ),
        schemas.DimensionWeightCreate(
            dimension_code="O",
            dimension_name="开放性",
            weight=0.20,
            ideal_score=15.0,
            min_score=10.0,
            description="需要较强的学习能力和适应能力",
        ),
    ]

    explanation = (
        "根据岗位需求分析，该岗位最看重尽责性（30%）和外向性（25%），"
        "其次是开放性（20%）。神经质和精神质权重相对较低。"
        "建议候选人在尽责性和外向性维度上达到理想分数以获得更好的匹配度。"
    )

    return schemas.DimensionSuggestionResponse(
        dimensions=mock_dimensions, explanation=explanation
    )


async def calculate_candidate_match_ai(
    candidate: Candidate, job_profile: JobProfile
) -> schemas.CandidateMatchResponse:
    """
    计算候选人与岗位的匹配度。
    
    综合考虑：
    1. 性格测评结果与岗位要求的匹配
    2. 简历信息与岗位要求的匹配
    3. 各维度的权重配置
    
    TODO: 接入真实AI模型进行复杂的匹配分析
    """
    # Mock数据 - 实际应基于候选人数据和岗位画像进行AI分析
    mock_result = schemas.CandidateMatchResponse(
        match_score=78.5,
        dimension_scores=[
            {
                "dimension_code": "E",
                "dimension_name": "外向性",
                "candidate_score": 16.0,
                "ideal_score": 18.0,
                "weight": 0.25,
                "match_rate": 0.89,
            },
            {
                "dimension_code": "C",
                "dimension_name": "尽责性",
                "candidate_score": 18.0,
                "ideal_score": 20.0,
                "weight": 0.30,
                "match_rate": 0.90,
            },
            {
                "dimension_code": "O",
                "dimension_name": "开放性",
                "candidate_score": 13.0,
                "ideal_score": 15.0,
                "weight": 0.20,
                "match_rate": 0.87,
            },
            {
                "dimension_code": "N",
                "dimension_name": "神经质",
                "candidate_score": 7.0,
                "ideal_score": 8.0,
                "weight": 0.15,
                "match_rate": 0.88,
            },
            {
                "dimension_code": "P",
                "dimension_name": "精神质",
                "candidate_score": 4.0,
                "ideal_score": 6.0,
                "weight": 0.10,
                "match_rate": 0.67,
            },
        ],
        strengths=[
            "尽责性表现优秀，具有很强的责任心和执行力",
            "外向性良好，沟通协调能力强",
            "开放性较好，学习能力和适应能力不错",
        ],
        weaknesses=[
            "精神质维度得分偏低，创新思维可能需要加强",
            "抗压能力需要进一步评估",
        ],
        recommendation="该候选人与岗位要求匹配度较高（78.5%），特别是在尽责性和外向性方面表现突出，"
        "建议安排面试。面试时可重点关注其创新能力和抗压能力。",
        suitable=True,
    )

    return mock_result
