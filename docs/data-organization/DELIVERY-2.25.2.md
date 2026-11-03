# Novel Studio 2.25.2 — Data Organization Usability Preview

本轮仅优化现有 AI 资料整理的界面与操作，不增加新的 Agent、依赖、数据库或资料权限。

- 准备资料、编辑方案、检查确认、查看使用四阶段指引。
- 保存状态、保存、放弃、预览集中到固定操作栏；有修改时可保存后预览。实际创建待审资料仍需独立勾选确认，任何后续修改使旧确认失效。
- 分类与资料使用单项编辑器，切换时保留尚未保存的字段与数值；稳定键避免输入时重新挂载控件。
- 历史区域独立滚动、搜索和清空；来源筛选、已选来源标签和字符计数更清楚。
- 示例只填本地可编辑目标，不发送 AI 请求，不创建事实或数值。
- 模型控制在用户展开时初始化，关闭面板后保留同一方案内的配置。复杂模型与权限流程仍由原系统负责。
- 修复父工作台的嵌套滚动样式导致固定操作栏失效的问题。
- 使用现有主题变量、RTL 逻辑布局和 reduced-motion；新文案提供简中/英文。

## Verification boundaries

Scoped backend tests cover the unchanged domain protection/backup behavior. Real headless browser interactions cover this UI update and the existing adoption/history workflows. The final delivery report records packaged Windows startup, artifact hashes and protected-file verification separately. No new remote model, third-party API, native mouse/keyboard, IME or DPI acceptance is implied by this interface-only update.

The previous release remains available. Nothing is committed, pushed or published automatically. The proposal snapshot is still historical evidence, and live comparison views read original records. Canon, State, Knowledge and manuscript formats are unchanged.
