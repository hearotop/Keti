# Skill 与工具联动

## 选择顺序

1. 使用当前会话已提供且匹配任务的 Skill 或连接器。
2. 使用本地确定性工具完成小型处理。
3. 能力仍缺失时，列出候选 Skill、来源、许可证、所需权限、预期输入输出和降级方案。
4. 仅在用户授权后安装；安装后读取其完整 `SKILL.md` 并遵循指令。

不得扫描任意用户目录、静默克隆仓库、自动执行未知脚本或自动 `pip install`。

## Archify

系统架构、工作流、时序、数据流或状态机图优先调用 `$archify`。输入清晰的节点、关系、边界、关键状态和输出位置。保留生成的 HTML/SVG 源产物，在 `assets/manifest.json` 登记为 `generated_diagram`。若不可用，保留 Mermaid/PlantUML 文本作为可编辑降级产物，不声称已经生成图片。

## PPT Master

已有 `.pptx` 模板或用户明确要求生成演示文稿时调用 `$ppt-master`。提供：模板路径、受众与时长、逐页目标、已验证资产路径、引用、speaker notes 要求。不得把外部参考图伪装成本地实验图。不可用时输出 `presentations/outline.md` 和 `presentations/speaker_notes.md`。

## 学术检索

优先开放、权威、可引用来源，如 Crossref、OpenAlex、Semantic Scholar、arXiv、出版社页面与专业组织。Google Scholar 可用于发现线索，但应尽量回到论文或出版社原始页面核验。不得绕过百度文库、IEEE、ACM 等站点的登录、验证码或付费限制。

## 文档与代码

读取 PDF、表格、日志和源码时保留原始路径；生成派生物时记录工具和命令。运行实验前确认命令的作用范围，按风险使用沙箱与授权机制。
