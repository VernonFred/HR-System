# QZ·TalentLens 生产环境部署包

## 文件说明

```
deploy_production/
├── backend/
│   ├── app/              # 后端代码
│   ├── .env              # 环境变量（含 API 密钥）
│   ├── .env.example      # 环境变量模板
│   └── requirements.txt  # Python 依赖
└── frontend/
    └── dist/             # 前端静态文件
```

## 首次启动

后端首次启动会自动：
- 创建 SQLite 数据库 (hr.db)
- 初始化 admin 用户（密码: admin123）
- 导入专业测评问卷（MBTI、DISC、EPQ）

## 默认账户

- 用户名: admin
- 密码: admin123

**请首次登录后立即修改密码！**
