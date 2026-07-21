#!/usr/bin/env python3
"""Create Keti's non-destructive project scaffold."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIRECTORIES = (
    "tasks", "sources", "experiments/data", "experiments/logs",
    "assets/external_references",
    "assets/generated_diagrams", "assets/local_experiments",
    "reports", "presentations", "templates",
)

CODE_DIRECTORIES = ("src", "tests", "experiments/scripts")


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def files(title: str, code_generation: bool) -> dict[str, str]:
    now = timestamp()
    yaml_title = json.dumps(title, ensure_ascii=False)
    return {
        "project.yaml": (
            f"title: {yaml_title}\n"
            'direction: "unknown"\nmajor: "unknown"\n'
            'advisor:\n  name: "unknown"\n  preferences: []\n'
            'objectives: []\ndeliverables: []\ndeadline: "unknown"\n'
            'constraints: []\nresources:\n  local_paths: []\n  cloud_refs: []\n'
            f'capabilities:\n  code_generation: {str(code_generation).lower()}\n'
            f'status: "planning"\ncreated_at: "{now}"\nupdated_at: "{now}"\n'
        ),
        "master_task.md": (
            f'---\nproject: {yaml_title}\nstatus: "planning"\nupdated_at: "{now}"\n---\n\n'
            f'# 课题总任务书：{title}\n\n## 目标与成功标准\n\n'
            '## 范围与约束\n\n## 资料与证据现状\n\n## 任务 DAG\n\n'
            '| ID | 任务 | 依赖 | 状态 | 交付物 |\n|---|---|---|---|---|\n\n'
            '## 里程碑与风险\n\n## 决策与变更记录\n'
        ),
        "sources/source_registry.json": json.dumps(
            {"schema_version": "1.0", "sources": []}, ensure_ascii=False, indent=2
        ) + "\n",
        "assets/manifest.json": json.dumps(
            {"schema_version": "1.0", "assets": []}, ensure_ascii=False, indent=2
        ) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--code-generation", required=True, choices=("yes", "no"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    planned: list[str] = []
    skipped: list[str] = []

    code_generation = args.code_generation == "yes"
    directories = BASE_DIRECTORIES + (CODE_DIRECTORIES if code_generation else ())
    for directory in directories:
        path = root / directory
        (skipped if path.exists() else planned).append(f"dir:{directory}")
        if not args.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    for relative, content in files(args.title, code_generation).items():
        path = root / relative
        if path.exists():
            skipped.append(f"file:{relative}")
            continue
        planned.append(f"file:{relative}")
        if not args.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    print(json.dumps({"root": str(root), "dry_run": args.dry_run,
                      "code_generation": code_generation,
                      "created_or_planned": planned, "skipped_existing": skipped},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
