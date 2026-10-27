# Novel Studio 2.23.0 · Daily Reliability & Planning Preview

计划中心复用作者便笺 `metadata/studio/reading.json` 中的 todos 和 revision_tasks；新 schedule 字段可选，旧记录无需迁移。日期是作者工作的现实日历，进度由作者填写；它们不是故事日期或已发生事实，不自动运行 AI。

## 使用

- 完整导航 → 写作 → 计划中心，或正文快捷工具条 → 计划中心。
- 新建计划，设置开始/截止日期、关联章节、优先级、进度和最多 30 个子项。
- 今日与逾期、本周、月历、未安排、全部计划读取同一份待办。完成和归档保留原记录，旧待办编辑器也保留新增安排字段。
- 保存冲突保留输入，可读取最新记录比较并明确选择新基线；不会自动覆盖。
- 未完成事项只读汇总最近 50 条项目任务和待审修订；建立跟进计划不会重新执行任务。
- 变更影响先搜索人物/设定/章节，再查看现有关系与来源，支持打开来源和建立复查计划。它不扫描未绑定正文，也不把关联解释为因果。

## AI 与任务

任务历史及正文助手显示实际任务元数据，未报告的模型/参数保持未知。断线状态查询采用有限退避，联网恢复或手动刷新可重连，不能重放模型请求。历史筛选、详情、分页中的迟到响应不会覆盖新选择。

## 存储

设置 → 文件与存储 → 缓存维护。扫描后主动选择类别，二次确认；仅处理至少 48 小时未变化的固定目录缓存与所选作品缩略图。15 分钟预览过期；文件变化即要求重新扫描；构建与清理共用互斥标记。缩略图缺失沿用原图回退。清理不接受任意路径，不删除正文、原图、历史、依赖环境、备份或发行 ZIP。

缓存删除量按文件逻辑大小计算，不冒充实测释放空间。没有符合条件文件时是正常空状态。意外中断留下的构建互斥标记需人工核实，没有自动破锁操作。

## Verification

See DELIVERY.md after this run. Local tests, browser integration, native Windows and real AI are separate gates. No automatic paid/remote calls or author-work edits.

Project license and copyright remain owner decisions; this Preview does not grant a new open-source license.
