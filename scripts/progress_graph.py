#!/usr/bin/env python3
"""维护 Keti 节点记忆图：同步任务状态、记录当前节点、支持跳转与回溯。

任务文件 frontmatter 是任务状态的唯一事实来源；本脚本维护的是导航记忆、
访问历史和检查点，不替代任务书。所有命令都允许任意节点作为当前节点。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
STATUS_ORDER = (
    "completed",
    "awaiting_review",
    "in_progress",
    "ready",
    "pending",
    "failed",
    "blocked",
    "stale",
    "unknown",
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def state_dir(root: Path) -> Path:
    return root / "state"


def graph_path(root: Path) -> Path:
    return state_dir(root) / "progress_graph.json"


def history_path(root: Path) -> Path:
    return state_dir(root) / "progress_history.jsonl"


def checkpoint_dir(root: Path) -> Path:
    return state_dir(root) / "checkpoints"


def emit(payload: dict, code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"无法解析 JSON：{path}：{exc}") from exc
    return value if isinstance(value, dict) else None


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def load_tasks(root: Path) -> tuple[dict[str, dict], list[str]]:
    """读取 tasks/*.md，返回任务表和解析警告。"""
    tasks: dict[str, dict] = {}
    warnings: list[str] = []
    task_dir = root / "tasks"
    if not task_dir.is_dir():
        return tasks, [f"未找到任务目录：{task_dir}"]
    for path in sorted(task_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONT.match(text)
        if not match:
            warnings.append(f"跳过缺少 YAML frontmatter 的任务：{path.name}")
            continue
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            warnings.append(f"跳过无法解析 frontmatter 的任务：{path.name}：{exc}")
            continue
        if not isinstance(meta, dict):
            warnings.append(f"跳过 frontmatter 不是映射的任务：{path.name}")
            continue
        task_id = str(meta.get("id") or path.stem)
        if task_id in tasks:
            warnings.append(f"任务 ID 重复，保留先出现的文件：{task_id}")
            continue
        tasks[task_id] = {
            "path": path,
            "relative": str(path.relative_to(root)),
            "meta": meta,
            "text": text,
        }
    return tasks, warnings


def project_title(root: Path) -> str:
    config = root / "project.yaml"
    if not config.exists():
        return root.name
    try:
        value = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return root.name
    if isinstance(value, dict) and value.get("title"):
        return str(value["title"])
    return root.name


def build_graph(root: Path, existing: dict | None = None) -> dict:
    tasks, warnings = load_tasks(root)
    previous_nodes = (existing or {}).get("nodes") or {}
    nodes: dict[str, dict] = {}

    for task_id, item in tasks.items():
        meta = item["meta"]
        old = previous_nodes.get(task_id) or {}
        status = str(meta.get("status") or "pending")
        depends_on = [str(value) for value in (meta.get("depends_on") or [])]
        nodes[task_id] = {
            "id": task_id,
            "title": str(meta.get("title") or task_id),
            "path": item["relative"],
            "status": status,
            "depends_on": depends_on,
            "downstream": [],
            "missing_dependencies": [],
            "unmet_dependencies": [],
            "ready": False,
            "last_visited_at": old.get("last_visited_at"),
            "last_started_at": old.get("last_started_at"),
            "visit_count": int(old.get("visit_count") or 0),
            "last_checkpoint": old.get("last_checkpoint"),
            "notes": old.get("notes") or "",
        }

    for task_id, node in nodes.items():
        for dependency in node["depends_on"]:
            if dependency in nodes:
                nodes[dependency]["downstream"].append(task_id)
            else:
                node["missing_dependencies"].append(dependency)
        node["unmet_dependencies"] = [
            dependency
            for dependency in node["depends_on"]
            if dependency not in nodes or nodes[dependency]["status"] != "completed"
        ]
        node["ready"] = node["status"] in {"ready", "pending"} and not node["unmet_dependencies"]

    for node in nodes.values():
        node["downstream"].sort()

    previous_navigation = (existing or {}).get("navigation") or {}
    stack = [node_id for node_id in (previous_navigation.get("stack") or []) if node_id in nodes]
    index = int(previous_navigation.get("index", len(stack) - 1))
    if stack:
        index = max(0, min(index, len(stack) - 1))
    else:
        index = -1

    current = (existing or {}).get("current_node")
    if current not in nodes:
        current = stack[index] if stack else None
    if current and current not in stack:
        stack.append(current)
        index = len(stack) - 1

    summary: dict[str, int] = {"total": len(nodes)}
    for status in STATUS_ORDER:
        summary[status] = 0
    for node in nodes.values():
        status = node["status"]
        summary[status] = summary.get(status, 0) + 1

    edges = [
        {"from": dependency, "to": task_id, "type": "depends_on"}
        for task_id, node in nodes.items()
        for dependency in node["depends_on"]
    ]

    graph = {
        "schema_version": 1,
        "project_root": str(root),
        "project_title": project_title(root),
        "generated_at": (existing or {}).get("generated_at") or now(),
        "updated_at": now(),
        "source": "tasks/*.md",
        "current_node": current,
        "navigation": {"stack": stack, "index": index},
        "nodes": nodes,
        "edges": edges,
        "checkpoints": (existing or {}).get("checkpoints") or [],
        "summary": summary,
        "warnings": warnings,
    }
    return graph


def sync_graph(root: Path, existing: dict | None = None) -> dict:
    if existing is None:
        existing = read_json(graph_path(root))
    graph = build_graph(root, existing)
    write_json(graph_path(root), graph)
    return graph


def append_history(root: Path, action: str, **fields) -> None:
    event = {"at": now(), "action": action}
    event.update(fields)
    path = history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def resolve_node(graph: dict, value: str) -> tuple[str | None, list[str]]:
    nodes = graph.get("nodes") or {}
    if value in nodes:
        return value, []
    prefix = sorted(node_id for node_id in nodes if node_id.startswith(value))
    if len(prefix) == 1:
        return prefix[0], []
    lowered = value.lower()
    title_matches = sorted(
        node_id
        for node_id, node in nodes.items()
        if lowered in str(node.get("title", "")).lower()
    )
    if len(title_matches) == 1:
        return title_matches[0], []
    candidates = prefix or title_matches
    if not candidates:
        candidates = sorted(nodes)
    return None, candidates


def touch(node: dict) -> None:
    node["last_visited_at"] = now()
    node["visit_count"] = int(node.get("visit_count") or 0) + 1


def move_to(graph: dict, node_id: str, action: str, reason: str = "", mark_started: bool = False) -> dict:
    previous = graph.get("current_node")
    navigation = graph.get("navigation") or {"stack": [], "index": -1}
    stack = list(navigation.get("stack") or [])
    index = int(navigation.get("index", -1))

    if node_id != previous:
        if index < len(stack) - 1:
            stack = stack[: index + 1]
        stack.append(node_id)
        index = len(stack) - 1
    elif not stack:
        stack = [node_id]
        index = 0

    node = graph["nodes"][node_id]
    touch(node)
    if mark_started:
        node["last_started_at"] = now()
    graph["current_node"] = node_id
    graph["navigation"] = {"stack": stack, "index": index}
    graph["updated_at"] = now()
    return {"from": previous, "to": node_id, "index": index, "stack": stack}


def task_meta(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONT.match(text)
    if not match:
        raise ValueError(f"任务缺少 YAML frontmatter：{path}")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"任务 frontmatter 不是映射：{path}")
    return meta, text


def write_task(path: Path, meta: dict, text: str) -> None:
    body = FRONT.sub("", text, count=1)
    rendered = (
        "---\n"
        + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
        + "\n---\n"
        + body
    )
    path.write_text(rendered, encoding="utf-8")


def append_task_log(text: str, line: str) -> str:
    marker = "## 回溯记录"
    if marker in text:
        start = text.find(marker) + len(marker)
        next_heading = text.find("\n## ", start)
        entry = f"- {line}\n"
        if next_heading >= 0:
            return text[:next_heading] + "\n" + entry + text[next_heading:]
        return text.rstrip() + "\n" + entry
    return text.rstrip() + f"\n\n{marker}\n\n- {line}\n"


def downstream_of(graph: dict, node_id: str) -> list[str]:
    affected: list[str] = []
    frontier = [node_id]
    while frontier:
        current = frontier.pop()
        for child in (graph["nodes"].get(current) or {}).get("downstream") or []:
            if child not in affected and child != node_id:
                affected.append(child)
                frontier.append(child)
    return sorted(affected)


def print_status(graph: dict, detailed_node: str | None = None) -> None:
    nodes = graph.get("nodes") or {}
    print(f"项目：{graph.get('project_title')}（{graph.get('project_root')}）")
    current = graph.get("current_node")
    if current and current in nodes:
        print(f"当前节点：{current}  [{nodes[current]['status']}]  {nodes[current]['title']}")
    else:
        print("当前节点：未选择")
    navigation = graph.get("navigation") or {}
    stack = navigation.get("stack") or []
    index = navigation.get("index", -1)
    if stack:
        rendered = " -> ".join(
            f"[{node_id}]" if position == index else node_id
            for position, node_id in enumerate(stack)
        )
        print(f"导航：{rendered}")
    else:
        print("导航：空")

    summary = graph.get("summary") or {}
    parts = [f"{key}={summary.get(key, 0)}" for key in STATUS_ORDER if summary.get(key, 0)]
    print("状态统计：" + ("，".join(parts) if parts else "无任务"))
    print("")

    if detailed_node:
        node = nodes.get(detailed_node)
        if not node:
            print(f"未知节点：{detailed_node}")
            return
        print(f"节点：{node['id']}  {node['title']}")
        print(f"状态：{node['status']}")
        print(f"文件：{node['path']}")
        print(f"依赖：{', '.join(node['depends_on']) or '无'}")
        print(f"未满足依赖：{', '.join(node['unmet_dependencies']) or '无'}")
        print(f"缺失依赖：{', '.join(node['missing_dependencies']) or '无'}")
        print(f"下游：{', '.join(node['downstream']) or '无'}")
        print(f"访问：{node['visit_count']} 次；最近访问：{node['last_visited_at'] or '从未'}")
        print(f"最近检查点：{node['last_checkpoint'] or '无'}")
        return

    print(f"{'ID':<20} {'状态':<16} {'就绪':<6} 标题")
    for node_id in sorted(nodes):
        node = nodes[node_id]
        ready = "yes" if node["ready"] else "no"
        print(f"{node_id:<20} {node['status']:<16} {ready:<6} {node['title']}")

    candidates = [
        node_id
        for node_id, node in sorted(nodes.items())
        if node["ready"] or node["status"] in {"in_progress", "awaiting_review"}
    ]
    print("")
    print("可执行或可继续节点：" + (", ".join(candidates) if candidates else "暂无"))
    warnings = graph.get("warnings") or []
    if warnings:
        print("")
        print("图同步警告：")
        for warning in warnings:
            print(f"- {warning}")
    print("")
    print("提示：任意节点都可以 start；依赖未完成时会显示风险，但仍需用户确认后执行。")


def command_sync(root: Path) -> int:
    graph = sync_graph(root)
    append_history(
        root,
        "sync",
        current_node=graph.get("current_node"),
        summary=graph.get("summary"),
        warnings=graph.get("warnings"),
    )
    return emit(
        {
            "action": "sync",
            "graph": str(graph_path(root)),
            "current_node": graph.get("current_node"),
            "summary": graph.get("summary"),
            "warnings": graph.get("warnings"),
        }
    )


def command_status(root: Path, node: str | None, as_json: bool) -> int:
    graph = sync_graph(root)
    detailed = None
    if node:
        detailed, candidates = resolve_node(graph, node)
        if detailed is None:
            return emit(
                {"error": f"未知节点：{node}", "candidates": candidates},
                code=2,
            )
    if as_json:
        return emit(graph)
    print_status(graph, detailed)
    return 0


def command_move(root: Path, action: str, node: str, reason: str) -> int:
    graph = sync_graph(root)
    node_id, candidates = resolve_node(graph, node)
    if node_id is None:
        return emit({"error": f"未知节点：{node}", "candidates": candidates}, code=2)
    graph = read_json(graph_path(root)) or graph
    change = move_to(graph, node_id, action, reason, mark_started=action == "start")
    write_json(graph_path(root), graph)
    node_data = graph["nodes"][node_id]

    warnings: list[str] = []
    if node_data["status"] == "completed":
        warnings.append("该节点已标记完成；如需重做，请先执行 reopen。")
    if node_data["unmet_dependencies"]:
        warnings.append(
            "依赖未完成：" + ", ".join(node_data["unmet_dependencies"]) + "；可继续，但需在节点执行卡中说明风险。"
        )
    if node_data["missing_dependencies"]:
        warnings.append(
            "依赖节点不存在：" + ", ".join(node_data["missing_dependencies"])
        )
    if node_data["status"] in {"failed", "blocked", "stale"}:
        warnings.append(f"节点当前状态为 {node_data['status']}，重新开始前请确认原因已处理。")

    append_history(
        root,
        action,
        node=node_id,
        from_node=change["from"],
        to_node=change["to"],
        reason=reason,
        status=node_data["status"],
        unmet_dependencies=node_data["unmet_dependencies"],
    )
    return emit(
        {
            "action": action,
            "node": node_id,
            "title": node_data["title"],
            "status": node_data["status"],
            "ready": node_data["ready"],
            "unmet_dependencies": node_data["unmet_dependencies"],
            "missing_dependencies": node_data["missing_dependencies"],
            "downstream": node_data["downstream"],
            "from": change["from"],
            "to": change["to"],
            "navigation": graph["navigation"],
            "warnings": warnings,
            "requires_user_confirmation": True,
            "message": "已切换当前节点；执行前仍需向用户展示节点执行卡并获得明确确认。",
        }
    )


def command_back(root: Path, steps: int, reason: str, forward: bool = False) -> int:
    graph = sync_graph(root)
    navigation = graph.get("navigation") or {"stack": [], "index": -1}
    stack = list(navigation.get("stack") or [])
    index = int(navigation.get("index", -1))
    if not stack or index < 0:
        return emit({"action": "forward" if forward else "back", "message": "导航历史为空。"}, code=0)
    target = min(len(stack) - 1, index + steps) if forward else max(0, index - steps)
    if target == index:
        return emit(
            {
                "action": "forward" if forward else "back",
                "message": "已经到达导航边界。" if forward else "已经到达导航起点。",
                "current_node": graph.get("current_node"),
            }
        )
    previous = graph.get("current_node")
    stack_index = target
    graph["navigation"] = {"stack": stack, "index": stack_index}
    graph["current_node"] = stack[stack_index]
    touch(graph["nodes"][stack[stack_index]])
    graph["updated_at"] = now()
    write_json(graph_path(root), graph)
    append_history(
        root,
        "forward" if forward else "back",
        node=graph["current_node"],
        from_node=previous,
        to_node=graph["current_node"],
        reason=reason,
        steps=steps,
    )
    return emit(
        {
            "action": "forward" if forward else "back",
            "from": previous,
            "to": graph["current_node"],
            "status": graph["nodes"][graph["current_node"]]["status"],
            "navigation": graph["navigation"],
            "message": "已移动导航光标；任务状态未改变。",
        }
    )


def command_checkpoint(root: Path, note: str) -> int:
    graph = sync_graph(root)
    graph = read_json(graph_path(root)) or graph
    created = now()
    checkpoint_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    directory = checkpoint_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{checkpoint_id}.json"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"{checkpoint_id}-{suffix}.json"
        suffix += 1
    checkpoint_id = candidate.stem

    snapshot = json.loads(json.dumps(graph, ensure_ascii=False))
    snapshot["checkpoint"] = {
        "id": checkpoint_id,
        "created_at": created,
        "note": note,
        "current_node": graph.get("current_node"),
        "statuses": {node_id: node.get("status") for node_id, node in graph.get("nodes", {}).items()},
    }
    write_json(candidate, snapshot)

    relative = str(candidate.relative_to(root))
    graph.setdefault("checkpoints", []).append(
        {
            "id": checkpoint_id,
            "created_at": created,
            "note": note,
            "current_node": graph.get("current_node"),
            "path": relative,
        }
    )
    current = graph.get("current_node")
    if current and current in graph.get("nodes", {}):
        graph["nodes"][current]["last_checkpoint"] = checkpoint_id
    graph["updated_at"] = now()
    write_json(graph_path(root), graph)
    append_history(
        root,
        "checkpoint",
        checkpoint=checkpoint_id,
        note=note,
        current_node=current,
    )
    return emit(
        {
            "action": "checkpoint",
            "checkpoint": checkpoint_id,
            "path": str(candidate),
            "current_node": current,
            "note": note,
        }
    )


def resolve_checkpoint(root: Path, value: str) -> Path | None:
    directory = checkpoint_dir(root).resolve()
    candidate = Path(value).expanduser()
    if candidate.suffix != ".json":
        candidate = directory / f"{value}.json"
    if not candidate.exists():
        matches = sorted(directory.glob(f"{value}*.json"))
        if len(matches) == 1:
            return matches[0].resolve()
        return None
    resolved = candidate.resolve()
    if directory != resolved.parent:
        return None
    return resolved


def command_restore(root: Path, checkpoint: str) -> int:
    path = resolve_checkpoint(root, checkpoint)
    if path is None:
        return emit({"error": f"未找到检查点：{checkpoint}"}, code=2)
    try:
        snapshot = read_json(path)
    except ValueError as exc:
        return emit({"error": str(exc)}, code=2)
    if not snapshot or not isinstance(snapshot.get("nodes"), dict):
        return emit({"error": f"检查点格式无效：{path}"}, code=2)

    current = read_json(graph_path(root)) or {}
    snapshot["project_root"] = str(root)
    snapshot["updated_at"] = now()
    merged_checkpoints = {}
    for item in (current.get("checkpoints") or []) + (snapshot.get("checkpoints") or []):
        if isinstance(item, dict) and item.get("id"):
            merged_checkpoints[item["id"]] = item
    snapshot["checkpoints"] = sorted(
        merged_checkpoints.values(), key=lambda item: item.get("created_at") or ""
    )
    write_json(graph_path(root), snapshot)
    append_history(
        root,
        "restore",
        checkpoint=snapshot.get("checkpoint", {}).get("id", path.stem),
        current_node=snapshot.get("current_node"),
    )
    return emit(
        {
            "action": "restore",
            "checkpoint": snapshot.get("checkpoint", {}).get("id", path.stem),
            "path": str(path),
            "current_node": snapshot.get("current_node"),
            "summary": snapshot.get("summary"),
            "task_files_unchanged": True,
            "message": "已恢复图记忆和导航位置；任务文件状态未改变。需要回退任务状态请使用 reopen。",
        }
    )


def command_reopen(root: Path, node: str, reason: str, cascade: bool) -> int:
    graph = sync_graph(root)
    node_id, candidates = resolve_node(graph, node)
    if node_id is None:
        return emit({"error": f"未知节点：{node}", "candidates": candidates}, code=2)
    node_data = graph["nodes"][node_id]
    path = root / node_data["path"]
    if not path.exists():
        return emit({"error": f"任务文件不存在：{path}"}, code=2)

    changed: list[str] = []
    stamp = now()
    try:
        meta, text = task_meta(path)
        meta["status"] = "ready"
        meta["updated_at"] = stamp
        approval = meta.get("user_approval")
        if not isinstance(approval, dict):
            approval = {}
        approval["execution"] = "pending"
        approval["deliverable_review"] = "pending"
        meta["user_approval"] = approval
        text = append_task_log(text, f"{stamp}：节点回溯（reopen）：{reason}")
        write_task(path, meta, text)
        changed.append(str(path))
    except (ValueError, yaml.YAMLError) as exc:
        return emit({"error": str(exc)}, code=2)

    cascaded: list[str] = []
    if cascade:
        for downstream in downstream_of(graph, node_id):
            target = graph["nodes"].get(downstream)
            if not target:
                continue
            target_path = root / target["path"]
            if not target_path.exists():
                continue
            try:
                target_meta, target_text = task_meta(target_path)
                target_meta["status"] = "stale"
                target_meta["updated_at"] = stamp
                target_approval = target_meta.get("user_approval")
                if not isinstance(target_approval, dict):
                    target_approval = {}
                target_approval["deliverable_review"] = "pending"
                target_meta["user_approval"] = target_approval
                target_text = append_task_log(
                    target_text,
                    f"{stamp}：上游节点 {node_id} 回溯，标记为 stale。",
                )
                write_task(target_path, target_meta, target_text)
                changed.append(str(target_path))
                cascaded.append(downstream)
            except (ValueError, yaml.YAMLError):
                continue

    graph = sync_graph(root, read_json(graph_path(root)) or graph)
    append_history(
        root,
        "reopen",
        node=node_id,
        reason=reason,
        cascade=cascaded,
    )
    return emit(
        {
            "action": "reopen",
            "node": node_id,
            "reason": reason,
            "changed_files": changed,
            "cascaded": cascaded,
            "current_node": graph.get("current_node"),
            "warning": None
            if cascade or not node_data["downstream"]
            else f"未级联更新下游节点：{', '.join(node_data['downstream'])}；如需一起回退请加 --cascade。",
            "message": "节点已回到 ready；执行前仍需用户确认。",
        }
    )


def command_history(root: Path, limit: int, as_json: bool) -> int:
    path = history_path(root)
    events: list[dict] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
    events = events[-limit:] if limit > 0 else events
    if as_json:
        return emit({"history": events})
    if not events:
        print("暂无导航历史。")
        return 0
    for event in events:
        action = event.get("action", "?")
        at = event.get("at", "?")
        node = (
            event.get("node")
            or event.get("to_node")
            or event.get("to")
            or event.get("current_node")
            or event.get("checkpoint")
            or ""
        )
        reason = event.get("reason") or event.get("note") or ""
        print(f"{at}  {action:<10} {node}  {reason}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Keti 节点记忆图：同步、跳转、回溯")
    parser.add_argument("--project-root", required=True, type=Path, help="课题项目根目录")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync", help="从 tasks/*.md 重建记忆图")

    status_parser = subparsers.add_parser("status", help="查看节点图和当前进度")
    status_parser.add_argument("--node", help="查看指定节点的详情")
    status_parser.add_argument("--json", action="store_true", help="输出完整 JSON")

    for name, help_text in (("start", "选择任意节点开始"), ("jump", "跳转到任意节点")):
        move_parser = subparsers.add_parser(name, help=help_text)
        move_parser.add_argument("--node", required=True, help="节点 ID 或标题")
        move_parser.add_argument("--reason", default="", help="跳转原因")

    back_parser = subparsers.add_parser("back", help="沿导航历史回溯")
    back_parser.add_argument("--steps", type=int, default=1, help="回溯步数")
    back_parser.add_argument("--reason", default="", help="回溯原因")

    forward_parser = subparsers.add_parser("forward", help="沿导航历史前进")
    forward_parser.add_argument("--steps", type=int, default=1, help="前进步数")
    forward_parser.add_argument("--reason", default="", help="前进原因")

    checkpoint_parser = subparsers.add_parser("checkpoint", help="保存当前进度检查点")
    checkpoint_parser.add_argument("--note", default="", help="检查点说明")

    restore_parser = subparsers.add_parser("restore", help="恢复检查点的图记忆")
    restore_parser.add_argument("--checkpoint", required=True, help="检查点 ID 或文件")

    reopen_parser = subparsers.add_parser("reopen", help="将节点回退为 ready，并可选级联下游")
    reopen_parser.add_argument("--node", required=True, help="节点 ID 或标题")
    reopen_parser.add_argument("--reason", required=True, help="回溯原因")
    reopen_parser.add_argument("--cascade", action="store_true", help="将传递下游标记为 stale")

    history_parser = subparsers.add_parser("history", help="查看导航历史")
    history_parser.add_argument("--limit", type=int, default=20, help="显示最近 N 条")
    history_parser.add_argument("--json", action="store_true", help="输出 JSON")

    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    if not root.exists():
        return emit({"error": f"项目根目录不存在：{root}"}, code=2)

    try:
        if args.command == "sync":
            return command_sync(root)
        if args.command == "status":
            return command_status(root, args.node, args.json)
        if args.command in {"start", "jump"}:
            return command_move(root, args.command, args.node, args.reason)
        if args.command == "back":
            return command_back(root, max(1, args.steps), args.reason, forward=False)
        if args.command == "forward":
            return command_back(root, max(1, args.steps), args.reason, forward=True)
        if args.command == "checkpoint":
            return command_checkpoint(root, args.note)
        if args.command == "restore":
            return command_restore(root, args.checkpoint)
        if args.command == "reopen":
            return command_reopen(root, args.node, args.reason, args.cascade)
        if args.command == "history":
            return command_history(root, args.limit, args.json)
    except ValueError as exc:
        return emit({"error": str(exc)}, code=2)
    except OSError as exc:
        return emit({"error": str(exc)}, code=2)
    return emit({"error": f"未知命令：{args.command}"}, code=2)


if __name__ == "__main__":
    raise SystemExit(main())
