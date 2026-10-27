# Novel Studio — AI 接手规则

本目录为 Windows **运行发行包**。本规则用于 AI 阅读与维护本包，不替代对应源码工程自己的 AGENTS.md。

## 开始工作

1. 先读 [AI-DEVELOPMENT.md](AI-DEVELOPMENT.md)、[ARCHITECTURE.md](ARCHITECTURE.md) 和 [DEVELOPMENT.md](DEVELOPMENT.md)。
2. 明确用户要改软件功能、外观，还是创作小说。软件开发授权不等于小说写作授权。
3. 找到用户指定的真实源码根，读取该根及目标子目录的 AGENTS.md。发行目录、源码根、小说工作区、应用个人数据是不同位置，不假设某个盘符或用户名。
4. 如果只有运行包：取得同版本 NovelStudio-Developer.zip 或用户指定的对应完整源码。不能声称在完整源码上完成了修改，也不能把反编译结果当作原始工程。

## 开发边界

- 沿用现有编辑器、Action Registry、TaskManager、Codex SDK、MCP、API Provider 和备份系统。
- 修改源代码并重新构建，不直接编辑 _internal/resources/frontend 的压缩 JS 或 EXE。
- 普通 UI 工作不修改小说 Final、Canon、State、Knowledge、Timeline、人物、文献、图片和历史。测试写入放在明确隔离的临时工作区。
- 不把作者秘密、未来大纲或含秘密的修订意见直接提供给 Writer。Writer / Planner / Checker 使用现有隔离包。
- 用户没有明确要求时，不安装小说插件、不生成正文、不提交或推送 Git、不发布包。
- 不修改用户全局 Codex 登录、config.toml 或权限。普通模型不能冒充具备 Agent / Skills / 文件操作能力。
- 密钥仅使用已有系统凭据/会话存储；不写入文档、前端、日志、普通数据库或 ZIP。
- 高风险 Action 的固定 Proposal、项目作用域、有效期、版本检查、一次性确认与真实回执必须保留；不依赖模型自觉遵守 Prompt。
- 不开放任意 Shell、SQL、Python、文件系统或外部请求工具。
- 复用已安装依赖，新增依赖先查实际版本/API/许可证。react-resizable-panels 使用现有 V4 API。
- 用户要求不验证时，不自行运行测试或桌面验收；若为交付构建，只报告构建结果。构建成功不等于运行验收通过。

## 交付

简短报告实际改动、文件、构建/验证的真实边界和产物位置。发行目录不得包含私稿、文献、生成图片、凭据、运行日志或开发缓存。保留旧包，不覆盖真实数据。
