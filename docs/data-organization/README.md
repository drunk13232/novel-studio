# AI 资料整理 / AI Data Organization — 2.25.2 Preview

## 用来做什么

把作者选择的世界资料、人物补充资料或剧情材料组织成可编辑的分类、字段、数值表和对比视图。AI 决定的是一个可供审阅的组织方案，不能改变项目文件权限，也不能决定什么成为 Canon。

入口：**世界设定 → AI 世界创作工作台 → 资料整理**。不配置 AI 也可手动设计分类，或点击“添加空白数值表”。

1. 填写整理目标，可粘贴资料，或勾选当前作品中的设定/人物。只有明确选择的有限来源参与本次请求。
2. 建立方案。需要 AI 时，展开“AI 帮我设计”，选择现有具体模型及高级控制，查看上下文，再勾选发送授权并开始。
3. 修改分类、字段、列类型、单位和资料值。未知留空；零值与未知不同。表格字段分页编辑，单格数值支持连续输入。
4. 保存方案，点击“预览保存去向”，检查将新增的分类和条目，确认后保存为 **PENDING / REFERENCE** 待审资料。
5. 打开“资料对比表”，直接读取当前原条目。表格列可展开查看行明细；可筛选、排序、导出当前页 CSV/JSON，或打开原条目继续编辑。

## 存储约定

- 继续使用 Bible 模板与实体：`bible/categories.json`、`bible/template-versions/<id>/<version>.json`、`bible/entities/<stable-id>.json`。
- 每张数值资料表是一个普通实体中的类型化 `table` 字段；每条新资料都有独立的既有实体文件。不是把每个单元格拆成文件，也不生成新数据库。
- `metadata/data-organization/<plan-id>.json` 保存输入快照、可编辑方案、模型回执与确认回执。快照用于追溯，不作为当前数值权威。
- 对比表只保存实体和字段引用，每次读取原值；不复制另一份正式数值。跨条目引用使用项目内稳定 ID。
- 不覆盖已选的原实体。要沿用原条目时，使用原模板与 `existing_id`、不携带覆盖字段。后续修改仍走原条目的版本/审核流程。
- 人物/剧情整理是补充设定条目和关联；不会替换 Character Canon、Outline、Timeline、Knowledge 或 State 的正式格式。
- 原有 Data Center 完整备份包含 `metadata` 与 `bible`。恢复为新作品后，方案与引用保留；不自动重放任务。

## 数据类型与来源

支持文本、长文本、数值、带单位数量、日期、架空日期、单选、未知/是/否、单条/多条实体引用，以及有类型列的表格。字段和表格列可改名、修改说明；顶层字段可用按钮排序，表格列顺序可在高级 JSON 中调整。正在使用的字段不能直接移除造成静默丢值。

- 数值：`0` 是已知零；`null` 是未知。数量：`{"value":12,"unit":"吨"}`；不能以 `12` 假装数量。
- 表格：`[{"period":"元年","stock":{"value":12,"unit":"吨"}},{"period":"次年","stock":null}]`。
- `AUTHOR_INPUT`、`AI_PROPOSED`、`SOURCE_QUOTE`、`CONDITIONAL`、`UNKNOWN` 分开记录。模型不能把输出标成作者输入。
- 原文引用必须在所选来源中精确匹配。**匹配只证明这段字存在，不证明单位换算、数值提取或推断正确**；作者仍须审阅。
- 选中的设定来源只发送允许 AI 使用的字段和未锁定摘要；不默认发送完整私密详情。人物来源不包含秘密、运行状态和 Knowledge。
- 数量排序要求同单位；不会猜测换算。CSV 数量拆成值/单位列，字符串公式前缀作转义，保留数字负值。

## 安全与限制

每方案最多 8 类模板、24 条资料、8 个对比视图；每分类 24 个顶层字段，每表 16 列、200 行。表格列为受支持的标量类型，不递归套表。大批材料应分批整理。

确认采用修订绑定的预览和显式确认，重复点击复用同一回执；来源/模板变化会阻止旧方案应用。运行任务可取消，迟到结果不覆盖编辑。异常写入回滚仅涉及本次明确列出的新文件及分类文件；不宣称具备进程崩溃时的跨文件事务保证。

