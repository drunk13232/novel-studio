# Selection & Save Reliability — 2.24.13 Preview

## 简体中文

浏览器 textarea API 会规范化换行，而候选和报告中的 UTF-16 偏移仍属于原始文本。旧路径直接混用两者，可能无法定位、误报保留失败，或重写另一个范围。

- 复用原有指挥台、文学评分、TaskManager 与 Diff；用小型共享工具精确映射视图/来源坐标，不统一改写现有候选或项目文件。
- 引用定位、保留到光标和局部重写以作者看到的真实选区为依据。未选前后文保持原始文本；非法范围、半个 CRLF、拆开的代理对或已变化的视图会被拒绝。
- 文学评分的选段仍只进入本地范围预览；明确运行后才请求模型。取消选择后不继续使用旧选段。原始来源和版本继续绑定。
- 只有作者在现有 Diff 确认采用时，替换文本的换行才映射到原文件的 LF/CRLF 格式；UTF-8 BOM 和接受前原始字节快照保留。原始候选/采用记录仍保留原文本。原文件本来混合换行时，既有保护继续拒绝覆盖；本轮不自动修复或迁移作品。
- 既有 Diff 首次挂载即读取真实差异；换行表现不同但内容相同的候选不会误卡在加载中。采用回执按逻辑换行核对，不忽略内容或末尾换行变化。
- 不改变正常编辑器保存、撤销、恢复、Canon/State/Knowledge 提交权限，不新增后台扫描、Agent、依赖或界面工作台。

## 验证边界

实际浏览器 textarea API、隔离本地服务和固定 MOCK 写作响应用于确定性校验；不是远端文学能力验收。对照保留的 2.24.12 前端资源验证旧问题，不修改旧发行包。原生 GUI、实体中文输入法、Windows DPI、真实语音、新远端 AI 与长期使用未重新验收。详细计数见本轮 LOCAL-DELIVERY.json。

个人使用推荐 Setup 并选择原数据目录。便携 Preview 保留公开演示用途；Developer ZIP 是本地开发快照，尚未成为重新复扫的公开源码候选。本次经公开 Allowlist 复扫后准备 GitHub Preview；私人 Developer ZIP 不作为公开资产。旧发行包和桌面快捷方式保持原样。

## English

Native textarea API values normalize newlines while stored candidates and report offsets remain raw UTF-16. A small shared mapping fixes evidence navigation, retain-to-cursor, partial rewrite and literary-source selection without migrating projects or rewriting candidate snapshots. Invalid, split or mismatched ranges are rejected; unchanged source prefixes/suffixes remain exact.

The existing Diff reads initial changes on mount and compares logical newline representations. Adoption receipts still distinguish actual content or terminal-newline changes.

Only explicit author adoption through the existing Diff maps replacement line breaks to the original document LF/CRLF style. UTF-8 BOM, raw candidate provenance and the pre-adoption byte snapshot are retained. Existing mixed-source write guards, revision checks, author confirmation and Canon/State/Knowledge boundaries remain. No background polling or new dependency was added.

Browser/local service tests with fixed MOCK writing are distinct from remote-AI quality and native GUI, physical IME/DPI, voice and long-duration acceptance. The retained 2.24.12 frontend is used read-only for comparison. Setup can use existing data; portable Preview is a public demo, and Developer ZIP is not a newly reviewed public source candidate.

## Standard reference

[HTML textarea API values and selection offsets](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#textFieldSelection).
