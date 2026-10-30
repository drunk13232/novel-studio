# Novel Studio 2.24.21 — Author Navigation Reliability Preview

本地 Preview / PARTIAL。未自动公开、提交或更新快捷方式。

## 作者可见的变化

正文存在未保存修改而准备切换页面时，仍使用原有“保存后离开 / 保留恢复副本后离开 / 继续编辑”。保存或恢复副本写入期间显示实际状态，避免重复提交；“继续编辑”、关闭和 Esc 仍可取消离开。取消离开不会谎称撤销已经发出的保存请求。已经完成的保存按真实结果保留，但旧回执不再让作者被迫跳离当前正文。

离开前还会核对项目、章节、页面、读取代次和输入。如果在等待中发生变化，则留在当前页面供作者检查。保存失败时，原因直接显示在当前弹窗中；只有作者明确重试才再写入。关闭自动恢复时，对应恢复副本选项有不可用说明，正文保存仍沿用现有接口。

## 实际验证

31 个独立 headless 浏览器场景：12 个本轮离开弹窗场景、18 个正文/候选/任务导航回归、1 个撤销/重做/Ctrl+S/重开场景。使用隔离合成章节和真实本地业务接口核对保存字节、恢复副本和失败后的输入保留。故障场景中的 HTTP 503 是明确注入的传输故障，不是实际磁盘故障。没有调用 AI。

较早的重复运行发现测试标记与上一次已保存的隔离标记碰撞，导致撤销断言无效；现使用每次独立标记并正确等待保存请求，保留了原始失败观察，不删改验收条件。没有以模拟模型或浏览器运行冒充原生桌面验收。

原生 Windows 窗口点击、物理中文输入法、系统 DPI、语音和本轮真实云端 AI 均 UNVERIFIED。沿用既有 Diff、权限、文件保存、恢复和版本机制，不修改正式 Canon / State / Knowledge / Final。先前隔离服务退出异常的根因仍未知，本轮干净退出不能证明历史问题已修复。

## English

Pending author navigation has its own owner. Choosing Continue editing, close or Escape cancels only that navigation; an actual save already sent may still finish and is reported truthfully. Late save/recovery receipts cannot resume cancelled or superseded navigation. Live scope and text are rechecked before leaving. Real write progress, duplicate-submit protection, in-dialog failure feedback and explicit retry reuse existing file/recovery APIs.

31 unique isolated headless-browser scenarios passed. No cloud model was called. Native GUI, physical IME/DPI, voice and real cloud-AI acceptance are not newly verified. HTTP failure injection and test-marker isolation corrections are identified separately. No new dependency, Agent, data format, database migration, permission expansion or public release.
