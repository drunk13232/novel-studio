# 码字看板 / Writing Dashboard

Novel Studio 2.21.4 Preview。扩展原有写作统计、字数保存事件、项目目标和日记，不另建事件数据库，不迁移旧项目。

## 怎样使用

在作品中通过完整导航的「码字看板」、全部工具搜索，或正文上方的迷你进度打开。书架卡片显示本书今日保存净增。原来的今日、本周、本月、正文总字数和趋势仍保留。

- 最近365天热力图：按每日保存净增分档。鼠标悬停查看日期、净增和日记；负净增使用减号、斜纹及虚线，不能与没有保存混淆。支持方向键、Home、End、回车选择日期。
- 连续纪录：当日净增严格大于零才算码字日。今日净增为零时，当前连续纪录可延续至昨天；今日为负则中断。历史最长纪录、累计码字日和最高正净增日期只来自实际记录。
- 时段分布：全部已记录保存事件按 UTC+08:00 的24小时归组。这是保存时点分布，不是写作时长、键盘活动或专注时间。
- 配速：使用包含未写作日的最近7个自然日日均净增。优先采用看板全书目标，否则用作品已设置的目标汉字数。日均不大于零时显示「暂无配速」，没有目标时提示设置；预测只作当前条件下的参考。
- 来源：手动、AI接受、版本恢复、未知来源分别展示正增、删除和净增。占比图的分母仅为手动与AI接受的正向保存净差，不能解释为原创比例；粘贴内容同样属于手动保存。日净增及当前正文库存不是手打字数。
- 日、周、卷、书目标：进度条按已保存目标计算，超过目标显示为100%，负进度条最低为0但文字仍显示真实负数。目标和日记刷新不覆盖正在编辑的输入。
- 上周总结：固定为上一个完整周一至周日的净增、正净增日数、最高正净增日期。无记录时不补造历史。

## 保存刷新

正文成功保存、AI候选真实接受及版本恢复后，通过本地 `novel-writing-metrics-changed` 通知刷新轻量进度。失败、拒绝、草稿恢复缓存、候选生成和修订稿初始复制不会冒充正文保存。独立修订稿后续实际编辑保存计本次净差，全书库存复用现有成书目录所选的当前正文，每章/篇只选一份，不把修订副本叠加累计。

写作台小组件不轮询、不读取整本正文。打开/重新打开及跨日后窗口恢复可见时读取一次本地元数据。日目标由下向上跨过时，按项目和日期只提示一次，重复保存不弹；不自动调整目标。一次性提醒标志只存本机界面存储，统计事件和日记仍保存在原项目 `metadata/studio/writing.json`。清除界面存储后提醒标志会重置。

## 兼容与隐私

事件仍使用原 `NET_SAVE_DIFF` 格式，旧记录保持不变。兼容旧的缺少method字段记录及AI来源别名。旧版 `OBSERVED_EXTERNAL_ESTIMATE` 只保留，明确排除在码字统计外；打开看板不再扫描后制造这些事件。未知/异常/未来日期事件不冒充已验证保存。

统计和日记只由本地项目接口读取，不进入AI上下文，不上传、不调用模型、不跨作品汇总。时区沿用既有 UTC+08:00，避免旧项目日界线变化。实际正文、Final、Canon、State、Knowledge及文件格式不因本功能改变。

## 接口与实现

- `GET /api/projects/{p}/experience/statistics`：保留原响应字段，新增calendar、streaks、hourly、pace、sources、last_week、quality及goal_progress。
- `GET /api/projects/{p}/experience/writing-progress`：只读统计元数据，用于正文迷你进度。
- `GET /api/studio/library`：每本书附带同口径writing_progress，复用已有元数据读取，避免每本书额外请求。
- 原goals/daily-note写接口继续复用，成功回执后刷新。
- Recharts继续懒加载；没有新增前端或后端依赖。使用既有主题和i18next，新文案简中、英语完整，其他语言回退。图表和样式遵循reduced-motion。

## 本轮验证边界

用户明确要求不操控电脑，本轮不执行浏览器或桌面点击、输入和窗口操作。LOCAL逻辑/API/纯内存DOM检查与Windows生产构建分开报告；构建成功不代表桌面交互验收。

针对性检查：

```powershell
python -m pytest web/backend/tests/test_writing_dashboard.py web/backend/tests/test_writing_dashboard_api.py -q
node web/frontend/scripts/check-writing-metrics.mjs
node web/frontend/scripts/check-writing-client.mjs
```

前端脚本复用已安装的TypeScript与Node内置断言。隔离执行记录位于private-checks，既不进入源码候选，也不进入Windows包。
