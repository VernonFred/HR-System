## Purpose
沉淀 deployment operations 领域的稳定业务规则，作为后续需求和重构的规格依据。

## Requirements

### Requirement: 本地与生产部署
系统 SHALL 支持本地开发启动、前端 Vite 构建、后端 FastAPI/Gunicorn 服务和 Nginx 代理部署。

#### Scenario: 生产发布
- **WHEN** 发布前后端变更
- **THEN** 操作人员 SHALL 先构建前端 dist，再同步后端变更文件，最后重启后端服务并验证健康检查

### Requirement: 敏感信息保护
系统文档和规范 SHALL 使用占位符描述服务器密码、API Key、JWT Secret 和数据库凭据。

#### Scenario: 写入 OpenSpec
- **WHEN** 从运维文档提取部署规范
- **THEN** 输出内容 SHALL 不包含真实密钥、密码或 Token
