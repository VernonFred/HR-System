## Context

`QuestionnaireDetailDrawer.vue` 和 `backend/app/api/assessments/service.py` 同时承载 UI、统计、导出和业务规则，后续每个小需求都会增加回归面。现有 docs 已覆盖产品、AI、API、数据库、部署和维护，但缺少可执行的规格入口。

## Goals / Non-Goals

**Goals:**
- 将高频变更的统计/导出纯逻辑拆出，降低单文件复杂度。
- 保留现有行为和外部接口。
- 建立 OpenSpec 规格目录，用于后续需求提案和归档。

**Non-Goals:**
- 不一次性拆完所有 1000 行以上文件。
- 不改变数据库结构。
- 不重写问卷详情抽屉模板和样式体系。
- 不把真实服务器、密钥、Token 写入规范。

## Decisions

- 前端优先抽 pure utilities，而非拆模板组件，避免影响 DOM 导出和 ECharts 渲染。
- 后端保留 `service.py` wrapper，路由继续调用原函数名，降低 API 回归风险。
- OpenSpec 先沉淀稳定业务事实，再用 change 记录本次重构。
- `.trae/` 自动适配不是当前目标工具，保留 `.codex/` 适配。

## Risks / Trade-offs

- 工具函数拆分后需要构建验证防止类型导入遗漏。
- 后端统计逻辑迁移必须保留历史状态兼容和 JSON 字符串兼容。
- OpenSpec 首版是收束版规范，不替代详细 docs。
