## Purpose
沉淀 data model 领域的稳定业务规则，作为后续需求和重构的规格依据。

## Requirements

### Requirement: 核心数据表
系统 SHALL 使用 users、questionnaires、assessments、submissions、candidates、portrait_cache、job_profiles、profile_matches 等核心数据实体保存业务数据。

#### Scenario: 问卷提交保存
- **WHEN** 用户完成答题或测评
- **THEN** submissions SHALL 保存 assessment_id、questionnaire_id、提交状态、答案、得分和提交时间

### Requirement: JSON 字段兼容
系统 SHALL 兼容历史 JSON 字段以对象或字符串形式保存的情况。

#### Scenario: 读取历史提交答案
- **WHEN** submissions.answers 是 JSON 字符串
- **THEN** 后端 SHALL 解析为对象后参与统计和导出
