#!/usr/bin/env python3
"""Discover Keti resources from explicit, bounded roots without modifying them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TYPES = {
    ".pptx": "ppt-template",
    ".potx": "ppt-template",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".svg": "image",
    ".ttf": "font",
    ".otf": "font",
    ".woff": "font",
    ".woff2": "font",
    ".zip": "archive",
}


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def pack_metadata(path: Path, root: Path, cache: dict[Path, dict]) -> dict:
    for parent in (path.parent, *path.parents):
        if not inside(parent, root):
            break
        manifest = parent / "pack.json"
        if manifest.is_file():
            if manifest not in cache:
                try:
                    cache[manifest] = json.loads(manifest.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    cache[manifest] = {}
            return cache[manifest]
    return {}


def scan(root: Path, priority: int, origin: str) -> list[dict]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        return []
    resources = []
    manifests: dict[Path, dict] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TYPES:
            continue
        resolved = path.resolve()
        if not inside(resolved, root):
            continue
        pack = pack_metadata(path, root, manifests)
        resources.append({
            "name": path.name,
            "type": TYPES[path.suffix.lower()],
            "path": str(resolved),
            "origin": origin,
            "priority": priority,
            "size_bytes": path.stat().st_size,
            "license": pack.get("license", "unknown"),
            "pack_id": pack.get("id"),
            "pack_version": pack.get("version"),
        })
    return resources


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--user-path", action="append", default=[], type=Path)
    args = parser.parse_args()
    project = args.project_root.expanduser().resolve()
    roots: list[tuple[Path, int, str]] = []
    for supplied in args.user_path:
        roots.append((supplied, 1, "user"))
    roots.extend(((project / "templates", 2, "project"), (project / "assets", 2, "project")))
    if args.cache_root:
        roots.append((args.cache_root, 4, "cache"))
    resources = []
    seen = set()
    for root, priority, origin in roots:
        for resource in scan(root, priority, origin):
            if resource["path"] not in seen:
                seen.add(resource["path"])
                resources.append(resource)
    resources.sort(key=lambda item: (item["priority"], item["type"], item["name"]))
    print(json.dumps({"schema_version": "1.0", "resources": resources}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
