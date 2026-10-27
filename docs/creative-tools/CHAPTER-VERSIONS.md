# 章节平行版本（if 线）

本功能管理同一章节的替代剧情草稿，复用现有章节稳定 ID、正文安全保存、历史检查点和 Monaco Diff。不创建新的小说事实系统。

## 作者使用

1. 先保存当前正文，再打开“章节平行版本”。面板会显示它关联的主稿文件路径。长篇沿用成书目录的 Final / Draft 选择，不会把当前打开的其他修订文件默认为正史。
2. “复制主稿为新支线”仅在面板内建立草稿。填写名称、说明并编辑正文，然后“保存新支线”。它不会改变当前正文、Canon、State、Knowledge 或时间线。
3. “并排 Diff”按需载入原有对比编辑器。左侧是本次读取的主稿，右侧是当前支线编辑内容；比较不会保存或采用修改。
4. 对未提交且可编辑的主稿，保存支线后点击“确认切为主稿”，检查摘要并再次确认。主稿仍使用原文件路径，原内容会变成可选择的版本；操作有历史回执。
5. 正式 Final、已提交章节或目录主稿源已经改变时，只能“保留为修订候选”。候选及确认时的两侧快照全部保存在项目历史区，不创建任何章节文件，不改变默认搜索、统计或成书。“查看候选 Diff”读取冻结快照，后续版本编辑不会改变它。真正采用正式稿修改仍须原有修订审核流程。
6. “归档此支线”不永久删除内容。开启“显示已归档”后可以恢复；当前主稿不能归档。
7. 选择已保存版本可以下载独立草稿 TXT。发生冲突或尚未保存时，也可以“下载未保存输入 TXT”，保留当前输入，不请求后端写入、不清除未保存标记；文件名明确包含 `unsaved`。这是显式附加草稿，不是正式成书。默认成书导出仍只使用原有主稿选择。

每章最多 30 个版本，包含归档版本；单份正文使用现有 2 MiB 编辑上限，单章版本数据合计上限 24 MiB。没有平行版本的老项目读取时不会建立记录。

## 保存、撤销与隔离

- 完整支线正文只保存在 `history/parallel-versions/<chapter-key>/versions.json`；它不属于章节扫描目录，也不进入默认全文索引、Context 或字数库存。
- 当前主稿正文仍保存在原 `chapters/.../draft.*` 等原有路径。`canonical_id` 只表示平行版本槽位关联，不是 Canon 或剧情事实提交权限。
- 切换要求作者确认、元数据 etag、主稿 etag 和目标版本 etag 同时匹配；请求 ID 用于安全重试和防止重复执行。客户端不传任意目标文件路径或可执行脚本。
- 主稿保存、切换和撤销复用 `Workspace.save` 与 `_save_lock`。服务不再次获取 HTTP 已持有的 OS mutation lease。
- 通过 `writing_origin('VERSION_SWITCH')` 保存的切换和撤销不增加码字事件。全书当前库存仍通过原有成书目录读取。
- 撤销要求主稿和版本资料仍与本次回执一致。后续编辑、创建新版本或变更版本资料后，不会用撤销覆盖新工作；请通过历史对照处理。
- `PRE_VERSION_SWITCH`、`PRE_UNDO_VERSION_SWITCH` 和元数据历史检查点保留恢复依据。普通保存失败尽可能恢复本次操作；遇到外部后到写入不会强行覆盖。
- 一个轻量 `pending.json` 标记主稿事务。如果进程在提交中断、或补偿遇到外部变更，后续版本写入会暂停，读取、Diff 和下载仍可使用。系统不自动恢复或重放写入。作者可点击“检查安全恢复方案”，先查看当前正文与事务开始前快照的只读 Diff。只有正文和版本资料仍属于该次事务已知的 before / after 哈希、历史完整、原稿仍可编辑时，才能显式确认回退；会再次核对冻结 etag 和记录指纹并保留恢复前检查点。外部后到编辑、Final、已提交稿或缺失旧撤销快照都会禁用恢复，不提供强制覆盖。恢复不会自动重放原操作。
- 现有 Data Center 的完整项目备份包含 `history/`；恢复到新作品后，版本文件仅在新项目根内解析。文件不保存本机绝对目录或固定旧项目 ID。

## 接口

