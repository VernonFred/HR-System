#!/bin/bash

# 切换远程仓库到GitHub
# 用途: 从Gitee切换到GitHub

echo "🔄 切换远程仓库到GitHub"
echo "================================"
echo ""

# 显示当前远程仓库
echo "📋 当前远程仓库:"
git remote -v
echo ""

# 提示输入GitHub仓库地址
echo "💡 请先在GitHub上创建仓库，然后输入仓库地址"
echo ""
echo "GitHub仓库地址格式："
echo "  HTTPS: https://github.com/你的用户名/仓库名.git"
echo "  SSH:   git@github.com:你的用户名/仓库名.git"
echo ""

read -p "请输入GitHub仓库地址: " github_url

if [ -z "$github_url" ]; then
    echo "❌ 错误: 仓库地址不能为空"
    exit 1
fi

# 删除旧的远程仓库
echo ""
echo "🗑️  移除Gitee远程仓库..."
git remote remove origin

# 添加GitHub远程仓库
echo "➕ 添加GitHub远程仓库..."
git remote add origin "$github_url"

# 确认更改
echo ""
echo "✅ 远程仓库已更新:"
git remote -v

echo ""
echo "🚀 推送代码到GitHub..."
read -p "是否立即推送所有代码到GitHub? (y/n): " confirm

if [ "$confirm" = "y" ]; then
    git push -u origin master
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 成功推送到GitHub!"
        echo ""
        echo "🌐 查看您的仓库:"
        echo "   ${github_url%.git}"
    else
        echo ""
        echo "❌ 推送失败!"
        echo ""
        echo "💡 可能的原因:"
        echo "  1. GitHub仓库不为空（已有README等文件）"
        echo "  2. 没有配置SSH密钥或HTTPS认证"
        echo "  3. 网络问题"
        echo ""
        echo "🔧 解决方案:"
        echo "  # 如果仓库不为空，先拉取再推送:"
        echo "  git pull origin master --allow-unrelated-histories"
        echo "  git push -u origin master"
        echo ""
        echo "  # 如果是认证问题，配置SSH或使用Personal Access Token"
    fi
else
    echo ""
    echo "⏸️  已跳过推送"
    echo ""
    echo "💡 稍后手动推送:"
    echo "   git push -u origin master"
fi

echo ""
echo "================================"
echo "✨ 完成!"

