"""
JD文件文本提取器。
支持PDF、Word、TXT格式。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: str) -> str:
    """从PDF提取文本（使用pdfplumber）."""
    try:
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        full_text = "\n".join(text_parts)
        return full_text.strip()
        
    except ImportError:
        logger.warning("pdfplumber未安装，使用mock数据")
        return "【Mock】这是一个产品经理岗位的JD，需要具备产品规划、用户洞察、数据分析等能力..."
    except Exception as e:
        logger.error(f"PDF提取失败: {e}")
        raise


def extract_text_from_word(file_path: str) -> str:
    """从Word文档提取文本（使用python-docx）."""
    try:
        from docx import Document
        
        doc = Document(file_path)
        text_parts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text.strip())
        
        full_text = "\n".join(text_parts)
        return full_text.strip()
        
    except ImportError:
        logger.warning("python-docx未安装，使用mock数据")
        return "【Mock】这是一个软件工程师岗位的JD，需要具备编码能力、系统设计、问题排查等能力..."
    except Exception as e:
        logger.error(f"Word提取失败: {e}")
        raise


def extract_text_from_txt(file_path: str) -> str:
    """从TXT文件提取文本."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text.strip()
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                text = f.read()
            return text.strip()
        except Exception as e:
            logger.error(f"TXT提取失败: {e}")
            raise
    except Exception as e:
        logger.error(f"TXT提取失败: {e}")
        raise


def extract_jd_text(file_path: str) -> str:
    """
    根据文件后缀自动选择提取器。
    
    Args:
        file_path: 文件路径
    
    Returns:
        提取的文本内容
    """
    suffix = Path(file_path).suffix.lower()
    
    if suffix == '.pdf':
        return extract_text_from_pdf(file_path)
    elif suffix in ['.doc', '.docx']:
        return extract_text_from_word(file_path)
    elif suffix == '.txt':
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")

