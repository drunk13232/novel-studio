# Security Model 1.0

执行层只接受项目作用域 API、严格 Pydantic/JSON Schema 和有限表达式。导入不接受 YAML 标签/锚点/别名；限制深度、文件大小、数量、表达式树、幂次数、扫描规模。没有 eval/exec/Shell/SQL 或任意网络函数；没有插件自动安装。

实验运行只接收冻结 JSON，不接收小说文件路径。子进程清除凭据类环境变量与 Codex/MCP 身份，使用 JSON 管道和 OS 资源限制；输出最大 1 MB。求解不读取正文、Canon、State、Knowledge 或用户密钥。取消终止该 Job/子进程，不结束其他 Codex。

AI 使用现有模型路由和远端发送授权。Codex 仅访问独立的本次实验 capsule，禁用 Shell/文件修改/其他 MCP，多项目线程不共享。设计结果经过重新校验，仅保存 Proposal；数值和形式化假设须作者逐项确认。AI 待批准操作沿用 V2.8 的 Session/Confirmation/Action Dispatcher。

受控助手增加六项实验操作：list_world_experiments、create_experiment_draft、check_experiment_configuration、request_experiment_design、request_experiment_run、open_experiment_report。实验执行请求是 Level 3；不能替作者冻结规则，不能写 Canon 或覆盖正式稿。前端排队回执不宣称任务已完成。

报告和来源快照属于私有项目元数据，由现有备份保护，不加入公开 Allowlist。开源许可证仍由所有者决定，不覆盖用户小说、文献、图片和私人实验。

V2.9.2 preserves the original 512 MiB owned-process budget and runtime timeout. Native numerical threads and CP-SAT workers are bounded to one. Author adoption creates existing inspiration/PENDING records, not a Canon/State commit. Rejected proposals cannot execute late.
