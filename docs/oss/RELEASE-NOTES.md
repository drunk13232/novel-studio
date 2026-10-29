# Novel Studio 2.24.10 Director Save & Navigation Preview

## 简体中文

本版修复现有创作指挥台，不新增 Agent、依赖或数据格式。

- 查看“我的流程”再返回时，全书目标与说明草稿保留，键盘焦点返回原入口。
- 保存回执只确认本次提交；等待期间继续输入的内容保留为未保存修改。候选选择与刷新不清空无关草稿。
- 关闭、上下文、世界实验室、Diff 和 Python 交接继续经过作者的离开保护；待保存期间不能误丢输入。
- 窗口关闭后，迟到的候选或 Python 回执不再自动打开新界面。已实际保存的候选仍留在原项目，不自动采用。
- 其他窗口改变记录后，暂存、复核和改写拒绝静默使用作者尚未查看的新版本。

### 验证边界

两组隔离浏览器检查分别覆盖保存回执和工作台交接，各 9 项通过。请求使用本地真实业务服务；延迟回执和一次保存失败由测试注入，并非真实网络事故。前端生产构建通过。没有新调用远端模型，没有采用小说候选。验证资料只使用公开演示模板，不含私人作品。

本轮不操作用户电脑界面。原生窗口交互、实体中文输入法、系统 DPI、真实语音及新远端 AI 调用均未重新验收。Windows 包验证另行记录在发布记录中；构建或 worker 通过不等于 GUI 通过。保持 Preview / PARTIAL。

## English

This update repairs the existing Creative Director without adding agents, dependencies or data formats.

- Visiting My Workflows retains book-target and reason drafts and restores trigger focus.
- Receipts acknowledge submitted values only. Later typing stays unsaved; selection and refresh preserve unrelated drafts.
- Existing author leave protection covers close, context, world lab, Diff and Python handoffs, including pending saves.
- Late receipts cannot reopen a closed view. Valid staged proposals remain in their original project and are not adopted.
- Unseen record revisions are rejected before staging, review or rewrite.

Two isolated headless browser suites passed nine checks each against the actual local domain services. Delayed receipts and one failed save are controlled test injections. Production frontend build passed. No new remote-model call or author adoption occurred. Fixtures use public demonstration data only.

Native GUI, physical Chinese IME, system DPI, installed voices and new remote-AI calls were not reaccepted. Packaged-worker or build success does not establish GUI acceptance. This remains Preview / PARTIAL.
