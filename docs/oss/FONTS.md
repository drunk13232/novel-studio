> Historical font/sample verification is described below; 2.24.0 reruns the locked resource copy/hash checks, not every PDF rendering sample.

# PDF 字体来源、分发与显示复核

## 来源与差异

四个 LiberationSans TTF 来自官方 npm 的 pdfjs-dist 6.3.289。下载包 SHA-512 与 package-lock.json 的完整性字段一致；四文件与原开发资源及原发行资源逐字节一致，没有本机损坏。构建脚本只复制资源，不转换字体。

与另一份官方 Liberation 1.07.4 二进制相比，字体内部表、字形数量和顺序不同。FontTools 分别核对四种样式，每种的 668 个共同 Unicode 字符轮廓均完全相同。差异存在于上游不同分发构建，不能据此宣称四字体损坏，也不能任意替换：PDF.js 的字形顺序与宽度映射依赖原文件。没有核实原编译工具链或逐字节可重复构建。

## 许可与源码

采用未修改的官方 npm 资源。LICENSE_LIBERATION 为 GPL-2.0 带 Liberation 字体例外，独立于 PDF.js 的 Apache-2.0 和项目 Apache-2.0 许可。保留原条款，并随候选提供完整官方 1.07.4 SFD 源码包、COPYING、License.txt、AUTHORS、Makefile/导出脚本及来源校验；位置是 desktop/third-party/font-source，Windows 为 _internal/resources/third-party/font-source。字体是可以替换的本地资源，不编译进 EXE。原源码包的许可和源码文件均保持原样。

GPL 字体例外及原条款按随附全文解释；项目许可不覆盖这些资源。该记录不是对所有依赖的笼统法律保证。

## 实际修复与验证

生产后端原先只挂载 /assets，没有挂载构建已生成的 /pdf，导致中文 CMap 404。已通过现有 FastAPI StaticFiles 挂载限定的 dist/pdf，不扩大文件读取范围。最终候选恢复全部官方字体、CMap 和 WASM。

独立安装环境的应用文献库实际打开原创双页样本，检查非嵌入中英文字体、中文标点、四种英文样式和第二页切换；修复前中文加载失败，修复后文字和页面可见。范围是这个样本，不是所有 PDF、所有特殊字形和全部打印导出均已验证。真实中文输入法、DPI、加密/损坏 PDF 和复杂字体仍按 Preview 边界披露。

来源：
- [官方 npm 版本](https://www.npmjs.com/package/pdfjs-dist/v/6.3.289)
- [PDF.js 固定版本字体说明](https://github.com/mozilla/pdf.js/blob/v6.3.289/external/standard_fonts/README.md)
- [Liberation 1.x 官方项目](https://github.com/liberationfonts/liberation-1.7-fonts)
- [官方 1.07.4 SFD 源码](https://releases.pagure.org/liberation-fonts/liberation-fonts-1.07.4.tar.gz)
