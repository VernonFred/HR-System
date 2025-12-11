"""
JD（岗位需求）AI解析器。
将JD文本解析为结构化的岗位信息。
"""
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def parse_jd_with_ai(jd_text: str) -> Dict[str, Any]:
    """
    使用AI解析JD文本，提取结构化信息。
    
    Args:
        jd_text: JD文本内容
    
    Returns:
        解析结果:
        {
            "name": "岗位名称",
            "department": "部门",
            "level": "职级",
            "description": "岗位描述",
            "key_abilities": [{"name": "能力名", "importance": "高/中/低"}],
            "personality_preferences": ["外向型", "高尽责性"],
            "experience_requirements": "3-5年",
            "education_requirements": "本科及以上"
        }
    """
    
    # TODO: 接入真实AI服务
    # 这里先返回mock数据，用于测试
    
    logger.info(f"解析JD文本（长度: {len(jd_text)}字符）")
    
    # Mock数据：根据JD内容关键词智能判断
    jd_lower = jd_text.lower()
    
    if "产品" in jd_text or "product" in jd_lower:
        return {
            "name": "产品经理",
            "department": "产品部",
            "level": "P5-P7",
            "description": "负责产品规划、需求分析、用户体验优化、跨部门协作，推动产品从0到1落地。需要具备强数据驱动思维和用户洞察能力。",
            "key_abilities": [
                {"name": "产品规划能力", "importance": "高"},
                {"name": "用户洞察力", "importance": "高"},
                {"name": "数据分析能力", "importance": "中"},
                {"name": "跨部门协作", "importance": "高"},
                {"name": "需求分析能力", "importance": "高"},
                {"name": "决策判断力", "importance": "中"},
                {"name": "项目推进能力", "importance": "高"},
                {"name": "创新思维", "importance": "中"},
            ],
            "personality_preferences": ["外向型", "高尽责性", "开放性高", "情绪稳定"],
            "experience_requirements": "3-5年产品经验",
            "education_requirements": "本科及以上学历",
        }
    
    elif "工程师" in jd_text or "developer" in jd_lower or "engineer" in jd_lower:
        if "实施" in jd_text or "implementation" in jd_lower:
            return {
                "name": "实施工程师",
                "department": "交付部",
                "level": "P3-P5",
                "description": "负责客户现场实施、技术支持、系统部署、问题排查和解决。需要良好的沟通能力和客户服务意识。",
                "key_abilities": [
                    {"name": "技术理解能力", "importance": "高"},
                    {"name": "问题解决能力", "importance": "高"},
                    {"name": "客户沟通能力", "importance": "高"},
                    {"name": "方案交付能力", "importance": "中"},
                    {"name": "文档编写能力", "importance": "中"},
                    {"name": "项目管理", "importance": "中"},
                    {"name": "应急响应能力", "importance": "高"},
                    {"name": "知识沉淀能力", "importance": "低"},
                ],
                "personality_preferences": ["外向型", "高尽责性", "亲和力强"],
                "experience_requirements": "1-3年实施或技术支持经验",
                "education_requirements": "大专及以上学历",
            }
        else:
            return {
                "name": "软件工程师",
                "department": "技术部",
                "level": "P4-P7",
                "description": "负责系统设计、编码实现、代码审查、性能优化、问题排查。需要扎实的编程基础和系统设计能力。",
                "key_abilities": [
                    {"name": "编码实现能力", "importance": "高"},
                    {"name": "系统设计能力", "importance": "高"},
                    {"name": "问题排查能力", "importance": "高"},
                    {"name": "代码质量意识", "importance": "中"},
                    {"name": "技术学习能力", "importance": "高"},
                    {"name": "团队协作", "importance": "中"},
                    {"name": "文档编写能力", "importance": "低"},
                    {"name": "性能优化能力", "importance": "中"},
                ],
                "personality_preferences": ["内向型", "高尽责性", "逻辑性强"],
                "experience_requirements": "2-5年软件开发经验",
                "education_requirements": "本科及以上学历，计算机相关专业优先",
            }
    
    elif "销售" in jd_text or "sales" in jd_lower:
        return {
            "name": "销售经理",
            "department": "销售部",
            "level": "M1-M3",
            "description": "负责客户开发、商务谈判、业绩达成、团队管理。需要强沟通能力和抗压能力。",
            "key_abilities": [
                {"name": "客户关系管理", "importance": "高"},
                {"name": "商务谈判能力", "importance": "高"},
                {"name": "业绩达成能力", "importance": "高"},
                {"name": "市场洞察力", "importance": "中"},
                {"name": "沟通表达能力", "importance": "高"},
                {"name": "抗压能力", "importance": "高"},
                {"name": "客户需求挖掘", "importance": "中"},
                {"name": "资源整合能力", "importance": "中"},
            ],
            "personality_preferences": ["外向型", "高进取心", "情绪稳定", "自驱力强"],
            "experience_requirements": "3年以上销售经验",
            "education_requirements": "大专及以上学历",
        }
    
    else:
        # 默认通用岗位
        return {
            "name": "待定岗位",
            "department": "AI解析的部门",
            "level": "待定",
            "description": "AI解析的岗位描述（基于JD内容）...",
            "key_abilities": [
                {"name": "沟通协作", "importance": "中"},
                {"name": "学习能力", "importance": "中"},
                {"name": "执行能力", "importance": "中"},
                {"name": "问题解决", "importance": "中"},
            ],
            "personality_preferences": ["待定"],
            "experience_requirements": "待定",
            "education_requirements": "待定",
        }

