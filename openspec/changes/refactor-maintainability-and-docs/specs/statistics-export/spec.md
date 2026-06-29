## MODIFIED Requirements

### Requirement: 统计报告导出
系统 SHALL 支持将完整问卷统计导出为 PDF、PNG 和 Excel，导出内容不受当前页面分页限制；内部实现 MAY 拆分为独立工具或服务，但 SHALL 保持导出行为一致。

#### Scenario: Excel 逐人明细导出
- **WHEN** 管理员选择 Excel 导出
- **THEN** 文件 SHALL 包含提交明细、题目统计、答题明细和选项人员明细
