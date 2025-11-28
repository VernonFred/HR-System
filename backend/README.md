# TalentLens 后端服务

智能人才洞察平台 - Flask API 后端

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（可选）：

```bash
# DeepSeek API 配置（AI 分析功能需要）
DEEPSEEK_API_KEY=your_api_key_here

# 管理员密码
ADMIN_PASSWORD=epq_admin_123
```

### 3. 启动服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动。

## 📡 API 接口

### 认证接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 管理员登录 |
| `/api/auth/logout` | POST | 退出登录 |
| `/api/auth/status` | GET | 检查登录状态 |

### AI 分析接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/ai/analyze` | POST | AI 智能分析候选人 |

**请求示例：**

```json
{
    "candidate": {
        "name": "张三",
        "position": "产品经理",
        "scores": { "E": 18, "N": 8, "P": 10, "L": 15 }
    },
    "type": "personality"  // personality | interview | development
}
```

### 简历解析接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/resume/upload` | POST | 上传并解析简历 |

**支持格式：** PDF, PNG, JPG, XLSX, XLS

### 健康检查

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 服务健康检查 |

## 🔑 获取 DeepSeek API Key

1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册账号并登录
3. 在控制台创建 API Key
4. 将 API Key 设置为环境变量 `DEEPSEEK_API_KEY`

## 📁 项目结构

```
backend/
├── app.py              # 主应用
├── config.py           # 配置文件
├── requirements.txt    # 依赖列表
├── uploads/            # 上传文件目录
└── README.md           # 说明文档
```

## 🔧 开发说明

### 添加新的分析类型

在 `app.py` 的 `build_analysis_prompt` 函数中添加新的 `analysis_type` 分支。

### 扩展简历解析

在 `parse_resume` 函数中添加对新文件格式的支持。

## 📝 注意事项

1. **AI 功能需要配置 API Key**：未配置时，AI 分析接口将返回错误
2. **图片 OCR 需要安装 Tesseract**：
   - macOS: `brew install tesseract tesseract-lang`
   - Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-chi-sim`
3. **生产环境建议**：
   - 使用 gunicorn 运行
   - 配置 HTTPS
   - 设置更复杂的密码

