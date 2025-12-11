# QZ·TalentLens API 接口文档

> **版本**: v1.0  
> **更新日期**: 2025年12月8日  
> **API 基础路径**: `http://localhost:9000`

---

## 一、概述

### 1.1 认证方式

系统使用 JWT (JSON Web Token) 进行身份认证。

**请求头格式**:
```
Authorization: Bearer <access_token>
```

### 1.2 响应格式

所有 API 响应均为 JSON 格式。

**成功响应**:
```json
{
  "data": { ... },
  "message": "success"
}
```

**错误响应**:
```json
{
  "detail": "错误描述"
}
```

### 1.3 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 二、认证接口

### 2.1 用户登录

**POST** `/auth/login`

**请求体**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "admin"
}
```

### 2.2 用户注册

**POST** `/auth/register`

**请求体**:
```json
{
  "username": "newuser",
  "password": "password123"
}
```

**响应**: 同登录响应

### 2.3 刷新 Token

**POST** `/auth/refresh`

**请求体**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**响应**: 同登录响应

### 2.4 修改密码

**POST** `/auth/change-password`

**请求头**: 需要认证

**请求体**:
```json
{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

**响应**:
```json
{
  "message": "密码修改成功"
}
```

### 2.5 修改用户名

**POST** `/api/auth/update-username`

**请求头**: 需要认证

**请求体**:
```json
{
  "username": "new_username"
}
```

**响应**:
```json
{
  "message": "用户名更新成功",
  "username": "new_username"
}
```

---

## 三、候选人接口

### 3.1 获取候选人列表

**GET** `/api/candidates`

**请求头**: 需要认证

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |
| search | string | 否 | 搜索关键词 |

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "name": "张三",
      "phone": "13800138000",
      "position": "产品经理",
      "created_at": "2025-12-08T10:00:00",
      "submission_count": 3,
      "last_submission_at": "2025-12-08T15:30:00"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 3.2 获取单个候选人

**GET** `/api/candidates/{candidate_id}`

**请求头**: 需要认证

**响应**:
```json
{
  "id": 1,
  "name": "张三",
  "phone": "13800138000",
  "position": "产品经理",
  "created_at": "2025-12-08T10:00:00",
  "submissions": [
    {
      "id": 1,
      "questionnaire_name": "MBTI 性格测试",
      "submitted_at": "2025-12-08T15:30:00",
      "score": 85
    }
  ]
}
```

### 3.3 删除候选人

**DELETE** `/api/candidates/{candidate_id}`

**请求头**: 需要认证

**响应**:
```json
{
  "message": "删除成功",
  "id": 1
}
```

### 3.4 获取候选人画像

**GET** `/api/candidates/{candidate_id}/profile`

**请求头**: 需要认证

**响应**:
```json
{
  "candidate": {
    "id": 1,
    "name": "张三",
    "phone": "13800138000",
    "position": "产品经理"
  },
  "assessments": {
    "mbti": {
      "type": "INTJ",
      "scores": { "E": 30, "I": 70, ... }
    },
    "disc": {
      "dominant": "D",
      "scores": { "D": 80, "I": 60, ... }
    }
  },
  "ai_analysis": {
    "summary": "综合分析...",
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["待发展项1"]
  }
}
```

### 3.5 获取候选人问卷提交

**GET** `/api/candidates/{candidate_id}/survey-submissions`

**请求头**: 需要认证

**响应**:
```json
{
  "submissions": [
    {
      "id": 1,
      "questionnaire_name": "员工满意度调查",
      "submitted_at": "2025-12-08T15:30:00",
      "answers": [
        {
          "question": "您对工作环境满意吗？",
          "answer": "满意",
          "score": 4
        }
      ]
    }
  ]
}
```

---

## 四、测评接口

### 4.1 获取问卷列表

**GET** `/api/assessments/questionnaires`

**请求头**: 需要认证

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| category | string | 否 | 分类: professional/scored/survey |

**响应**:
```json
[
  {
    "id": 1,
    "code": "mbti",
    "name": "MBTI 性格测试",
    "description": "...",
    "category": "professional",
    "question_count": 93,
    "is_active": true
  }
]
```

### 4.2 获取问卷详情

**GET** `/api/assessments/questionnaires/{questionnaire_id}`

**请求头**: 需要认证

**响应**:
```json
{
  "id": 1,
  "code": "mbti",
  "name": "MBTI 性格测试",
  "description": "...",
  "questions": [
    {
      "id": 1,
      "text": "在社交场合中，你更倾向于...",
      "type": "single",
      "options": [
        {"text": "主动与人交流", "dimension": "E"},
        {"text": "等待他人接近", "dimension": "I"}
      ]
    }
  ]
}
```

### 4.3 创建问卷

**POST** `/api/assessments/questionnaires`

**请求头**: 需要认证

**请求体**:
```json
{
  "name": "新问卷",
  "description": "问卷描述",
  "category": "survey",
  "questions": [
    {
      "text": "问题1",
      "type": "single",
      "options": [
        {"text": "选项A", "score": 1},
        {"text": "选项B", "score": 2}
      ]
    }
  ]
}
```

**响应**:
```json
{
  "id": 10,
  "code": "survey_20251208",
  "name": "新问卷",
  "message": "创建成功"
}
```

### 4.4 更新问卷

**PUT** `/api/assessments/questionnaires/{questionnaire_id}`

**请求头**: 需要认证

**请求体**: 同创建问卷

**响应**:
```json
{
  "id": 10,
  "message": "更新成功"
}
```

### 4.5 删除问卷

**DELETE** `/api/assessments/questionnaires/{questionnaire_id}`

**请求头**: 需要认证

**响应**:
```json
{
  "message": "删除成功"
}
```

### 4.6 导入问卷

**POST** `/api/assessments/questionnaires/import`

**请求头**: 需要认证

**请求体**: `multipart/form-data`
| 字段 | 类型 | 说明 |
|------|------|------|
| file | file | JSON/Excel/Word 文件 |

**响应**:
```json
{
  "id": 11,
  "name": "导入的问卷",
  "question_count": 20,
  "message": "导入成功"
}
```

### 4.7 获取提交记录

**GET** `/api/assessments/submissions`

**请求头**: 需要认证

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| questionnaire_id | int | 否 | 问卷 ID |
| category | string | 否 | 分类 |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "candidate_name": "张三",
      "candidate_phone": "13800138000",
      "questionnaire_name": "MBTI 性格测试",
      "submitted_at": "2025-12-08T15:30:00",
      "score": 85,
      "result_type": "INTJ"
    }
  ],
  "total": 50
}
```

### 4.8 删除提交记录

**DELETE** `/api/assessments/submissions/{submission_id}`

**请求头**: 需要认证

**响应**:
```json
{
  "message": "删除成功"
}
```

---

## 五、公开测评接口

> 这些接口不需要认证，供候选人填写测评使用

### 5.1 获取测评信息

**GET** `/api/public/assessment/{code}`

**响应**:
```json
{
  "code": "mbti",
  "name": "MBTI 性格测试",
  "description": "...",
  "estimated_time": "15分钟",
  "question_count": 93,
  "form_fields": ["name", "phone", "position"]
}
```

### 5.2 获取测评题目

**GET** `/api/public/assessment/{code}/questions`

**响应**:
```json
{
  "questions": [
    {
      "id": 1,
      "text": "在社交场合中，你更倾向于...",
      "type": "single",
      "options": [
        {"id": "a", "text": "主动与人交流"},
        {"id": "b", "text": "等待他人接近"}
      ]
    }
  ]
}
```

### 5.3 提交测评答案

**POST** `/api/public/assessment/{code}/submit`

**请求体**:
```json
{
  "name": "张三",
  "phone": "13800138000",
  "position": "产品经理",
  "answers": [
    {"question_id": 1, "answer": "a"},
    {"question_id": 2, "answer": "b"}
  ]
}
```

**响应**:
```json
{
  "submission_id": 100,
  "result": {
    "type": "INTJ",
    "description": "建筑师型人格...",
    "scores": { "E": 30, "I": 70, ... }
  },
  "message": "提交成功"
}
```

---

## 六、岗位画像接口

### 6.1 获取岗位画像列表

**GET** `/api/job-profiles`

**请求头**: 需要认证

**响应**:
```json
[
  {
    "id": 1,
    "name": "产品经理",
    "department": "产品部",
    "description": "...",
    "dimensions": [
      {"name": "产品规划", "weight": 25},
      {"name": "用户洞察", "weight": 20}
    ]
  }
]
```

### 6.2 创建岗位画像

**POST** `/api/job-profiles`

**请求头**: 需要认证

**请求体**:
```json
{
  "name": "产品经理",
  "department": "产品部",
  "description": "负责产品规划...",
  "dimensions": [
    {"name": "产品规划", "weight": 25, "description": "..."},
    {"name": "用户洞察", "weight": 20, "description": "..."}
  ]
}
```

**响应**:
```json
{
  "id": 1,
  "message": "创建成功"
}
```

### 6.3 AI 分析简历

**POST** `/api/job-profiles/analyze-resume`

**请求头**: 需要认证

**请求体**: `multipart/form-data`
| 字段 | 类型 | 说明 |
|------|------|------|
| file | file | PDF/Word 简历文件 |

**响应**:
```json
{
  "dimensions": [
    {"name": "项目管理", "weight": 25, "description": "..."},
    {"name": "技术能力", "weight": 20, "description": "..."}
  ],
  "analysis": "AI 分析说明..."
}
```

### 6.4 AI 分析 JD

**POST** `/api/job-profiles/analyze-jd`

**请求头**: 需要认证

**请求体**:
```json
{
  "jd_text": "岗位职责：\n1. 负责产品规划..."
}
```

**响应**: 同简历分析

### 6.5 人岗匹配

**POST** `/api/job-profiles/{profile_id}/match`

**请求头**: 需要认证

**响应**:
```json
{
  "matches": [
    {
      "candidate_id": 1,
      "candidate_name": "张三",
      "match_score": 85,
      "dimension_scores": {
        "产品规划": 90,
        "用户洞察": 80
      }
    }
  ]
}
```

---

## 七、AI 接口

### 7.1 获取 AI 路由状态

**GET** `/api/ai/router-status`

**请求头**: 需要认证

**响应**:
```json
{
  "available": true,
  "api_key_status": {
    "valid": true,
    "days_remaining": 25,
    "warning": null
  },
  "models": {
    "pro": {"status": "available", "model_id": "Qwen/Qwen2.5-32B-Instruct"},
    "normal": {"status": "available", "model_id": "Qwen/Qwen2.5-7B-Instruct"},
    "expert": {"status": "available", "model_id": "deepseek-ai/DeepSeek-R1-0528"}
  }
}
```

### 7.2 AI 一键配置维度

**POST** `/api/ai/generate-dimensions`

**请求头**: 需要认证

**请求体**:
```json
{
  "job_title": "产品经理",
  "description": "负责产品规划..."
}
```

**响应**:
```json
{
  "dimensions": [
    {"name": "产品规划", "weight": 25, "description": "..."},
    {"name": "用户洞察", "weight": 20, "description": "..."}
  ],
  "analysis": "AI 分析说明..."
}
```

---

## 八、系统设置接口

### 8.1 更新 API Token

**POST** `/api/settings/update-token`

**请求头**: 需要认证

**请求体**:
```json
{
  "api_key": "new_api_key",
  "expires": "2026-01-06"
}
```

**响应**:
```json
{
  "message": "Token 更新成功"
}
```

---

## 九、统计分析接口

### 9.1 获取分析概览

**GET** `/analytics/summary`

**请求头**: 需要认证

**响应**:
```json
{
  "total_candidates": 100,
  "total_submissions": 250,
  "completion_rate": 0.85,
  "recent_submissions": [
    {
      "date": "2025-12-08",
      "count": 15
    }
  ]
}
```

---

## 十、系统接口

### 10.1 健康检查

**GET** `/health`

**响应**:
```json
{
  "status": "healthy",
  "database": "connected",
  "ai": "available"
}
```

### 10.2 清除所有数据（管理员）

**DELETE** `/api/admin/clear-all-data`

**请求头**: 需要认证（管理员）

**响应**:
```json
{
  "message": "数据清除成功",
  "deleted": {
    "candidates": 100,
    "submissions": 250
  }
}
```

---

## 附录

### A. 错误码说明

| 错误码 | 说明 |
|--------|------|
| INVALID_CREDENTIALS | 用户名或密码错误 |
| TOKEN_EXPIRED | Token 已过期 |
| INVALID_TOKEN | Token 无效 |
| PERMISSION_DENIED | 无权限 |
| NOT_FOUND | 资源不存在 |
| VALIDATION_ERROR | 参数验证失败 |

### B. 数据类型说明

| 类型 | 说明 |
|------|------|
| datetime | ISO 8601 格式，如 `2025-12-08T15:30:00` |
| phone | 11 位手机号 |
| score | 0-100 整数 |

### C. 相关文档

- [产品功能架构](./01_产品功能架构文档.md)
- [数据库表文档](./07_数据库表文档.md)
- [大模型架构文档](./03_大模型架构文档.md)

