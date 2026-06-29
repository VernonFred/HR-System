## Purpose
沉淀 statistics export 领域的稳定业务规则，作为后续需求和重构的规格依据。

## Requirements

### Requirement: 问卷统计展示
系统 SHALL 展示提交趋势、得分分布、题目分析和选项明细；题目分析 SHALL 支持分页和图表切换。

#### Scenario: 多选题统计
- **WHEN** 多选题一个提交人选择多个选项
- **THEN** total_answers SHALL 表示答题人数，total_selections SHALL 表示选择次数

### Requirement: 统计报告导出
系统 SHALL 支持将完整问卷统计导出为 PDF、PNG 和 Excel，导出内容不受当前页面分页限制。

#### Scenario: 文本题多页内容导出
- **WHEN** 文本题代表性回答超过页面分页数量
- **THEN** 导出文件 SHALL 包含全部文本汇总内容

### Requirement: 非匿名逐人答题明细
系统 SHALL 在 Excel 导出中提供逐人答题明细和选项人员明细；匿名问卷不得反推人员身份。

#### Scenario: 筛选某选项人员
- **WHEN** 管理员在 Excel 的“选项人员明细”筛选某题某选项
- **THEN** 非匿名数据 SHALL 显示对应提交人的姓名、手机号和提交时间；缺失身份信息 SHALL 留空或显示匿名
