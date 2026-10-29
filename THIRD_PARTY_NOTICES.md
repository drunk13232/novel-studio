> Current project license: Apache-2.0, Copyright 2026 drunk13232 (owner decision, 2026-10-27). Root LICENSE/NOTICE/COPYRIGHT apply to original software. Older version-specific “pending” statements below describe historical releases only and do not override this decision. Third-party notices are retained unmodified; users' creative works are excluded.

# 第三方声明与分发边界

项目原创代码的 LICENSE 尚未选择；第三方版权和许可不受项目选择覆盖。安装版本详见 docs/oss/DEPENDENCIES.md 与 desktop/third-party/manifest.json。原始许可文本保存在 desktop/third-party/javascript、python 和相应资产目录，Windows 对应 _internal/resources/third-party。

|技术|实际版本|许可 / 处理|
|---|---|---|
|React / React DOM|19.3.0|MIT，保留声明|
|CodeMirror / @uiw|锁文件|MIT；正文编辑器实际使用 CodeMirror|
|Monaco|0.57.0|MIT；修订 Diff|
|React Flow|12.12.0|MIT|
|Dagre|3.1.1|MIT|
|dnd-kit/react|0.5.0|MIT|
|vis-timeline|8.5.4|MIT / Apache-2.0，以原许可文件为准|
|FastAPI|0.142.2|MIT|
|PyInstaller|6.22.3|GPL 带特殊打包例外，保留完整条款|
|pywebview|6.2.1|BSD-3-Clause|
|Codex SDK / OpenAI SDK|0.160.1 / 3.28.0|Apache-2.0；Codex CLI 不在本应用包中|
|官方 MCP SDK|2.3.0|MIT|
|PDF.js|6.3.289|Apache-2.0；不能替代附带字体/WASM 的许可|
|python-docx|1.2.0|MIT|
|pypdf|6.19.0|BSD-3-Clause|
|Pillow|12.3.0|MIT-CMU|
|Keyring|25.7.0|MIT|
|Lucide 图标|1.54.0|ISC|
|cmdk / 分栏|1.1.1 / 4.14.4|MIT|
|certifi|实际环境清单|MPL-2.0；原样分发，提供上游源码定位；修改时文件级义务|
|DOMPurify|实际环境清单|MPL-2.0 OR Apache-2.0，按随附许可|
|caniuse-lite|实际环境清单|CC-BY-4.0，开发依赖数据，保留归属|

PDF 标准字体从锁定的官方 pdfjs-dist 复制；LICENSE_FOXIT 为 BSD 风格，LICENSE_LIBERATION 为 GPL-2.0 带字体例外，不能由 PDF.js 的 Apache-2.0 覆盖。四个 Liberation TTF 已与官方 npm 包逐字节核对，保留原资源以兼容字形顺序。完整官方 1.07.4 SFD 源码包、许可和构建说明随候选保存在 desktop/third-party/font-source；Windows 为 _internal/resources/third-party/font-source。不同上游二进制的字体表差异及 668 个共同字符轮廓比对见 docs/oss/FONTS.md。WASM 的 LICENSE_QCMS、LICENSE_OPENJPEG、LICENSE_JBIG2 和 CMaps 许可完整保留。

