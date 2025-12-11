#!/bin/bash
# 部署前检查脚本
echo "======================================"
echo "部署前检查开始..."
echo "======================================"
echo ""

# 1. 检查 Python 语法
echo "1️⃣ 检查 Python 语法..."
python3 check_syntax.py
if [ $? -ne 0 ]; then
    echo "❌ Python 语法检查失败！请修复后再部署"
    exit 1
fi
echo ""

# 2. 检查依赖
echo "2️⃣ 检查依赖..."
poetry check
if [ $? -ne 0 ]; then
    echo "⚠️  依赖检查有警告"
fi
echo ""

# 3. 尝试导入主模块
echo "3️⃣ 检查主模块..."
python3 -c "from app.main import app; print('✅ 主模块导入成功')"
if [ $? -ne 0 ]; then
    echo "❌ 主模块导入失败！"
    exit 1
fi
echo ""

# 4. 检查环境变量
echo "4️⃣ 检查环境变量..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在"
else
    echo "✅ .env 文件存在"
fi
echo ""

echo "======================================"
echo "✅ 所有检查通过！可以安全部署"
echo "======================================"

