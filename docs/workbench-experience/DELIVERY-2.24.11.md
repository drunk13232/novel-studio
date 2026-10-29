# Task & Review Reliability — 2.24.11 Local Preview

## 简体中文

本版复用现有创作指挥台、评审存储、TaskManager、写入锁和 SDK，不新增 AI 框架或数据格式。

- 作者接管保留未保存的文字、目标、计划与补充要求，表单启用后恢复候选区焦点。
- 新状态优先；较早读取晚到不能将候选或已结束任务退回旧状态。刷新在收到结果时检查当前本地编辑。
- 复核报告按创作记录与报告 ID 绑定；切换或关闭后，旧成功/失败回执均不会显示在新记录中。
- 报告可重新读取；失败说明与重试只针对已有本地文件，不触发模型。旧候选报告在本地或已保存编辑后明确标记为历史参考。
- 停止、暂停、终止核对当前执行身份，旧视图不能误取消新任务。
- Codex 连接检查只读登录/运行时状态，不再占用作者写入队列和工作区写入锁。来源、会话校验、单次探测保护和真正写入的锁均保留；异常后清除“检查中”，允许再次检查；更晚的已验证连接结果不会被旧探测失败覆盖。

### 验证口径

11 个新增报告/状态场景和 27 个相邻保存、交接、接管场景通过。受控连接检查保持等待时，真实本地候选保存已独立完成；这不是远端模型响应速度测试。后端相关 API 与探测安全测试 28 项通过、1 项跳过。阶段、报告内容、延迟与故障为合成测试输入，TaskManager、报告存储、API 和候选保存使用实际本地服务。没有新远端模型调用。

Windows 包的检查另记本地交付记录。构建、worker、静默安装和浏览器通过不等于原生窗口、实体中文输入法、系统 DPI、声音或远端 AI 通过。保持 Preview / PARTIAL，旧版与用户作品保留。此本地版本未自动发布 GitHub。

## English

This local Preview reuses the Director, review storage, TaskManager, SDK and author-write protections, without new dependencies or data formats.

Author takeover retains local edits and restores focus after controls are writable. Ordered, scoped reads prevent older records or reports from replacing newer state. Saved reports have visible loading/errors and GET-only retries, and retained reviews are labelled historical after candidate changes. Stop/pause/terminate verify execution identity. Read-only Codex health checks no longer hold author-write serialization or the workspace lease; origin, nonce, single-flight and actual-write guards remain. Unexpected probe failure releases the checking state for explicit retry.

Eleven new report/state scenarios and 27 adjacent browser scenarios passed. A held synthetic health response no longer prevents an actual local candidate save. Relevant backend API/probe checks passed 28 tests with one skip. Stages, report content and injected faults are controlled test inputs, not AI judgments. Real local storage, TaskManager and API paths are exercised; no new remote model call occurred.

Packaged-worker/silent-install/browser/build success does not establish native GUI, physical IME/DPI, voices or real-AI acceptance. This remains Preview / PARTIAL, preserves old releases and is not automatically published to GitHub.
