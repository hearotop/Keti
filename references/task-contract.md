# 任务书契约

每个 `tasks/*.md` 使用 YAML frontmatter，供脚本可靠解析：

```markdown
---
id: "04-experiments"
title: "实验设计与数据分析"
status: "pending"
depends_on: ["03-implementation"]
updated_at: "2026-07-21T20:00:00+08:00"
retry_count: 0
---

# 实验设计与数据分析

## 目标
说明可判定的目标和非目标。

## 输入与证据
- `path`: 用途、来源、版本或哈希、可访问状态

## 执行步骤
- [ ] 可操作步骤

## 交付物
- `experiments/metrics.json`
- `assets/local_experiments/latency.png`

## 验收规则
```yaml
checks:
  - type: file_exists
    path: experiments/metrics.json
  - type: json_keys
    path: experiments/metrics.json
    keys: [mean_latency, throughput]
  - type: command
    command: ["python", "-m", "pytest", "-q"]
    cwd: "."
```

上例适用于需要代码的计算实验。若用户选择不生成代码，实验/分析任务应依赖方法设计、数据采集或已有数据任务，不得保留虚构的 `implementation` 依赖。

## 风险与降级
列出风险、触发条件和可接受降级。

## 错误日志
仅追加真实执行错误、尝试及结果。

## 变更历史
- 时间、提出者、变更、影响范围和理由。
```

## 状态机

`pending -> ready -> in_progress -> completed`。验证失败进入 `failed`，可修复后回到 `in_progress`；缺少用户输入、权限或外部条件时进入 `blocked`；上游变化后进入 `stale`。不得用勾选框同时表达多个状态。

## 验收检查类型

验证脚本支持：

- `file_exists`：相对项目根路径存在。
- `file_nonempty`：普通文件且非空。
- `json_valid`：可解析为 JSON。
- `json_keys`：JSON 顶层包含指定键。
- `command`：以参数数组执行命令；必须显式提供，禁止 shell 字符串。

命令检查只运行任务书中的受信任命令。审查任务书来源后再执行验证脚本。
