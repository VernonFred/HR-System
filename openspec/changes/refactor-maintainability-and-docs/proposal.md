## Why

当前问卷统计与导出链路集中在超大 Vue/CSS/Python 文件中，维护成本高；同时项目文档分散在多份中文 Markdown 中，缺少变更前可引用的统一规格。

## What Changes

- 拆分问卷详情抽屉中题型判断、提交导出、答题明细导出等纯函数。
- 拆分后端 assessments service 中统计与导出职责，保留原有对外函数名。
- 初始化 OpenSpec，并将现有中文文档收束为领域规格。
- 记录后续仍需拆分的大文件，避免本次一次性重构导致回归风险。

## Capabilities

### New Capabilities
- `code-maintainability`: 代码规模审计、关键文件拆分和后续拆分治理。
- `documentation-governance`: 中文 docs 到 OpenSpec 的规范化沉淀。

### Modified Capabilities
- `statistics-export`: 内部实现拆分，不改变用户可见导出能力。

## Impact

- 前端：问卷详情抽屉、问卷导出工具函数、题型判断工具函数。
- 后端：assessments 统计服务、答题明细导出服务、提交记录 Excel 导出服务。
- 文档：新增 `openspec/` 和 Codex OpenSpec 技能适配文件。
- 不新增数据库迁移，不改变 API path，不写入敏感凭据。
