# 证据与资产契约

`assets/manifest.json` 使用对象形式，顶层包含 `schema_version` 和 `assets`。每项至少包含：

```json
{
  "id": "exp-latency-001",
  "kind": "local_experiment",
  "path": "assets/local_experiments/latency.png",
  "caption": "不同断电频率下的平均恢复延迟",
  "created_at": "2026-07-21T20:00:00+08:00",
  "source": {
    "type": "generated",
    "script": "experiments/scripts/plot_latency.py",
    "inputs": ["experiments/data/latency.csv"],
    "command": ["python", "experiments/scripts/plot_latency.py"]
  },
  "used_by": ["05-report", "06-presentation"],
  "verification": {"status": "verified", "verified_at": "2026-07-21T20:05:00+08:00"}
}
```

## 分类要求

- `external_reference`：记录标题、作者/机构、URL 或 DOI、访问日期、许可/合理使用说明、原始 caption 和页码（如有）。不得暗示是本项目实验结果。
- `generated_diagram`：记录可编辑源文件、渲染工具、渲染命令/Skill 和设计依据。
- `local_experiment`：记录生成脚本、输入数据、实验配置、命令和时间。核心结论优先使用此类资产。

## 数据桥

`experiments/metrics.json` 必须包含 `schema_version`、`generated_at`、`experiment_id`、`metrics`、`units`、`inputs` 和 `command`。指标值必须来自原始数据或日志；报告引用指标时同时记录实验 ID。

## 核验顺序

1. 检查路径在项目根内且文件存在。
2. 检查文件可解析/可读取，而非只看扩展名。
3. 检查来源和生成链完整。
4. 检查 caption 与数据含义一致。
5. 检查报告/PPT 中的引用与清单路径一致。
