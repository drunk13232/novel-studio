# Novel Studio 2.24.23 — Verified Save Feedback Preview

本地 Preview / PARTIAL。未自动上传、提交或更新快捷方式。

## 保存反馈与实际结果

正文保存回执必须对应同一路径、提交文本、换行/BOM 和实际版本元数据。明确成功后，恢复副本清理或更新失败单独显示原因，不把它误报成正文写入失败。最新输入只有确实被写入相应恢复副本时才显示已保留，旧回执不能替较新输入背书。

回执无法读取、连接中断或服务端错误可能发生在实际写入之后。此时仅调用一次现有只读文件接口核对，不自动重发写入。完全匹配才确认该版本；不同版本保留编辑并提供比较，仍无法确认时暂停自动保存并显示未确认状态。统计仅通知现有视图重新读取，不制造保存事件、字数、时长或模型用量。

保存未确认或磁盘版本不同，即使撤销回旧缓存，也仍保留保存按钮和导航/退出保护。作者可明确选择手动保存本机恢复副本，再重新载入磁盘比较；该手动操作不会打开全局自动恢复、改变正文或写入 Canon。没有自动覆盖外部修改。

## 实际验证

47 个独立 headless 场景：18 个保存回执/格式/保护场景，12 个离开弹窗回归，15 个安全退出回归，2 个正文确认成功但恢复清理失败后仍能完成已授权离开/退出的组合场景。使用隔离合成项目、真实本地保存/恢复接口、磁盘字节核对；故障由明确响应注入产生，退出边界是记录/拒绝替身，不是原生关窗。

验证正常回执、清理失败、JSON 损坏、连接中断、写入后的服务端错误、不同/不可读取的磁盘版本、未确认后撤销与明确手动恢复、较新输入、CRLF、BOM、空文件及混合换行只读。所有非显式重试场景没有重放主写入；撤销后的明确保存退出被真实版本冲突拒绝，未触及模拟桌面边界。

章节读取期间原本显示加载区并卸载编辑器，本轮未将不可输入的加载状态误判为丢字，也未改动该路径。没有新增框架、Agent、依赖、数据库迁移、事件存储格式或桌面权限。

原生 Windows 窗口、实体中文输入法、系统 DPI、真实语音/云端 AI、物理断盘与长期性能未新增验收。既有全局 config.toml 差异及较早隔离服务退出异常仍未归因；不自动修改/回滚配置，不把当前检查当作历史根因修复。作品与旧版本保留，公开 Allowlist 仍为上次已发布版本。

## English

Confirmed manuscript writes and recovery maintenance have separate outcomes. A bounded read-only verification resolves ambiguous receipts only when the exact requested content, format and file metadata match; writes are not automatically replayed. Newer edits remain in the editor. Unconfirmed/conflicting state survives undo to an old cache and continues to protect navigation, unload and exit.

Authors can explicitly keep a local recovery snapshot before reloading for comparison without enabling automatic recovery. Statistics refreshes never create events or estimate writing time. No new dependency, format, migration, Agent or permission.

47 isolated headless browser flows passed. Faults and desktop boundaries are labelled controlled doubles; no native GUI, physical IME/DPI, voice or real-cloud-AI acceptance is claimed.
