# Keti

Keti 是一个面向毕业设计、科研项目、实验课题、论文和组会汇报的 Agent Skill。它采用任务书驱动架构（Task-Driven Architecture），先建立带依赖与验收规则的任务 DAG，再逐项执行、验证和更新，减少长周期科研工作中的上下文漂移、无效返工和虚构数据。

仓库地址：[https://github.com/hearotop/Keti](https://github.com/hearotop/Keti)

## 核心能力

- 初始化课题名称、方向、专业、导师偏好、资料位置、交付物和约束。
- 明确询问是否需要生成或修改代码，并据此裁剪工作流。
- 将课题拆分为带依赖、输入、交付物和机器验收规则的模块任务书。
- 建立文献、外部参考图、架构图和本地实验图的溯源清单。
- 验证任务交付物，失败时记录实际错误并限制重复尝试。
- 根据导师反馈计算受影响的下游任务，只重新执行必要部分。
- 联动 [Archify](https://github.com/tt-a1i/archify.git) 生成架构、流程、时序和状态图。
- 联动 [PPT Master](https://github.com/hugohe3/ppt-master.git) 使用真实模板、实验图表和讲稿生成汇报材料。
- 只读发现本地 Skill；第三方 Skill 必须经过来源、许可证和权限审查后再安装。

## 两种任务流程

需要代码时，Keti 可采用：

```text
文献调研 → 系统架构 → 代码实现 → 实验 → 报告 → 汇报
```

不需要代码时，Keti 自动跳过代码架构、实现、构建和单元测试：

```text
文献调研 → 研究方法/数据采集 → 分析 → 报告 → 汇报
```

是否生成代码由用户明确决定，Keti 不会根据专业方向自行推断。

## 安装

将仓库克隆到 Codex Skills 目录：

```bash
git clone https://github.com/hearotop/Keti.git ~/.codex/skills/keti
python -m pip install -r ~/.codex/skills/keti/requirements.txt
```

也可以将仓库放入其他支持 `SKILL.md` 的 Agent Skill 目录。具体发现和调用方式以所使用的 Agent 平台为准。

## 快速开始

在支持 Skills 的 Agent 中输入：

```text
使用 $keti 初始化我的课题。课题名称是《……》，方向是……，专业是……，导师偏好……。这个课题不需要生成代码，需要完成文献综述、数据分析、项目报告和汇报 PPT。
```

如果没有说明是否需要代码，Keti 会先询问：

```text
本课题是否需要生成或修改代码？
```

初始化脚本也可以单独运行。建议先预览：

```bash
python scripts/init_project.py \
  --root /path/to/research-project \
  --title "课题名称" \
  --code-generation no \
  --dry-run
```

确认后移除 `--dry-run`。脚本只补齐缺失结构，不覆盖已有文件。

## 生成的课题结构

```text
research-project/
├── project.yaml                 # 课题元数据和代码生成选择
├── master_task.md               # 总任务书与 DAG
├── tasks/                       # 模块任务书
├── sources/
│   └── source_registry.json     # 文献和资料登记
├── experiments/
│   ├── data/
│   ├── logs/
│   └── scripts/                 # 仅代码模式创建
├── assets/
│   ├── manifest.json            # 资产溯源清单
│   ├── external_references/
│   ├── generated_diagrams/
│   └── local_experiments/
├── reports/
├── presentations/
├── templates/
├── src/                         # 仅代码模式创建
└── tests/                       # 仅代码模式创建
```

实际目录和任务会按课题需要裁剪。

## 工具脚本

| 脚本                                 | 用途                                    |
| ------------------------------------ | --------------------------------------- |
| `scripts/init_project.py`          | 非覆盖式初始化课题目录和基础清单        |
| `scripts/probe_environment.py`     | 只读检查当前模式所需的环境能力          |
| `scripts/verify_deliverables.py`   | 执行任务书中的文件、JSON 和命令验收规则 |
| `scripts/invalidate_tasks.py`      | 计算并标记变更任务的传递下游为`stale` |
| `scripts/discover_local_skills.py` | 在显式指定的目录中只读发现本地 Skill    |

示例：验证一个任务的交付物：

```bash
python scripts/verify_deliverables.py \
  --task /path/to/research-project/tasks/04-analysis.md \
  --project-root /path/to/research-project
```

示例：预览导师反馈影响范围，并在确认后应用：

```bash
python scripts/invalidate_tasks.py \
  --project-root /path/to/research-project \
  --changed 04-analysis

python scripts/invalidate_tasks.py \
  --project-root /path/to/research-project \
  --changed 04-analysis \
  --apply
```

## 可选 Skill 集成

| Skill      | 上游仓库                                                       | 用途                                      |
| ---------- | -------------------------------------------------------------- | ----------------------------------------- |
| Archify    | [tt-a1i/archify](https://github.com/tt-a1i/archify.git)         | 架构图、流程图、时序图、数据流图和状态图  |
| PPT Master | [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master.git) | 可编辑 PPTX、模板套用、真实素材编排与讲稿 |

这两个 Skill 均为可选集成。Keti 只在当前 Agent 环境已提供对应 Skill 时调用；若未安装，应先说明来源、许可证、权限和风险，并获得用户授权，不会静默下载或执行第三方代码。

## 真实性与安全规则

- 报告和 PPT 只能引用本地存在且已登记的真实资产。
- 外部参考图、生成式架构图和本地实验图必须分类管理。
- 搜索摘要不是已核验事实；外部事实必须保留可追溯引用。
- 缺少数据时不得生成占位数据、假图、虚构引用或虚构实验结果。
- 不绕过登录、验证码、付费墙或版权限制。
- 不静默下载、安装或执行第三方 Skill；需要用户授权并遵循运行环境权限。

## Skill 结构

```text
Keti/
├── SKILL.md
├── agents/openai.yaml
├── assets/
│   ├── master-task-template.md
│   └── task-template.md
├── references/
│   ├── workflow.md
│   ├── task-contract.md
│   ├── evidence-contract.md
│   └── integrations.md
├── scripts/
├── requirements.txt
└── LICENSE
```

## 许可证

本项目使用 [Apache License 2.0](LICENSE)。
