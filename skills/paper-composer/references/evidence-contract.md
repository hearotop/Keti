# 证据与追溯契约

## 目标

论文中的每个事实、数字、图表和引用都必须能回到一个已登记的证据条目。证据清单同时服务于写作、合规检查和审稿问答。

## 清单位置

`evidence/manifest.json`，顶层结构：

```json
{
  "schema_version": 1,
  "generated_at": "2026-11-19T12:00:00+08:00",
  "items": []
}
```

每个条目至少包含：

```json
{
  "id": "E3",
  "kind": "figure",
  "path": "inputs/evidence/figures/main_result.png",
  "title": "主结果对比",
  "created_at": "2026-11-18T20:00:00+08:00",
  "source": {
    "type": "generated",
    "script": "inputs/evidence/scripts/plot_main.py",
    "inputs": ["inputs/evidence/data/main.csv"],
    "command": ["python", "inputs/evidence/scripts/plot_main.py"]
  },
  "supports": ["C1", "C2"],
  "used_by": ["sections/04-results.md"],
  "caption": "本文方法与三个基线的准确率对比，误差棒为五次重复的标准差。",
  "status": "verified",
  "notes": ""
}
```

## 证据类型

| 类型 | 说明 | 必填字段 |
|---|---|---|
| `experiment_data` | 原始或派生数据 | 路径、采集/生成命令、时间、单位 |
| `metric` | 结构化指标 | 指标名、值、单位、来源实验 ID |
| `figure` | 图片或矢量图 | 生成脚本、输入数据、caption |
| `table` | 表格数据 | 来源数据、生成方式、caption |
| `literature` | 可核验文献 | 作者、标题、期刊/会议、年份、DOI/URL |
| `prior_draft` | 既往稿件或笔记 | 版本、日期、可复用范围 |
| `external_reference` | 外部图表或数据 | 出处、许可、访问日期；不得冒充本地结果 |

## 论点—证据矩阵

在 `outline/outline_map.md` 或章节头部维护：

| 论点 ID | 论点 | 证据 ID | 证据状态 | 缺口/替代方案 |
|---|---|---|---|---|
| C1 | 方法在主指标上优于基线 | E3, E4 | verified | - |
| C2 | 提升在低资源场景更明显 | E5 | stale | 需重跑 E5 |

规则：

- 一个论点至少绑定一个 `verified` 证据。
- 证据为 `stale`、`missing` 或 `unreadable` 时，论点不得写成确定结论。
- 不得用多个弱证据拼接出强结论；需要说明证据边界。

## 数字追溯

- 正文、摘要、图表标题中的每个数字都必须来自 `metric` 或 `table` 条目。
- 同一数字在正文、图表和摘要中保持一致；修改数据后同步更新所有引用位置。
- 百分比、误差、显著性、样本量必须带单位和统计口径。
- 不把单次运行结果写成稳定结论；不省略失败运行或异常条件。

## 图表规则

- 每张图表必须有唯一 ID、caption、数据来源和生成方式。
- 正文首次引用图表时使用同一编号；图表按出现顺序编号。
- 外部图表必须有引用和许可说明，并放入 `external_reference` 分类。
- 图表不得裁掉坐标轴、单位、图例或误差信息来制造效果。
- 无法复现的历史图表标记 `unverified`，在交付报告中说明。

## 文献规则

- 只登记可访问、可核验的文献；搜索摘要和模型记忆不算证据。
- 每条文献保留 DOI、URL 或出版社页面，记录访问日期。
- 不引用未读过的文献来支撑具体结论。
- 引用格式由机构模板决定；文献库键名保持稳定，转换格式时不改键。

## 缺口与降级

- 缺数据：标记 `gap`，向用户说明需要补做的实验或可接受的降级表述。
- 缺文献：改写为“本研究观察”或删除该断言，不伪造引用。
- 图表不可复现：保留原图并标记 `unverified`，在合规报告中披露。
- 结果与预期不符：如实报告，不篡改数据或选择性省略。
