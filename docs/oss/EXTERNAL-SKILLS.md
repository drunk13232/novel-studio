# 外部创作能力来源

|能力|来源与本地证据|分发方式|
|---|---|---|
|NovelForge|https://github.com/XINGANLIU/web-novel-writing-skill ，固定 308ae728abf1c5526cfc533cde47904ff1f63584，MIT|快照 .novelforge 内的文件与原 LICENSE；不是 Novel Studio 原创|
|Sepia|https://github.com/Nanako0129/sepia ，安装锁 d6cc9cbe9f9302552e6b4627756c7a9eb55affd1；本机 0.12.3 LICENSE 为 MIT|外部安装；不分发插件缓存|
|Screenwriting|https://github.com/jtydhr88/screenwriting-skills ，安装锁 51115f18d160aa8b2ac5813e4432b6f0b425358f；本机插件 2.0.0 缓存未找到顶层 LICENSE；上游 README 声明技能 MIT、引文版权独立，见上游 NOTICE|外部安装；许可须在选用的上游版本核实，不以本机存在表示可再分发|
|Story Skills|本机插件 0.22.1 顶层 LICENSE 为 MIT|外部安装，原生 CLI 需要其数据格式；不迁移用户小说|
|Research Skills|本机 research-codex 0.4.2 未找到顶层 LICENSE|外部安装；再分发许可未确认，不纳入快照|

在 Codex 原生插件管理中按上游文档安装明确需要的插件，检查实际版本与授权；不自动下载整套重叠框架。本项目只保留现有路由和适配入口。普通文本 API 不能运行 Codex Skills。
