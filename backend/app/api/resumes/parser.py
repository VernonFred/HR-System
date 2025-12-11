"""简历管理 - AI解析服务."""
import re
import json
import logging
from typing import Dict, List, Any, Optional
from app.api.resumes.schemas import ResumeParsedData, EducationItem, ExperienceItem, ProjectItem

logger = logging.getLogger(__name__)


async def parse_resume_with_ai(
    resume_text: str, 
    analysis_level: str = "pro"
) -> ResumeParsedData:
    """
    使用AI解析简历文本，提取结构化信息并进行深度分析.
    
    Args:
        resume_text: 简历文本内容
        analysis_level: 分析级别 (pro/expert)
        
    Returns:
        解析后的结构化数据（包含AI分析结果）
    """
    from app.core.ai.portrait_router import call_portrait_model
    from app.core.ai.ai_client import parse_json_safely, pick_content_text
    
    # 构建简历解析的提示词
    system_prompt = _build_resume_parse_system_prompt()
    user_prompt = _build_resume_parse_user_prompt(resume_text)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        logger.info(f"🔍 开始AI解析简历 (level={analysis_level})")
        print(f"🔍 开始AI解析简历 (level={analysis_level})")
        
        # 调用AI模型
        response = await call_portrait_model(
            messages=messages,
            level=analysis_level,
            max_tokens=2048,
            temperature=0.3,
        )
        
        # 解析AI返回的JSON
        content = pick_content_text(response)
        result = parse_json_safely(content)
        
        if not result:
            logger.warning("⚠️ AI解析返回空结果，使用规则解析兜底")
            return _rule_based_parse(resume_text)
        
        logger.info(f"✅ AI解析简历成功 model={response.get('model', 'unknown')}")
        print(f"✅ AI解析简历成功 model={response.get('model', 'unknown')}")
    
        # 转换为 ResumeParsedData
        return _convert_ai_result_to_parsed_data(result, resume_text)
        
    except Exception as e:
        logger.warning(f"❌ AI解析简历失败: {e}，使用规则解析兜底")
        print(f"❌ AI解析简历失败: {e}，使用规则解析兜底")
        return _rule_based_parse(resume_text)


