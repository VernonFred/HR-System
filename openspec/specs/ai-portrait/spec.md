## Purpose
沉淀 ai portrait 领域的稳定业务规则，作为后续需求和重构的规格依据。

## Requirements

### Requirement: AI 画像生成
系统 SHALL 基于测评结果、简历数据和岗位画像生成候选人画像，包含综合评价、优势亮点、潜在风险和岗位匹配建议。

#### Scenario: 单模型画像生成
- **WHEN** 候选人完成专业测评并触发画像生成
- **THEN** 系统 SHALL 使用当前配置的单一 AI 模型生成差异化画像内容

### Requirement: 降级与透明提示
系统 SHALL 在 AI 调用失败时使用可解释的降级结果，并在界面或日志中保留失败原因。

#### Scenario: AI 请求失败
- **WHEN** AI 服务返回错误或超时
- **THEN** 系统 SHALL 不阻断页面基础展示，并 SHALL 提供可排查的错误信息
