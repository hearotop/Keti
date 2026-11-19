# Keti

Keti 是一个面向毕业设计、科研项目、实验课题、论文和组会汇报的 Agent Skill。它采用任务书驱动架构（Task-Driven Architecture），先建立带依赖与验收规则的任务 DAG，再逐项执行、验证和更新，减少长周期科研工作中的上下文漂移、无效返工和虚构数据。

仓库地址：[https://github.com/hearotop/Keti](https://github.com/hearotop/Keti)

## 核心能力

- 初始化课题名称、方向、专业、导师偏好、资料位置、交付物和约束。
- 明确询问是否需要生成或修改代码，并据此裁剪工作流。
- 将课题拆分为带依赖、输入、交付物和机器验收规则的模块任务书。
- 用节点记忆图保留当前节点、导航历史和检查点，支持任意节点开始、跳跃与回溯。
- 建立文献、外部参考图、架构图和本地实验图的溯源清单。
- 验证任务交付物，失败时记录实际错误并限制重复尝试。
- 根据导师反馈计算受影响的下游任务，只重新执行必要部分。
- 联动 [Archify](https://github.com/tt-a1i/archify.git) 生成架构、流程、时序和状态图。
- 联动 [PPT Master](https://github.com/hugohe3/ppt-master.git) 使用真实模板、实验图表和讲稿生成汇报材料。
- 附带 Paper Composer Skill：按机构投稿模板和用户内容大纲，把已有实验证据组织成可校验的论文成稿。
- 只读发现本地 Skill；第三方 Skill 必须经过来源、许可证和权限审查后再安装。
- 按“用户资源 → 课题资源 → 本地缓存 → 可选远程包”发现 PPT 与图片，核心仓库不捆绑大文件。

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

任务 DAG 只表达依赖，不限制起点。已有任务即使尚未完成，用户也可以指定任意节点开始；依赖未完成时会提示缺失产物和返工风险。

## 节点记忆图

Keti 在每个课题的 `state/` 下维护节点记忆图：

- `progress_graph.json`：当前节点、导航栈、依赖缺口、访问次数和检查点索引。
- `progress_history.jsonl`：追加式记录开始、跳转、回溯、检查点和恢复事件。
- `checkpoints/`：图状态快照。

常用命令：

```bash
# 任务书新增或状态变化后同步
python scripts/progress_graph.py --project-root /path/to/project sync

# 查看当前节点、依赖缺口和整张图
python scripts/progress_graph.py --project-root /path/to/project status

# 从任意节点开始，或跳转到其他节点
python scripts/progress_graph.py --project-root /path/to/project start --node 04-analysis
python scripts/progress_graph.py --project-root /path/to/project jump --node 06-presentation --reason "先准备汇报骨架"

# 沿导航历史回溯 / 前进
python scripts/progress_graph.py --project-root /path/to/project back --steps 1
python scripts/progress_graph.py --project-root /path/to/project forward --steps 1

# 保存或恢复图记忆
python scripts/progress_graph.py --project-root /path/to/project checkpoint --note "实验前基线"
python scripts/progress_graph.py --project-root /path/to/project restore --checkpoint <id>

# 回退任务状态，可选级联下游
python scripts/progress_graph.py --project-root /path/to/project reopen --node 03-implementation \
  --reason "接口调整" --cascade
```

语义：`start`/`jump` 只切换当前节点，不改变任务状态，执行前仍须确认；`back`/`forward` 只移动导航光标；`checkpoint`/`restore` 只保存和恢复图记忆；只有 `reopen` 会改任务状态。任务文件 frontmatter 始终是状态的唯一事实来源，任何跳转都不等于验收通过或依赖已满足。

## 投稿论文成稿（Paper Composer）

仓库同时包含独立 Skill [skills/paper-composer](skills/paper-composer/SKILL.md)，用于“实验已积累大量数据，需要按目标单位模板写成论文”的场景。它把输入分为两类权威：

- **机构模板**：LaTeX `.tex` / `.cls`、Word `.docx` / `.dotx`，或可读的投稿指南，决定页面、字体、章节层级、引用格式和必需声明。
- **用户内容大纲**：决定中心论点、章节意图、关键结果和取舍。

核心流程为：模板剖析 → 证据盘点 → 大纲映射 → 骨架确认 → 逐节成稿 → 组装合规 → 验收。所有数字、图表和引用必须回到证据清单；缺证据时标记缺口，不编造内容。

```bash
python skills/paper-composer/scripts/init_manuscript.py \
  --root /path/to/manuscript \
  --title "论文题目" \
  --format latex \
  --template /path/to/institution-template \
  --outline /path/to/outline.md \
  --dry-run

python skills/paper-composer/scripts/inspect_template.py \
  --root /path/to/manuscript \
  --path /path/to/institution-template

python skills/paper-composer/scripts/verify_manuscript.py \
  --root /path/to/manuscript --strict
```

若所用平台只发现仓库根目录的 `SKILL.md`，可将 `skills/paper-composer/` 单独复制或链接到该平台的 Skill 目录。

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

已有课题时可以直接指定起点：

```text
使用 $keti 查看节点记忆图，并从“05-report”开始。先列出未完成的依赖和缺失产物，再决定是否继续。
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
├── state/                       # 节点记忆图
│   ├── progress_graph.json      # 当前节点、导航栈、依赖缺口、检查点索引
│   ├── progress_history.jsonl   # 跳转与回溯事件
│   └── checkpoints/             # 图状态快照
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
| `scripts/progress_graph.py`         | 同步节点记忆图，支持任意起点、跳跃、回溯和检查点 |
| `scripts/discover_local_skills.py` | 在显式指定的目录中只读发现本地 Skill    |
| `scripts/discover_resources.py` | 按优先级只读发现显式范围内的 PPT、图片和字体资源 |

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

## 可选资源包

大型 PPT、字体和成套图片不进入核心 Git 仓库。Keti 只提交 [资源目录](assets/resource-catalog.json)，实际文件存放在 `.keti-resource-cache/packs/`、课题目录或用户明确指定的位置。

资源选择优先级为：用户提示词指定资源、当前课题资源、本地缓存、远程可选资源包。发现候选：

```bash
python scripts/discover_resources.py \
  --project-root /path/to/research-project \
  --cache-root .keti-resource-cache/packs \
  --user-path /optional/user/assets
```

命令仅执行只读扫描。远程资源需要在用户确认来源、许可证、大小和缓存位置后下载；字体不会被自动安装。

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
├── skills/
│   └── paper-composer/          # 投稿论文成稿 Skill
│       ├── SKILL.md
│       ├── agents/
│       ├── assets/
│       ├── references/
│       └── scripts/
├── requirements.txt
└── LICENSE
```

## 许可证

本项目使用 [Apache License 2.0](LICENSE)。
