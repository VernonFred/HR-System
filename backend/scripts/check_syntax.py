#!/usr/bin/env python3
"""
后端代码语法检查脚本
在启动服务器之前运行，确保所有Python文件没有语法错误
"""
import sys
import os
import py_compile
import importlib.util
from pathlib import Path

def check_python_syntax(directory: str) -> tuple[bool, list[str]]:
    """
    检查指定目录下所有Python文件的语法
    
    Args:
        directory: 要检查的目录路径
        
    Returns:
        (是否全部通过, 错误列表)
    """
    errors = []
    checked_count = 0
    
    # 获取所有Python文件
    root_path = Path(directory)
    python_files = list(root_path.rglob("*.py"))
    
    print(f"🔍 检查 {len(python_files)} 个Python文件...")
    print("-" * 50)
    
    for py_file in python_files:
        # 跳过虚拟环境和缓存目录
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        checked_count += 1
        relative_path = py_file.relative_to(root_path)
        
        try:
            # 方法1: 使用py_compile检查语法
            py_compile.compile(str(py_file), doraise=True)
            
            # 方法2: 尝试加载模块（更严格的检查）
            spec = importlib.util.spec_from_file_location("module", py_file)
            if spec and spec.loader:
                # 只检查语法，不实际执行
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                compile(source, str(py_file), 'exec')
                
            print(f"  ✅ {relative_path}")
            
        except SyntaxError as e:
            error_msg = f"{relative_path}:{e.lineno}: {e.msg}"
            errors.append(error_msg)
            print(f"  ❌ {relative_path}")
            print(f"     └─ 第{e.lineno}行: {e.msg}")
            if e.text:
                print(f"     └─ {e.text.strip()}")
                
        except Exception as e:
            # 其他错误（如编码问题）
            error_msg = f"{relative_path}: {str(e)}"
            errors.append(error_msg)
            print(f"  ⚠️ {relative_path}: {str(e)}")
    
    print("-" * 50)
    print(f"📊 检查完成: {checked_count} 个文件")
    
    return len(errors) == 0, errors


def main():
    """主函数"""
    # 获取backend目录
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    app_dir = backend_dir / "app"
    
    if not app_dir.exists():
        print(f"❌ 错误: 找不到app目录: {app_dir}")
        sys.exit(1)
    
    print("=" * 50)
    print("🚀 后端代码语法检查")
    print("=" * 50)
    print()
    
    # 检查app目录
    success, errors = check_python_syntax(str(app_dir))
    
    print()
    
    if success:
        print("✅ 所有文件语法检查通过！")
        print("   可以安全启动服务器")
        sys.exit(0)
    else:
        print(f"❌ 发现 {len(errors)} 个语法错误:")
        for error in errors:
            print(f"   • {error}")
        print()
        print("⚠️ 请修复以上错误后再启动服务器")
        sys.exit(1)


if __name__ == "__main__":
    main()

