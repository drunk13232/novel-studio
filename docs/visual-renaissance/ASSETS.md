# 主题美术资源与分发边界

本轮新增资源没有从商业软件截图、概念图、第三方角色模型或未知素材站裁取。

## 栅格插画

`manuscript`、`ink`、`observatory`、`gothic`、`cyber`、`greenhouse` 六幅插画由内置 image_gen 按本轮提示词生成。提示词在 `generation.json`；原始 PNG 在 `art-source/`，实际运行的 WebP 在 `web/frontend/public/themes/`。不声称它们是人工分层 PSD 或矢量原画；PNG 保留像素源稿，SVG 装饰则可逐节点编辑。

运行资源为 1440×480 的 WebP；压缩仅涉及尺寸与格式，不将整张 UI 概念图切片。插画不包含私人小说、人物或朝武芳乃/蕾姆的角色形象。项目中其他历史素材仍沿用原有资源清单和许可记录。

## 矢量原稿

`folio.svg`（书页）、`mountains.svg`（远山）、`orbits.svg`（星轨）、`arch.svg`（尖拱）、`circuit.svg`（电路）、`fern.svg`（植物）、`petals.svg`（花瓣）、`lace.svg`（蕾丝）、`typeset.svg`（排版）、`grid.svg`（仪表网格）和 `paper-grain.svg`（纸纹）均为本轮程序编写的独立 SVG。没有外部图像、脚本、在线字体或动态网络资源；开发者可以直接编辑节点、路径和线宽。

## 字体、图标与其他组件

字体只引用本机字体及既有系统回退，不分发微软字体。图标继续使用已安装的 Lucide，弹窗继续使用 Radix，动画使用已有 Motion；其必要声明由原有许可证收集流程保留。没有复制 tweakcn 预设、Mantine/shadcn 组件源码或商业主题资源。

私人角色立绘、Live2D Core、模型、贴图、动作和语音仍在原有个人数据/授权资源范围内。本轮没有将它们加入主题清单、源码候选或 Windows ZIP。

本说明记录实际来源，不代替所有者决定整个 Novel Studio 的最终开源许可证和版权主体，也不为第三方角色资产授予额外公开许可。
