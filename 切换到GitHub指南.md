# 切换到GitHub国际版指南

> 从Gitee切换到GitHub的完整步骤  
> 版本: v1.0

---

## 📋 准备工作

### Step 1: 在GitHub创建仓库

1. **登录GitHub**
   - 访问 https://github.com
   - 使用您的账号登录（用户名: VernonFred）

2. **创建新仓库**
   - 点击右上角 "+" → "New repository"
   - 填写仓库信息：
     - Repository name: `HR-System` 或 `hr-evaluation`
     - Description: `HR人事系统 - AI智能招聘管理平台`
     - Public/Private: 根据需要选择
     - ⚠️ **不要**勾选 "Initialize with README"
     - ⚠️ **不要**添加 .gitignore 或 license
   - 点击 "Create repository"

3. **复制仓库地址**
   
   GitHub会显示仓库地址，有两种格式：
   
   **SSH格式（推荐）**:
   ```
   git@github.com:VernonFred/HR-System.git
   ```
   
   **HTTPS格式**:
   ```
   https://github.com/VernonFred/HR-System.git
   ```

---

## 🔄 方法一：使用自动化脚本（推荐）

```bash
cd /Users/Python项目/HR人事
./switch-to-github.sh
```

脚本会引导您：
1. 显示当前远程仓库
2. 输入GitHub仓库地址
3. 自动切换远程仓库
4. 询问是否立即推送

---

## 🔄 方法二：手动切换

```bash
# 1. 进入项目目录
cd /Users/Python项目/HR人事

# 2. 查看当前远程仓库
git remote -v

# 3. 移除Gitee远程仓库
git remote remove origin

# 4. 添加GitHub远程仓库（替换为您的实际地址）
git remote add origin git@github.com:VernonFred/HR-System.git
# 或使用HTTPS:
# git remote add origin https://github.com/VernonFred/HR-System.git

# 5. 确认远程仓库已更新
git remote -v

# 6. 推送所有代码到GitHub
git push -u origin master
```

---

## 🔑 配置GitHub认证

### 方式一：SSH密钥（推荐，一次配置永久使用）

**1. 检查是否已有SSH密钥**
```bash
ls -la ~/.ssh
```

**2. 如果没有，生成新密钥**
```bash
ssh-keygen -t ed25519 -C "wunaijiusi@gmail.com"
# 直接按回车使用默认位置
# 可以设置密码或直接按回车跳过
```

**3. 复制公钥**
```bash
cat ~/.ssh/id_ed25519.pub
# 复制输出的所有内容
```

**4. 添加到GitHub**
- 登录GitHub
- 点击头像 → Settings
- 左侧菜单点击 "SSH and GPG keys"
- 点击 "New SSH key"
- Title: `MacBook` 或任意名称
- Key: 粘贴刚才复制的公钥
- 点击 "Add SSH key"

**5. 测试连接**
```bash
ssh -T git@github.com
# 应该看到: Hi VernonFred! You've successfully authenticated...
```

---

### 方式二：Personal Access Token（HTTPS方式）

**1. 生成Token**
- 登录GitHub
- 点击头像 → Settings
- 左侧菜单底部 → Developer settings
- Personal access tokens → Tokens (classic)
- Generate new token → Generate new token (classic)
- Note: `HR-System-Mac`
- Expiration: 90 days 或 No expiration
- 勾选权限:
  - ✅ repo (完整权限)
  - ✅ workflow
- 点击 "Generate token"
- ⚠️ **立即复制Token**（只显示一次）

**2. 使用Token推送**
```bash
# 第一次推送时会要求输入密码
git push -u origin master

# Username: VernonFred
# Password: [粘贴您的Personal Access Token]
```

**3. 缓存凭证（避免每次输入）**
```bash
git config --global credential.helper store
```

---

## 🚀 推送代码到GitHub

### 正常推送（仓库为空）

```bash
git push -u origin master
```

### 处理冲突（仓库已有内容）

如果GitHub仓库已经有README或其他文件：

