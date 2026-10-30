# Novel Studio 2.24.19 — Assistant Navigation Safety Preview

## 更新 / Changes

- 修复助手结果导航读取期间继续输入导致未保存正文被旧磁盘内容替换的问题。现有“打开文档 / 查看正文候选 / 查看创作任务”入口会在真正导航前重新检查当前项目、页面、章节、较新的导航与未保存输入。
- 真实文件读取失败或已过时的响应会停止后续展示；明确重试清除本次操作的旧错误，旧请求错误不覆盖新操作。
- Existing result navigation rechecks live editor ownership and unsaved input after lookups. Failed or superseded loads stop candidate/task display. Explicit retries clear their own errors.
- 沿用 Action Registry、作者确认、Diff、源版本、自动保存与作品隔离。No added dependencies, data migration or permission expansion.

## 下载 / Downloads

- `NovelStudio-2.24.19-Preview-Setup.exe` — Windows installer / 安装程序。
- `NovelStudio-2.24.19-Windows-Preview.zip` — portable Windows build / 便携版。
- `SHA256SUMS.txt` — SHA-256 checksums / 校验值。
- Public source is in the repository and GitHub-generated source archives. The private Developer ZIP is not published.

## 实际检查 / Evidence

The completed local build passed 18 headless pointer/keyboard navigation flows plus one Ctrl+S/undo/redo/reopen flow in isolated synthetic data, 57 scoped backend tests (133.50 seconds), TypeScript/Vite production build, frozen-source/frontend alignment, payload/privacy scans, a bounded executable WASI worker, and an isolated silent install/uninstall with 5,212 matching payload files. Browser and worker checks are not native desktop acceptance. No real novel or paid AI was used.

本次公开前将独立复扫 allowlist 源码和发行 payload；完整 Windows CI 的结果在发布时按实际提交追加。

## 已知限制 / Known limitations

- Preview / PARTIAL. Native GUI, physical Chinese IME, system DPI, voices, new real Codex/MCP/cloud-AI and prolonged-use acceptance remain UNVERIFIED.
- Selected-text AI preparation/cancellation has a known delayed-dispatch boundary: an already authorized candidate task may start after the assistant receipt times out or is cancelled. Check actual task history before retrying; avoid that route with paid models until a later fix. A candidate still cannot automatically adopt itself into manuscript or Canon.
- 选区任务准备与取消仍有后续修复在研；不把未完成代码混入本版，不宣称该链路已经通过。
- Recovery copies remain window-local until explicitly saved or downloaded.
- One previous isolated test service needed owned-process cleanup after a local connection reset; the shutdown cause remains unresolved. This does not establish native desktop exit behavior.
- PyInstaller executables are unsigned and may trigger antivirus warnings; verify SHA-256 and use the official repository assets.

Existing projects and previous releases are retained. Project license: Apache-2.0, copyright drunk13232. User-created works and separately licensed/private character assets are not relicensed or bundled.
