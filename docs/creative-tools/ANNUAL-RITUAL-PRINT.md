# 写作仪式、年度码字与印刷 PDF

本轮沿用项目原有保存事件、目标、日记、专注工具、成书装配及 PDF 阅读器。无新增前后端依赖，不连接 AI 或远端服务。界面提供简中、英文，其他语言沿现有回退。

## 写作仪式

- 默认关闭，按当前小说保存到 `metadata/studio/writing-ritual.json`；既有项目备份会保留该元数据，不迁移或改动原事件格式。
- 可开关、改名、增删和排序最多 12 个声明式步骤，分为写作前、写作后。内置日目标、专注工具入口、结束一句话；自定义清单项不会执行脚本。
- 始终允许跳过，可记住跳过并在设置恢复。检查项无需勾选即可继续；不自动打开 AI 或开始番茄钟。保存等待期间也可离开；已经提交的保存仍可完成，此时跳过仅应用于本次。
- 日目标仍保存在现有 goals 数据中，通过 `/experience/ritual/daily-goal` 只更新 daily，并用 `expected_daily` 校验旧值；不会 GET 后整份覆盖周、卷、全书目标。冲突时保留输入，可读取最新目标再决定保存。
- 专注步骤先退出可选仪式，下一帧打开原 `novel-open-focus-tools` 面板，避免面板藏在模态之后。作者仍需在原面板主动开始。
- 一句话只追加到现有日记，使用 `expected_note` 校验已读版本；日记有变化时返回冲突并保留输入，不覆写，也不截断超过 1000 字的合并结果。
- 仪式配置有 etag；迟到响应不会覆盖较新的输入。目标和一句话草稿均登记现有未保存保护；关闭按钮及外层弹窗请求通过 `onCloseRequestReady` 进入同一个放弃确认。保存并继续只在作者没有输入更晚草稿时前进，不会因一份迟到回执跳走。明确“不保存目标，继续”或“放弃输入并跳过”才放弃本次输入。

接口（均限定当前项目 `/api/projects/{p}`，写请求沿原本机会话校验）：

- `GET /experience/ritual`：只读设置、etag、UTC+8 日期、现有目标与当日日记；首次打开不创建文件。
- `PUT /experience/ritual`：`{etag,settings:{enabled,skip_remembered,steps}}`。
- `PUT /experience/ritual/daily-goal`：`{daily,expected_daily}`，在现有 goals 锁内只更新 daily；冲突返回 `RITUAL_GOAL_CHANGED`。
- `PUT /experience/ritual/reflection`：`{day,text,expected_note}`，追加并复用已有日记存储。

前端：`WritingRitualSettings({project})`，`WritingRitual({project,phase,onDone,onSkip,onClose,onCloseRequestReady})`。父入口可以 `loadWritingRitual` + `shouldOfferWritingRitual` 判断是否显示。

## 本书写作年报

`GET /experience/annual?year=YYYY` 只读当前书的保存事件，不扫描其他小说，不读取正文用于计时。按既有 UTC+08:00 时区分自然年：闰年完整 366 天，当前年截至今日。

- 保存净差统计；删文为负，重复保存为零，估算/无效/未来事件排除。方法未标记的有效旧记录沿用原兼容口径。
- 手动、AI 接受、恢复、未知来源分别展示。来源占比和净差不证明原创性；`VERSION_SWITCH` 只更新快照，不将已有版本切换冒充本次新写作。
- 码字日为当日总净增大于 0；连续纪录仅限所选年份内，最高日仅取有正净增的日期。
- 月度、24 小时按真实保存时间分组，绝不称为写作时长。
- 卷与章使用当前目录映射、按保存次数排序；无法映射的历史记录保留在总来源统计中。不会推断历史完稿日期、作者身份或某作品是跨书最活跃项目。
- 空年报有真实空状态；打开、切年、刷新均不产生写作事件，没有定时轮询。
- 缺失核心来源数字或项目不匹配时明确报错；缺失月度、时段、日历等可选记录时显示不完整说明，不补造零值。分享图对长书名、笔名与超大数字按列宽收缩/省略，避免跨列遮挡；不因此改变统计原值。

`WritingAnnualReport({project,onClose})` 提供本地 Canvas 分享 PNG。图中仅含允许的汇总数字及用户手动填写的笔名、书名；不抓取整个网页，不自动带入项目名、路径、章名、日记、正文或配置。

真实离线 Edge Canvas 验证使用实际 `paintAnnualShare` 函数和原创合成数字，输出：

`docs/daily-writing-ritual/private-checks/annual-share-local.png`

实测 1080 × 1280、127177 字节、0 外部请求；已打开图像检查中文与负数图形可见。这是 LOCAL HEADLESS 证据，未操作用户窗口。

## 成书内的印刷 PDF

成书中心增设 PDF 格式，复用 `BookCenter.assemble` 的章节范围、草稿/正式稿判定、正文与封面选择。未添加第二套正文/出版数据库。

