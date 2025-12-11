"""问卷/测评管理 - Pydantic模型."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


# ========== 问卷相关 ==========

class QuestionOption(BaseModel):
    """问题选项 - 兼容多种格式."""
    label: Optional[str] = None  # A, B, C, D 或选项标签
    text: Optional[str] = None  # 选项文本
    value: Optional[str] = None  # 选项值（前端编辑器格式）
    score: Optional[int] = None  # 得分
    
    @property
    def display_text(self) -> str:
        """获取显示文本：优先text，其次label."""
        return self.text or self.label or self.value or ""


class Question(BaseModel):
    """问题 - 兼容多种格式."""
    id: Union[int, str]  # 支持整数或字符串ID
    text: str  # 问题文本
    type: Optional[str] = None  # 题目类型：radio/checkbox/text/scale等
    options: Optional[List[QuestionOption]] = None  # 选项（单选/多选题）
    dimension: Optional[str] = None  # 所属维度 (E/N/P/L)
    required: Optional[bool] = True  # 是否必答
    scale: Optional[dict] = None  # 量表配置
    optionA: Optional[str] = None  # 二选一选项A
    optionB: Optional[str] = None  # 二选一选项B


class QuestionnaireBase(BaseModel):
    """问卷基础模型."""
    name: str
    type: str  # EPQ/DISC/MBTI/custom
    category: str = "survey"  # professional/scored/survey
    description: Optional[str] = None


class QuestionnaireCreate(QuestionnaireBase):
    """创建问卷."""
    questions_count: int = 0
    estimated_minutes: int = 15
    questions_data: Dict[str, Any] = {}
    scoring_rules: Dict[str, Any] = {}
    # ⭐ 新增：自定义问卷字段
    custom_type: Optional[str] = None  # scored/non_scored
    scoring_config: Dict[str, Any] = {}  # 评分配置
    # ⭐ 问卷用途（评分问卷专用）
    purpose: Optional[str] = None  # assessment: 能力测评 / survey: 满意度调查


class QuestionnaireUpdate(BaseModel):
    """更新问卷."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None  # professional/scored/survey
    questions_data: Optional[Dict[str, Any]] = None
    scoring_rules: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    questions_count: Optional[int] = None
    estimated_minutes: Optional[int] = None
    # ⭐ 新增：自定义问卷字段
    custom_type: Optional[str] = None
    scoring_config: Optional[Dict[str, Any]] = None
    # ⭐ 问卷用途（评分问卷专用）
    purpose: Optional[str] = None


class QuestionnaireResponse(QuestionnaireBase):
    """问卷响应."""
    id: int
    questions_count: int
    estimated_minutes: int
    status: str
    created_at: datetime
    updated_at: datetime
    # ⭐ 新增：自定义问卷字段
    custom_type: Optional[str] = None
    scoring_config: Optional[Dict[str, Any]] = None  # 允许为 None
    # ⭐ 问卷用途（评分问卷专用）
    purpose: Optional[str] = None

    class Config:
        from_attributes = True


class QuestionnaireDetailResponse(QuestionnaireResponse):
    """问卷详情响应."""
    questions_data: Dict[str, Any]
    scoring_rules: Dict[str, Any]
    # custom_type和scoring_config继承自QuestionnaireResponse


class QuestionnaireListResponse(BaseModel):
    """问卷列表响应."""
    items: List[QuestionnaireResponse]
    total: int


# ========== 测评相关 ==========

class AssessmentBase(BaseModel):
    """测评基础模型."""
    name: str
    questionnaire_id: int
    valid_from: datetime
    valid_until: datetime
    description: Optional[str] = None


class AssessmentCreate(AssessmentBase):
    """创建测评."""
    form_fields: Optional[List[Dict[str, Any]]] = []  # ⭐ 表单字段配置
    page_texts: Optional[Dict[str, Any]] = {}  # ⭐ 页面文案配置
    # ⭐ 分发机制
    link_type: str = "temporary"  # temporary/permanent
    allow_repeat: bool = True  # 允许重复提交
    repeat_check_by: str = "phone"  # 重复判断依据
    repeat_interval_hours: int = 0  # 重复提交间隔（小时）
    max_submissions: int = 0  # 最大提交次数（0=不限）


class AssessmentUpdate(BaseModel):
    """更新测评配置."""
    name: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    description: Optional[str] = None
    form_fields: Optional[List[Dict[str, Any]]] = None
    page_texts: Optional[Dict[str, Any]] = None
    # ⭐ 分发机制
    link_type: Optional[str] = None
    allow_repeat: Optional[bool] = None
    repeat_check_by: Optional[str] = None
    repeat_interval_hours: Optional[int] = None
    max_submissions: Optional[int] = None


