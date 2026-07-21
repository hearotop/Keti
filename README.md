# 🎓 Keti (`keti`)

> 🚀 **An Enterprise-Grade, Task-Driven Agent Skill for End-to-End Academic Research Automation.**
> 
> **Keti** 基于 **Agent Skills 开放标准 (`SKILL.md`)** 构建，专为学术研究、系统实验、架构绘图 (Archify)、文献检索与汇报 PPT 自动生成打造。

---

## 🌟 核心特性 (Key Features)

- **📋 任务驱动开发架构 (Task-Driven Architecture / TDA)**
  - 将复杂的科研工作流拆解为有向无环图 (DAG) 任务文件 (`01_task_literature.md`, `02_task_architecture.md` 等)。
  - 规避 LLM 运行过程中的上下文漂移 (Context Drift) 问题。
- **📊 真实资产强绑定与双库校验 (Zero-Hallucination Asset Linking)**
  - 所有报告、论文与 PPT 引用的图片必须存在于本地并注册在 `manifest.json` 中。
  - 防止传统 AI 遗留的“幻觉图片”或虚构实验数据。
- **🎨 原生 Archify 架构绘图集成 (`Archify Skill`)**
  - 支持声明式代码绘图 (Diagrams-as-Code)。
  - 自动调用 `Archify Skill` 将编译为高分辨率 UML 流程图、时序图与状态机图。
- **🔍 动态 Skill 探索与运行时挂载 (Dynamic Discovery & Auto-Download)**
  - 执行过程中如发现缺少特定功能（如电路波形绘制、高阶 LaTeX 导出），自动检索本地 `./skills/` 及开源社区。
  - 自动克隆符合开源许可（MIT/Apache-2.0）的 Skill 并即时注入上下文。
- **🔄 增量反馈与防死循环引擎 (Incremental Feedback & Circuit Breaker)**
  - 导师提出修改意见后，仅增量重编译受影响的下游任务文件。
  - 单个任务执行失败上限 3 次，自动输出错误日志并触发告警保护。

---

## 📂 项目目录结构 (Directory Structure)

```directory
Keti/
├── SKILL.md                         # Keti 核心规范与 System Prompt
├── README.md                        # 项目说明文档
├── LICENSE                          # 开源协议 (MIT)
├── requirements.txt                 # Python 依赖清单
├── templates/
│   ├── master_task_template.md      # 课题主任务书模板
│   └── lab_presentation_style.pptx  # 默认组会汇报 PPT 模板
├── scripts/
│   ├── probe_environment.py         # 系统环境与 Skill 依赖探针
│   ├── verify_deliverables.py       # 交付物死循环校验脚本
│   └── skill_discovery.py           # 动态 Skill 探索与下载工具
└── assets/
    └── manifest.json                # 图表与实验数据元数据索引库
