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
└── templates/
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
| 汇报 | 报告结构稳定 | 模板、逐页内容、真实素材和讲稿齐备 |

当 `capabilities.code_generation: false` 时删除“代码架构”和“实现”阶段，不生成相关任务或探测相关依赖。实验可直接依赖研究方法、已有数据、问卷、仪器记录或第三方软件输出。

每个阶段都使用两道门：进入阶段前由用户确认本节点执行卡；机器验收后由用户审阅重要文件。未通过用户验收时保持 `awaiting_review`，不得启动下游。申请书、项目书、各类报告、论文和 PPT 按 `project.yaml.deliverables` 分别建节点，禁止互相替代。

## 变更传播

- 文献事实变化：影响引用该事实的架构论证、报告和演示。
- 架构变化：影响实现、实验、报告和演示。
- 实现变化：影响测试、实验、报告和演示。
- 实验设计或数据变化：影响实验结论、报告和演示。
- 报告措辞变化：通常只影响报告与演示。
- 演示排版变化：只影响演示。

先由任务的显式 `depends_on` 计算传递下游，再根据实际影响缩小或扩大范围，并记录理由。
