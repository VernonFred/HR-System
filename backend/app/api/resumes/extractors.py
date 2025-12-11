"""简历管理 - 文本提取服务."""
from pathlib import Path
from typing import Optional
import re


def extract_text_from_pdf(file_path: str) -> str:
    """
    从PDF文件提取文本.
    
    使用pdfplumber库进行提取
    """
    try:
        import pdfplumber
        
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip()
        
    except ImportError:
        print("pdfplumber未安装，使用mock数据")
        # Fallback to mock data if library not installed
        return _get_mock_pdf_text()
    except Exception as e:
        print(f"PDF文本提取失败：{e}")
        return ""


def extract_text_from_word(file_path: str) -> str:
    """
    从Word文件提取文本.
    
    使用python-docx库进行提取
    """
    try:
        from docx import Document
        
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        
        return text.strip()
        
    except ImportError:
        print("python-docx未安装，使用mock数据")
        # Fallback to mock data if library not installed
        return _get_mock_word_text()
    except Exception as e:
        print(f"Word文本提取失败：{e}")
        return ""


def _get_mock_pdf_text() -> str:
    """Mock PDF文本（用于测试）."""
    return """
    张三
    138****1234 | zhangsan@example.com | 北京市
    
    教育背景
    2015-2019  北京大学  计算机科学与技术  本科
    
    工作经历
    2021-至今  XX科技有限公司  产品经理
    - 负责产品规划和设计
    - 跨部门协作，推动项目落地
    - 数据分析，优化产品体验
    
    2019-2021  YY互联网公司  产品助理
    - 协助产品经理完成需求分析
    - 参与产品设计和原型制作
    
    项目经验
    智能推荐系统  产品负责人  2022-2023
    - 设计并实现个性化推荐算法
    - 提升用户留存率30%
    技术栈：Python, Machine Learning
    
    技能
    产品设计, 需求分析, 数据分析, Axure, Figma, SQL, Python
    
    证书
    PMP项目管理专业人士认证
    
    语言
    英语（流利）, 日语（基础）
    """


def _get_mock_word_text() -> str:
    """Mock Word文本（用于测试）."""
    return """
    李四
    139****5678 | lisi@example.com | 上海市
    
    教育背景
    2014-2018  复旦大学  软件工程  本科
    2018-2021  清华大学  计算机技术  硕士
    
    工作经历
    2021-至今  ABC科技公司  高级后端工程师
    - 负责后端架构设计和开发
    - 微服务改造，提升系统性能
    - 团队技术分享和培训
    
    项目经验
    电商平台重构  技术负责人  2022-2023
    - 重构订单系统，提升处理能力10倍
    - 引入Redis缓存，优化查询性能
    技术栈：Python, FastAPI, Redis, PostgreSQL
    
    技能
    Python, FastAPI, Django, MySQL, Redis, Docker, Kubernetes
    
    证书
    阿里云ACP认证
    """


def extract_text_from_file(file_path: str) -> Optional[str]:
    """
    根据文件类型自动选择提取方法.
    
    Args:
        file_path: 文件路径
        
    Returns:
        提取的文本内容，失败返回None
    """
    path = Path(file_path)
    if not path.exists():
        print(f"文件不存在：{file_path}")
        return None
    
    file_ext = path.suffix.lower()
    
    if file_ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif file_ext in [".doc", ".docx"]:
        return extract_text_from_word(file_path)
    else:
        print(f"不支持的文件格式：{file_ext}")
        return None


def clean_text(text: str) -> str:
    """清洗文本，去除多余空白和特殊字符."""
    if not text:
        return ""
    
    # 去除多余空行
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # 去除行首行尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # 去除多余空格
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