后端 `ChapterVersions(existing_studio_tools)`；路由 factory 为 `chapter_version_routes(service)`，前缀 `/api/projects/{p}/chapter-versions`：

- `GET ?path=...`：状态与版本列表；不会自动创建数据。
- `GET /detail/{version_id}?path=...`：明确选择的版本正文与主稿对照。
- `POST /versions`、`PUT /versions/{version_id}`：支线保存、名称与说明维护；主稿正文只能回到原编辑器修改。
- `POST /versions/{version_id}/archive`：确认归档或恢复，不永久删除。
- `POST /switch`：固定版本及 etag 的作者确认操作。`mode=switch` 采用可编辑主稿；`mode=revision` **仅保留历史区修订候选**。
- `GET /operations?path=...`：最近最多 100 条可读取的主稿切换或候选记录，扫描最多 1000 个操作日志。`unavailable` 披露跳过的损坏记录数量，`truncated` 披露读取范围有限；单条损坏不拖垮整份列表。
- `GET /operations/{id}/comparison?path=...`：明确选择的、只读冻结切换或候选对比。两侧来自当时的历史检查点，不会随之后正文或支线编辑变化；须结合 `status` 与 `review_only` 解读，不能当作当前正文。
- `POST /operations/{id}/undo`：确认后撤销仍符合校验的切换，或撤回候选记录。
- `GET /detail/{version_id}/download?path=...`：明确选择的独立草稿 TXT。
- `GET /recovery?path=...`：只读恢复方案，包括 `required / can_recover / reason`、当前 etag、冻结 `recovery_etag` 和必要两侧正文。不创建历史、执行恢复或自动写入。
- `POST /recovery`：显式 `confirm=true`、`operation_id / recovery_etag / state_etag / main_etag / request_id` 绑定的固定恢复请求；确认后仍重新校验。相同成功请求返回既有回执，不重复保存。

主要实际结果：`APPLIED`、`REVIEW_CANDIDATE`、`UNDONE`、`RECOVERED`；错误状态 `ROLLED_BACK`、`RECOVERY_REQUIRED`。候选回执为 `requires_review=true`、`canonical_changed=false`、`paths=[]`，不能被当成主稿切换成功。

前端 `ChapterVersionsPanel({project,path,theme?,onOpen,onChanged?})`。通过现有 `useUnsavedChanges` 参与全局未保存保护。`onChanged(paths)` 只在收到实际切换、撤销或已确认恢复回执时触发；受保护稿候选不触发正文刷新。

## 检查边界

`test_chapter_versions.py` 使用真实本地保存、成书目录、SQLite 搜索、统计观察器、Data Center 备份恢复，并在隔离子进程验证完整 FastAPI 本机会话和 mutation lease。

`check-chapter-versions.mjs` 在内存 DOM 中运行真实 React 组件，传输、Dialog 和 Diff 使用明确本地适配；不能当作浏览器或 Windows EXE 验收。所有测试数据均为合成隔离作品。

## 字段与状态模型

`versions.json` 使用版本化 JSON，不依赖新增数据库表：

| 字段 | 含义 |
| --- | --- |
| `schema_version` | 当前为 `1`，不迁移既有章节格式 |
| `chapter_id` | 现有规划/正文服务提供的章节稳定 ID |
| `main_path` | 原有、项目内的主稿相对路径，不从显示章号推断另一文件 |
| `canonical_id` | 本组版本当前映射到主稿的版本 ID；不代表 Canon 提交 |
| `versions[].id` | 稳定 `version_<32位十六进制>` ID |
| `versions[].name / description` | 作者命名和说明 |
| `versions[].content` | 支线全文；读取当前主稿版本时以原文件内容为准 |
| `versions[].archived` | 可恢复归档状态；主稿不可归档 |
| `versions[].created_at / updated_at` | 本地记录时间，不作为写作时长 |
| `last_switch` | 最后一次已采用主稿切换记录 |

返回的 `state_etag` 绑定完整版本记录，`main_etag` 绑定现有正文文件，版本 `etag` 绑定名称、说明、内容和归档状态。切换同时校验三者；没有由模型自由生成的任意路径写入。

切换日志记录 `id / fingerprint / at / status / target / from_id / to_id / before_etag / after_etag`，引用既有 `before_revision / before_state_revision`。记录中不重复保存完整正文，审阅通过引用的历史快照复现。`review_only=true` 明确区分待审候选与实际主稿切换。`pending.json` 只保存一个事务 ID，不保存正文、密钥或全局路径。