def _build_resume_parse_system_prompt() -> str:
    """构建简历解析的系统提示词 - V38增强版."""
    return """你是一名资深的人力资源专家和简历分析师，具备丰富的招聘经验和人才评估能力。

【你的任务】
1. 精准提取简历中的结构化信息
2. 深度分析候选人的职业特征和发展潜力
3. 识别简历中的亮点、风险和需验证的疑点
4. 为后续的人才画像生成提供高质量的分析基础

【输出要求】
必须输出合法 JSON，结构如下：

{
  "name": "候选人姓名",
  "email": "邮箱地址",
  "phone": "手机号码",
  "location": "所在城市",
  "target_position": "求职意向/目标岗位",
  "education": [
    {
      "school": "学校名称",
      "major": "专业",
      "degree": "学历（本科/硕士/博士）",
      "start_date": "开始时间",
      "end_date": "结束时间"
    }
  ],
  "experience": [
    {
      "company": "公司名称",
      "position": "职位",
      "start_date": "开始时间",
      "end_date": "结束时间",
      "responsibilities": ["职责描述1", "职责描述2"],
      "achievements": ["具体成果/业绩（如有）"]
    }
  ],
  "projects": [
    {
      "name": "项目名称",
      "role": "担任角色",
      "start_date": "开始时间",
      "end_date": "结束时间",
      "description": "项目描述",
      "technologies": ["技术1", "技术2"],
      "impact": "项目成效/影响（如有）"
    }
  ],
  "skills": ["技能1", "技能2"],
  "certificates": ["证书1", "证书2"],
  "languages": ["语言能力1", "语言能力2"],
  "summary": "简历摘要（50-100字，概括候选人的核心竞争力）",
  "ai_analysis": {
    "core_strengths": [
      "核心优势1（从经历中推断，非简历自述）",
      "核心优势2",
      "核心优势3"
    ],
    "potential_risks": [
      "潜在风险1（从经历中发现的问题点）",
      "潜在风险2"
    ],
    "career_trajectory": "职业轨迹分析（100-150字）：分析跳槽频率（是否频繁/稳定）、晋升速度（是否有明显上升）、行业选择（是否专注/跨界）、职业发展规律",
    "work_style": "工作风格推断（80-120字）：基于工作内容推断其做事风格，如偏执行还是偏策略、偏独立还是偏协作、偏创新还是偏稳健",
    "suitable_environment": "适合的工作环境（80-120字）：推断适合什么类型的团队（大厂/创业公司/传统企业）、管理风格（扁平/层级）、工作节奏（快节奏/稳定）",
    "stability_assessment": "稳定性评估（50-80字）：基于工作时长、跳槽规律推断候选人的稳定性，是否有频繁跳槽风险",
    "growth_potential": "成长潜力评估（80-120字）：基于学历、经历、技能发展推断候选人的学习能力和成长空间",
    "soft_skills_inference": [
      "推断的软技能1（如：沟通能力强 - 因为有跨部门协调经历）",
      "推断的软技能2（如：抗压能力好 - 因为有高压项目经历）",
      "推断的软技能3"
    ],
    "interview_focus_points": [
      "面试需重点验证的问题1（如：某段经历时间短，需了解离职原因）",
      "面试需重点验证的问题2（如：项目成果描述模糊，需追问具体贡献）",
      "面试需重点验证的问题3"
    ],
    "red_flags": [
      "简历疑点/红旗1（如：工作经历有空白期）",
      "简历疑点/红旗2（如：职位描述与公司规模不匹配）"
    ],
    "overall_impression": "整体印象（100-150字）：综合评价候选人的整体素质、与目标岗位的匹配度、值得关注的特点"
  }
}

【分析原则】
1. 独立判断：不要轻信简历中的自我评价（如"沟通能力强"），要从具体经历中推断
2. 有理有据：每个分析结论都要有简历内容支撑，不能凭空臆断
3. 关注细节：注意时间线的连贯性、职位的合理性、成果的具体性
4. 客观中立：既要发现亮点，也要识别风险，保持客观
5. 实用导向：分析结果要对招聘决策有实际帮助

【注意事项】
1. 如果某个字段在简历中找不到，返回空字符串或空数组
2. 时间格式统一为 "YYYY" 或 "YYYY-MM"
3. ai_analysis 是深度分析，必须有洞察力，禁止简单复述简历内容
4. red_flags 和 interview_focus_points 特别重要，帮助面试官发现需要追问的点"""


def _build_resume_parse_user_prompt(resume_text: str) -> str:
    """构建简历解析的用户提示词."""
    return f"""请分析以下简历内容，提取结构化信息并进行深度分析：

---简历内容开始---
{resume_text}
---简历内容结束---

请严格按照JSON格式输出，不要包含任何解释性文字。"""


