## ADDED Requirements

### Requirement: 中文文档规范沉淀
项目 SHALL 将现有中文 Markdown 文档中的稳定业务规则提取为 OpenSpec capability specs。

#### Scenario: 提取部署规范
- **WHEN** 从部署文档提取服务器或环境变量说明
- **THEN** OpenSpec SHALL 使用占位符，不包含真实密钥、密码或 Token

### Requirement: OpenSpec 与 docs 并存
OpenSpec SHALL 作为需求和变更治理入口，现有 docs SHALL 保留为详细操作说明。

#### Scenario: 后续新增需求
- **WHEN** 新需求影响现有能力
- **THEN** 应先创建 OpenSpec change，再实施代码修改
