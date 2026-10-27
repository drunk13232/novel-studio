# Novel Studio 2.20 · 角色助手与 Python 操作

本版是 Character Agents & Python Control **Preview**。芳乃、蕾姆、Python 和 Codex 使用同一个受控 Action Registry、既有业务服务和 TaskManager。两位角色的工具权限一致，设置、聊天、脚本和任务来源按作品与角色隔离。没有另建小说数据库或 Agent 框架。

## 从软件内开始

1. 打开一部小说，在“全部创作工具”中选“Python 操作”，也可在快捷命令中搜索 Python。
2. 选择当前助手，查看其权限和本轮具体模型、思考强度、上下文预算。
3. 选择“章节、参考与人物”示例，按作品实际目录修改章号，然后运行。
4. 输出、每步真实回执、失败原因和待确认操作会显示在面板中。保存脚本后可从同角色、同作品重新打开。
5. 重要操作显示固定确认卡。确认只执行这项操作，不授权模型另行规划，也不自动重放先前写入。

```python
from novel_studio_api import Studio
studio = Studio.connect()
print(studio.projects.current())
print(studio.chapters.list())
studio.ui.open_chapter(2)
studio.ui.open_reference("chapter", number=1)
print(studio.characters.search())
```

正文读取需要作者在当前角色权限中明确启用，并在脚本中指定章节。世界、人物身份与便笺读取也有独立授权。右侧参考只读，保持中央编辑器、保存、撤销和未保存保护。`open_reference` 等 UI 操作收到真正的前端完成回执后才成功。

## 与角色助手一起使用

“打开第二章，把第一章放在右侧，并找出第二章提到的人物”会由现有 Codex MCP / 已支持工具调用的 API 选择真实动作。角色表达风格不能改变操作权限。模型未确认支持工具时仍是问答模式，不会以文本 JSON 冒充执行。

模型可以提出 `run_python_plan`，由同一权限层处理后启动独立 Python 子任务。运行结果用 `get_python_run` 查询；排队回执不是任务完成。角色的检索、执行、等待确认、取消与错误表现使用实际任务事件，原有私人模型和语音设置保持独立。

## Python 调用 AI / Codex

在顶部选具体模型和参数后，调用 `studio.ai.start(...)`。此接口为 **Level 3**，每次都需要固定操作确认。只有检查要求和明确授权的章节进入现有 Context Builder；不自动发送整书、不跨服务商回退、不改正文。

```python
from novel_studio_api import Studio, StudioError
studio = Studio.connect()
try:
    task = studio.ai.start("检查指定章节的叙事因果，引用原文，信息不足写未知。", chapters=[1, 2])
    print(task)
except StudioError as error:
    print(error.result)   # 待确认时脚本停止，不继续执行后续写入。
```

确认后，界面提供“用读取脚本续接已确认任务”，只读取已经创建的任务，不再次启动 AI。`studio.tasks.events(id)` 读取增量真实事件，`wait(id)` 有限等待，`cancel(id)` 取消本角色拥有的任务。正在运行且实际适配器支持的 Codex 可用 `steer(id, instruction)` 追加说明；不改模型、权限或暗中重启。

已完成任务可 `studio.tasks.share(id, "rem", "请整理这份结果")`。该交接仍需作者确认；接收角色通过 `tasks.shared()` 和 `tasks.get(id)` 读取固定结果。聊天记录不随任务一起共享；接收方不能停止或干预原任务。

面板显示自己创建的 AI 子任务真实事件和停止按钮；普通聊天日志不会重复保留这些私人正文片段。开启本角色的本地聊天保存时，固定结果另存到作品的私人记录，便于重启后明确读取；关闭保存时不宣称完整结果可跨重启恢复。

## 历史与恢复

脚本、运行输出和明确的任务来源保存在作品 `metadata/python-control/<persona>/`，由已有项目备份包含。程序重启不会自动重放 Python、待确认写入或正在运行的 AI。原 TaskManager 仍管理历史任务；读回结果不会再次调用模型。角色聊天沿用已有本地历史与有长度上限的上下文，不将讨论写成 Canon。

运行记录中的 WAITING_CONFIRMATION 表示解释器在确认点已停止；记录还显示独立确认结果。审批后需执行新的读取脚本或修改后的后续计划，不从任意 Python 栈位置自动恢复。

## 外部 Python

开发者在源码中 `pip install -e python`，再由作者在软件“外部 Python”页主动创建短期本机授权。示例连接代码包含临时 token 和本机请求 nonce，不应写入 Git 或截图分享。仅接受 `127.0.0.1`、固定会话和当前作品；15 分钟、切换作品、撤销、退出后失效。外部 SDK 的 Python 进程本身仍由作者在操作系统中管理，不属于内置 WASI 沙箱。

## 明确边界

已开放操作见 [动作接口](ACTION-API.md) 和机器可读 `ACTION-CATALOG.json`，不代表全部工作台已经完全可编程。复制/排序/导出章节、任意正文保存、正式 Canon/State Commit、全套文学评分批次等仍使用原有 UI 流程。本版不允许脚本越过这些流程。

内置 Python 是真正的 CPython WASI：支持 Python 语法、循环、函数与所带标准库；不包含任意本机文件、网络、Shell、SQL、第三方 C 扩展或 pip 安装。它适合调用应用动作并编排结果，不是通用系统终端。

新增界面优先提供简体中文与英语；其他语言沿用明确回退。个人 Live2D / 语音资源不进入公开源码或发行 ZIP。本版不替用户选择项目最终许可证。

见 [技术与安全决策](TECHNICAL-DECISIONS.md)、[Python SDK](PYTHON-API.md)。实际验收与限制由交付报告记录，不能以本地测试替代真实 AI 和 Windows 操作。


## 2026-10-21 稳定性修复

桌面启动器在进入 Python、逻辑求解或 MCP 子进程之前，先分派工作模式；这些子进程不初始化用户目录、桌面窗口、WebView 或用户配置。修复精简环境下 `Could not determine home directory` 导致内置 Python 无法运行的问题。

外部 Python 的空闲临时授权不再锁住内置控制台。正在执行和等待确认的操作仍串行，原有风险等级、项目作用域和作者确认保持生效。Python 面板当前标签的文字对比已修复。

修改后的隔离执行与相关权限检查共 17 项通过；实际桌面结果另见本机交付报告。此说明不代表所有 AI 服务、Windows 输入法、语音或完整应用操作已验收。

历史记录现在分别显示“脚本在确认点停止”与“原定操作已执行／拒绝／取消”等确认结果。选中历史时只显示该条记录，不混入当前会话输出、步骤或模型回执。原运行与审批记录均保留，不伪造重新执行。