def _convert_ai_result_to_parsed_data(result: Dict[str, Any], resume_text: str) -> ResumeParsedData:
    """将AI返回的结果转换为 ResumeParsedData - V38增强版."""
    # 提取教育背景
    education = []
    for edu in result.get("education", []):
        if isinstance(edu, dict):
            education.append(EducationItem(
                school=edu.get("school", ""),
                major=edu.get("major"),
                degree=edu.get("degree"),
                start_date=edu.get("start_date"),
                end_date=edu.get("end_date")
            ))
    
    # 提取工作经历（V38: 增加 achievements）
    experience = []
    for exp in result.get("experience", []):
        if isinstance(exp, dict):
            exp_item = ExperienceItem(
                company=exp.get("company", ""),
                position=exp.get("position", ""),
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                responsibilities=exp.get("responsibilities", [])
            )
            # 如果有成就，添加到职责后面
            achievements = exp.get("achievements", [])
            if achievements:
                exp_item.responsibilities.extend([f"[成果] {a}" for a in achievements])
            experience.append(exp_item)
    
    # 提取项目经验（V38: 增加 impact）
    projects = []
    for proj in result.get("projects", []):
        if isinstance(proj, dict):
            desc = proj.get("description", "")
            impact = proj.get("impact", "")
            if impact:
                desc = f"{desc} | 成效: {impact}" if desc else impact
            projects.append(ProjectItem(
                name=proj.get("name", ""),
                role=proj.get("role"),
                start_date=proj.get("start_date"),
                end_date=proj.get("end_date"),
                description=desc,
                technologies=proj.get("technologies", [])
            ))
    
    # V38: 构建更丰富的摘要（包含所有AI分析维度）
    ai_analysis = result.get("ai_analysis", {})
    summary = result.get("summary", "")
    
    # 如果有AI分析，将其整合到摘要中
    if ai_analysis:
        analysis_parts = []
        
        # 整体印象（最重要，放最前面）
        if ai_analysis.get("overall_impression"):
            analysis_parts.append(f"【整体印象】{ai_analysis['overall_impression']}")
        
        # 核心优势
        if ai_analysis.get("core_strengths"):
            strengths = ai_analysis['core_strengths']
            if isinstance(strengths, list):
                analysis_parts.append(f"【核心优势】{'、'.join(strengths)}")
    
        # 潜在风险
        if ai_analysis.get("potential_risks"):
            risks = ai_analysis['potential_risks']
            if isinstance(risks, list):
                analysis_parts.append(f"【潜在风险】{'、'.join(risks)}")
        
        # 职业轨迹
        if ai_analysis.get("career_trajectory"):
            analysis_parts.append(f"【职业轨迹】{ai_analysis['career_trajectory']}")
    
        # 工作风格
        if ai_analysis.get("work_style"):
            analysis_parts.append(f"【工作风格】{ai_analysis['work_style']}")
        
        # 适合环境
        if ai_analysis.get("suitable_environment"):
            analysis_parts.append(f"【适合环境】{ai_analysis['suitable_environment']}")
        
        # V38新增: 稳定性评估
        if ai_analysis.get("stability_assessment"):
            analysis_parts.append(f"【稳定性评估】{ai_analysis['stability_assessment']}")
        
        # V38新增: 成长潜力
        if ai_analysis.get("growth_potential"):
            analysis_parts.append(f"【成长潜力】{ai_analysis['growth_potential']}")
        
        # V38新增: 软技能推断
        if ai_analysis.get("soft_skills_inference"):
            skills = ai_analysis['soft_skills_inference']
            if isinstance(skills, list):
                analysis_parts.append(f"【软技能推断】{'；'.join(skills)}")
        
        # V38新增: 面试重点
        if ai_analysis.get("interview_focus_points"):
            points = ai_analysis['interview_focus_points']
            if isinstance(points, list) and points:
                analysis_parts.append(f"【面试重点】{'；'.join(points)}")
        
        # V38新增: 红旗/疑点
        if ai_analysis.get("red_flags"):
            flags = ai_analysis['red_flags']
            if isinstance(flags, list) and flags:
                analysis_parts.append(f"【需关注】{'；'.join(flags)}")
        
        if analysis_parts:
            summary = summary + "\n\n" + "\n".join(analysis_parts) if summary else "\n".join(analysis_parts)
    
    return ResumeParsedData(
        name=result.get("name", _extract_name_fallback(resume_text)),
        email=result.get("email", _extract_email_fallback(resume_text)),
        phone=result.get("phone", _extract_phone_fallback(resume_text)),
        location=result.get("location", ""),
        target_position=result.get("target_position", ""),
        education=education,
        experience=experience,
        projects=projects,
        skills=result.get("skills", []),
        certificates=result.get("certificates", []),
        languages=result.get("languages", []),
        summary=summary
    )


# =============================================================================
# 规则解析兜底（当AI失败时使用）
# =============================================================================

def _rule_based_parse(text: str) -> ResumeParsedData:
    """
    规则解析兜底：使用正则表达式和规则进行简单解析.
    当AI解析失败时使用。
    """
    lines = text.split('\n')
    
    return ResumeParsedData(
        name=_extract_name_fallback(lines, text),
        email=_extract_email_fallback(text),
        phone=_extract_phone_fallback(text),
        location=_extract_location_fallback(text),
        target_position=_extract_target_position_fallback(text, lines),
        education=_extract_education_fallback(text),
        experience=_extract_experience_fallback(text),
        projects=[],
        skills=_extract_skills_fallback(text),
        certificates=[],
        languages=[],
        summary="（AI解析失败，使用规则提取基本信息）"
    )


