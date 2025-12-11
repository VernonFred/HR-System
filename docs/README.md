# QZ·TalentLens 文档中心

> **系统名称**: QZ·TalentLens - 人员初步画像智能工具  
> **版本**: v1.0  
> **更新日期**: 2025年12月8日

---

## 📚 文档索引

### 核心文档

| 序号 | 文档名称 | 说明 | 适用对象 |
|------|----------|------|----------|
| 01 | [产品功能架构文档](./01_产品功能架构文档.md) | 系统功能模块、架构设计、数据流 | 产品、开发 |
| 02 | [产品使用指南](./02_产品使用指南.md) | 系统操作指南、功能使用说明 | HR、管理员 |
| 03 | [大模型架构文档](./03_大模型架构文档.md) | AI 模型配置、智能降级策略 | 开发、运维 |
| 04 | [部署交付文档](./04_部署交付文档.md) | 服务器部署、环境配置 | 运维、开发 |
| 05 | [后续维护文档](./05_后续维护文档.md) | 日常维护、故障处理 | 运维 |
| 06 | [API接口文档](./06_API接口文档.md) | 后端 API 接口详细说明 | 开发 |
| 07 | [数据库表文档](./07_数据库表文档.md) | 数据库表结构、关系说明 | 开发 |
| 08 | [依赖安装文档](./08_依赖安装文档.md) | 环境依赖、安装步骤 | 开发、运维 |

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 检查环境
python3 --version  # 需要 3.10+
node --version     # 需要 18+
```

### 2. 安装依赖

```bash
# 后端
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 3. 启动服务

```bash
# 后端 (终端1)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 9000

# 前端 (终端2)
cd frontend
npm run dev
```

### 4. 访问系统

- 前端: http://localhost:5173
- 后端 API: http://localhost:9000
- API 文档: http://localhost:9000/docs
- 默认账号: admin / admin123

---

## 📋 系统功能

| 模块 | 功能 |
|------|------|
| 人员画像 | 候选人综合画像展示 |
| 岗位画像配置 | AI 辅助岗位能力配置 |
| 专业测评 | MBTI/DISC/EPQ 测评管理 |
| 问卷中心 | 自定义问卷创建和管理 |
| 人员管理 | 人员数据统计和管理 |
| 系统设置 | 账户安全、AI 配置 |

---

## 🔧 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Pinia |
| 后端 | FastAPI + SQLModel + Pydantic |
| AI | ModelScope API (Qwen) |
| 数据库 | SQLite / PostgreSQL |

---

## 📞 技术支持

如有问题，请查阅相关文档或联系技术支持。


