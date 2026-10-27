# Template Authoring Guide 1.0

1. 复制 examples 中一个真实可运行模板。
2. 使用新的 experiment_id；变量英文 id、中文 name，值明确或 null。
3. 写明假设与 origin。演示假设标为 DEMO / accepted=false，作者使用前自行接受。
4. 指定公式、依赖或约束，写明自然语言意义。
5. 配置验收类型、阈值、单位、依据和局限。
6. 在高级编辑中校验 JSON/YAML；另存草稿并确认版本后运行。

五个内置模板：旅行时间、事件顺序、资源收支、单位公式、自定义逻辑约束。所有示例参数虚构，不携带私人作品。模板不是 Canon 输入，也不迁移 Story Skills story.md。

分享默认为清空原值和私有来源。自行公开时还需检查名称、公式、阈值和报告结果。不得将真实世界参数未经证据审查用作经济或社会预测。

本版没有随机模拟引擎。seed 字段保留复现信息，报告明确 random_simulation=false，不能把它当作已经运行 Monte Carlo。

New executable examples: magic-consumption (20 remaining), author-gravity (g=2, energy=100 J), finite-schedule (one machine=7 h/FAIL, two machines=4 h/PASS). These are demonstration values, not Canon.
