# Creative Workflow Reliability Preview · 2.22.1

This release extends existing writing, review, revision and publishing services. It adds no dependency, AI framework, database migration or new manuscript authority.

## 入口 / Entry points

在小说内打开「全部工具」。日常写作导航保留原来六个主要入口，新工具位于原有创作、分析、世界观或管理分组。

| 工具 | 入口与使用 |
| --- | --- |
| 情绪与张力曲线 | 文学评审上方或全部工具 → 情绪与张力曲线。选择范围和叠加线，明确执行本地分析，再检查证据、作者评分和低张力区段。 |
| 写作仪式 | 码字看板 → 写作仪式设置。默认关闭；启用后书架「继续写作」呈现可跳过步骤。进入专注设置会结束剩余仪式并打开原番茄钟；不会自动开始计时。 |
| 写作年报 | 码字看板 → 写作年报。选择年份，按当前作品查看保存事件。分享图仅用汇总与手填笔名/书名，不读取真实身份。 |
| 虚拟读者画像 | 文学评审上方或全部工具 → 虚拟读者画像。编辑画像、选择章节和模型、核对范围与预算，再明确开始。 |
| 世界观地图 | 世界观分组 → 世界观地图。新建地图、选择地点后点画布放标记；逐点绘制路线/区域，再完成和保存。地点详情可返回所在地图。 |
| 印刷预览 | 出版 / 导出 → 印刷 PDF。沿用同一章节选择和版式，生成固定 PDF，再按页预览或导出同一文件。 |
| 章节平行版本 | 先打开正文，再打开全部工具 → 章节平行版本。替代稿只在历史中保存；可编辑主稿切换须确认，Final 只保存待审候选。 |
| 章节音频导出 | 管理分组 → 章节音频导出。选择本机声音和范围、核对预览、确认导出。取消或退出后可检查并继续原任务。 |

关闭一天写作时可用「结束写作 · 一句话记录」；记录会明确追加到现有当日日记，冲突时不覆盖另一份修改。

## Honest data and author control

- Curves are transparent **rough local lexical/dialogue signals**, not a semantic emotion model or literary quality score. Evidence-poor chapters remain unknown. Character lines measure nearby text, not a character's proven inner state. Planned milestones never become observations.
- Author corrections are separate, version-bound metadata and take precedence while their source remains current. Flat spans are configurable reminders, not literary verdicts.
- Annual reports are **per project**, using existing saved-text net changes and UTC+08:00, matching the dashboard. Manual, accepted AI, restoration and unknown sources remain separate. No writing-time estimate or inferred past history is added. Cross-project rankings are intentionally absent.
- Reader reactions are **model simulations**, not survey data or objective scores. Existing public-reader isolation and exact-source validation remain authoritative. Long scopes are independent bounded reading groups, not a claim that every persona remembers an entire novel. No model starts from merely opening or approving a preview.
- Alternative chapter versions never enter the default chapter catalog, search, Writer context, timeline or book export. Switching an editable draft reuses safe save and does not manufacture writing events. Protected Final / committed text remains unchanged; those alternatives become review candidates, not silently promoted main text.
- Map annotations are not story facts. Creating a location uses the existing Bible service and produces a draft/reference entry. Map metadata and assets are included in existing full backup/restore; lightweight backups may omit originals.
- Printed previews and exported PDFs use **the exact same immutable bytes**, not two layout engines. TXT/Word/EPUB continue through their existing paths. Installed Edge/Chrome is required for local PDF generation; it is not downloaded or redistributed. System fonts may fall back. Widows/orphans are discouraged by CSS, but not claimed as automatically diagnosed.
- Audio uses installed Windows SAPI voices, never a remote TTS service. Quality depends on the speech pack. Without enough same-project, same-voice/rate completed samples, duration/size forecasts remain unknown. With at least 500 recorded characters, the preview may show an explicitly approximate local calibration; language and punctuation can change actual duration. Externally modified WAV files are preserved under their original names, while resumed output receives a new suffix. Completed chapters report actual WAV duration and size. Source changes require a new preview; verified completed chapters can be skipped on resume.