MPL 原样依赖对应源码：[certifi](https://github.com/certifi/python-certifi)。二进制 Python/Tcl/Tk 许可在发行资源或其原目录；不删除所需声明。

NovelForge 在 .novelforge 内按其 MIT LICENSE 和原版权分发，来源固定于 docs/oss/EXTERNAL-SKILLS.md。项目 templates 和兼容入口中的派生部分也保留该归属，不称作原创框架。

外部安装，不进入候选：Sepia、Story Skills、Screenwriting、Research 插件缓存，ComfyUI / 模型、Pandoc、Codex CLI、WebView2 安装程序。ComfyUI 集成仅调用用户服务；不能将其 GPL 源码或模型权利视为本项目原创。Pandoc GPL-2.0-or-later；包内没有 pandoc.exe。外部插件顶层许可无法确认的只保留安装说明，不再分发其缓存或源码。

系统中文字体仅引用名称，不复制字体文件。PDF 自带的 Liberation / Foxit 是独立资源，区别于系统字体。原创演示封面由 Pillow 几何绘制，无私人原图；演示正文/资料是虚构样本。未加入用户图片、书籍原文和模型缓存。

这份清单是技术许可核对，不是笼统的法律兼容保证。项目许可证、版权主体、资源义务和公开安全审核须在发布前完成。

项目拟定许可不自动覆盖用户小说、上传文献或个人图片。Apache 全文、NOTICE 和版权信息目前仍为待用户确认的候选，未生效。

## V2.9 World Logic Lab 新增直接分发依赖

Z3 Solver 5.1.0.0 (MIT)、NetworkX 3.7 (BSD-3-Clause)、SymPy 1.14.0 (BSD-3-Clause)、Pint 0.26.1 (BSD-3-Clause)、jsonschema 4.26.0 (MIT)。许可原文与传递依赖声明在 desktop/third-party/python，Windows包随附。Z3 Windows原生 DLL 通过官方 wheel 收集。mpmath/flexcache/flexparser/platformdirs 许可以随附全文为准。未分发 Pymunk、Mesa 或外部自定义 Python 扩展。

World Logic Lab 使用现有 React Flow、Dagre、Recharts，许可义务沿用前述声明。私人实验、设定引用、运行记录不在公开源码或发行包中。项目正式开源许可证及版权主体仍待所有者确认，未创建生效 LICENSE。

## International Preview 新增依赖

直接运行分发：i18next 26.4.3、react-i18next 17.0.16、i18next-http-backend 4.0.2，均为 MIT。只用于开发与验证：i18next-cli 1.75.2（MIT）、Playwright 1.64.0（Apache-2.0）。完整声明由现有 collect_licenses.py 收集；不将 Playwright 浏览器或开发工具当成软件运行要求。Intl 由现有 Edge/WebView2 提供，不复制 CLDR 数据包或商业字体。新增界面译文是机器辅助候选，项目许可证和版权主体仍待确认。

## V2.9.2 finite-resource scheduling additions

Google OR-Tools 9.15.6755 (Apache-2.0) is bundled for bounded integer scheduling. Its required distributions are numpy 2.5.4 (BSD-3-Clause and bundled notices), pandas 3.0.6 (BSD-3-Clause), protobuf 6.33.6 (BSD-3-Clause), absl-py 2.5.1 (Apache-2.0), immutabledict 4.3.1 (MIT), python-dateutil 2.9.0.post0 (dual Apache-2.0/BSD-3-Clause), six 1.17.0 (MIT), and tzdata 2026.5 (Apache-2.0 and included IANA/public-domain notices). The existing collector retains installed distribution license files, including NumPy’s bundled-library notices. No optional SimPy, SALib, Pymunk or Mesa runtime is installed or advertised as available.

The project license remains an owner decision. These dependency notices do not license user manuscripts, sources, images or experimental records.

## Optional local Live2D companion (2.10.3)

l2d 2.1.1 wrapper is MIT; embedded Live2D Cubism Core and SDK/model materials have separate proprietary and sample terms. Runtime and Haru sample are not distributed in source or Windows archives. User-approved local development validation does not grant a public expandable-model AI application license. See docs/live2d/TECHNICAL-SELECTION.md. Offline voices are installed Windows SAPI5 synthesizers; no cloned actor voice assets are included.

## 2.11 Chinese text statistics

Jieba 0.42.1 (MIT, https://github.com/fxsjy/jieba) is bundled for on-demand deterministic Chinese segmentation. Its bundled dictionaries and notices are collected with the installed Python dependency. No uploaded novel or user dictionary is distributed. Project-wide license and copyright approval remain unchanged.

## 2.19 controlled interaction additions

@radix-ui/react-context-menu 2.3.8 (MIT, https://github.com/radix-ui/primitives)
is declared as a direct frontend dependency. It was already present in the
installed dependency graph; no separate framework or service is introduced.
Its installed license and required Radix primitives are retained by the existing
license collector. Workspace layouts continue to use react-resizable-panels
4.14.4 (MIT), and commands continue to use cmdk 1.1.1 (MIT). The project license
and copyright holder remain the owner's decision. User authoring data is excluded.

## 2.21.5 bounded cross-chapter replacement

Python `regex` 2026.9.29 (https://github.com/mrabarnett/mrab-regex) is bundled
for Unicode matching with per-call timeouts. Its installed metadata declares
`Apache-2.0 AND CNRI-Python`; preserve the entire installed LICENSE.txt and
metadata in desktop/third-party/python/regex and the corresponding Windows
resources. This is not Python eval and does not accept executable replacement
code. No new frontend dependency is added.

The 1,324-byte offline keyboard tick is original deterministic procedural PCM
audio, with no third-party sample, cloned voice or network resource. Its origin
and checksum are in web/frontend/public/sounds. It follows the project's eventual
owner-approved licensing; this notice does not choose a project license.

## 2.22.2 public-candidate rescan

The current notice inventory is docs/oss/DEPENDENCIES.md and desktop/third-party/manifest.json. Retain every included license/NOTICE, CPython/WASI historical terms, the separately licensed PDF font source archive, and asset provenance manifests. Runtime packages differ from development-only tools and externally installed services. No new dependency was introduced by the A/B reliability pass or this documentation/CI preparation.

Existing study/theme artwork is tracked by hashed manifests and authoring records; no private character model, proprietary Cubism Core or voice asset is admitted to the public source. Procedural typing audio has an offline origin/checksum manifest. This is not an independent legal clearance of character IP, generated artwork or the original project's copyright. Owner confirmation is still required; no root LICENSE is activated by this note.

Three missing direct frontend notice copies were repaired during the 2.22.2 public review: @recogito/react-text-annotator 4.3.6 (BSD-3-Clause), @uiw/react-codemirror 4.25.12 (MIT) and i18next-http-backend 4.0.2 (MIT). Exact-source URLs and SHA-256 are in desktop/third-party/SUPPLEMENTAL-NOTICES.json. Original copyright/license text is unmodified; these are dependency notices, not a selected project license.

## Windows setup wrapper (2.23.0)

The optional Setup.exe wrapper uses unmodified NSIS 3.13, nsDialogs/System and the zlib compressor. The applicable NSIS notices are in `licenses/installer/NSIS-3.13.txt` and in the installed `INSTALLER-THIRD-PARTY-NOTICES.txt`. Official source and license: https://nsis.sourceforge.io/ and https://nsis.sourceforge.io/License . The compiler is a separate development-only portable tool, not an application dependency or a resident service. The wrapper adds no license grant for Novel Studio or user-created works. Previously sealed portable ZIPs retain their original manifests and notices.


## 2.24.0 public review candidate

Custom Workflows adds no dependency. The new public candidate retains the full collected third-party notices, original study/theme artwork provenance, procedural sound manifest, CPython/WASI lock and Liberation corresponding source. Public installer defaults to LocalAppData, excludes private models/voices/Core and includes the formal root LICENSE, NOTICE and COPYRIGHT. The private repository history and older audit runtime files are not redistributed. This statement is not independent legal clearance of user-supplied or third-party character IP.

## Verified missing Python notice originals (2.24.0)

Jieba 0.42.1 (MIT), openai-codex 0.160.1 and openai-codex-cli-bin 0.160.1 (Apache-2.0) installed metadata declared the licenses but omitted their full text. The official matching GitHub version tags supply unmodified LICENSE and applicable NOTICE copies. URLs, SHA-256 and version checks are recorded in desktop/third-party/PYTHON-SUPPLEMENTAL-NOTICES.json and enforced by collect_licenses.py. Existing upstream copyright remains intact.

### SDK-paired Codex runtime in 2.24.9

The personal Windows package now includes the official `openai-codex-cli-bin` 0.160.1 runtime used by the installed Python SDK. Its Apache-2.0 LICENSE and NOTICE were already tracked in the corresponding-version Python supplemental notice manifest. The explicit Ratatui 0.30.2 MIT notice and the bundled ripgrep 15.2.0 (revision e89fff89ac) MIT license are included with SHA-256 and official-source references. No Codex login, user configuration or credentials are bundled. An explicit runtime override remains available.
