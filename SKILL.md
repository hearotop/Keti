---
name: keti
description: 以任务书驱动方式管理端到端科研课题：初始化课题元数据，盘点本地或云端资料，规划学术检索，生成带依赖和验收标准的 DAG 模块任务书，协调代码、实验、Archify 图表、报告及 PPT，校验真实数据与资产溯源，并依据导师反馈增量更新受影响任务。用于毕业设计、科研项目、实验课题、论文与组会汇报的规划、执行、续做、审查或变更管理。
---

# Keti

以项目事实为依据维护科研课题，不把计划、证据和结论混在一起。先建立任务书，再执行；先验证交付物，再解锁下游。

## 读取资源

- 初始化或修改课题时，读取 [references/workflow.md](references/workflow.md)。
- 创建或审查任务书时，读取 [references/task-contract.md](references/task-contract.md)。
- 登记图表、文献、实验指标或检查报告/PPT真实性时，读取 [references/evidence-contract.md](references/evidence-contract.md)。
- 需要调用其他 Skill 时，读取 [references/integrations.md](references/integrations.md)。
- 使用 `assets/` 中的模板作为起点；不要改写 Skill 自身模板。

## 核心工作流

1. 定位项目根目录。优先使用用户指定目录；否则使用当前工作目录。把所有运行产物写入课题项目，不写入本 Skill 目录。
2. 检查 `project.yaml`。若不存在，收集课题名称、方向、专业信息、导师信息与偏好、已有资料位置、目标交付物、截止时间及约束。**必须询问“本课题是否需要生成或修改代码？”**，除非用户已经明确说明。把答案记录为 `capabilities.code_generation: true|false`；不得根据专业方向自行推断。其他未知字段明确记为 `unknown`，仅追问会阻塞当前阶段的字段。
3. 按用户选择运行环境探针：
   `python <skill-dir>/scripts/probe_environment.py --project-root <project-root> --code-generation <yes|no>`。
   把缺失能力分为 `required`、`optional`、`unavailable`，给出降级路径；不得因可选依赖缺失阻塞规划。
4. 初始化新项目时运行：
   `python <skill-dir>/scripts/init_project.py --root <project-root> --title <title> --code-generation <yes|no>`。
   已有项目只补齐缺失结构，禁止覆盖用户文件；执行前用 `--dry-run` 预览。
5. 盘点本地资料、代码、数据、模板和云端链接。建立 `sources/source_registry.json`。云端资料必须先获取可访问内容；链接本身不是证据。
6. 制定检索计划。优先权威论文库、开放 API、出版社页面和专业组织；记录查询词、日期、来源及访问状态。遇到登录、验证码、付费墙或版权限制时停止绕过，改用摘要、开放版本或请用户提供合法副本。
7. 生成 `master_task.md` 和 `tasks/*.md`。任务粒度按实际课题裁剪，不强制生成无关模块。若 `code_generation` 为 `false`，不得创建代码架构、实现、构建、单元测试等任务，也不得为这些能力安装依赖；实验任务改为依赖用户已有数据、仪器记录或既有软件输出。每个任务必须声明依赖、输入、步骤、交付物、机器可验证验收规则、证据、状态和变更历史。
8. 只执行依赖已完成的任务。执行前把状态置为 `in_progress`；完成后运行：
   `python <skill-dir>/scripts/verify_deliverables.py --task <task-file> --project-root <project-root>`。
   验证通过才置为 `completed`。失败时记录实际错误和下一步，最多连续自修复三次；仍失败则置为 `blocked` 并向用户说明所需输入或权限。
9. 需要代码时，代码与计算实验必须输出可复现命令、原始日志、结构化指标和图表生成脚本；不需要代码时，保留数据采集方法、原始记录、处理过程及人工操作说明。禁止把预期结果写成实测结果。报告和 PPT 只能使用清单中已登记且本地存在的真实资产。
10. 收到导师反馈或需求变更时，先更新直接受影响任务，再运行：
    `python <skill-dir>/scripts/invalidate_tasks.py --project-root <project-root> --changed <task-id> --apply`。
    审阅失效列表后仅重做传递下游；纯排版变更不得重跑实验，算法或实验设计变更必须使相关报告与 PPT 失效。
11. 汇报阶段优先调用可用的 PPT Master Skill，并传入真实模板、已验证图表和逐页讲稿要求；无该 Skill 时生成逐页 Markdown 大纲与 speaker notes，不伪造 `.pptx`。
12. 最终汇报已完成、阻塞、失效和待用户决策的任务，以及关键产物的真实路径。

## 强制规则

- 保留用户已有文件与未提交修改；所有会覆盖、下载、安装、联网写入或发布的动作均遵循当前环境授权。
- 不静默下载或安装第三方 Skill。先扫描当前已提供的 Skill；能力缺口再提出候选、来源、许可证、权限和风险，获得授权后使用受支持的安装机制。
- 不把搜索摘要当作已核验事实。每个外部事实保留可追溯引用；每个图表区分 `external_reference`、`generated_diagram` 与 `local_experiment`。
- 不以固定文件大小或“300 DPI”替代内容验证。图片验收同时检查存在性、可读性、来源、生成方式和任务相关性。
- 不在证据缺失时生成占位数据、虚构引用、虚构实验结果或假图。

## 推荐任务 DAG

需要代码时可选择：`literature -> architecture -> implementation -> experiments -> report -> presentation`。不需要代码时使用裁剪链：`literature -> methodology/data collection -> analysis -> report -> presentation`。允许文献与资料盘点并行；报告依赖已验证证据；演示依赖报告结构和已验证资产。