- A5 148 × 210 mm、32 开 130 × 185 mm。
- 字体、字号、缩进、段距、行高、页边距复用左侧现有控制；新增装订边、章名页眉、页码。每章以 CSS named page 另起新页。
- 本机已安装 Microsoft Edge / Chrome 才可生成，不自动下载安装。字体来自本机系统，缺字可能回退，需作者人工检查。
- 独立临时浏览器 profile，CSP 禁脚本、连接、外部字体与网页；封面以本地重编码后的 data URI 提供。使用现有 Windows Job API 回收仅本次浏览器子进程，超时 60 秒，原生窗口不显示。
- 单次上限 1000 章、200 万字符、50 MB PDF；渲染中不持作品全局写锁。项目 scope 与本机会话 nonce 不变。
- 每次使用独立请求编号，可在预检或排版中取消。取消可以先于注册到达；仅停止该请求及其本软件拥有的子进程，不终止其他浏览器。单本只运行一份排版，全局最多四份排队/执行；前端忽略取消后及旧参数的迟到回执。
- Chromium 会把物理尺寸量化到设备像素；缓存前用已有 pypdf 一次性规范 MediaBox/CropBox 到声明尺寸，字形坐标不重排，只调整外侧空白边界。
- 正文装配保留真实 `document_revision`，开始排版前重读并严格检查全文及版本相等。追加正文后不能将旧前缀绑定到新版本。
- 输出到应用私有缓存 `print-previews/{project}`，正文、Canon、State、Knowledge 不写入。正式导出只复制屏幕正在预览的 PDF，核对同一 SHA-256；不会另行生成一份。
- 预览是生成时快照；改动正文或参数后要重新生成。保存/恢复事件、回到窗口与手动检查会重新核对源版本，无轮询。无法核实或已变化时明确提示；导出默认阻止旧快照，作者主动勾选后才复制该固定版本。PDF 阅读器复用现有 react-pdf，按页加载。章节下拉只跳转已经验证的真实 PDF 页，同时写入 PDF 章节书签。定位同时要求实际 H2 字号/标题与正文开头锚点，目录提到同名章节不会算章首页；匹配不到或多个候选显示“无法自动定位”，不猜页码。
- 长于 1000 字符的段落给出真实源行、引文、UTF-16 定位与版本证据，可跳正文；无法验证定位时不提供假跳转。
- 孤行/寡行使用 CSS `orphans:2;widows:2` 尽量避免；浏览器没有可靠逐处判定能力，本版本不宣称已自动检查通过。长段落提醒也不等于确定排版错误。

接口：

- `POST /book/print-preview`：现有成书字段 + `format:pdf,paper_size,gutter_mm,running_header,page_numbers,request_id`，返回一个不可变 artifact 或明确 `CANCELLED` 回执。
- `POST /book/print-preview/{request_id}/cancel`：取消指定请求，返回真实状态；无需等待排版锁。
- `GET /book/print/{id}/source-status`：只读核实 `source_versions`，返回 `CURRENT / CHANGED / UNKNOWN`。
- `GET /book/print/{id}/file`：先验证项目、文件哈希，再提供同一 PDF 预览/下载。
- `POST /book/print/{id}/export`：`{directory,allow_snapshot:false}`，复制相同文件到用户选定目录；禁止写入小说、应用数据或工程目录。同名内容不同的文件不会被覆盖。

前端 `BookCenter` 新增可选 `onOpen(path,location)`，沿原作者保护跳转。PDF 加载器和 PDF.js 仍按需导入。

## 本轮实际检查

- 本次仪式/年报与印刷合计 **37 项后端检查通过**（21 项仪式/年报，16 项印刷），包含真实本机 Edge 排版和取消。原看板 23 项是上一轮回归证据，不能冒充本次重新执行。
- **106 项实际 React/未保存注册表/Canvas 记录器检查**；涵盖目标并发冲突、外层关闭、保存时继续输入、缺记录降级和长文本/大数字边界。API 是隔离 fixture，Canvas 记录器不是实际 PNG，不冒充真实模型或原生 UI。
- **43 项实际 PrintEdition 操控检查**，涵盖取消预检/排版、迟到结果、版本核查、旧快照导出确认；PDF viewer seam 仅供测试控件，不冒充 PDF 页面显示验证。
- 印刷模块的真实 Edge headless 生成 A5、32 开中文与英文 PDF，pypdf 读取字形文本、页数、实际尺寸；预览、导出字节与 SHA-256 完全相同。
- create_app 真实本地 HTTP 生成/下载/导出 PDF，校验隔离项目全部文件前后哈希相同。
- 当前全工程 `tsc --noEmit -p web/frontend/tsconfig.json` 通过。
- 新的大数字分享布局本轮由实际 Canvas 绘制函数配合记录器验证，**未重新生成真实 PNG**。上文 `annual-share-local.png` 保留上一轮真实离线渲染证据，不冒充本轮新增图像。
- Windows EXE、物理打印、中文输入法和原生桌面点击没有由这些检查覆盖；需要父任务或作者另行验收。

检查脚本：`test_writing_annual_ritual.py`、`test_print_preview.py`（真实 Edge 例需显式 `NOVEL_VERIFY_PRINT=1`）、`check-writing-ritual-annual.mjs`、`check-print-edition.mjs`、`render-writing-annual-card.mjs`。

技术依据：[Chrome Headless 官方说明](https://developer.chrome.com/docs/automation-and-testing/headless)、[CSS 页边内容与现有限制](https://developer.chrome.com/blog/print-margins)。本功能调用已安装浏览器，不再分发 Chromium 本体；无新增依赖许可证。现有 pypdf、react-pdf 和 pywin32 仍适用原第三方声明。

