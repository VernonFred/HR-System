"""岗位画像 - AI辅助服务 V5.

功能：
1. 分析优秀员工简历，生成岗位画像配置建议
2. 分析 JD 文本，生成岗位画像配置建议

定位：辅助工具，不存储简历数据

V5 更新：
- 使用 ModelScope Pro (32B) 模型
- 使用新的 V5 提示词
"""

import logging
from typing import Dict, List, Any, Optional

from app.core.ai.ai_client import AIClientError, pick_content_text, parse_json_safely
from app.core.ai.portrait_router import call_portrait_model
from app.core.ai.prompt_builder import (
    build_job_resume_analysis_prompt,
    build_job_jd_analysis_prompt,
)

logger = logging.getLogger(__name__)


async def analyze_resume_for_job_profile(
    resume_text: str,
    job_title: str,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析优秀员工简历，生成岗位画像配置建议 - V5 版本.
    
    Args:
        resume_text: 简历文本内容
        job_title: 岗位名称
        department: 部门名称（可选）
        
    Returns:
        岗位画像配置建议
    """
    # 使用 V5 提示词
    messages = build_job_resume_analysis_prompt(resume_text, job_title, department)
    
    try:
        # V5: 使用 ModelScope Pro (32B) 模型
        logger.info(f"🎯 岗位画像-简历分析: {job_title}")
        print(f"🎯 岗位画像-简历分析: {job_title}")
        
        response = await call_portrait_model(
            messages=messages,
            level="pro",  # 使用 32B 模型
            max_tokens=2048,
            temperature=0.4,
        )
        
        # 解析响应
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        data = parse_json_safely(content)
        
        # 填充默认值
        result = _fill_defaults(data, job_title, department)
        
        logger.info(
            "✅ AI分析简历成功: job_title=%s, dimensions=%d",
            job_title,
            len(result.get("dimensions", []))
        )
        print(f"✅ AI分析简历成功: {job_title}, {len(result.get('dimensions', []))} 个维度")
        
        return result
        
    except Exception as e:
        logger.error("❌ AI分析简历失败: %s", e, exc_info=True)
        print(f"❌ AI分析简历失败: {e}")
        # 降级到规则化分析
        return _fallback_analysis(resume_text, job_title, department)


async def analyze_jd_for_job_profile(
    jd_text: str,
    job_title: str,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析 JD 文本，生成岗位画像配置建议 - V5 版本.
    
    Args:
        jd_text: JD（岗位描述）文本
        job_title: 岗位名称
        department: 部门名称
        
    Returns:
        岗位画像配置建议
    """
    # 使用 V5 提示词
    messages = build_job_jd_analysis_prompt(jd_text, job_title, department)
    
    try:
        # V5: 使用 ModelScope Pro (32B) 模型
        logger.info(f"🎯 岗位画像-JD分析: {job_title}")
        print(f"🎯 岗位画像-JD分析: {job_title}")
        
        response = await call_portrait_model(
            messages=messages,
            level="pro",  # 使用 32B 模型
            max_tokens=2048,
            temperature=0.4,
        )
        
        # 解析响应
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        data = parse_json_safely(content)
        
        # 填充默认值
        result = _fill_defaults(data, job_title, department)
        
        logger.info("✅ AI分析JD成功: job_title=%s", job_title)
        print(f"✅ AI分析JD成功: {job_title}")
        
        return result
        
    except Exception as e:
        logger.error("❌ AI分析JD失败: %s", e, exc_info=True)
        print(f"❌ AI分析JD失败: {e}")
        return _fallback_analysis(jd_text, job_title, department)


def _fill_defaults(data: Dict[str, Any], job_title: str, department: Optional[str]) -> Dict[str, Any]:
    """填充默认值并规范化输出."""
    result = {
        "name": data.get("name") or job_title,
        "department": data.get("department") or department or "未知部门",
        "description": data.get("description") or f"{job_title}岗位能力要求",
        "tags": data.get("tags") or [],
        "dimensions": data.get("dimensions") or [],
        "analysis": data.get("analysis") or "AI分析完成"
    }
    
    # 验证维度权重
    dimensions = result["dimensions"]
    if dimensions:
        total_weight = sum(d.get("weight", 0) for d in dimensions)
        
        # 如果权重不是100，自动归一化
        if total_weight != 100 and total_weight > 0:
            for dim in dimensions:
                dim["weight"] = round(dim.get("weight", 0) * 100 / total_weight, 1)
    
    # 确保 tags 是列表
    if isinstance(result["tags"], str):
        result["tags"] = [t.strip() for t in result["tags"].split(",") if t.strip()]
    
    return result


def _fallback_analysis(
    text: str,
    job_title: str,
    department: Optional[str]
) -> Dict[str, Any]:
    """降级分析 - 使用规则化方法生成基础配置."""
    
    logger.info("使用降级分析方案: %s", job_title)
    
    # 基础能力维度模板
    default_dimensions = [
        {"name": "专业技能", "weight": 30, "description": f"{job_title}所需的核心专业技能"},
        {"name": "沟通协作", "weight": 20, "description": "团队协作与跨部门沟通能力"},
        {"name": "学习能力", "weight": 20, "description": "快速学习新知识和适应变化的能力"},
        {"name": "问题解决", "weight": 15, "description": "分析问题和解决问题的能力"},
        {"name": "责任心", "weight": 15, "description": "工作态度和责任担当"},
    ]
    
    # 简单的标签提取
    tags = _extract_tags(text)
    
    return {
        "name": job_title,
        "department": department or "未知部门",
        "description": f"{job_title}岗位，需要具备相关专业技能和良好的团队协作能力。",
        "tags": tags[:6],  # 最多6个标签
        "dimensions": default_dimensions,
        "analysis": "基于规则化分析生成的基础配置，建议根据实际情况调整维度权重。"
    }


def _extract_tags(text: str) -> List[str]:
    """从文本中提取标签."""
    
    # 常见技能和特质关键词
    keywords_map = {
        "沟通": "沟通能力",
        "协调": "协调能力",
        "管理": "管理能力",
        "分析": "分析能力",
        "创新": "创新思维",
        "团队": "团队协作",
        "执行": "执行力",
        "领导": "领导力",
        "策划": "策划能力",
        "设计": "设计能力",
        "开发": "开发能力",
        "运营": "运营能力",
        "销售": "销售能力",
        "客户": "客户导向",
        "数据": "数据分析",
        "项目": "项目管理",
        "产品": "产品思维",
        "技术": "技术能力",
        "业务": "业务理解",
        "抗压": "抗压能力",
    }
    
    tags = []
    for keyword, tag in keywords_map.items():
        if keyword in text and tag not in tags:
            tags.append(tag)
    
    return tags[:8]  # 最多8个标签


async def configure_job_dimensions(
    job_title: str,
    description: Optional[str] = None,
    existing_dimensions: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    AI智能配置岗位能力维度和权重.
    
    Args:
        job_title: 岗位名称
        description: 岗位描述（可选）
        existing_dimensions: 已有的维度列表（可选）
        
    Returns:
        配置好的维度列表和分析说明
    """
    has_existing = existing_dimensions and len(existing_dimensions) > 0
    
    # 构建提示词
    if has_existing:
        # 场景1：已有维度，智能分配权重
        dim_list = "\n".join([
            f"- {d.get('name', '未命名')}: {d.get('description', '无描述')}"
            for d in existing_dimensions
        ])
        prompt = f"""你是一位资深的人力资源专家，请为"{job_title}"岗位的能力维度智能分配权重。

岗位描述：{description or '无'}

已有的能力维度：
{dim_list}

请根据以下原则分配权重：
1. 权重总和必须等于100
2. 根据岗位特点，核心能力权重应该更高
3. 考虑能力维度之间的关联性和重要性差异
4. 权重分配要有区分度，避免平均分配

请输出JSON格式：
{{
  "dimensions": [
    {{"name": "维度名称", "weight": 权重数值, "description": "维度描述"}}
  ],
  "analysis": "权重分配的考量说明（50字以内）"
}}"""
    else:
        # 场景2：全新配置，生成维度和权重
        prompt = f"""你是一位资深的人力资源专家，请为"{job_title}"岗位设计能力模型。

岗位描述：{description or '无'}

请根据以下原则设计能力维度：
1. 设计4-6个核心能力维度
2. 权重总和必须等于100
3. 维度要具体、可衡量，避免过于抽象
4. 核心能力权重应该更高（25-35），次要能力适中（15-25），辅助能力较低（5-15）
5. 每个维度需要有清晰的描述

岗位类型参考：
- 技术类：专业技能、问题解决、学习能力、代码质量、团队协作
- 管理类：领导力、战略思维、团队管理、沟通协调、决策能力
- 销售类：客户开发、谈判能力、目标导向、抗压能力、市场洞察
- 行政类：执行力、细节把控、流程管理、沟通协调、服务意识
- 人事类：人才识别、沟通能力、制度建设、员工关系、战略思维

请输出JSON格式：
{{
  "dimensions": [
    {{"name": "维度名称", "weight": 权重数值, "description": "维度描述（20-40字）"}}
  ],
  "analysis": "能力模型设计说明（50字以内）"
}}"""

    messages = [
        {"role": "system", "content": "你是一位专业的人力资源顾问，擅长设计岗位能力模型。请直接输出JSON，不要包含其他内容。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        logger.info(f"🎯 AI配置能力维度: {job_title}")
        
        response = await call_portrait_model(
            messages=messages,
            level="pro",
            max_tokens=1024,
            temperature=0.3,
        )
        
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        data = parse_json_safely(content)
        
        # 验证和修正权重
        dimensions = data.get("dimensions", [])
        if dimensions:
            total = sum(d.get("weight", 0) for d in dimensions)
            if total != 100 and total > 0:
                # 归一化权重
                for d in dimensions:
                    d["weight"] = round(d.get("weight", 0) * 100 / total)
                # 处理舍入误差
                diff = 100 - sum(d["weight"] for d in dimensions)
                if diff != 0:
                    dimensions[0]["weight"] += diff
        
        logger.info(f"✅ AI配置完成: {job_title}, {len(dimensions)} 个维度")
        
        return {
            "dimensions": dimensions,
            "analysis": data.get("analysis", "AI配置完成")
        }
        
    except Exception as e:
        logger.error("❌ AI配置维度失败: %s", e, exc_info=True)
        # 降级处理
        return _fallback_dimension_config(job_title, existing_dimensions)


def _fallback_dimension_config(
    job_title: str,
    existing_dimensions: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """降级处理 - 规则化配置维度."""
    
    if existing_dimensions and len(existing_dimensions) > 0:
        # 已有维度，均分权重
        count = len(existing_dimensions)
        base_weight = 100 // count
        remainder = 100 % count
        
        dimensions = []
        for i, d in enumerate(existing_dimensions):
            dimensions.append({
                "name": d.get("name", f"维度{i+1}"),
                "weight": base_weight + (1 if i < remainder else 0),
                "description": d.get("description", "")
            })
        
        return {
            "dimensions": dimensions,
            "analysis": "基于规则分配权重，建议根据实际情况调整"
        }
    else:
        # 全新配置，使用默认模板
        default_dimensions = [
            {"name": "专业技能", "weight": 30, "description": f"{job_title}所需的核心专业能力"},
            {"name": "沟通协作", "weight": 25, "description": "跨部门沟通与团队协作能力"},
            {"name": "问题解决", "weight": 20, "description": "分析问题和解决问题的能力"},
            {"name": "学习能力", "weight": 15, "description": "快速学习新知识和适应变化的能力"},
            {"name": "责任心", "weight": 10, "description": "工作态度和责任担当"},
        ]
        
        return {
            "dimensions": default_dimensions,
            "analysis": "基于通用模板生成，建议根据岗位特点调整"
        }