## Local storage and safety

All new project records use existing project metadata, review or history directories. Original save-event formats are unchanged. Raw project data, map backgrounds, reader profiles and reports never enter public source or binary candidates. AI features only transmit the author-confirmed public manuscript scope to the selected existing Provider; no silent Provider fallback is added.

- `metadata/studio/world-maps.json`: map annotations, stable Bible and asset IDs.
- `metadata/studio/writing-ritual.json`: opt-in ritual preferences, separate from word events.
- Existing writing events: sole source for annual aggregates and goals/journal integration.
- `history/parallel-versions`: alternatives, fixed confirmations, operation journals and undo.
- Existing literary review directory: personas' model reaction reports and bounded batch manifests.
- `metadata/studio/audio-exports`: export receipts and frozen chapter hashes, no credentials.
- Application-owned print cache: derived PDFs and source revisions; not a new manuscript authority.

Audio output is restricted to an explicitly selected folder outside the source/project/app configuration roots. Original path components are checked before resolving links. Start uses a short-lived project-bound preview; resume revalidates scope, source versions and finished-file hashes. Cancellation acknowledgement is serialized with file publication.

## Verification boundaries

See [DELIVERY.md](DELIVERY.md) for the final run. Deterministic/HTTP, in-memory React, genuine offline Chromium PDF/Canvas, actual SAPI file synthesis, remote inference and native GUI are reported separately. No remote reader-model test, native desktop clicking, physical IME or listening sign-off is implied by compilation or generated files.

The existing desktop 2.21.8 entry and old release remain available; this candidate does not silently switch the personal shortcut or enter an author's private work during tests.

## Development

Use the existing backend virtual environment and frontend toolchain. New tests use isolated projects. There is no pip/npm install needed for these features. Optional native PDF/speech capabilities are probed on demand; their absence does not prevent normal writing.

Technical basis: [Chromium Headless](https://developer.chrome.com/docs/chromium/headless), [Microsoft SAPI file output](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms723597(v=vs.85)). Existing React/Recharts, React-PDF/PDF.js, Pydantic, Pillow, python-docx/pypdf, SAPI/comtypes and revision services remain responsible for their respective jobs. Project-wide open-source licensing remains the owner's decision; no new license grant is asserted here.

## Reliability refinement / 可靠性深化

- 地图支持40步本地撤销/重做、Ctrl+S、精确坐标、标记别名、缺失地点重绑、绘制撤点/取消，以及未保存草稿下载。内部切换地图前会确认未完成绘制；草稿包含待完成点位。保存冲突不强制覆盖。底图先用已有缩略图，需要时加载原图。
- 读者批次明确计入未写章节；失去任务时只从严格匹配的已有报告恢复，不重发模型。坏记录、丢报告、取消和旧证据均分别显示。
- 仪式日目标采用 expected_daily 条件更新；目标和结束日记有未保存关闭保护。年报按所选年份验证响应，重复或无效可选数据不猜测、不冒充完整图表。
- PDF 可取消，已完成请求复用前核对哈希，正文改变后默认阻止旧快照导出；源状态核查中隐藏直接下载，作者仍可明确选择原快照。
- 章节版本提供只读中断恢复预览，确认后仅回退仍完全匹配的本事务，不覆盖后续工作。普通历史也能看冻结 Diff。旧快照缺失时明确阻止自动恢复。
- 音频重开显示运行任务，进度读取失败可手动重试，不重复合成；流式校验避免整份WAV载入内存。坏历史逐条隔离，本地任务取消不被正文写队列挡住，仍要求有效会话。

See [HARDENING.md](HARDENING.md) and [DELIVERY.md](DELIVERY.md) for implementation and verification limits.
