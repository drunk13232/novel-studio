# Visual Renaissance — 技术与设计决策

基线 2.16.2；交付 2.17.0。主题扩展不重写业务，也不引入新的 UI 框架。

## 实际研究与取舍

- [shadcn/ui](https://github.com/shadcn-ui/ui) 与其 [Theming 文档](https://ui.shadcn.com/docs/theming)：采用背景/前景、强调色/文字色的成对语义 Token 思路。保留项目普通 CSS，不迁入 Tailwind 或复制整套组件。仓库 MIT。
- [tweakcn](https://github.com/jnsahaj/tweakcn)：参考可视化主题预览和少量高价值自定义参数。未复制预设、源码或图片，未运行其 Node 服务。仓库 Apache-2.0；本项目的最终许可证仍由所有者决定。
- [Mantine](https://github.com/mantinedev/mantine) 和 [Theme object](https://mantine.dev/theming/theme-object/)：参考统一的颜色、间距、圆角和组件表现，未安装重叠的组件库。仓库 MIT。
- [Radix Primitives](https://github.com/radix-ui/primitives)：复用已安装 `@radix-ui/react-dialog 1.2.0`（MIT）的焦点、Escape 和弹窗语义，不自行实现复杂弹窗框架。
- [Motion](https://github.com/motiondivision/motion) 与 [accessible animations](https://motion.dev/docs/react-accessibility)：复用现有 `motion 14.0.0`（MIT）与 `MotionConfig`；系统减少动画、专注模式及原有动画关闭继续有效。没有持续背景动画或新渲染循环。主题换色以原子更新避免前景/背景过渡不一致造成短暂低对比。
- [Lucide](https://github.com/lucide-icons/lucide) 与 [License](https://lucide.dev/license)：复用 `lucide-react 1.54.0`（ISC；其派生来源按原声明保留），图标笔画一致。不下载其他图标或字体包。

已安装 React 19.3.0、Vite 7.3.7、TypeScript 5.9.3。实际版本从本地包清单核对；本轮没有升级或新增依赖。Windows WebView2 支持情况通过最终 EXE 的实际页面检查记录，不用浏览器通过替代。

## 一个主题，不止一组颜色

主题目录在 `web/frontend/src/themes.ts`。16 个稳定 ID 保留旧 9 项；7 项新增设计覆盖书页装帧、墨画留白、星图、哥特尖拱、精密仪表、植物温室与极简排版。

统一语义色板、字体层次、形状 Token 与主题家族样式分别承担颜色、标题、卡片/控件和构图差异。正文的用户字体、字号、行距与编辑宽度不被主题覆盖。主题不创建或重载编辑器，也不触发 AI。

主插画只在欢迎区和空状态；书架仅替换系统默认封面素材，不覆盖作者自己的封面。私人芳乃/蕾姆资源继续由原有本地资源服务提供，未复制到新资源目录。

## 预览与保存

画廊使用相同 Token 的实际 HTML/共享组件渲染缩略与大预览，不用生成图冒充 UI。示例评分为空值，不伪造评审结果。模型和完整编辑器不会为主题缩略图初始化。

预览仅存在 React 内存和 DOM；应用后由现有偏好写入队列持久化。取消或关闭设置恢复保存外观。收藏独立持久化。新增偏好可选且有默认值；旧主题 ID 不变，未知旧主题只在读取时安全回退，不因此改写旧文件。

主题 JSON 只包含稳定 ID 和白名单外观参数；32 KB 导入限制、颜色格式、整数范围和额外字段拒绝均有验证。不接受脚本、CSS、外部网址、模型、字体下载或文件路径。格式见 `web/frontend/public/themes/theme.schema.json`。

## 资源与性能

6 幅图由本轮内置 image_gen 制作，原始 PNG 与提示词保留；WebP 合计 590,418 字节。只做尺寸与格式压缩，没有截取概念图。独立 SVG 为可编辑原稿，不含外部依赖或脚本。资源清单逐项锁定 SHA-256。

主界面仅加载当前主题实际使用的图片；画廊图片使用原生 lazy 解码。隐藏主题不初始化 WebGL、模型或后台服务。当前实现不承诺浏览器立即回收所有已缓存解码图像；实际内存和启动证据在交付报告中单独说明。
