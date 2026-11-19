# 机构模板契约

## 目标

把机构模板中**可执行、可验证**的格式约束提取为结构化档案，供骨架生成、逐节写作和最终组装使用。模板是格式权威，不是内容来源。

## 支持的输入

| 类型 | 扩展名 | 提取重点 |
|---|---|---|
| LaTeX 示例稿 | `.tex` | 文档类、宏包、章节命令、摘要/关键词、引用与图表环境 |
| LaTeX 类文件 | `.cls`、`.sty` | 页面、字体、标题层级、页眉页脚、必需命令 |
| LaTeX 模板包 | `.zip` | 先列出内容；解压后重新扫描 `.tex` / `.cls` |
| Word 模板 | `.docx`、`.dotx` | 页面、页边距、样式表、标题层级、页眉页脚、占位文本 |
| 投稿指南 | `.pdf`、`.md`、`.txt`、网页正文 | 页数/字数、匿名、章节、引用、声明、文件命名 |

PDF 只做文本级证据。无法提取文字时，请用户提供指南正文、可访问页面或官方模板，不根据文件外观猜测要求。

## 档案字段

`template/profile.json` 至少包含：

```json
{
  "schema_version": 1,
  "generated_at": "2026-11-19T12:00:00+08:00",
  "sources": [],
  "analyses": [],
  "merged": {
    "document_class": null,
    "packages": [],
    "page": {"size": null, "margins_cm": {}, "columns": null},
    "fonts": {"body": null, "heading": null, "size_pt": null},
    "line_spacing": null,
    "sections": [],
    "sections_source": null,
    "citation": {"style": null, "bibliography_style": null},
    "figures": {"caption_position": null, "numbering": null},
    "tables": {"caption_position": null, "numbering": null},
    "required_sections": [],
    "declarations": [],
    "limits": {"pages": null, "words": null, "abstract_words": null},
    "anonymity": "unknown",
    "build": {"engine": null, "bibliography_tool": null}
  },
  "unknowns": [],
  "anomalies": [],
  "confidence": "medium"
}
```

字段无法从输入中确认时填 `null` 或写入 `unknowns`，不得猜测。`confidence` 取值：`high`（多份显式模板互证）、`medium`（单一模板或示例稿）、`low`（仅指南文字或 PDF 文本）。

## LaTeX 提取规则

- `\documentclass[options]{class}`：记录类名与选项。
- `\usepackage[options]{pkg}`：记录宏包，重点识别 `geometry`、`fontspec`、`ctex`、`titlesec`、`natbib`、`biblatex`、`booktabs`、`caption`、`setspace`。
- 页面：`geometry` 的 `a4paper`、`letterpaper`、`margin`、`top`、`bottom`、`left`、`right`、`textwidth`、`columnsep`。
- 字体：`\setmainfont`、`\setsansfont`、`\setmonofont`、`ctex`、`mathptmx`、`newtxtext`、`lmodern` 等。
- 章节：按出现顺序记录 `\part`、`\chapter`、`\section`、`\subsection`、`\subsubsection` 的层级与标题；区分带星号与编号版本。
- 引用：`\bibliographystyle`、`biblatex` 的 `style=`、`natbib` 选项、`\bibliography` 路径。
- 图表：`\caption` 位置、`\label` 规则、子图宏包、表格宏包。
- 必需内容：`abstract`、`keywords`、`acknowledgements`、`appendix`、数据/代码可用性、利益冲突、作者贡献。
- 构建：记录模板说明中的引擎（`pdflatex`、`xelatex`、`lualatex`）和参考文献流程（BibTeX/Biber）。

## Word 提取规则

- 读取 `word/styles.xml` 的 `docDefaults` 与命名样式，记录字体、字号、加粗、斜体、大纲级别。
- 读取 `word/document.xml` 的 `sectPr`，记录页面尺寸、页边距、分栏、页眉页脚距离。
- 识别 `Heading 1` 到 `Heading 4` 及模板自定义标题样式。
- 提取示例稿中的标题文本作为章节骨架；提取页眉页脚与占位文本。
- `.dotx` 与 `.docx` 使用同一解析逻辑；生成时必须以模板为基准创建新文档，保留样式表。

## 模板保护

- 不修改 `.cls`、`.sty`、`.dotx`、示例 `.docx` 原件。
- 所有写作在 `sections/` 或 `build/` 副本中进行；记录相对模板的改动点。
- 不得删除模板的页眉页脚、编号域、样式继承、内容控件或水印等继承对象。
- 模板中的占位文本必须替换为真实内容或显式缺口标记，不能保留为成稿内容。

## 冲突处理

模板与用户大纲冲突时：

1. 格式、章节命名、长度和必需声明以模板为准。
2. 论证顺序、重点和取舍以用户大纲为准。
3. 无法同时满足时列出两种方案，说明对内容的影响，由用户决定。
4. 不得为了套模板而静默删除用户要求的关键论证，也不得为了保留论证而破坏模板格式。
