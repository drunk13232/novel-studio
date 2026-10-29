# Novel Studio 2.24.7 — Record Editing Preview

Local delivery · 2026-10-29 · Preview / PARTIAL

## 桌面选择与后续候选

本机快捷方式调整单独记录于本地审计，不在公开源码或可分发 ZIP 中携带个人数据路径。旧版保留。2.24.7 是独立本地候选，不自动替换用户选择的桌面版本，也不自动启动真实或演示项目。

## 真实问题与最小修复

在 2.24.6 发行前端与隔离演示后端上复现：编辑已有记录，保存 A 的真实 HTTP 回执被延迟，继续输入 B 和标签/优先级后释放回执，编辑窗关闭，B 丢失；后端实际只保存 A，正文不变。

- 本轮把已有记录的标签文本与编辑快照收进原有编辑状态，减少一个独立 Hook，不增加状态框架。
- 回执仅在当前编辑与已提交快照一致时关闭；否则保留后续修改。
- 已保存记录及 etag 成为新基线，后续文字/备注/优先级/分类和标签保留为未保存；下次明确保存不会因自身上一份回执使用旧版本而冲突。
- 后端生成的元数据不混成假脏状态；作者把字段改回已确认值后可正常关闭。
- 保存期间关闭、离开和撤销到旧基线均走原未保存保护；输入仍可继续。未更改的编辑不重复写入。
- 简中/英文提示区分正在保存的提交与继续输入但尚未保存的修改。异常回执不自动关闭窗口。

## 实际验证边界

已有记录编辑专项：8 组 LOCAL_BROWSER_PASS + 1 组 FAULT_INJECTION_UI_PASS。覆盖新文字/标签/优先级、再次保存、无变化保存、保存中撤销/关闭、仅标签变化和去除假脏状态、失败重试、修订事项、独立灵感、英文 900×600 窗口。备注与分类在修订/灵感路径实际验证。角色绑定字段沿用同一保留映射，但本轮没有单独验证其动态修改。

使用真实本地 API，延迟真实回执；503 注入单列，不是远端服务或 AI 成功。全部写入公开演示副本，原演示正文保持精确一致。生产整合、后端检查与打包结果见最终发行目录 WORKBENCH-VERIFICATION.json、INSTALLER-VERIFICATION.json；只有执行完才记录通过。

原生 WebView2、物理输入法、真实远端 AI、系统 DPI 和长期运行不是本轮已完成的验收。没有宣称启动、内存或模型性能提升；既有大型懒加载 chunk 提示仍在。没有新依赖、后端 API、数据库迁移、权限扩大或 Git 提交/推送/公开发布。

## English

This local candidate fixes existing-record editors losing newer input when an earlier save finishes. Retain later text/field changes and rebase them onto the actual acknowledged row and etag. Unchanged forms need no write; pending edits protect close/leave and undo intent. Chinese and English guidance separates saved submissions from newer unsaved edits.

Specialized browser checks: 8 local + 1 injected failure, including to-do, revision, inspiration and English 900×600 editing. Character-binding changes were not separately exercised. Real local API replies were delayed rather than replaced with fake success. Native GUI, physical IME, real remote AI and long-duration operation remain unverified.

Personal shortcut adjustments are recorded separately from public source and redistributable ZIPs. This local candidate does not automatically replace the selected desktop version. Existing projects, old versions and author approval remain protected.
