# Novel Studio：开发与重新打包

这些是给取得**对应完整源码**后的开发者使用的命令，不是让普通用户安装 Python 的步骤。本包的 EXE 可以直接启动；同版本开发源码 ZIP 与运行 ZIP 分开分发，小说工作区由用户明确选择。

## 环境与依赖

- Windows 打包使用 Python 3.12 系列；桌面依赖在 `desktop/requirements.txt`。
- 前端使用 React / TypeScript / Vite；Node 版本须满足对应源码依赖的 engines，以 package-lock.json 为准。
- Codex 登录、Skills、Pandoc、ComfyUI 为可选外部能力；普通手动写作不依赖远端 AI。
- 在源码根运行已有 `install-web.ps1` 安装后端虚拟环境与 npm 锁定依赖；此步骤联网，请在得到安装授权后执行。
- 如需打包，在同一虚拟环境安装 `desktop/requirements.txt`；不另建永久服务或修改全局 Codex 配置。

```powershell
# 当前目录必须是你获得的完整源码根。
.\install-web.ps1
& .\web\backend\.venv\Scripts\python.exe -m pip install -r .\desktop\requirements.txt
```

不要因为插件缺失自动安装另一套小说框架。依赖或许可不明确时记录缺项，继续可独立完成的 UI/API 工作。

2.20 的内置 Python Control 使用独立 CPython WASI 与 Wasmtime。Developer 包不包含大型运行目录；首次构建由 `desktop/fetch_python_runtime.py` 从锁定来源下载，验证 ZIP SHA-256 和逐文件哈希后才安装。Windows 运行 ZIP 已携带该运行时，普通用户无需安装 Python。

外部开发者 SDK 位于 `python/`，可 `python -m pip install -e python`。它仅通过作者主动创建的短期本机授权访问同一 Action Registry，不是原始文件/数据库控制接口。API 与权限文档见 `docs/character-control/`。

## 隔离开发示例（仅在用户允许启动时执行）

下面复制源码内已有的公开演示模板，不复制用户 projects、文献或真实偏好。环境变量必须在导入/启动后端前设置。

```powershell
$taskRoot = (Get-Location).Path
$taskPython = Join-Path $taskRoot 'web\backend\.venv\Scripts\python.exe'
$taskScratch = Join-Path $env:TEMP ('NovelStudio-dev-' + [guid]::NewGuid().ToString('N'))
$taskWorkspace = Join-Path $taskScratch 'workspace'
$taskData = Join-Path $taskScratch 'application-data'
New-Item -ItemType Directory -Path $taskScratch | Out-Null
Copy-Item -LiteralPath (Join-Path $taskRoot 'desktop\preview-template') -Destination $taskWorkspace -Recurse
$env:NOVEL_WORKSPACE = $taskWorkspace
$env:NOVEL_STUDIO_DATA = $taskData
$env:NOVEL_STUDIO_HOME = $taskData
$env:NOVEL_STATIC_DIR = Join-Path $taskRoot 'web\frontend\dist'
$env:NOVEL_PORT = '8765'
$env:NOVEL_DEMO = '1'
& $taskPython -m uvicorn app.main:app --app-dir (Join-Path $taskRoot 'web\backend') --host 127.0.0.1 --port 8765
```

模板缺失时先向提供者取得公开 fixture；不要改用私稿测试，也不要重新运行 prepare_preview.py 覆盖已有模板。

第二个终端进入源码 `web/frontend`，运行 `npm.cmd run dev`。现有 Vite `/api` 代理指向 127.0.0.1:8765，默认前端地址为 127.0.0.1:5173。端口占用时正常关闭自己启动的旧进程，不强制终止用户其他软件。

这套命令用于前端/API 开发，不等于桌面 IME、WebView2、退出或真实 Codex 验收。桌面源码启动从源码根读取前端 dist 和后端模块；作品工作区与应用数据单独指定，不要以真实小说工作区测试写入。独立演示 EXE 需用现有 build.ps1 的 Preview 模式构建，2.8.4 正式包也包含原有公开 demo-workspace，首次引导可选择独立演示模式。

