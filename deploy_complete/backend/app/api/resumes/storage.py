"""简历管理 - 文件存储服务."""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException


# 配置
UPLOAD_DIR = Path("uploads/resumes")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}


def ensure_upload_dir():
    """确保上传目录存在."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_candidate_dir(candidate_id: int) -> Path:
    """获取候选人的简历目录."""
    candidate_dir = UPLOAD_DIR / str(candidate_id)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    return candidate_dir


def validate_file(file: UploadFile) -> None:
    """验证上传的文件."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    # 检查文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式：{', '.join(ALLOWED_EXTENSIONS)}"
        )


async def save_resume_file(
    candidate_id: int,
    file: UploadFile
) -> Tuple[str, str, int]:
    """
    保存简历文件.
    
    Returns:
        (file_path, original_name, file_size)
    """
    ensure_upload_dir()
    validate_file(file)
    
    # 生成文件名：{candidate_id}_{timestamp}_{original_name}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = file.filename or "resume"
    file_ext = Path(original_name).suffix
    safe_name = f"{candidate_id}_{timestamp}{file_ext}"
    
    # 获取候选人目录
    candidate_dir = get_candidate_dir(candidate_id)
    file_path = candidate_dir / safe_name
    
    # 保存文件
    file_size = 0
    try:
        with open(file_path, "wb") as f:
            # 分块读取，避免内存占用过大
            chunk_size = 1024 * 1024  # 1MB
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                
                # 检查文件大小
                if file_size > MAX_FILE_SIZE:
                    # 删除已写入的文件
                    f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件大小超过限制（最大{MAX_FILE_SIZE / 1024 / 1024}MB）"
                    )
                
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        # 清理失败的文件
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")
    
    # 返回相对路径（使用字符串路径，避免路径计算问题）
    relative_path = str(file_path)
    return relative_path, original_name, file_size


def delete_resume_file(file_path: str) -> bool:
    """删除简历文件."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            
            # 如果候选人目录为空，删除目录
            parent_dir = path.parent
            if parent_dir.exists() and not any(parent_dir.iterdir()):
                parent_dir.rmdir()
            
            return True
        return False
    except Exception as e:
        print(f"删除文件失败：{e}")
        return False


def get_resume_file_path(file_path: str) -> Optional[Path]:
    """获取简历文件的完整路径."""
    path = Path(file_path)
    if path.exists():
        return path
    return None


def get_file_size(file_path: str) -> int:
    """获取文件大小（字节）."""
    try:
        return Path(file_path).stat().st_size
    except Exception:
        return 0

