# 校审技术选型与依据

检查日期：2026-10-15。实际编辑器为 CodeMirror 6（@uiw/react-codemirror 4.25.0）；Monaco 0.57.0 用于既有 Diff。未更换编辑器，没有新增依赖。

| 方案 | 官方依据与许可 | 本轮选择 |
| --- | --- | --- |
| pycorrector | [官方仓库](https://github.com/shibing624/pycorrector)、[源码](https://github.com/shibing624/pycorrector/blob/master/pycorrector/corrector.py)，Apache-2.0。支持多种拼写和文本纠错模型；默认 KenLM 在模型缺失时会下载约 2.8GB。包许可不等于所有模型权重的再分发许可。 | 评估但不安装、不下载权重，避免破坏轻量版。语义校对复用当前选择的 AI Provider。没有宣称已集成离线专业纠错模型。 |
| LanguageTool | [官方仓库与 LGPL-2.1-or-later](https://github.com/languagetool-org/languagetool)、[支持语言](https://help.languagetool.org/hc/en-us/articles/39254526141463-What-languages-does-LanguageTool-support)。包含中文规则；自托管需额外 Java 服务，公开服务器涉及正文发送边界。 | 评估但未启动新服务，也不把私人正文发往其公用服务。 |
| CodeMirror diagnostics | [官方引用手册](https://codemirror.net/docs/ref/#lint)。MIT。Diagnostic 的旧位置不等于更新后的当前位置。 | 复用现有精确选区定位，显式检查后跳转；版本变化拒绝旧引用，无每键红线。没有必要再装诊断依赖。 |
| Monaco Diff | [官方 API](https://microsoft.github.io/monaco-editor/typedoc/)，MIT。 | 继续使用已安装的 Diff，不写第二套差异引擎。 |
| Promptfoo | [Assertions and metrics](https://www.promptfoo.dev/docs/configuration/expected-outputs/) 与 [项目许可](https://github.com/promptfoo/promptfoo/blob/main/LICENSE)。 | 采用预先标注、程序断言、按层验证与模型意见分开的评估方法，不为少量样本增加完整运行框架。真实引用与保存回执用确定性检查；文学评价不作为金标准。 |
| SQLite FTS5 | [官方 FTS5 文档](https://www.sqlite.org/fts5.html)。原有 SQLite 组件。 | 保留原 trigram 表和搜索接口，增加可重建的文件签名缓存，只读变化的正文。三字符以上使用 MATCH，两字符词使用有上限的 instr 回退。没有迁移正式小说格式。 |
| Z3 / NetworkX / SymPy / Pint | 工程已有世界逻辑实验室及锁定验收、受限表达式、独立进程求解。 | 本轮不新增求解器。文字问题进入既有实验设计入口，作者确认前提后再算。SAT/UNSAT 或定性意见不得混为文学设定真伪。 |

## 证据与误报边界

AI 输出固定 JSON Schema；每条引用必须属于当前提供的来源包、逐字存在于当时实际原文，且文件版本仍相同。未定位引用撤回自动修改。跨章冲突至少需要两章的原文；仍标为潜在冲突。当前 State 与过往 Knowledge 获得时间没有凭证时维持未知。大纲、人物怀疑与文献不是已提交事实。

常见的短字引用会有多个位置，因此全部列出并让作者选择。术语保护使用真实变更区间检查，包括同名词多次出现和部分字被改动的情况。只有作者明确接受后，原 StudioTools 才能写草稿或另存 Final 修订稿。

项目整体开源许可证继续等待用户确认。本轮没有添加需要重新分发的新第三方运行组件；私人小说、模型、角色资源和测试运行结果不进入公开源码候选。
