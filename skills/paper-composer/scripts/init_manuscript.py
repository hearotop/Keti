#!/usr/bin/env python3
"""初始化投稿论文工作区。

只补齐缺失目录和文件，不覆盖用户已有内容。所有路径相对于 --root。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIRECTORIES = (
    "inputs/institution_template",
    "inputs/outline",
    "inputs/evidence",
    "template",
    "evidence",
    "outline",
    "sections",
    "bibliography",
    "build",
    "outputs",
    "reports",
)

OUTPUT_NAMES = {
    "latex": "manuscript.tex",
    "docx": "manuscript.docx",
    "markdown": "manuscript.md",
}


def timestamp() -> str:
    """返回带时区的本地时间字符串。"""
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).isoformat()


def yaml_string(value: str) -> str:
    """把任意字符串转成 YAML 可用的双引号标量。"""
    return json.dumps(value, ensure_ascii=False)


def record(actions: list[tuple[str, Path, str]], kind: str, path: Path, detail: str = "") -> None:
    actions.append((kind, path, detail))


def ensure_dir(root: Path, relative: str, dry_run: bool, actions: list[tuple[str, Path, str]]) -> None:
    path = root / relative
    if path.is_dir():
        record(actions, "skip", path, "目录已存在")
        return
    record(actions, "mkdir", path)
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)


def ensure_file(
    root: Path,
    relative: str,
    content: str,
    dry_run: bool,
    actions: list[tuple[str, Path, str]],
) -> None:
    path = root / relative
    if path.exists():
        record(actions, "skip", path, "文件已存在，保留原内容")
        return
    record(actions, "write", path)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def build_config(
    title: str,
    venue: str,
    language: str,
    output_format: str,
    template_path: str | None,
    outline_path: str | None,
    anonymous: str,
) -> str:
    """生成 manuscript.yaml 内容。"""
    output_name = OUTPUT_NAMES[output_format]
    template_value = yaml_string(template_path) if template_path else "null"
    outline_value = yaml_string(outline_path) if outline_path else "null"
    return "\n".join(
        [
            "schema_version: 1",
            f"title: {yaml_string(title)}",
            f"venue: {yaml_string(venue)}",
            f"language: {yaml_string(language)}",
            f"output_format: {yaml_string(output_format)}",
            'status: "initialized"',
            f'created_at: "{timestamp()}"',
            f'updated_at: "{timestamp()}"',
            "",
            "inputs:",
            '  institution_template_dir: "inputs/institution_template"',
            '  outline_dir: "inputs/outline"',
            '  evidence_dir: "inputs/evidence"',
            f"  institution_template: {template_value}",
            f"  outline: {outline_value}",
            "",
            "template:",
            '  profile: "template/profile.json"',
            '  report: "template/report.md"',
            "",
            "evidence:",
            '  manifest: "evidence/manifest.json"',
            "",
            "outline:",
            '  map: "outline/outline_map.md"',
            "",
            "sections: []",
            "bibliography: null",
            f"output: {yaml_string('outputs/' + output_name)}",
            f"anonymous: {yaml_string(anonymous)}",
            "",
            "limits:",
            "  pages: null",
            "  words: null",
            "",
            "gates:",
            "  template_profiled: false",
            "  evidence_inventoried: false",
            "  outline_mapped: false",
            "  skeleton_approved: false",
            "  draft_approved: false",
            "  compliance_verified: false",
            "",
        ]
    )


def build_outline_map(outline_path: str | None) -> str:
    source = outline_path if outline_path else "未提供"
    return "\n".join(
        [
            "# 大纲映射",
            "",
            "- 状态：未映射",
            f"- 大纲来源：`{source}`",
            "- 图例：`ready` / `gap` / `blocked` / `inferred`",
            "",
            "| 大纲节点 | 模板章节 | 章节目的 | 关键论点 | 证据 ID | 图表 ID | 引用键 | 字数 | 状态 |",
            "|---|---|---|---|---|---|---|---|---|",
            "|  |  |  |  |  |  |  |  |  |",
            "",
            "> 由 Paper Composer 在映射阶段填写。每个关键论点必须绑定至少一个证据 ID。",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化 Paper Composer 投稿论文工作区")
    parser.add_argument("--root", required=True, help="论文工作区根目录")
    parser.add_argument("--title", required=True, help="论文题目")
    parser.add_argument("--venue", default="", help="目标单位、期刊或会议")
    parser.add_argument("--language", choices=("zh", "en"), default="zh", help="论文语言")
    parser.add_argument(
        "--format",
        choices=tuple(OUTPUT_NAMES),
        default="latex",
        dest="output_format",
        help="目标输出格式",
    )
    parser.add_argument("--template", help="机构模板文件或目录的路径")
    parser.add_argument("--outline", help="用户内容大纲文件或目录的路径")
    parser.add_argument(
        "--anonymous",
        choices=("yes", "no", "unknown"),
        default="unknown",
        help="是否匿名投稿",
    )
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入磁盘")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    template_path = str(Path(args.template).expanduser().resolve()) if args.template else None
    outline_path = str(Path(args.outline).expanduser().resolve()) if args.outline else None

    warnings: list[str] = []
    for label, value in (("机构模板", template_path), ("用户大纲", outline_path)):
        if value and not Path(value).exists():
            warnings.append(f"{label}路径不存在：{value}")

    actions: list[tuple[str, Path, str]] = []

    if root.exists() and not root.is_dir():
        print(f"错误：--root 不是目录：{root}")
        return 2
    record(actions, "mkdir", root)
    if not args.dry_run:
        root.mkdir(parents=True, exist_ok=True)

    for relative in DIRECTORIES:
        ensure_dir(root, relative, args.dry_run, actions)

    for relative in ("inputs/institution_template", "inputs/outline", "inputs/evidence"):
        ensure_file(root, f"{relative}/.gitkeep", "", args.dry_run, actions)
    for relative in ("sections", "bibliography", "build", "outputs"):
        ensure_file(root, f"{relative}/.gitkeep", "", args.dry_run, actions)

    ensure_file(
        root,
        "manuscript.yaml",
        build_config(
            title=args.title,
            venue=args.venue,
            language=args.language,
            output_format=args.output_format,
            template_path=template_path,
            outline_path=outline_path,
            anonymous=args.anonymous,
        ),
        args.dry_run,
        actions,
    )
    ensure_file(
        root,
        "evidence/manifest.json",
        json.dumps(
            {"schema_version": 1, "generated_at": None, "items": []},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        args.dry_run,
        actions,
    )
    ensure_file(
        root,
        "outline/outline_map.md",
        build_outline_map(outline_path),
        args.dry_run,
        actions,
    )

    print(f"论文工作区：{root}")
    print("预览（未写入）：" if args.dry_run else "执行结果：")
    for kind, path, detail in actions:
        try:
            shown = path.relative_to(root)
        except ValueError:
            shown = path
        suffix = f"（{detail}）" if detail else ""
        print(f"  [{kind}] {shown}{suffix}")

    for warning in warnings:
        print(f"警告：{warning}")

    if not template_path and not outline_path:
        print("提示：尚未登记机构模板和用户大纲。可放入 inputs/ 目录，或用 --template / --outline 重新登记。")

    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