class AssessmentResponse(AssessmentBase):
    """测评响应."""
    id: int
    code: str  # 唯一访问码
    qr_code_url: Optional[str] = None
    form_fields: Optional[Any] = None  # ⭐ 表单字段配置（允许 None、dict 或 list）
    page_texts: Optional[Dict[str, Any]] = None  # ⭐ 页面文案配置
    # ⭐ 分发机制
    link_type: str = "temporary"
    allow_repeat: bool = True
    repeat_check_by: str = "phone"
    repeat_interval_hours: int = 0
    max_submissions: int = 0
    view_count: int = 0
    start_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class AssessmentDetailResponse(AssessmentResponse):
    """测评详情响应."""
    questionnaire_name: Optional[str] = None
    questionnaire_type: Optional[str] = None
    submissions_count: int = 0
    completed_count: int = 0


class AssessmentListResponse(BaseModel):
    """测评列表响应."""
    items: List[AssessmentResponse]
    total: int


# ========== 提交记录相关 ==========

class SubmissionCreate(BaseModel):
    """创建提交记录（候选人开始测评）."""
    assessment_code: str
    candidate_name: str
    candidate_phone: str
    candidate_email: Optional[str] = None
    gender: Optional[str] = None  # ⭐ 性别字段
    target_position: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = {}  # ⭐ 自定义字段数据


class AnswerSubmit(BaseModel):
    """提交答案."""
    submission_code: str
    answers: Dict[str, Any]  # {question_id: selected_option} 支持字符串、数字、数组等类型


class SubmissionResponse(BaseModel):
    """提交记录响应."""
    id: int
    code: str
    candidate_name: str
    candidate_phone: str
    candidate_email: Optional[str] = None  # V45: 新增邮箱
    gender: Optional[str] = None  # V45: 新增性别
    target_position: Optional[str] = None  # V45: 新增应聘岗位
    questionnaire_id: Optional[int] = None  # ⭐ 新增：问卷ID，用于前端过滤
    questionnaire_name: Optional[str] = None
    questionnaire_type: Optional[str] = None
    total_score: Optional[int] = None
    grade: Optional[str] = None
    status: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    # ⭐ 新增：自定义问卷评分字段
    max_score: Optional[int] = None
    score_percentage: Optional[float] = None
    result_details: Optional[Union[Dict[str, Any], List[Any]]] = None  # 允许为 None，支持 Dict 或 List

    class Config:
        from_attributes = True


class SubmissionDetailResponse(SubmissionResponse):
    """提交记录详情."""
    answers: Dict[str, Any]
    scores: Dict[str, Any]
    target_position: Optional[str] = None


class SubmissionListResponse(BaseModel):
    """提交记录列表响应."""
    items: List[SubmissionResponse]
    total: int


# ========== 公开API（候选人端） ==========

class PublicAssessmentInfo(BaseModel):
    """公开的测评信息."""
    name: str
    type: str  # EPQ/DISC/MBTI
    questions_count: int
    estimated_minutes: int
    valid: bool  # 是否在有效期内
    expired: bool  # 是否已过期
    description: Optional[str] = None
    form_fields: List[Dict[str, Any]] = []  # ⭐ 表单字段配置
    page_texts: Optional[Dict[str, Any]] = None  # ⭐ 页面文案配置
    questions: Optional[List[Dict[str, Any]]] = None  # ⭐ 问卷题目数据（用于前端 fallback）
    # ⭐ 重复提交配置
    allow_repeat: bool = True
    repeat_check_by: str = "phone"
    repeat_interval_hours: int = 0
    max_submissions: int = 0


class PublicSubmissionStart(BaseModel):
    """候选人开始测评响应."""
    submission_code: str
    questions: List[Question]  # 所有题目


class PublicSubmissionSuccess(BaseModel):
    """提交成功响应."""
    success: bool
    submission_code: str
    submitted_at: datetime
    message: str = "感谢您完成测评！"


# ========== V43: 问卷导入 ==========

class QuestionnaireImportResponse(BaseModel):
    """问卷导入响应."""
    success: bool
    message: str
    metadata: Dict[str, Any] = {}  # 问卷元数据（名称、描述等）
    questions: List[Dict[str, Any]] = []  # 解析出的题目列表

