# 静态资源管理

## 分层模型

- 核心层：`assets/resource-catalog.json`、小型预览和任务模板，可提交 Git。
- 项目层：课题自己的 `templates/` 与 `assets/`，跟随课题管理。
- 缓存层：`.keti-resource-cache/packs/` 或用户指定缓存，保存大型可选资源，不提交 Git。
- 用户覆盖层：提示词明确指定的模板或素材，优先级最高。

## 资源包格式

每个资源包目录必须包含 `pack.json`：

```json
{
  "schema_version": "1.0",
  "id": "nsfc-ppt-v1",
  "version": "1.0.0",
  "license": "Apache-2.0",
  "source": "https://example.invalid/releases/nsfc-ppt-v1.zip",
  "resources": [
    {
      "id": "nsfc-blue",
      "type": "ppt-template",
      "path": "ppt/nsfc-blue.pptx",
      "name": "国自然亮蓝白模板",
      "tags": ["国自然", "申请答辩", "亮蓝白"],
      "sha256": "..."
    }
  ]
}
```

`source` 未配置或 `license` 为 `unknown` 时，将包视为本地私有资源，不提供自动下载或再分发。

## 发现命令

```bash
python <skill-dir>/scripts/discover_resources.py \
  --project-root <project-root> \
  --cache-root <cache-root> \
  --user-path <optional-user-resource-path>
```

命令只读。向用户展示候选后，由用户选择模板或素材；不要仅凭文件名自动决定高成本 PPT 生产。

## 下载与缓存

远程包应发布为独立资源仓库的 Release 压缩包，而非核心仓库 Git 历史。下载前必须确认：来源、版本、压缩包大小、许可证、缓存位置和 SHA-256。下载后校验哈希，解压到以包 ID 和版本命名的缓存目录。不得自动安装字体；只说明字体名称、许可证、获取方式和回退字体。

## 交付物记录

任务使用资源后，在项目 `assets/manifest.json` 记录包 ID、版本、资源 ID、原始路径、许可证和用途。最终报告中区分“仅作为风格参考”和“直接复制进入交付物”的资源。
