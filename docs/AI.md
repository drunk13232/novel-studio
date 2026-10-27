# AI 功能说明

设置 → AI 接口可使用当前 Codex 登录、自定义 API 或本地 LM Studio / Ollama。Base URL 是服务根地址，Model ID 必须由服务商确认。连接测试可能计费，未配置密钥时不会伪造成功。ChatGPT 订阅不等于 API 余额。

普通 API 生成文本候选，按任务/项目模型路由，不自动取得文件权限。Writer 仅接收本章授权披露的 Writer-safe 信息；Author 与 Checker 使用不同资料。不会因编辑候选、审稿或 Research 自动修改 Canon / State。

Codex 小说工作流使用单独安装的官方 CLI 和 SDK。软件助手使用本地 stdio MCP 和现有 Action Registry。Codex MCP 白名单目前为：list_projects、open_project、open_chapter、search_characters、open_character、set_theme、get_project_status、create_character_draft、set_editor_font_size、set_editor_line_height、show_character_reference、open_settings_section。

其他已注册 Action 不代表已经开放给 Codex。真实成功依据工具执行和前端回执；等待确认不等于完成。确认后执行固定 Proposal，不授权模型自行扩大操作。

安装 Codex 后按其官方登录流程登录；可在启动进程中用 NOVEL_CODEX_BIN 指定真实 CLI 路径。不要把登录凭据放进工程，也不要用本项目覆盖全局 config.toml。

NovelForge 原始内容在 .novelforge，保留 MIT 和来源。Sepia、Story Skills、Screenwriting 和 Research 是外部可选安装，不含本机插件缓存。参考 docs/oss/EXTERNAL-SKILLS.md；版本和原生数据契约不匹配时显示限制，不能修改正式小说来迎合检查器。

AI 关闭或未登录时仍可手动写作。云端资料只按任务授权发送；首次连接新服务商检查提供商名称与内容范围。错误可为认证、配额、网络、模型/协议或工具能力问题，不默认跨服务商回退。
