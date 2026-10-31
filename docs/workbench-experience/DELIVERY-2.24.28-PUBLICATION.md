# 2.24.28 publication verification / 发布复核

Status: Preview / PARTIAL. This addendum supersedes the build-time “not reproduced” observation in DELIVERY-2.24.28.md; that file remains byte-identical to the Windows bundled build snapshot. The desktop version metadata also describes that earlier local-development stage; it is not a new publication/GUI claim.

## Actual checks / 实际检查

- 64 unique targeted local checks passed, plus three identified repeat checks. Fake-window tests and MockTransport/fixed local workers are not native GUI or remote AI.
- Two actual authenticated loopback save/recovery/shutdown cases preserved exact BOM/newline bytes.
- Five final isolated headless recovery cases passed: cache identity, held cleanup receipt, late changed-copy rejection, busy workspace, retry uncertainty. One earlier attempt returned an unrecorded non-success cleanup status; follow-up did not reproduce it. The test driver now records only redacted status/code and writes its failure report before teardown. A deliberate stale-revision test returned actual HTTP 412 / RECOVERY_CHANGED and correctly failed the driver; it is not counted as a product pass.
- Final same-configuration Windows Proactor service exit reproduced WinError 10054 and the existing 30-second graceful-shutdown timeout. Zero Uvicorn running tasks were reported, but listener transports were still present in the diagnostic snapshot. Root cause is unresolved. The process subsequently exited; no claim of clean or instant shutdown is made. No stdlib patch, event-loop replacement, increased timeout or unrelated process kill was used.
- Actual packaged bounded worker ran. Installer was silently installed and uninstalled in an isolated directory; known payload files matched, independent data and an extra file survived, and no system integration was requested. These are not native window interaction.
- Frontend TypeScript/Vite production build passed. Native GUI, physical Chinese IME, real system DPI, voices, remote Codex/MCP and long-running use are not newly verified. Exact-commit CI is recorded separately on the Release after it actually finishes.

## Safety and distribution / 安全与分发

No new dependencies, data migration, permission expansion or formal manuscript/Canon/State/Knowledge changes. Public source is an explicit reviewed snapshot with no parent/private Git history. Private works, conversations, character models/voices, credentials and user Codex configuration are excluded.

The installer uses the existing directory-selection flow and does not auto-enter the preview demo. The portable Preview retains its existing demo marker; an explicit workspace selects a real workspace. Older release artifacts are retained. Desktop shortcuts are not changed by this publication. Unsigned PyInstaller executables may trigger antivirus warnings; checksums verify download integrity and do not replace security review.

Older machine-local global Codex configuration drift remains unattributed and outside all candidates. It is not edited, reverted or uploaded. Local diagnostic logs and Developer ZIP are not public assets.

中文说明：任务排队与错误收尾已经补强，但最终隔离退出仍重现连接重置和原有超时，不能标为全面稳定。浏览器、回环接口、无界面安装及打包 worker 的通过不等于 Windows 原生窗口、中文输入法、系统 DPI 或真实云端 AI 验收。所有测试写入只在隔离项目。
