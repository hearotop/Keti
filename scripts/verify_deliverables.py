#!/usr/bin/env python3
"""Run explicit checks from a Keti task's YAML acceptance block."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml


def acceptance(task: Path) -> list[dict]:
    text = task.read_text(encoding="utf-8")
    marker = "## 验收规则"
    start = text.find(marker)
    if start < 0:
        raise ValueError("missing '## 验收规则' section")
    fence = text.find("```yaml", start)
    end = text.find("```", fence + 7) if fence >= 0 else -1
    if fence < 0 or end < 0:
        raise ValueError("acceptance section must contain a ```yaml block")
    data = yaml.safe_load(text[fence + 7:end]) or {}
    checks = data.get("checks")
    if not isinstance(checks, list):
        raise ValueError("acceptance YAML must contain a checks list")
    return checks


def safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"path escapes project root: {relative}")
    return path


def run(check: dict, root: Path) -> tuple[bool, str]:
    kind = check.get("type")
    if kind in {"file_exists", "file_nonempty", "json_valid", "json_keys"}:
        path = safe_path(root, str(check.get("path", "")))
        if kind == "file_exists":
            return path.exists(), str(path)
        if not path.is_file():
            return False, f"not a file: {path}"
        if kind == "file_nonempty":
            return path.stat().st_size > 0, f"size={path.stat().st_size}"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"invalid JSON: {exc}"
        if kind == "json_valid":
            return True, "valid JSON"
        keys = check.get("keys", [])
        missing = [key for key in keys if not isinstance(value, dict) or key not in value]
        return not missing, f"missing keys: {missing}" if missing else "all keys present"
    if kind == "command":
        command = check.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            return False, "command must be a non-empty string array"
        cwd = safe_path(root, str(check.get("cwd", ".")))
        try:
            result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=int(check.get("timeout", 300)))
        except Exception as exc:
            return False, str(exc)
        detail = (result.stdout + result.stderr)[-2000:]
        return result.returncode == 0, f"exit={result.returncode}\n{detail}"
    return False, f"unsupported check type: {kind}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    results = []
    try:
        checks = acceptance(args.task.resolve())
        for index, check in enumerate(checks, 1):
            ok, detail = run(check, root)
            results.append({"index": index, "type": check.get("type"), "ok": ok, "detail": detail})
        passed = bool(checks) and all(item["ok"] for item in results)
        error = None
    except Exception as exc:
        passed, error = False, str(exc)
    print(json.dumps({"task": str(args.task), "passed": passed, "error": error, "results": results}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
