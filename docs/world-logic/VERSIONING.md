# Versioning & Reproduction 1.0

schema_version 是开放格式版本，adapter_version 是内置执行契约版本。实验 draft 可以修改；确认会产生不可覆盖的 vN.json，保存完整定义、SHA-256 指纹、独立验收指纹、确认时间/原因及来源。

每次运行保存实际输入、假设、确认版本、求解器/依赖版本、执行时间、环境、输出、触发规则、未知项、错误和限制。AI 解释另存 Proposal sidecar，不修改原确定性报告。检测来源文件哈希变化时提示重新运行，旧报告保持原样。

反事实复制已确认 Baseline，记录 baseline_id/version 和修改原因；只改变指定输入，验收规则默认保持一致。比较列出输入和规则变化、输出及状态。规则变化不能忽略后宣布实验从 FAIL 改为 PASS。

敏感性分析最多 32 点，仅适用于有明确公式的数值输入，返回每个样本状态和输出。图形不补造缺失值；离散过渡区间不是精确临界值。未建模因素仍需人工解释。

现有 TaskManager 状态不重构：QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED/INTERRUPTED。数学 FAIL 和 INCONCLUSIVE 仍可能是成功执行的任务，查看报告 status；执行错误映射 FAILED，取消报告为 NOT RUN。恢复不会自动重启旧任务。

Scenarios record baseline definition and normalized acceptance fingerprints. Comparison verifies the frozen baseline instead of unconditionally asserting preservation. Legacy records stay readable; optional defaults do not rewrite historical files.