JSON 高级编辑仍须通过 Pydantic/JSON Schema 验证；不执行公式、Python、SQL、Shell 或任意路径。没有新增 Agent、依赖或数据库迁移。外部 API 使用已有 Provider、上下文与预算/发送授权，不自动跨服务商回退。

已应用方案保留确认快照，不能在历史快照内改写当前值。请从对比表打开原条目编辑。来源变更会标为过期；原条目被移除时，视图保留缺失提示。

旧项目不迁移、不强制建表；旧版不认识新增 table 类型，不建议用旧版编辑已新增的表格模板。使用新功能前可保留完整备份。

新界面提供简中和英文，其他语言沿用现有回退。原生输入法/DPI/手工鼠标体验及远端第三方 API 按实际验收记录，不由构建成功推断。

## English usage and boundaries

Open **World Settings → AI Worldbuilding Studio → Data Organization**. Create a local draft, select only the intended sources, optionally request a design with the existing model controls, edit the categories/typed cells, save the proposal, preview destinations and explicitly create pending reference entries.

AI is a structure designer, not a filesystem or Canon authority. Canonical character, State, Knowledge, Timeline and manuscript formats remain unchanged. Character/plot material becomes supplementary pending Bible entries. No selected original record is overwritten. Comparison views read live original entity fields; proposal snapshots are historical evidence only.

Unknown values stay null, not zero. Quantities have separate numeric value and unit. Table fields are arrays of typed row objects (16 columns / 200 rows), not executable formulas. Proposals are limited to 8 templates and 24 records. Exact source-quote matching is not semantic verification of extracted values. The author must review the proposal.

Full Data Center backup/restore includes organization metadata, template versions and entity files. No resumed AI work or implicit author adoption follows restoration. Existing stable IDs and revision checks are reused. This is a local Preview; consult the delivery note for actual local, browser, real-AI and packaged startup evidence.

## 2.25.1 日常使用补强 / Quality update

- 高级 JSON 未载入时不能刷新、新建、复制或提交旧确认。先“检查并载入定义”，或明确放弃；载入后重新预览与确认。
- “复制结构新建”进入新建表单，重新填写目标、选择来源。只复用分类/字段/视图，不复制旧值、来源、任务、模型回执或授权。原方案保持不变；沿用既有模板时使用当前模板，模板变更不兼容会明确报错。
- 左侧历史可搜索并翻页，不再只能找最近 50 条。输入搜索后点击查找或回车；搜索无匹配时可清空查询。
- 对比表中未知值不会标成条目被删；删除提醒不因排序消失。同一实体的重复历史引用只显示/导出一次。
- 补充说明在“资料草稿”表单可见可改；来源列表可按名称筛选。

Unloaded JSON invalidates confirmation and blocks destructive local transitions. Structure reuse starts a new plan with no old values, source snapshots, tasks or AI consent. History supports search/pagination. Unknown values and missing entities are distinct; repeated stable IDs are deduplicated. Supplemental descriptions are editable before confirmation.

## 2.25.2 操作与界面 / Usability

- 顶部显示准备、编辑、确认、使用四个阶段；保存状态和主要操作集中显示。
- 分类与资料在左侧切换、右侧编辑，未保存内容留在方案中；移除分类仍受既有引用保护。
- 修改后可点“保存并预览去向”。保存方案不等于写入资料，仍须检查预览、勾选并明确确认；继续编辑会使旧预览失效。
- “更多操作”里可以刷新数据、复制结构新建；高级 JSON 收在底部，未载入时保持原有保护。
- 历史区独立滚动，支持查找和清空；来源可筛选、按标签移除。示例目标只填写文本，不发送请求或生成资料。
- 展开“AI 帮我设计”后才初始化模型控制，关闭再展开不清空本方案已填写的配置。

The workflow indicator and sticky action bar keep save/review steps visible. Edit one category or record at a time; switching preserves pending values. Save & preview never adopts a proposal: explicit author confirmation remains required, and further edits invalidate review. More actions holds refresh and structure reuse. Model controls initialize when explicitly expanded and remain available within that proposal. Goal examples only fill local editable text.
