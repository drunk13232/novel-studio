# Novel Studio 2.24.27 — Recovery Integrity Preview

RESULT: PARTIAL / Local Preview. Public 2.24.26 and prior local versions are retained. This build is not automatically published or assigned to a desktop shortcut.

## 修复范围

- 恢复副本 API 读取/写入回执返回实际存储文件的 SHA-256。新版客户端清理时携带此版本；副本已经变化时返回 412，保留较新副本。磁盘格式仍只有 path、etag、content、saved_at 四项，无迁移。损坏副本明确报错并保留，不能静默删除。
- 正文已经确认落盘后，恢复副本清理最多等待 10 秒，涵盖排队和响应等待；未确认的清理保留缓存与警告，不把它冒充正文保存失败，不重发正文写入。队列中取消清理不释放仍然未完成的旧写入。
- 回执只有在项目、路径、载入代次、当前文字和缓存原始值仍属于本次操作时才清理本地缓存。撤销后重做、新输入、较新的恢复写入及晚到请求均不能被旧清理回执抹掉。
- 保存结果尚不确定时，再次保存被拒绝仍保持未确认状态、离开保护和明确授权的手动恢复选择。WORKSPACE_BUSY 不再被新误判为磁盘内容冲突；已有的真实冲突不会因此被清除。
- 重新读取章节时收起旧恢复按钮，恢复/放弃入口也检查当前读取和保存归属。取消读取后仍可查看并明确恢复原副本。放弃副本等待真实删除回执；版本已变化时先保留，重新读取和检查后由作者再次选择。

## 实际验证

26 个本轮隔离 headless 场景：9 个恢复流程，加 17 个受影响的既有保存、读取、工作区恢复、只读磁盘快照回归。它们检查真实本地 API、磁盘字节、缓存、保存事件游标、页面状态与实际 AbortError。故障由明确的本地 HTTP 503/403、损坏回执和延迟注入；不是云端模型验收。迟到清理由仅测试环境启用的固定项目/路径调度入口转发到真实受认证的 API，实际返回 412；不假装客户端中断能保证服务端停止。

15 项真实本地后端 API 检查通过，包括存储格式不变、并发版本保护、缺失版本、幂等删除、坏格式保留、会话和项目隔离及码字事件不变。56 条前端本地传输适配器断言验证串行队列、取消与权限门禁；它们单独标注，不充作浏览器、AI 或原生桌面检查。无新依赖或模型请求。

原生 Windows 窗口点击、实体中文输入法、实际系统 DPI、语音及真实云端 AI 本轮未验收。已有 chunk 警告仍在。Windows Proactor 异常后的某项隔离服务退出仍未归因，不作为正常退出通过。打包工作进程、冻结源码比对与静默安装结果在交付报告单列，不代替图形桌面验收。

## 使用提示

- 正文保存成功但出现恢复维护警告：磁盘确认与副本维护是两项状态。保留独立作品备份，不反复点击保存试图清掉警告。
- 提示恢复副本已经变化：先重新打开并检查最新副本，再决定恢复或保留磁盘版本。新版不会替你丢弃未知的新副本。
- 保存结果未确认：使用已有只读磁盘比较/重新读取，或明确选择手动恢复副本；不要把未知状态当作已经安全保存。
- 工作区忙碌：等待现有操作结束后明确重试，不自动循环重发。

## 实现与兼容边界

只在既有恢复 API 和前端请求层增加窄版本条件，不开放任意请求 Header 或通用可取消写入。旧版显式无条件删除 API 仍保留兼容；新版自动清理始终携带版本。该本机协议只支持单个 SHA-256 / missing 标记，采用条件请求防止旧操作覆盖新状态的原则，并不宣称实现完整 RFC Header 语法。正文保存和恢复写入 PUT 没有被强制加上取消或超时；浏览器中止不能证明后台写入已经停止。恢复副本不是持久备份。

参考：[RFC 9110 If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1)、[AbortController.abort](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)。

## English

Version-bound cleanup compares the actual stored recovery-file SHA-256 and rejects a changed copy with 412. Existing four-field files need no migration. A ten-second cleanup deadline separates confirmed manuscript writes from unconfirmed maintenance. Late callbacks compare current scope, text and raw local-cache identity before removal. They cannot clear newer recovery input, release an older pending write or replay a manuscript save.

Rejected retries preserve prior uncertainty/conflicts and navigation protection. Busy-workspace rejection does not create a new disk conflict. Recovery actions are hidden during chapter loading and guarded against active reads/saves; author discard waits for an actual receipt and retains changed copies for explicit reread/review.

26 current isolated headless cases, 15 real local API tests and 56 separately labelled local-transport assertions passed. No model call. Injected response failures/delays and the fixed test-only deferred dispatcher are identified. Native GUI, physical IME/DPI, voices and real cloud AI are UNVERIFIED. A Windows Proactor/isolated-service shutdown issue remains unattributed. Packaged-worker, source-alignment and silent-installer results are separate gates. No new dependency, schema migration, data relocation, Canon/Final/State/Knowledge write, global Codex edit, shortcut update, Git commit/push or publication.
