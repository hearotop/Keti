# 课题工作流

## 目录约定

```text
project-root/
├── project.yaml
├── master_task.md
├── tasks/
├── sources/
│   ├── source_registry.json
│   └── literature_summary.md
├── experiments/
│   ├── data/
│   ├── logs/
│   ├── metrics.json
│   └── scripts/
├── assets/
│   ├── manifest.json
│   ├── external_references/
│   ├── generated_diagrams/
│   └── local_experiments/
├── reports/
├── presentations/
├── templates/
└── state/
    ├── progress_graph.json
    ├── progress_history.jsonl
    └── checkpoints/
```

只创建课题需要的目录。源数据保持只读或另存派生版本。

## 初始化字段

在 `project.yaml` 中记录：

- `title`、`direction`、`major`
- `advisor.name`、`advisor.preferences`
- `objectives`、`deliverables`、`deadline`
- `capabilities.code_generation`：必须来自用户明确选择，不得推断
- `constraints`：设备、软件、网络、伦理、保密、引用格式等
- `resources.local_paths` 与 `resources.cloud_refs`
- `status`、`created_at`、`updated_at`

## 阶段门

| 阶段 | 可进入条件 | 可完成条件 |
|---|---|---|
| 资料盘点 | 项目元数据可用 | 注册表记录路径、类型、可访问性与摘要状态 |
| 文献检索 | 关键词和范围明确 | 查询日志、引用信息和证据等级完整 |
| 架构设计 | 需求和约束已确认 | 设计文档与可编辑图源已验证 |
| 实现 | 接口和验收规则明确 | 构建及测试命令成功，日志落盘 |
| 实验 | 实现可运行，变量已定义 | 原始数据、命令、指标和图表可复现 |
| 申请书/项目书 | 申报要求、论证依据和成果边界已确认 | Markdown 正文完整、引用可追溯并经用户验收 |
| 报告 | 所引用证据已验证 | 引用、数据、图表路径均可追溯 |
| 节点导航 | 任务书存在 | 记忆图已同步，当前节点、依赖缺口和导航历史可查 |
| 汇报 | 报告结构稳定 | 模板、逐页内容、真实素材和讲稿齐备；PPT 验收需通过完整构建（SVG→PPTX→PDF→PNG），无超界/重叠/换行异常，数学公式原版呈现，缩写标注全称，论文数据出处可追溯 |

当 `capabilities.code_generation: false` 时删除“代码架构”和“实现”阶段，不生成相关任务或探测相关依赖。实验可直接依赖研究方法、已有数据、问卷、仪器记录或第三方软件输出。

每个阶段都使用两道门：进入阶段前由用户确认本节点执行卡；机器验收后由用户审阅重要文件。未通过用户验收时保持 `awaiting_review`，不得自动启动下游；用户可指定任意节点提前开始，但必须先提示依赖缺口和返工风险。申请书、项目书、各类报告、论文和 PPT 按 `project.yaml.deliverables` 分别建节点，禁止互相替代。

## 任意起点、跳跃与回溯

任务 DAG 表达依赖关系，不限制用户选择起点。用户可以直接从任意节点开始，包括依赖尚未完成的节点。

```bash
# 同步任务状态到记忆图
python <skill-dir>/scripts/progress_graph.py --project-root <root> sync

# 查看当前节点、导航历史和依赖缺口
python <skill-dir>/scripts/progress_graph.py --project-root <root> status

# 从任意节点开始或跳转
python <skill-dir>/scripts/progress_graph.py --project-root <root> start --node 03-implementation
python <skill-dir>/scripts/progress_graph.py --project-root <root> jump --node 05-report --reason "先写报告骨架"

# 沿导航历史回溯或前进
python <skill-dir>/scripts/progress_graph.py --project-root <root> back --steps 1
python <skill-dir>/scripts/progress_graph.py --project-root <root> forward --steps 1

# 保存/恢复图记忆
python <skill-dir>/scripts/progress_graph.py --project-root <root> checkpoint --note "实验前基线"
python <skill-dir>/scripts/progress_graph.py --project-root <root> restore --checkpoint <id>

# 回退任务状态并可选级联下游
python <skill-dir>/scripts/progress_graph.py --project-root <root> reopen --node 02-architecture \
  --reason "架构接口调整" --cascade
```

语义：

- `start` / `jump` 只切换当前节点和导航位置，不改变任务状态；执行前仍必须展示节点执行卡并获得用户确认。
- 依赖未完成时，脚本会输出 `unmet_dependencies` 和风险提示。用户可继续，但 Agent 必须在执行卡中说明缺失产物、并行风险和可能的返工。
- `back` / `forward` 只移动导航光标，不自动回退任务状态，也不删除任何文件。
- `checkpoint` 保存当前图状态和导航位置；`restore` 只恢复图记忆，任务文件状态保持不变。
- `reopen` 才把节点状态改回 `ready`；`--cascade` 会把传递下游标记为 `stale`，并记录回溯原因。
- 任务文件 frontmatter 始终是任务状态的唯一事实来源；记忆图是导航和历史，不是新的状态源。

## 变更传播

- 文献事实变化：影响引用该事实的架构论证、报告和演示。
- 架构变化：影响实现、实验、报告和演示。
- 实现变化：影响测试、实验、报告和演示。
- 实验设计或数据变化：影响实验结论、报告和演示。
- 报告措辞变化：通常只影响报告与演示。
- 演示排版变化：只影响演示。

先由任务的显式 `depends_on` 计算传递下游，再根据实际影响缩小或扩大范围，并记录理由。

每次任务新增、删除、依赖或状态变化后，运行 `progress_graph.py sync`，使当前节点、导航栈和依赖缺口与任务书一致。需要回退已完成节点时用 `reopen`，不要只改记忆图。
