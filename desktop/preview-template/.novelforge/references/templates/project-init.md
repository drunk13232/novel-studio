# 📋 项目初始化模板

> 新建小说项目时，复制此模板并填写所有 `[占位符]` 字段。完成后保存为 `project.json`。

---

## 项目配置文件 (project.json)

```json
{
  "title": "[小说名称，建议2-6字，朗朗上口]",
  "genre": "[主类型：玄幻/修仙/都市/言情/科幻/悬疑/历史/游戏]",
  "subgenre": "[子类型：如 东方玄幻、都市重生、甜宠、星际战争等]",
  "target_wordcount": "[目标总字数，如 2000000 表示两百万字]",
  "target_platform": "[发布平台：起点中文网/番茄小说/晋江/纵横/刺猬猫/其他]",
  "tone": "[整体基调：热血/轻松/黑暗/温馨/搞笑/严肃/史诗]",
  "core_selling_point": "[一句话卖点：读者为什么要追这本书？如"扮猪吃虎的爽感+缜密的力量体系"]",
  "reference_works": [
    "[参考作品1，如：斗破苍穹]",
    "[参考作品2，如：诡秘之主]",
    "[参考作品3，可选]"
  ],
  "target_audience": "[目标读者画像：性别偏好/年龄段/阅读习惯，如 男频18-30岁、追求爽感]",
  "update_frequency": "[更新频率：日更/隔日更/周更，每次字数如 日更4000字]",
  "created_at": "[创建日期，格式 YYYY-MM-DD]",
  "current_phase": "Phase 1",
  "current_volume": 1,
  "current_chapter": 0,
  "total_wordcount": 0
}
```

---

## 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `title` | ✅ | 书名，直接影响读者第一印象，需体现类型特征 |
| `genre` | ✅ | 决定加载哪套类型模板和写作规则 |
| `subgenre` | ✅ | 细分类型，影响剧情节奏和套路参考 |
| `target_wordcount` | ✅ | 总字数规划，用于计算卷章分配 |
| `target_platform` | ✅ | 不同平台有不同的读者口味和审核规则 |
| `tone` | ✅ | 统一全书语言风格的基准 |
| `core_selling_point` | ✅ | 写作过程中反复对照的核心卖点，防止跑偏 |
| `reference_works` | 建议 | 参考作品帮助AI理解你想要的风格方向 |
| `target_audience` | ✅ | 决定用词深度、情感密度、节奏快慢 |
| `update_frequency` | 建议 | 帮助规划写作进度和章节库存 |
| `current_phase` | 自动 | 当前所处的创作阶段（Phase 1-10） |
| `current_volume` | 自动 | 当前正在创作的卷数 |
| `current_chapter` | 自动 | 当前已完成的章节数 |
| `total_wordcount` | 自动 | 已完成的总字数，自动累加 |

---

## 初始化后自动创建的目录结构

```
[小说名]/
├── project.json                 ← 本文件，项目全局配置
├── settings/
│   ├── world-setting.md         ← 世界观设定
│   ├── power-system.md          ← 力量体系详解（如需单独拆分）
│   ├── geography.md             ← 地理图志（如需单独拆分）
│   ├── rules.md                 ← 硬性规则（合约体系）
│   ├── relationship-map.md      ← 人物关系图谱
│   └── characters/
│       ├── [主角名].md          ← 主角角色卡
│       └── [女主/重要配角].md   ← 各配角角色卡
├── outlines/
│   ├── master-outline.md        ← 全局大纲（所有卷的概要）
│   └── volumes/
│       ├── vol-01/
│       │   ├── volume-outline.md    ← 第一卷大纲
│       │   ├── chapter-001-outline.md ← 第1章细纲
│       │   ├── chapter-002-outline.md ← 第2章细纲
│       │   └── ...
│       └── vol-02/
│           └── ...
├── chapters/
│   └── vol-01/
│       ├── ch-001.md            ← 第1章正文
│       └── ...
├── state/
│   ├── global-state.md          ← 全局状态快照（每章更新）
│   ├── foreshadow-tracker.md    ← 伏笔追踪器
│   └── timeline.md              ← 时间线记录
└── reviews/                     ← 质检审查报告
```

> **提示**：`current_phase`、`current_volume`、`current_chapter`、`total_wordcount` 四个字段由系统自动维护，请勿手动修改。
