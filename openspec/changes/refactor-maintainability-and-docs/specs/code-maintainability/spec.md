## ADDED Requirements

### Requirement: 超大文件治理
项目 SHALL 对超过 800 行的前端和后端源码建立维护性审计清单，并优先拆分高频变更和高风险职责混合文件。

#### Scenario: 发现 P0 文件
- **WHEN** 源码文件达到 2500 行以上
- **THEN** 该文件 SHALL 进入 P0 拆分清单，并记录拆分建议

### Requirement: 兼容式重构
重构 SHALL 优先保持 API path、函数对外调用名、数据库字段和用户可见行为不变。

#### Scenario: 后端 service 拆分
- **WHEN** 统计实现移动到新模块
- **THEN** 原 `service.py` SHALL 保留兼容 wrapper 供路由继续调用