## 验证场景

- 新项目只读查看不会建立平行版本记录。
- 创建、重命名、编辑、归档及恢复支线；稳定请求 ID 不重复创建。
- 未确认切换被拒绝；主稿、版本、元数据任一 etag 变化均不采用旧输入。
- 主稿原路径保持不变，原文被保留；关闭并重建服务后可恢复版本映射。
- CRLF 和 UTF-8 BOM 经安全切换和撤销后仍保持；只有一个当前主稿版本。
- Final 与已提交章节拒绝直接切换；只读候选不会产生任何 `chapters/` 文件。候选不进入默认 SQLite 检索或成书。
- 候选保存后再编辑支线，旧候选 Diff 仍显示确认时的固定输入。
- 切换与撤销不会增加码字事件；全书当前库存读取原有主稿。
- 后续正文编辑、新版本及外部元数据变化阻止覆盖；失败补偿不会覆盖外部后到内容。
- 进程中断边界通过隔离故障注入检查，重开服务后只读并阻止新版本写入，不自动重放；已知前后状态可由作者审阅并确认回退。恢复再次中断时仍须新读方案和明确确认。
- 实际 Data Center 备份及恢复为新项目后，支线、稳定 ID 和内容仍可在新项目根内读取。
- 完整 FastAPI `TestClient` 穿过本机会话校验和现有单层 `studio-data.lock`，执行创建、确认、切换、幂等重试与撤销。
- React 本地内存 DOM 检查覆盖输入焦点、未保存放弃确认、Diff 按需加载、归档恢复、真实回执显示、项目隔离、只读候选对比。

这些是本地服务及组件检查，不代表本轮执行过真实浏览器、Windows 桌面点击或远端 AI 验收。


## 本轮可靠性补强

- **可审阅恢复**：覆盖切换开始前、正文已落盘、版本资料已落盘、撤销中断和撤销记录发布中断。新撤销记录引用它自身开始前的正文及版本资料检查点。旧撤销记录缺少这些引用时保持人工核对限制，不推测恢复范围。
- **后续编辑优先**：恢复只接受该事务的已知正文及元数据哈希。任何其他编辑、检查点期间的外部变化、章节已提交或出现优先 Final 都会使恢复不可执行。Canon、State、Knowledge 和时间线从不被此操作修改。
- **真实历史 Diff**：普通主稿切换现在也可以查看固定快照。旧回执缺少 `version_etag` 时，以当时保存的候选字节哈希校验兼容；不会改写原回执。损坏、超限、错误路径或不可渲染字段的日志逐条隔离，显示读取限制。
- **输入与成功回执保留**：未保存或冲突中的正文可直接下载带 `unsaved` 标签的 TXT；此下载不保存支线、不修改正文、不清除未保存保护。归档已经收到成功回执后，若刷新失败，仍显示归档成功及稍后重读提示，并将当前版本置为只读；不误报“写入失败”。
- **资源与权限**：复用已有 `history/revisions`、`Workspace.save`、3 个现有 RLock 和 HTTP mutation lease，不增加数据库、第三方依赖、后台任务或新的 AI 操作权限。恢复、切换和撤销均使用 `VERSION_SWITCH` 来源，不新增码字净增事件。

### Actual local checks / 实际本地检查

定向后端检查使用合成隔离项目，执行真实保存、统计观察器、成书/检索边界、Data Center 备份恢复，以及完整 FastAPI 本机会话和单层 OS lease。新增检查包含：确认前只读、重复恢复回执幂等、无待处理事务不造假方案、外部正文/资料变化拒绝、Final/已提交保护、恢复中断后不自动续写、CRLF/BOM 精确保留、损坏快照拒绝、普通与旧回执冻结 Diff、坏日志隔离及有界历史覆盖。

React/jsdom 检查运行真实组件的状态与生命周期，网络、Dialog 和 Diff 使用明确本地适配，检查显式恢复确认、取消不写入、未保存输入阻止恢复、下载不改变输入/请求、归档后刷新失败仍保留成功、坏日志提示、普通冻结 Diff 与旧项目晚到响应隔离。

这些证据属于 **LOCAL PASS**，不能表述为浏览器实机、Windows EXE、远端 AI 或用户验收通过。此模块不需要远端 AI 服务。
