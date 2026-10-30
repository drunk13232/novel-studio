# Novel Studio 2.24.25 — Recovery Progress Preview

本地 Preview / PARTIAL。旧本地 2.24.24、公开 2.24.23 与 Public Allowlist 保留；不自动提交、发布、接入快捷方式或改变真实作品目录。

## 实际复现

保存的净增已被后端真实记录（示例为 6 汉字），但正文回执和后续核对失败。作者成功重新载入磁盘后，编辑器已是新版本，顶部码字组件仍显示旧的 0 字。组件没有卸载，也没有收到统计失效通知。

另确认：磁盘未变化的未确认保存缺少直接比较/重载入口；真正空文件的预览设置空字符串后不会打开窗口。

## 本轮修复

只在原来同项目同文件的保存结果待核对、且作者成功重载不同磁盘修订时，通知已有统计客户端重读实际保存事件。载入代次和当前项目检查继续生效。普通保存、未写入、未变修订、取消或失败的重载不补造字数，也不因普通重复打开而增加统计请求。日目标提醒仍由现有真实统计与每天一次的机制决定；手动/AI/恢复来源保持原样。

未确认状态现在直接提供已有的查看磁盘和重载操作，无需等磁盘变化轮询。重载沿用原来的编辑保护/手动恢复/作者确认。提示使用中性的“磁盘版本已变化”，不推定是谁修改。

现有磁盘比较窗口用明确状态表示读取中、成功、失败和空文件。请求按项目、文件、载入代次和本次 AbortController 校验归属，关闭与作用域变化取消读取，10 秒时限覆盖读取，失败只允许明确重试；迟到响应不能重新打开已关闭窗口。窗口只读，复制须作者主动点击；测试不写系统剪贴板。

## 验证

28 个独立 headless 场景：6 个统计/重载场景、4 个磁盘快照场景、12 个保存回执/格式回归、6 个 2.24.24 核对时限回归。真实本地保存、磁盘字节、统计 API 和事件游标核对；故障响应/延迟明确注入，无模型调用。

统计覆盖已提交、未提交、普通保存、后续隔离外部字节变化、取消重载、失败后明确重试。保存事件游标在核对前后保持一致；元数据通知只含项目和种类，未包含正文。日目标达成提醒一次。快照覆盖真空文件、关闭后的迟到响应、读取失败重试与超时。保留原失败记录；没有更改验收阈值。

未新增完整历史测试、原生 Windows 窗口点击、实体中文输入法、DPI、语音、真实云端 AI 或多项目原生窗口验收。不能把 headless、冻结资源校验或受限工作进程当作 GUI 通过。浏览器取消读取也不保证后台立即结束处理。原始保存 PUT 的等待时限不在本轮改动范围。旧候选外配置漂移和早前隔离服务退出异常未归因，不回滚全局配置。

## English

After an uncertain same-file save, a successful author reload of a changed revision invalidates only the existing local progress view. Actual saved-event records remain authoritative; no events, counts, source shares or writing time are invented. Normal, unchanged, failed or cancelled reloads avoid duplicate progress refreshes.

Existing compare/reload actions are visible for unconfirmed saves. Read-only snapshots support actual empty content, loading, errors, explicit retry, cancellation and a 10-second deadline. Current project/file/load ownership gates late results. Twenty-eight isolated headless cases passed; native GUI/IME/DPI/voice/cloud-AI acceptance remains unverified. No dependency, Agent, schema, migration, shortcut or publication change.
