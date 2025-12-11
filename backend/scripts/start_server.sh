#!/bin/bash
# 后端服务器启动脚本
# 在启动服务器之前先检查Python语法

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

echo "=================================================="
echo "🔧 HR人事系统 - 后端服务器启动"
echo "=================================================="
echo

# 1. 语法检查
echo "📝 步骤 1/2: 检查Python语法..."
if poetry run python scripts/check_syntax.py; then
    echo
else
    echo
    echo "❌ 语法检查失败，请修复错误后重试"
    exit 1
fi

# 2. 启动服务器
echo "📝 步骤 2/2: 启动Uvicorn服务器..."
echo

PORT=${PORT:-9000}
HOST=${HOST:-0.0.0.0}

echo "🌐 服务器地址: http://${HOST}:${PORT}"
echo "📖 API文档: http://${HOST}:${PORT}/docs"
echo
echo "按 Ctrl+C 停止服务器"
echo "=================================================="
echo

poetry run uvicorn app.main:app --reload --host "$HOST" --port "$PORT"

