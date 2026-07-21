#!/usr/bin/env python3
"""Compute and optionally mark transitive downstream Keti tasks as stale."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def load_task(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONT.match(text)
    if not match:
        raise ValueError(f"missing YAML frontmatter: {path}")
    return yaml.safe_load(match.group(1)) or {}, text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--changed", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    task_dir = args.project_root.resolve() / "tasks"
    tasks: dict[str, tuple[Path, dict, str]] = {}
    for path in sorted(task_dir.glob("*.md")):
        meta, text = load_task(path)
        task_id = meta.get("id")
        if task_id:
            tasks[str(task_id)] = (path, meta, text)
    if args.changed not in tasks:
        print(json.dumps({"error": f"unknown task id: {args.changed}", "known": sorted(tasks)}, ensure_ascii=False))
        return 2
    affected: set[str] = set()
    frontier = {args.changed}
    while frontier:
        parent = frontier.pop()
        for task_id, (_, meta, _) in tasks.items():
            if task_id not in affected and parent in (meta.get("depends_on") or []):
                affected.add(task_id)
                frontier.add(task_id)
    changed_files = []
    if args.apply:
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        for task_id in sorted(affected):
            path, meta, text = tasks[task_id]
            meta["status"] = "stale"
            meta["updated_at"] = now
            body = FRONT.sub("", text, count=1)
            rendered = "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip() + "\n---\n" + body
            path.write_text(rendered, encoding="utf-8")
            changed_files.append(str(path))
    print(json.dumps({"changed": args.changed, "downstream": sorted(affected), "applied": args.apply,
                      "changed_files": changed_files}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
