from app.schemas import AnalyticsSummary, CandidateOut, PositionBucket, RadarIndicator, RadarSeries, SubmissionScore, TrendSeries

# ⚠️ Mock候选人数据 - 与数据库保持一致（3个候选人，对应EPQ/DISC/MBTI）
MOCK_CANDIDATES = [
    CandidateOut(
        id=1,
        name="张三",
        position="产品经理",          # EPQ测评
        phone="138****5678",
        score=85,
        grade="A",
        level="P6",
        status="已完成",
        tags=["外向型", "结构化分析"],
        updated_at="2025-12-02",
        dimensions=[
            SubmissionScore(dimension="E", score=85, grade="A", grade_label="外向性"),
            SubmissionScore(dimension="N", score=45, grade="B", grade_label="神经质"),
            SubmissionScore(dimension="P", score=68, grade="B", grade_label="精神质"),
            SubmissionScore(dimension="L", score=82, grade="A", grade_label="掩饰性"),
        ],
    ),
    CandidateOut(
        id=2,
        name="李四",
        position="实施工程师",        # DISC测评
        phone="139****5678",
        score=75,
        grade="B",
        level="P5",
        status="已完成",
        tags=["谨慎型", "注重细节"],
        updated_at="2025-12-03",
        dimensions=[
            SubmissionScore(dimension="D", score=72, grade="B", grade_label="支配型"),
            SubmissionScore(dimension="I", score=65, grade="B", grade_label="影响型"),
            SubmissionScore(dimension="S", score=78, grade="B", grade_label="稳健型"),
            SubmissionScore(dimension="C", score=85, grade="A", grade_label="谨慎型"),
        ],
    ),
    CandidateOut(
        id=3,
        name="王五",
        position="软件工程师",        # MBTI测评
        phone="137****9999",
        score=80,
        grade="A",
        level="P5",
        status="已完成",
        tags=["INTJ", "系统思维"],
        updated_at="2025-12-04",
    ),
    # ❌ 已删除赵六 - 只保留3个候选人对应EPQ/DISC/MBTI测评
]

MOCK_ANALYTICS = AnalyticsSummary(
    positionDistribution=[
        PositionBucket(name="产品", value=32),
        PositionBucket(name="后端", value=24),
        PositionBucket(name="前端", value=18),
        PositionBucket(name="数据", value=12),
    ],
    matchDistribution=[
        PositionBucket(name=">90", value=8),
        PositionBucket(name="80-90", value=14),
        PositionBucket(name="70-80", value=22),
        PositionBucket(name="<70", value=10),
    ],
    radarIndicators=[
        RadarIndicator(name="外向 E", max=24),
        RadarIndicator(name="神经 N", max=24),
        RadarIndicator(name="精神 P", max=24),
        RadarIndicator(name="掩饰 L", max=24),
    ],
    radarSeries=[
        RadarSeries(name="候选人 A", value=[18, 10, 12, 16]),
        RadarSeries(name="理想模型", value=[20, 12, 14, 18]),
    ],
    personalityPie=[
        PositionBucket(name="外向型", value=40),
        PositionBucket(name="内向型", value=32),
        PositionBucket(name="中性", value=18),
    ],
    dimensionTrendLabels=["近1周", "近1月", "近3月"],
    dimensionTrendSeries=[
        TrendSeries(name="外向 E", data=[16, 18, 19]),
        TrendSeries(name="神经 N", data=[8, 9, 10]),
        TrendSeries(name="精神 P", data=[10, 11, 12]),
        TrendSeries(name="掩饰 L", data=[14, 15, 15]),
    ],
    gradeCutoffs={"A": 18, "B": 12, "C": 8},
    totalCandidates=120,
    avgScore=79.6,
)
