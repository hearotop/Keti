# 成稿工作流与阶段门

## 阶段总览

```text
输入门 → 模板剖析 → 证据盘点 → 大纲映射 → 骨架确认 → 逐节成稿 → 组装合规 → 验收移交
```

每个阶段都有两道门：进入前由用户确认执行范围；产出后由用户验收。未验收不得解锁下一阶段。

## 阶段门

| 阶段 | 可进入条件 | 可完成条件 |
|---|---|---|
| 输入门 | 用户提出投稿目标 | 模板、大纲、证据库、投稿元数据已登记；阻塞项已明确 |
| 模板剖析 | 至少有一份模板或指南 | `template/profile.json` 与 `template/report.md` 已生成；未知项已列出 |
| 证据盘点 | 实验数据和图表可访问 | `evidence/manifest.json` 完整；缺口与过期项已标记 |
| 大纲映射 | 大纲和证据清单可用 | `outline/outline_map.md` 覆盖全部大纲节点；冲突与缺口已列出 |
| 骨架确认 | 映射经用户确认 | 骨架稿包含模板章节层级、证据占位和引用占位；用户确认结构 |
| 逐节成稿 | 骨架已确认 | 各章节完成且通过单节验收；占位符有明确说明 |
| 组装合规 | 正文经用户验收 | 成稿可从模板构建；合规报告逐项通过或已记录例外 |
| 验收移交 | 校验脚本无阻断错误 | 用户验收通过；交付清单与缺口清单齐全 |

## 各阶段产物

| 阶段 | 产物 |
|---|---|
| 输入门 | `manuscript.yaml` |
| 模板剖析 | `template/profile.json`、`template/report.md` |
| 证据盘点 | `evidence/manifest.json` |
| 大纲映射 | `outline/outline_map.md` |
| 骨架确认 | `sections/` 下的骨架稿 |
| 逐节成稿 | `sections/` 下的正文、`bibliography/` |
| 组装合规 | `build/`、`outputs/`、`reports/compliance.md` |
| 验收移交 | 校验输出与最终交付清单 |

## 命令

```bash
# 初始化工作区，先预览
python <skill-dir>/scripts/init_manuscript.py \
  --root <manuscript-root> --title "<题目>" --format latex --language zh --dry-run

# 剖析机构模板
python <skill-dir>/scripts/inspect_template.py \
  --root <manuscript-root> --path <模板文件或目录>

# 校验成稿
python <skill-dir>/scripts/verify_manuscript.py \
  --root <manuscript-root> --strict
```

## 变更传播

| 变化 | 必须重做 |
|---|---|
| 更换机构模板 | 模板剖析、骨架、组装、合规检查；正文可复用但需重新套版 |
| 模板版本更新 | 模板剖析、组装、合规检查 |
| 用户大纲调整 | 大纲映射及受影响的章节；必要时重排骨架 |
| 实验结果或指标更新 | 证据清单、引用该证据的章节、图表、结论与合规检查 |
| 文献更新 | 引用该文献的章节与参考文献表 |
| 仅措辞修改 | 对应章节与最终校验 |

先按显式依赖计算影响范围，再向用户报告重做成本；不得因排版变化重跑实验。

## 节点交互格式

执行前：

```markdown
### 待确认：<阶段或章节>
- 目标：...
- 输入：`...`
- 本次操作：...
- 预计产物：`...`
- 缺口与风险：...
- 待决定：...

是否执行当前阶段？
```

完成后：

```markdown
### 完成：<阶段或章节>
- 状态：`awaiting_review`
- 完成内容：...
- 校验结果：...
- 重要文件：
  - 正文：`sections/...`
  - 模板：`template/profile.json`
  - 证据：`evidence/manifest.json`
  - 合规：`reports/compliance.md`
- 未解决缺口：...
- 下一步：...

请选择：验收通过 / 修改当前阶段 / 暂停。
```