def _extract_name_fallback(lines_or_text, text: str = None) -> str:
    """提取姓名（兜底方法）."""
    if isinstance(lines_or_text, str):
        text = lines_or_text
        lines = text.split('\n')
    else:
        lines = lines_or_text
        if text is None:
            text = '\n'.join(lines)
    
    # 方法1：查找"姓名："后面的内容
    name_patterns = [
        r'姓\s*名[：:]\s*([\u4e00-\u9fa5]{2,4})',
        r'Name[：:]\s*([\u4e00-\u9fa5]{2,4})',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    # 方法2：简历开头的中文名
    for line in lines[:10]:
        line = line.strip()
        if line in ["个人简历", "简历", "求职简历", "基本信息", "个人信息"]:
            continue
        clean_line = line.replace(" ", "")
        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', clean_line):
            return clean_line
    
    return "未知"


def _extract_email_fallback(text: str) -> str:
    """提取邮箱（兜底方法）."""
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else ""


def _extract_phone_fallback(text: str) -> str:
    """提取手机号（兜底方法）."""
    match = re.search(r'1[3-9]\d{9}', text)
    return match.group(0) if match else ""


def _extract_location_fallback(text: str) -> str:
    """提取所在地（兜底方法）."""
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "西安", "重庆"]
    for city in cities:
        if city in text:
            return city + "市"
    return ""


def _extract_target_position_fallback(text: str, lines: List[str]) -> str:
    """提取目标岗位（兜底方法）."""
    position_patterns = [
        r'求职意向[：:]\s*([^\n\r,，、;；]{2,25})',
        r'应聘[岗位职位]*[：:]\s*([^\n\r,，、;；]{2,25})',
        r'目标[岗位职位]*[：:]\s*([^\n\r,，、;；]{2,25})',
        r'期望[岗位职位]*[：:]\s*([^\n\r,，、;；]{2,25})',
    ]
    
    for pattern in position_patterns:
        match = re.search(pattern, text)
        if match:
            position = match.group(1).strip()
            position = re.sub(r'[\s\-—–()（）\[\]【】]+$', '', position)
            if position and 2 <= len(position) <= 25:
                return position
    
    return ""


def _extract_education_fallback(text: str) -> List[EducationItem]:
    """提取教育背景（兜底方法）."""
    items = []
    education_section = _extract_section(text, ["教育背景", "教育经历", "学历"])
    if not education_section:
        return items
    
    lines = education_section.split('\n')
    for line in lines:
        if re.search(r'\d{4}', line):
            school_match = re.search(r'[\u4e00-\u9fa5]{2,20}(大学|学院)', line)
            if school_match:
                items.append(EducationItem(
                    school=school_match.group(0),
                    major="",
                    degree="",
                    start_date="",
                    end_date=""
                ))
    
    return items


def _extract_experience_fallback(text: str) -> List[ExperienceItem]:
    """提取工作经历（兜底方法）."""
    items = []
    experience_section = _extract_section(text, ["工作经历", "工作经验", "任职经历"])
    if not experience_section:
        return items
    
    lines = experience_section.split('\n')
    for line in lines:
        if re.search(r'\d{4}', line):
            company_match = re.search(r'[\u4e00-\u9fa5]{2,20}(公司|科技|集团)', line)
            if company_match:
                items.append(ExperienceItem(
                    company=company_match.group(0),
                    position="",
                    start_date="",
                    end_date="",
                    responsibilities=[]
        ))
    
    return items


def _extract_skills_fallback(text: str) -> List[str]:
    """提取技能列表（兜底方法）."""
    skills_section = _extract_section(text, ["技能", "专业技能", "技术栈"])
    if not skills_section:
        return []
    
    skills = re.split(r'[,，、\s]+', skills_section)
    return [s.strip() for s in skills if s.strip() and len(s.strip()) > 1]


def _extract_section(text: str, keywords: List[str]) -> str:
    """提取特定章节的内容."""
    lines = text.split('\n')
    section_lines = []
    in_section = False
    
    for line in lines:
        if any(keyword in line for keyword in keywords):
            in_section = True
            continue
        
        if in_section:
            if len(line.strip()) < 10 and any(kw in line for kw in ["背景", "经历", "经验", "能力", "证书"]):
                break
            section_lines.append(line)
    
    return '\n'.join(section_lines)
