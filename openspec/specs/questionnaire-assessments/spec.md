## Purpose
沉淀 questionnaire assessments 领域的稳定业务规则，作为后续需求和重构的规格依据。

## Requirements

### Requirement: 问卷链接分发
系统 SHALL 支持一个问卷生成多个分发链接，每个链接有独立有效期、匿名设置、重复提交设置和页面文案。

#### Scenario: 修改问卷内容
- **WHEN** 管理员修改问卷题目内容
- **THEN** 已有链接 SHALL 读取最新问卷内容，链接 URL 和访问码不变

### Requirement: 部门路由
系统 SHALL 支持入口问卷按用户选择的字段值路由到实际答题问卷，并把提交归属到实际答题问卷。

#### Scenario: 未命中路由映射
- **WHEN** 用户选择的字段值未配置映射
- **THEN** 系统 SHALL 回退到入口问卷

### Requirement: 匿名轻量防重复
匿名问卷 SHALL 使用浏览器本地匿名设备标识进行轻量防重复；该机制不承诺跨设备强身份识别。

#### Scenario: 同设备重复提交
- **WHEN** 匿名问卷已在同一浏览器设备完成提交
- **THEN** 系统 SHALL 阻止再次完成提交
