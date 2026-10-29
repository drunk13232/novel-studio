# Novel Studio 2.24.13 Selection & Save Reliability Preview

## 简体中文

本次合并 2.24.11–2.24.13 的可靠性修复，继续使用现有创作指挥台、任务管理、文学评分与 Diff，不新增 Agent、依赖或数据迁移。

- 作者接管、保存等待和报告刷新期间保留本地输入；迟到或不属于当前任务的回执不再覆盖当前状态。
- 候选经追加、改写、取消保留或重启恢复发生变化后，旧审查报告明确标为历史；缺失来源依据时不冒充当前评价。
- 修复 CRLF、CR、混合换行和 emoji 下的证据定位、保留到光标、局部改写及文学评分选区，避免选错文字。
- 修复首次 Diff 差异读取和换行核对；作者明确采用候选时保留原文件 LF/CRLF、UTF-8 BOM 和接受前快照。已有混合换行来源仍拒绝静默覆盖。
- 已采用回执仅忽略编辑器换行表现差异，不忽略正文差异或末尾换行变化。
- Codex 连接检查与作者保存分离；检查异常后可以再次尝试，不自动重放写作任务。

### 下载与升级

- 普通 Windows 用户：下载 `NovelStudio-2.24.13-Preview-Setup.exe`。
- 便携体验：下载 `NovelStudio-2.24.13-Windows-Preview.zip`；它保留公开演示模式。
- 作品独立于安装目录。升级前建议在软件中创建备份，并在安装器中选择原有数据目录；不要用演示数据覆盖作品。
- `SHA256SUMS.txt` 用于检查下载完整性。未提供代码签名，PyInstaller EXE 可能被杀毒软件误报；不要盲目关闭安全防护。

### 验证边界

本轮使用隔离公开演示数据、本地真实业务 API、实际 headless 浏览器和固定 MOCK 写作响应。固定响应不是真实 AI 能力验收。发布记录分别记录 Windows CI、包内资源及静默安装/worker 结果。

仍为 **Preview / PARTIAL**：本轮没有重新验收原生窗口点击、实体中文输入法、系统 DPI、真实语音、新远端 AI 和长期使用。构建、worker 或浏览器通过不等于这些场景通过。

## English

This release incorporates the local 2.24.11–2.24.13 reliability fixes without new agents, dependencies or data migrations.

- Preserve local author input during takeover, pending saves and report refresh; reject obsolete execution receipts.
- Mark reports historical when their candidate changes, and show missing provenance rather than claiming a current evaluation.
- Map native textarea UTF-16 selections to exact source ranges across LF/CRLF/CR/mixed newlines and emoji, fixing quotation navigation, retain-to-cursor, partial rewrite and scoring selection.
- Initialize real Diff changes on mount and compare logical newline representations. Explicit adoption preserves document EOL, UTF-8 BOM and the original byte snapshot; existing mixed-source guards remain.
- Adoption receipts ignore newline representation only; actual content and terminal-newline differences remain significant.
- Read-only Codex checks no longer serialize author saves and recover after probe failures without replaying AI work.

Use the Windows Setup for installation, or the portable ZIP for the public demo. Keep creative data separate, back up before upgrading, and select your existing data directory explicitly. SHA-256 checksums are supplied. Binaries are unsigned; PyInstaller-based executables can trigger antivirus false positives. Do not blindly disable protection.

Validation uses isolated public fixtures, actual local APIs/headless browser and fixed MOCK writing. Native GUI, physical IME, system DPI, voices, new remote-model calls and long-duration use are not newly accepted. Keep **Preview / PARTIAL**; build, worker and browser checks are separate evidence gates.
