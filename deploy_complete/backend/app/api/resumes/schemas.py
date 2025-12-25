"""简历管理 - Pydantic schemas."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ========== 简历上传相关 ==========

class ResumeUploadResponse(BaseModel):
    """单个简历上传响应."""
    candidate_id: int
    file_name: str
    file_path: str
    file_size: int
    uploaded_at: datetime
    parsing_status: str = "pending"  # pending, parsing, completed, failed
    
    class Config:
        from_attributes = True


class BatchUploadItem(BaseModel):
    """批量上传中的单个文件结果."""
    file_name: str
    success: bool
    candidate_id: Optional[int] = None
    file_path: Optional[str] = None
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """批量上传响应."""
    total: int
    success_count: int
    failed_count: int
    items: List[BatchUploadItem]


# ========== 简历解析结果 ==========

class EducationItem(BaseModel):
    """教育经历."""
    school: str
    major: Optional[str] = None
    degree: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ExperienceItem(BaseModel):
    """工作经历."""
    company: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    responsibilities: List[str] = []


class ProjectItem(BaseModel):
    """项目经验."""
    name: str
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = []


class ResumeParsedData(BaseModel):
    """简历解析后的结构化数据."""
    # 基本信息
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    target_position: Optional[str] = None  # ⭐ 新增：目标岗位/应聘职位
    
    # 教育背景
    education: List[EducationItem] = []
    
    # 工作经历
    experience: List[ExperienceItem] = []
    
    # 项目经验
    projects: List[ProjectItem] = []
    
    # 技能
    skills: List[str] = []
    
    # 证书
    certificates: List[str] = []
    
    # 语言能力
    languages: List[str] = []
    
    # 其他信息
    summary: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class ResumeInfoResponse(BaseModel):
    """简历信息响应."""
    candidate_id: int
    has_resume: bool
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    parsing_status: Optional[str] = None
    parsed_data: Optional[ResumeParsedData] = None
    resume_text: Optional[str] = None
    
    class Config:
        from_attributes = True


# ========== 简历解析触发 ==========

class ResumeParseRequest(BaseModel):
    """手动触发简历解析请求."""
    candidate_id: int
    force_reparse: bool = False  # 是否强制重新解析


class ResumeParseResponse(BaseModel):
    """简历解析响应."""
    candidate_id: int
    status: str  # success, failed, in_progress
    message: str
    parsed_data: Optional[ResumeParsedData] = None

