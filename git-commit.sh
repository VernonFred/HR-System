#!/bin/bash

# HR人事系统 - Git提交脚本
# 用途: 快速提交代码到GitHub

echo "🚀 HR人事系统 - Git提交助手"
echo "================================"
echo ""

# 检查是否在正确的目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

echo "📋 步骤 1/5: 检查当前状态..."
echo "--------------------------------"
git status
echo ""

echo "🧹 步骤 2/5: 清理旧文件记录..."
echo "--------------------------------"
git add -u
echo "✅ 旧文件记录已清理"
echo ""

echo "➕ 步骤 3/5: 添加核心文件..."
echo "--------------------------------"

# 后端核心
git add backend/app/
git add backend/alembic/
git add backend/pyproject.toml
git add backend/poetry.lock
git add backend/.env.example
git add backend/alembic.ini
git add backend/.flake8
git add backend/pre_deploy_check.sh

# 前端
git add frontend/

# 文档
git add docs/

# 配置和脚本
git add docker-compose.yml
git add start_for_demo.sh
git add stop_demo.sh
git add 演示启动指南.md
git add .gitignore
git add 提交指南.md

echo "✅ 核心文件已添加"
echo ""

echo "📊 步骤 4/5: 查看将要提交的文件..."
echo "--------------------------------"
git status
echo ""

echo "💡 提示: 确认以下内容"
echo "  ✅ 已添加: backend/app/, frontend/, docs/"
echo "  ❌ 未添加: .env, hr.db, uploads/, test_*.py"
echo ""

read -p "❓ 确认提交这些文件? (y/n): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "❌ 取消提交"
    exit 0
fi

echo ""
echo "💾 步骤 5/5: 提交代码..."
echo "--------------------------------"

git commit -m "feat: HR人事系统核心功能完成

主要功能:
- ✅ 候选人管理 (增删改查、Excel导入)
- ✅ 测评管理 (创建、分发、结果查看)
- ✅ 人员画像 (AI分析、多测评交叉验证)
- ✅ 岗位画像 (AI辅助配置)
- ✅ 分发链接 (二维码、批量操作)
- ✅ 用户管理 (权限控制)

技术实现:
- 后端: Python 3.9+ / FastAPI / SQLModel / SQLAlchemy
- 前端: Vue 3 / TypeScript / Vite / Element Plus
- 数据库: SQLite (支持迁移到MySQL)
- AI集成: Claude API (支持多模型)

文档完善:
- 📖 产品功能文档
- 📖 API接口文档
- 📖 数据库设计文档
- 📖 部署指南
- 📖 使用手册

Phase 1 UI改造规划:
- 📋 详细实施计划
- 🎨 前端设计方案
- 🚀 AI功能增强规划"

if [ $? -eq 0 ]; then
    echo "✅ 提交成功!"
    echo ""
    
    echo "🚀 开始推送到GitHub..."
    echo "--------------------------------"
    
    # 检查是否有远程仓库
    if git remote | grep -q "origin"; then
        git push origin master
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 推送成功!"
            echo ""
            echo "📊 提交统计:"
            git log --oneline -1
            echo ""
            echo "🌐 查看GitHub仓库:"
            git remote get-url origin
        else
            echo ""
            echo "❌ 推送失败!"
            echo ""
            echo "💡 可能的原因:"
            echo "  1. 网络连接问题"
            echo "  2. 权限不足 (需要配置SSH或HTTPS认证)"
            echo "  3. 远程仓库有更新 (需要先 git pull)"
            echo ""
            echo "🔧 尝试手动推送:"
            echo "  git pull origin master --rebase"
            echo "  git push origin master"
        fi
    else
        echo ""
        echo "⚠️  未配置远程仓库"
        echo ""
        echo "💡 配置方法:"
        echo "  git remote add origin https://github.com/你的用户名/仓库名.git"
        echo "  git push -u origin master"
    fi
else
    echo "❌ 提交失败!"
    echo "请检查错误信息并重试"
fi

echo ""
echo "================================"
echo "✨ 完成!"

