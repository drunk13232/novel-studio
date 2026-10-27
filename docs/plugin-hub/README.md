# Novel Studio 2.21 · Plugin Hub Preview

设置 → **插件与接入**，或小说导航“全部创作工具 → 插件与接入”。没有打开作品时也能安装、配置与管理插件；需要作品的操作必须先打开小说。

## 使用

1. 在“开发与示例”下载一个示例 ZIP。
2. “导入本地插件”选择 ZIP，检查作者自述、版本、许可和操作权限，确认安装。
3. 安装后默认禁用。主动启用，再打开“详情与配置”。
4. 配置非敏感参数，选择命令，检查固定计划并运行。
5. Action 和 Python 命令在原 Python Control 显示真实输出、前端回执、停止和确认卡；入口命令直接打开已有页面。
6. 禁用、更新、卸载或修改配置会撤销该插件的待执行操作；卸载保留包文件，便于重新导入。

“服务接入”统一打开已有 AI Provider、模型分配、Codex/MCP、ComfyUI、Python 和实验模板入口。卡片表示配置能力，不表示已连接；打开页面不会启动全部 AI 服务。

## 首版插件类型

| 类型 | 实际执行方式 |
|---|---|
| `action` | 固定 Action 名与参数；参数可引用 `${setting_id}`，运行前由原 Pydantic Action Schema 校验 |
| `python` | UTF-8 `.py`，现有 CPython WASI 沙箱执行；`PLUGIN_CONFIG` 提供非敏感配置 |
| `entry` | 仅打开枚举内的设置分类或现有应用页面 |
| `resources` | 可下载数据模板；实验资源使用现有世界实验定义验证，导入仍在原功能中完成 |

这不是 VS Code、Obsidian 或任意 Python/npm 插件的兼容层。没有主机 DLL、动态网页脚本、安装钩子、pip/npm 自动安装或任意 MCP 子进程入口。新增原生协议需要另行审查实现适配器。普通 LLM 接口继续使用现有 Provider；插件不能读取密钥。

## 开发

插件 ZIP 根目录必须有 `manifest.json`。格式为 `novel-studio-plugin/1`。完整机器可读格式见 [manifest.schema.json](manifest.schema.json)，应用中也可打开 `/api/plugins/schema`。

三个可运行示例由 `app/extensions/examples.py` 的公开固定数据生成，不读取用户目录。离线开发源文件见 [examples](examples/)。

```powershell
python tools/build_plugin.py ./my-plugin ./my-plugin-1.0.0.zip
```

构建工具复用应用验证器并填充 SHA-256，不执行插件代码，不覆盖已有 ZIP。先按现有开发指南安装后端依赖。插件清单中 `author`、`license` 是作者自行声明，软件不代表审核或授予资源版权。

## 生命周期与安全

`预览 → 明确安装（禁用） → 主动启用 → 作者选择命令 → 原 Action / TaskManager → 真实结果`。

- 安装、启用及启动应用不运行插件；无网络插件商店或自动更新。
- Windows 与浏览器使用同一后端，不新建第二套领域服务或数据库。
- 插件的 Action 白名单在应用执行层强制检查，且必须同时满足作者当前角色、项目和上下文授权。
- Python、固定审批及子任务保留插件 ID、包版本和配置版本约束；禁用之后旧确认不能迟到执行。
- 正文、Final、Canon、State 与 Knowledge 不授予插件直接文件权限；修改候选仍走原 Proposal / Diff / Review 流程。
- ZIP 限制 1 MiB、解压 2 MiB、64 条目、单文件 256 KiB；脚本 64 KB。拒绝路径逃逸、大小写重名、链接、加密包、异常压缩比和未声明文件。
- 已安装文件运行前重新校验；不使用 Python `eval` 或主机动态导入加载插件。
- API Key 仍在原有系统凭据服务；插件配置只有有限类型的非敏感字段。
- 导出只含原始插件清单和文件，不含用户配置、作品、执行历史、临时授权或凭据。
- 用户插件位于已有用户数据作用域下的 `plugins/`。它们不进入 Windows 或 Developer 发行候选。
- 配置损坏时隔离插件功能并显示错误，普通写作继续可用。

## 技术依据

采用清单、稳定 ID、版本兼容、声明式贡献与按需运行，参考 [VS Code manifest](https://code.visualstudio.com/api/references/extension-manifest) 与 [Obsidian manifest](https://docs.obsidian.md/Reference/Manifest)。执行权限和运行器继续使用 Novel Studio 原有实现，没有引入插件框架依赖。项目与示例的公开许可仍待作者最终决定；示例目前标为本机演示用途。

## 当前边界

新管理界面优先提供简体中文和英语，其他语言使用明确回退。没有自动执行的文件监听插件、后台服务插件、任意 URL 代理或外部 Agent 框架。插件可以组合现有受控能力；不能据此声称所有软件功能都已开放或任意第三方协议已经兼容。
