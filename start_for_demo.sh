#!/bin/bash

# HR 人事系统演示启动脚本
# 用于在局域网内让其他人访问您的本地系统

echo "🚀 启动 HR 人事系统（演示模式）"
echo "=================================="

# 获取本机 IP
IP=$(ipconfig getifaddr en0)
if [ -z "$IP" ]; then
    IP=$(ipconfig getifaddr en1)
fi

if [ -z "$IP" ]; then
    echo "❌ 无法获取本机 IP 地址"
    echo "请手动检查网络连接"
    exit 1
fi

echo "📍 您的 IP 地址: $IP"
echo ""

# 检查后端是否在运行
if lsof -Pi :9000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 9000 已被占用，正在停止..."
    kill $(lsof -t -i:9000)
    sleep 2
fi

# 检查前端是否在运行
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 5173 已被占用，正在停止..."
    kill $(lsof -t -i:5173)
    sleep 2
fi

echo "🔧 启动后端服务..."
cd "$(dirname "$0")/backend"
export PATH="$HOME/Library/Python/3.12/bin:$PATH"

# 后台启动后端
nohup poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 9000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!

echo "✅ 后端已启动 (PID: $BACKEND_PID)"
echo "   日志: logs/backend.log"

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 5

# 检查后端是否成功启动
if curl -s http://localhost:9000/health > /dev/null; then
    echo "✅ 后端健康检查通过"
else
    echo "⚠️  后端可能未正常启动，请检查日志"
fi

echo ""
echo "🔧 启动前端服务..."
cd "$(dirname "$0")/frontend"

# 后台启动前端
nohup npm run dev -- --host > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "✅ 前端已启动 (PID: $FRONTEND_PID)"
echo "   日志: logs/frontend.log"

# 等待前端启动
echo "⏳ 等待前端启动..."
sleep 8

echo ""
echo "=================================="
echo "✅ 系统启动完成！"
echo ""
echo "📱 HR 部门访问地址:"
echo "   http://$IP:5173"
echo ""
echo "🔗 后端 API 地址:"
echo "   http://$IP:9000"
echo ""
echo "💡 提示:"
echo "   1. 请将上面的地址发送给 HR 部门"
echo "   2. 确保您的电脑保持开机状态"
echo "   3. 如果无法访问，请检查防火墙设置"
echo ""
echo "🛑 停止服务:"
echo "   运行: ./stop_demo.sh"
echo ""
echo "📊 查看日志:"
echo "   后端: tail -f logs/backend.log"
echo "   前端: tail -f logs/frontend.log"
echo "=================================="

# 保存 PID 以便后续停止
echo $BACKEND_PID > /tmp/hr_backend.pid
echo $FRONTEND_PID > /tmp/hr_frontend.pid

