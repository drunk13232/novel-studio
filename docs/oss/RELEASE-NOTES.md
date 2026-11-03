# Novel Studio 2.25.2 Data Organization Usability Preview

**Preview / PARTIAL.** Includes the local 2.25.0, 2.25.1 and 2.25.2 changes since public 2.24.31. Previous releases are retained.

## Highlights / 更新

- AI 资料整理：在世界创作工作台中设计分类、字段、带单位的数值表和对比视图；支持手动建立空表。AI 只产出可编辑提案。
- 保存后预览，作者明确确认才创建待审资料；复用原有稳定 ID、版本与权限机制，不自动采用正文、Canon、State 或人物事实。
- 实时对比原条目，支持筛选、排序与本地 CSV/JSON 导出。未知、零值、AI 假设和原文引用分开保留。
- 修复未载入 JSON 沿用旧确认、未知值/删除提示混淆、重复引用、重试残留错误以及重入保存后的导航问题。
- 仅复制结构新建、历史搜索分页、来源筛选、可编辑补充说明。
- 顶部固定保存/放弃/预览，分类与资料逐项编辑并保留输入；已确认快照可导航但不可改写。
- 模型参数按展开初始化；新增文案简中/英文，沿用主题、RTL 与 reduced-motion。不新增依赖或第二套存储系统。

## English

Design editable categories, typed fields and numeric tables in the existing Worldbuilding Studio. Optionally use the configured AI provider or start manually. Preview destinations and explicitly create pending reference records; nothing automatically adopts manuscript, Canon or State changes. Live comparison views read original fields, with local filtering, sorting and exports. Unknowns are never invented as zero.

This update protects unloaded JSON, fresh confirmation, duplicate/missing references, retry state and re-entry navigation. It adds structure-only reuse, searchable/paged history and clearer source selection. A sticky command bar and single category/record editors preserve pending input. Model controls initialize on explicit expansion. Existing services, formats and permissions remain; no new application dependencies.

## Verification boundaries / 验证边界

- 2.25.2 local delivery: 37 related backend checks and 26 real headless Edge interaction scenarios; browser interactions are not native desktop/IME/DPI acceptance.
- The final packaged EXE actually displayed a Windows window, served the new local API and exited cleanly. No native mouse/keyboard automation was performed.
- Real Codex proposal evidence belongs to local 2.25.1, using synthetic material only. There is no new cloud-AI call in 2.25.2. Official third-party API services require author configuration and remain separately unverified.
- Exact-public-commit CI, privacy scans, installer checks and server asset hashes are recorded during publication. Historical results never stand in for the current commit.
- No claim of literary truth, transaction durability across a process crash, real-provider compatibility across all models or complete native acceptance.

## Install / 安装

Use **NovelStudio-2.25.2-Preview-Setup.exe**, or fully extract **NovelStudio-2.25.2-Windows-Preview.zip**. Keep writing data separate and select your existing data directory. The installer contains no personal path, does not automatically launch, and requires no separate Python/Node installation for basic packaged use. WebView2 and optional external AI/ComfyUI/Skills/voices retain documented requirements. Offline manual writing remains available.

Source is Apache-2.0 with third-party notices retained. Private manuscripts, references, databases, credentials and private character assets are excluded. See the attached SHA256SUMS.txt. Unsigned PyInstaller executables may trigger antivirus reputation warnings: check the trusted source and hashes; do not disable protection blindly. Report security issues using GitHub private vulnerability reporting.