```bash
# 1. 先拉取GitHub上的内容
git pull origin master --allow-unrelated-histories

# 2. 如果有冲突，手动解决后提交
git add .
git commit -m "chore: 合并GitHub初始文件"

# 3. 推送
git push -u origin master
```

---

## ✅ 验证切换成功

**1. 检查远程仓库**
```bash
git remote -v
# 应该显示:
# origin  git@github.com:VernonFred/HR-System.git (fetch)
# origin  git@github.com:VernonFred/HR-System.git (push)
```

**2. 查看推送历史**
```bash
git log --oneline -5
```

**3. 在浏览器访问GitHub仓库**
```
https://github.com/VernonFred/HR-System
```

应该能看到您的所有代码和提交记录！

---

## 🔄 同时保留Gitee和GitHub

如果您想同时推送到两个平台：

```bash
# 1. 保留原来的Gitee作为备份
git remote rename origin gitee

# 2. 添加GitHub作为主仓库
git remote add origin git@github.com:VernonFred/HR-System.git

# 3. 查看所有远程仓库
git remote -v

# 4. 推送到GitHub
git push -u origin master

# 5. 同时推送到Gitee（备份）
git push gitee master
```

**一键推送到两个平台**:
```bash
# 创建别名
git config --global alias.push-all '!git push origin master && git push gitee master'

# 使用
git push-all
```

---

## ❌ 常见问题

### Q1: Permission denied (publickey)

**原因**: SSH密钥未配置或未添加到GitHub

**解决**:
```bash
# 1. 生成SSH密钥
ssh-keygen -t ed25519 -C "wunaijiusi@gmail.com"

# 2. 复制公钥
cat ~/.ssh/id_ed25519.pub

# 3. 添加到GitHub (见上面"配置GitHub认证"部分)

# 4. 测试连接
ssh -T git@github.com
```

---

### Q2: fatal: remote origin already exists

**原因**: 远程仓库名称冲突

**解决**:
```bash
# 先删除旧的
git remote remove origin

# 再添加新的
git remote add origin git@github.com:VernonFred/HR-System.git
```

---

### Q3: 推送被拒绝 (rejected)

**原因**: GitHub仓库有本地没有的提交

**解决**:
```bash
# 方案1: 拉取并合并
git pull origin master --allow-unrelated-histories
git push -u origin master

# 方案2: 强制推送（慎用）
git push -u origin master --force
```

---

### Q4: 网络连接问题

**解决**:
```bash
# 1. 使用HTTPS代替SSH
git remote set-url origin https://github.com/VernonFred/HR-System.git

# 2. 或配置代理（如果有VPN）
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy https://127.0.0.1:7890

# 3. 取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

## 📊 GitHub vs Gitee对比

| 特性 | GitHub | Gitee |
|------|--------|-------|
| 访问速度 | 国际网络 | 国内快速 |
| 知名度 | 全球最大 | 国内主流 |
| 免费私有仓库 | ✅ 无限 | ✅ 有限 |
| 协作功能 | ✅ 强大 | ✅ 良好 |
| Actions/CI | ✅ 免费额度 | ✅ 有限 |
| 推荐使用 | 国际合作 | 国内项目 |

---

## 🎯 推荐配置

**主仓库**: GitHub（国际版）
- 用于代码托管
- 开源分享
- 团队协作

**备份仓库**: Gitee（可选）
- 国内访问快
- 备份保险
- 演示方便

---

## 📝 更新提交约定

切换到GitHub后，提交流程不变，只是推送地址变了：

```bash
# 提交代码（不变）
git add .
git commit -m "feat: 新功能"

# 推送到GitHub（自动）
git push origin master
```

---

## ✨ 下一步

切换成功后：

1. ✅ 更新 `README.md`，添加GitHub仓库链接
2. ✅ 配置GitHub Actions（可选）
3. ✅ 设置仓库描述和主题
4. ✅ 继续开发Phase 1

---

**需要帮助？**
- GitHub文档: https://docs.github.com
- SSH配置问题: 查看上面的"配置GitHub认证"部分

**准备好切换了吗？运行命令开始：**
```bash
./switch-to-github.sh
```

