## 1. 当前变更收束

- [x] 1.1 移除答题明细导出 API fallback，避免静默导出缺少明细的 Excel。
- [x] 1.2 补齐题型别名映射。
- [x] 1.3 运行前端构建验证。

## 2. 关键文件拆分

- [x] 2.1 抽出前端题型判断工具。
- [x] 2.2 抽出前端提交导出与逐人答题明细组装工具。
- [x] 2.3 抽出后端问卷统计与答题明细导出服务。
- [x] 2.4 抽出后端提交记录 Excel 导出服务。

## 3. OpenSpec 规范化

- [x] 3.1 本地初始化 OpenSpec，关闭遥测。
- [x] 3.2 从中文 docs 提取领域规格。
- [x] 3.3 建立本次重构 change。
- [x] 3.4 运行 OpenSpec validate。

## 4. 验证与部署

- [x] 4.1 运行后端 pytest 指定套件。
- [x] 4.2 运行 `python -m compileall backend/app`。
- [x] 4.3 运行前端 `npm run build`。
- [x] 4.4 审查 diff，只提交本次相关文件。
- [ ] 4.5 推送 GitHub，构建并部署服务器，重启 `talentlens`。
