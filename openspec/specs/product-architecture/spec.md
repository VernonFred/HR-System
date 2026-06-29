## Purpose
沉淀 product architecture 领域的稳定业务规则，作为后续需求和重构的规格依据。

## Requirements

### Requirement: 产品核心模块
系统 SHALL 围绕候选人画像、专业测评、问卷中心、岗位画像配置、人员管理和系统设置组织功能。

#### Scenario: HR 使用核心流程
- **WHEN** HR 创建测评或问卷并收集提交
- **THEN** 系统 SHALL 能在画像、提交记录和统计页面展示相应数据

### Requirement: 用户可见术语按业务类型区分
系统 SHALL 对专业测评使用“测评”文案，对普通调查问卷和 `purpose=survey` 使用“答题”文案。

#### Scenario: 调查问卷入口
- **WHEN** 用户打开调查问卷入口链接
- **THEN** 页面 SHALL 显示“开始答题”等调查问卷文案，而不是“开始测评”