## 必要编译与验证边界

用户允许构建时在源码 `web/frontend` 运行 `npm.cmd run build`（包含 TypeScript 编译与 Vite 资源构建）。后端语法/最小 API/桌面交互是否执行，以用户本轮要求为准。

用户明确说“不验证”时不追加 pytest、浏览器、桌面或 AI 付费调用。本说明中的命令不是自动执行授权。构建通过、Mock/Local/Remote 请求通过、浏览器交互、桌面交互必须分开记录。

## 沿用现有打包

从源码根运行：

```powershell
# 目录示例。已存在时脚本会停止；选择尚未存在的版本目录。
.\desktop\build.ps1
# 如需公开演示资源：加 -Preview，沿用已有模板及 manifest。
```

默认版本读取 desktop/version.json，前端锁文件/后端/About/MCP 与其同步；显式目录必须匹配。不覆盖已有 NovelStudio 输出。构建流程是依赖许可收集 → 前端构建 → PyInstaller → README/定位配置 → package_zip.py。后者自动附上四份开发说明，来源为 desktop/developer-guide/。随后 package_source.py 通过固定白名单单独生成 NovelStudio-Developer.zip。

安装包 `NovelStudio/` 和 ZIP 必须一起保留 _internal；不只复制一个 EXE。输出目录不能带入 projects、Canon、State、私人文献/图片、API Key、auth.json、用户 .codex、运行历史或缓存。

只更新说明时，可把最新已构建的运行目录复制到一个新的发行目录，使用现有 package_zip.py 重新生成 ZIP；不要宣称重新编译了 EXE。只替换说明不会改变对应的运行功能版本。

## 如何继续维护说明

四份说明的唯一源位于 `desktop/developer-guide/`。修改此处，再打包；不要仅修改某次 release 内副本。更新软件功能时同步源码入口、Schema/依赖变化与验证限制，不写不存在的接口。

## 排错

- `Only EXE / 没有 src`：取得匹配版本完整源码，不对 minified JS 做正式维护。
- `Release already exists`：换一个新目录，保留旧包。
- `单实例锁`：用户正常退出旧窗口，确认未保存内容已处理；不要强制结束。
- `保存 409 / etag 冲突`：重新读取并比较版本，不无限重试覆盖。
- `缺少本机会话校验`：使用已有 api.ts 与会话机制，不删除来源/请求校验。
- `Codex 未登录 / 超时`：使用应用现有连接/重试信息；不重写用户全局认证。
- `模型能聊天不能用工具`：保留文本功能，Agent 能力标为未验证/不兼容。
- `字体未安装`：使用系统回退，或由用户自行安装合法字体；不随包复制系统字体。
## 2.8.4 维护入口
- 轻量标签：src/desk-tabs.tsx；复杂作者页面保留 React.lazy。
- 字体：app/system_fonts.py 使用 Windows GDI 名称枚举；检测失败显示 UNKNOWN，不扫描字体文件。
- 偏好：Studio.flushPrefs 合并设置版本，继续调用现有 api 写队列及 Preferences/atomic_json。
- 首次目录：launcher.py 的 first_setup/data_locations；开发机 data-location.json 不能进入公开包。
- 工具：/api/assistant/tools 返回 Action 目录与 Codex 白名单；目录表示工具已注册；协议、Dispatcher、浏览器、真实模型和原生桌面验证应分别记录。

### 2.8.4 检查修复
启动配置和版本元数据验证 JSON 类型；指定无效工作区会停止，不回退其他小说。演示只复制清单内文件。开发源码包含 templates/state 初始化模板。备份恢复前先完成设置保存，恢复期间不接受新的偏好写入。修复包经过20项专项审查，原生桌面 IME 和远端模型推理未在本轮验证。
