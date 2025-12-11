"""问卷管理 - 数据模型."""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON, Column
from sqlalchemy import Text


class Questionnaire(SQLModel, table=True):
    """问卷表."""
    __tablename__ = "questionnaires"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, index=True)  # EPQ人格测评
    type: str = Field(max_length=20)  # EPQ/DISC/MBTI/custom
    
    # ⭐ 问卷分类（导航用）
    # professional: 专业测评（MBTI/DISC/EPQ，有特定评分算法）
    # scored: 评分问卷（自定义，有评分配置）
    # survey: 调查问卷（自定义，无评分）
    category: str = Field(default="survey", max_length=20)
    
    questions_count: int = Field(default=0)  # 题目数量
    estimated_minutes: int = Field(default=15)  # 预计时长(分钟)
    questions_data: dict = Field(default={}, sa_column=Column(JSON))  # 题目数据
    scoring_rules: dict = Field(default={}, sa_column=Column(JSON))  # 计分规则
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    status: str = Field(default="active")  # active/inactive
    
    # ⭐ 新增：自定义问卷字段
    custom_type: Optional[str] = Field(default=None, max_length=20)  # scored/non_scored (仅自定义问卷)
    scoring_config: dict = Field(default={}, sa_column=Column(JSON))  # 评分配置（评分问卷使用）
    
    # ⭐ 问卷用途（评分问卷专用）
    # assessment: 能力测评/自评（结果展示：个人得分+等级）
    # survey: 满意度/评价调查（结果展示：统计汇总）
    purpose: Optional[str] = Field(default=None, max_length=20)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Assessment(SQLModel, table=True):
    """测评表（分发记录）."""
    __tablename__ = "assessments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)  # 测评名称
    code: str = Field(max_length=64, unique=True, index=True)  # 唯一访问码
    questionnaire_id: int = Field(foreign_key="questionnaires.id")
    valid_from: datetime  # 有效期开始
    valid_until: datetime  # 有效期结束
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    qr_code_url: Optional[str] = Field(default=None, max_length=512)  # 二维码URL
    
    # ⭐ 新增：表单字段配置
    form_fields: dict = Field(default={}, sa_column=Column(JSON))  # 候选人信息表单字段配置
    
    # ⭐ 新增：页面文案配置
    page_texts: dict = Field(default={}, sa_column=Column(JSON))  # 页面文案配置
    
    # ⭐ 分发机制扩展
    link_type: str = Field(default="temporary", max_length=20)  # temporary/permanent
    channel: str = Field(default="public_link", max_length=20)  # 分发渠道（预留扩展）
    allow_repeat: bool = Field(default=True)  # 允许重复提交
    repeat_check_by: str = Field(default="phone", max_length=20)  # 重复判断依据
    repeat_interval_hours: int = Field(default=0)  # 重复提交间隔（小时）
    max_submissions: int = Field(default=0)  # 最大提交次数（0=不限）
    view_count: int = Field(default=0)  # 浏览量统计
    start_count: int = Field(default=0)  # 开始测评数统计
    
    # ⭐ 预留：定向邀请（当前不使用）
    invite_list: Optional[str] = Field(default=None, sa_column=Column(Text))  # 邀请名单JSON
    require_verification: bool = Field(default=False)  # 需要验证身份
    
    created_by: Optional[int] = Field(default=None)  # 创建人ID
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Submission(SQLModel, table=True):
    """提交记录表."""
    __tablename__ = "submissions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=64, unique=True, index=True)  # SUB-20251201-001
    assessment_id: int = Field(foreign_key="assessments.id")
    questionnaire_id: int = Field(foreign_key="questionnaires.id")
    
    # 候选人信息
    candidate_name: str = Field(max_length=255)
    candidate_phone: str = Field(max_length=20)
    candidate_email: Optional[str] = Field(default=None, max_length=255)
    gender: Optional[str] = Field(default=None, max_length=10)  # ⭐ 性别
    target_position: Optional[str] = Field(default=None, max_length=255)
    
    # ⭐ 新增：自定义字段数据
    custom_data: dict = Field(default={}, sa_column=Column(JSON))  # 存储自定义字段数据
    
    # 答案和得分
    answers: dict = Field(default={}, sa_column=Column(JSON))  # 答案数据
    scores: dict = Field(default={}, sa_column=Column(JSON))  # 得分数据
    total_score: Optional[int] = Field(default=None)  # 总分
    grade: Optional[str] = Field(default=None, max_length=10)  # 等级 A/B/C/D
    result_details: dict = Field(default={}, sa_column=Column(JSON))  # ⭐ 多维度结果详情 (MBTI/DISC/EPQ/自定义问卷答案)
    
    # ⭐ 新增：自定义问卷评分字段
    max_score: Optional[int] = Field(default=None)  # 满分（仅评分问卷）
    score_percentage: Optional[float] = Field(default=None)  # 得分率（仅评分问卷）
    
    # 状态和时间
    status: str = Field(default="in_progress")  # in_progress/completed
    started_at: datetime = Field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = Field(default=None)
    
    # 关联到候选人表（通过手机号+姓名双重校验自动关联）
    candidate_id: Optional[int] = Field(default=None, foreign_key="candidates.id")

