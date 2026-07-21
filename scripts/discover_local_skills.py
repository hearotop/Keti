#!/usr/bin/env python3
"""Read-only discovery of local SKILL.md metadata under explicit roots."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


FRONT = re.compile(r"\A---\s*\n(.*?)\n---", re.S)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path)
    args = parser.parse_args()
    found = []
    for supplied in args.roots:
        root = supplied.expanduser().resolve()
        if not root.is_dir():
            continue
        for path in root.rglob("SKILL.md"):
            try:
                match = FRONT.match(path.read_text(encoding="utf-8"))
                meta = yaml.safe_load(match.group(1)) if match else {}
                if meta.get("name") and meta.get("description"):
                    found.append({"name": meta["name"], "description": meta["description"], "path": str(path.parent)})
            except (OSError, UnicodeError, yaml.YAMLError):
                continue
    found.sort(key=lambda item: (item["name"], item["path"]))
    print(json.dumps({"skills": found}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
