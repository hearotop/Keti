#!/usr/bin/env python3
"""Report Keti capabilities without installing or changing anything."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--code-generation", required=True, choices=("yes", "no"))
    args = parser.parse_args()
    root = args.project_root.resolve()
    code_generation = args.code_generation == "yes"
    requested_modules = ["yaml", "pptx", "openpyxl"]
    if code_generation:
        requested_modules.extend(("pandas", "matplotlib"))
    modules = {name: importlib.util.find_spec(name) is not None for name in requested_modules}
    tools = {name: shutil.which(name) for name in ("git", "rg", "pdftotext")}
    report = {
        "python": {"version": sys.version.split()[0], "supported": sys.version_info >= (3, 10)},
        "code_generation": code_generation,
        "project_root": {"path": str(root), "exists": root.exists(),
                         "writable": root.is_dir() and os.access(root, os.W_OK)},
        "python_modules": modules,
        "system_tools": tools,
        "notes": [
            "Network and external Skill availability are runtime capabilities and are not probed by this script.",
            "Missing optional modules do not block planning; use the active environment's supported tools or a documented fallback.",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["python"]["supported"] and root.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
