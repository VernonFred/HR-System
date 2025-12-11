#!/bin/bash

# HR 人事系统演示停止脚本

echo "🛑 停止 HR 人事系统"
echo "=================================="

# 从 PID 文件读取进程 ID
if [ -f /tmp/hr_backend.pid ]; then
    BACKEND_PID=$(cat /tmp/hr_backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "⏹️  停止后端服务 (PID: $BACKEND_PID)"
        kill $BACKEND_PID
    fi
    rm /tmp/hr_backend.pid
fi

if [ -f /tmp/hr_frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/hr_frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "⏹️  停止前端服务 (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID
    fi
    rm /tmp/hr_frontend.pid
fi

# 确保端口释放
if lsof -Pi :9000 -sTCP:LISTEN -t >/dev/null ; then
    echo "🔧 强制释放后端端口 9000"
    kill -9 $(lsof -t -i:9000)
fi

if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null ; then
    echo "🔧 强制释放前端端口 5173"
    kill -9 $(lsof -t -i:5173)
fi

echo "✅ 服务已停止"
echo "=================================="

