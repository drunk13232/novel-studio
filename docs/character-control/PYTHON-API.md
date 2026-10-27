# Python API 2.20

`Studio.connect()` 在内置 WASI 中使用标准输入输出上的受控 RPC。外部 Python 必须由作者显式提供 URL、短期 token 和 nonce；SDK 不搜索用户凭据、代理或数据库。每项调用都进入原 `Session.call`，由原 Pydantic Schema 校验。

| 命名空间 | 主要方法 | 说明 |
|---|---|---|
| projects | current, list, status | 当前作品及允许显示的书架元信息 |
| chapters | list(offset, limit), search(query), open(number), read(number,start,limit) | 分页目录；正文最多每片16000字符并返回覆盖范围与版本 |
| characters | search(query), get(id), create_draft(name,summary) | 摘要需授权；新人物仅 Proposal |
| world | search(query), get(id) | 非秘密摘要与真实来源 |
| ui | state, open_chapter, open_reference, layout, navigate | 原导航、只读参考分屏、既有布局，等待真实前端回执 |
| notes | create(text), list(kind), todo(text) | 原灵感箱与章节待办；原回收和恢复机制 |
| ai | models, start(instruction,chapters,controls) | 用户具体模型；重要调用确认；不自动跨 Provider |
| tasks | get, wait, events, cancel, steer, share, shared | 实际 TaskManager；受作品、角色、来源授权约束 |
| Studio | actions(), call(name,**args) | 同一 Registry 的完整已开放目录与类型 Schema |

所有方法返回真实字典，不将排队 ID 解释为完成。失败或待确认抛 `StudioError`，其 `result` 保留明确错误或 action_id。SDK 不自动重试可能写入或计费的调用。外部每个客户端使用独立幂等前缀，避免新脚本误复用上个脚本的调用编号。

```python
from novel_studio_api import Studio
s = Studio.connect()
catalog = s.actions()
for action in catalog["actions"]:
    print(action["name"], action["level"], action["parameters"])
```

例如 `s.call("inspirations_to_todos", ids=[...], chapter=2)` 保留灵感原文，记录来源 ID，跳过已转换条目，返回严格文本重复组。其重复判断是可审阅的精确规范化匹配，不假装完成语义聚类。

`controls` 复用现有 RequestControls，包括 `model`、`parameters.reasoning_effort` 和 `context`。只有实际模型支持的参数才能通过现有验证。模型内部不可见上下文不属于应用精确控制范围。正文超过本次完整章节上限时明确拒绝，要求分阶段选择，不以截断冒充读完。

任务交接只授予指定已完成结果的读取权。新角色若未获作品资料读取权仍拒绝；交接不授予任务取消、Steer、其他聊天、其他小说或 Canon 权限。
