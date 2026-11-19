#!/usr/bin/env python3
"""校验投稿论文工作区的结构、证据、占位符、图表、引用和合规产物。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - 运行环境缺少依赖时的明确提示
    yaml = None

PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME|XXX)\b|\{\{[^{}\n]+\}\}|\[\[[^\[\]\n]+\]\]|"
    r"待补|待定|占位|此处填写|insert\s+(?:text|figure|table)|\\missingfigure|\\todo\b",
    re.I,
)
FIGURE_MARKDOWN_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FIGURE_LATEX_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
CITE_LATEX_RE = re.compile(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\s*\{([^}]+)\}")
CITE_MARKDOWN_RE = re.compile(r"\[([^\]]*@[^\]]*)\]")
BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")
SECTION_PATTERNS = {
    "abstract": r"abstract|摘要",
    "introduction": r"introduction|引言|前言",
    "related work": r"related work|literature review|相关工作|文献综述",
    "method": r"method|methodology|approach|方法",
    "results": r"results|experiment|实验|结果",
    "discussion": r"discussion|讨论",
    "conclusion": r"conclusion|结论",
    "acknowledgements": r"acknowledg|致谢",
    "references": r"references|bibliography|参考文献",
    "appendix": r"appendix|附录",
}
ASSET_SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".tif", ".tiff")


class Report:
    """收集检查结果。"""

    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, code: str, message: str, path: Path | str | None = None) -> None:
        self.items.append(
            {
                "level": level,
                "code": code,
                "message": message,
                "path": str(path) if path is not None else None,
            }
        )

    def error(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.add("error", code, message, path)

    def warn(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.add("warning", code, message, path)

    def info(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.add("info", code, message, path)

    def count(self, level: str) -> int:
        return sum(1 for item in self.items if item["level"] == level)

    def print_human(self, root: Path) -> None:
        labels = {"error": "ERROR", "warning": "WARN", "info": "INFO"}
        print(f"检查论文工作区：{root}")
        for item in self.items:
            path = f" [{item['path']}]" if item["path"] else ""
            print(f"[{labels[item['level']]}] {item['message']}{path}")
        print(
            f"检查完成：{self.count('error')} 个错误，"
            f"{self.count('warning')} 个警告，{self.count('info')} 条提示。"
        )


def nested(config: dict, *keys: str, default=None):
    current = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def has_real_files(path: Path | None) -> bool:
    if path is None or not path.is_dir():
        return False
    return any(item.is_file() and item.name != ".gitkeep" for item in path.rglob("*"))


def list_section_files(root: Path, config: dict) -> list[Path]:
    declared = config.get("sections") or []
    files: list[Path] = []
    if isinstance(declared, str):
        declared = [declared]
    for value in declared:
        path = resolve_path(root, str(value))
        if path is not None:
            files.append(path)
    if files:
        return files
    sections_dir = root / "sections"
    if not sections_dir.is_dir():
        return []
    return sorted(
        item
        for item in sections_dir.rglob("*")
        if item.is_file()
        and item.suffix.lower() in {".md", ".tex", ".txt"}
        and item.name != ".gitkeep"
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def asset_exists(base: Path, root: Path, reference: str) -> bool:
    cleaned = reference.strip().strip("\"'")
    if not cleaned or cleaned.startswith(("http://", "https://", "data:", "#")):
        return True
    candidates = [Path(cleaned)]
    if not Path(cleaned).suffix:
        candidates.extend(Path(cleaned + suffix) for suffix in ASSET_SUFFIXES)
    for candidate in candidates:
        if candidate.is_absolute():
            if candidate.exists():
                return True
        elif (base / candidate).exists() or (root / candidate).exists():
            return True
    return False


def check_figures(text: str, section: Path, root: Path, report: Report) -> None:
    references = [m.group(1) for m in FIGURE_MARKDOWN_RE.finditer(text)]
    references += [m.group(1) for m in FIGURE_LATEX_RE.finditer(text)]
    for reference in references:
        if not asset_exists(section.parent, root, reference):
            report.error(
                "figure-missing",
                f"章节引用的图片不存在：{reference}",
                section,
            )


def collect_citation_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for match in CITE_LATEX_RE.finditer(text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key:
                keys.add(key)
    for match in CITE_MARKDOWN_RE.finditer(text):
        for part in match.group(1).split(";"):
            if "@" not in part:
                continue
            key = part.split("@", 1)[1].split(",")[0].strip()
            if key:
                keys.add(key)
    return keys


def parse_bib_keys(path: Path) -> set[str]:
    return set(BIB_KEY_RE.findall(read_text(path)))


def check_profile(root: Path, config: dict, report: Report) -> dict | None:
    profile_path = resolve_path(root, nested(config, "template", "profile", default="template/profile.json"))
    profiled = bool(nested(config, "gates", "template_profiled", default=False))
    if profile_path is None or not profile_path.exists():
        if profiled:
            report.error("template-profile-missing", "模板剖析门已开启，但 profile.json 不存在。", profile_path)
        else:
            report.warn("template-profile-missing", "尚未生成模板剖析档案。", profile_path)
        return None
    try:
        profile = json.loads(read_text(profile_path))
    except json.JSONDecodeError as exc:
        report.error("template-profile-invalid", f"模板档案不是有效 JSON：{exc}", profile_path)
        return None
    unknowns = profile.get("unknowns") or []
    if unknowns:
        report.warn(
            "template-unknowns",
            f"模板剖析仍有 {len(unknowns)} 个未知项：{', '.join(map(str, unknowns[:6]))}",
            profile_path,
        )
    confidence = profile.get("confidence")
    if confidence == "low":
        report.warn("template-low-confidence", "模板剖析置信度为 low，需人工核对版式。", profile_path)
    return profile


def check_template_input(root: Path, config: dict, report: Report) -> None:
    provided = resolve_path(root, nested(config, "inputs", "institution_template"))
    template_dir = root / "inputs" / "institution_template"
    if provided and provided.exists():
        report.info("template-input", "已登记机构模板。", provided)
        return
    if has_real_files(template_dir):
        report.info("template-input", "inputs/institution_template 中已有模板文件。", template_dir)
        return
    report.warn("template-missing", "尚未提供机构模板；不得仅凭经验确定投稿格式。", template_dir)


def check_outline(root: Path, config: dict, report: Report) -> None:
    provided = resolve_path(root, nested(config, "inputs", "outline"))
    outline_dir = root / "inputs" / "outline"
    if provided and provided.exists():
        report.info("outline-input", "已登记用户内容大纲。", provided)
    elif has_real_files(outline_dir):
        report.info("outline-input", "inputs/outline 中已有大纲文件。", outline_dir)
    else:
        report.warn("outline-missing", "尚未提供用户内容大纲。", outline_dir)

    map_path = resolve_path(root, nested(config, "outline", "map", default="outline/outline_map.md"))
    mapped = bool(nested(config, "gates", "outline_mapped", default=False))
    if map_path is None or not map_path.exists():
        if mapped:
            report.error("outline-map-missing", "大纲映射门已开启，但 outline_map.md 不存在。", map_path)
        else:
            report.warn("outline-map-missing", "尚未生成大纲映射表。", map_path)
        return
    content = read_text(map_path)
    if "未映射" in content:
        if mapped:
            report.error("outline-map-pending", "大纲映射门已开启，但映射表仍标记为未映射。", map_path)
        else:
            report.warn("outline-map-pending", "大纲映射表仍为初始模板。", map_path)


def check_evidence(root: Path, config: dict, report: Report) -> None:
    manifest_path = resolve_path(root, nested(config, "evidence", "manifest", default="evidence/manifest.json"))
    inventoried = bool(nested(config, "gates", "evidence_inventoried", default=False))
    if manifest_path is None or not manifest_path.exists():
        if inventoried:
            report.error("evidence-missing", "证据盘点门已开启，但 manifest.json 不存在。", manifest_path)
        else:
            report.warn("evidence-missing", "尚未生成证据清单。", manifest_path)
        return
    try:
        manifest = json.loads(read_text(manifest_path))
    except json.JSONDecodeError as exc:
        report.error("evidence-invalid", f"证据清单不是有效 JSON：{exc}", manifest_path)
        return
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        report.warn("evidence-empty", "证据清单为空。", manifest_path)
        return

    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            report.error("evidence-item-invalid", f"第 {index} 个证据条目不是对象。", manifest_path)
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            report.error("evidence-id-missing", f"第 {index} 个证据条目缺少 id。", manifest_path)
        elif item_id in seen:
            report.error("evidence-id-duplicate", f"证据 ID 重复：{item_id}", manifest_path)
        else:
            seen.add(item_id)

        item_path = str(item.get("path") or "").strip()
        if item_path and not item_path.startswith(("http://", "https://")):
            candidates = [resolve_path(root, item_path)]
            if manifest_path.parent != root:
                candidates.append(manifest_path.parent / item_path)
            if not any(candidate and candidate.exists() for candidate in candidates):
                report.error(
                    "evidence-path-missing",
                    f"证据 {item_id or index} 的路径不存在：{item_path}",
                    manifest_path,
                )
        status = str(item.get("status") or "").lower()
        if status in {"stale", "missing", "unverified", "unreadable"}:
            report.warn(
                "evidence-status",
                f"证据 {item_id or index} 状态为 {status}，不得支撑确定结论。",
                manifest_path,
            )


def check_sections(root: Path, config: dict, profile: dict | None, report: Report) -> list[Path]:
    files = list_section_files(root, config)
    approved = bool(nested(config, "gates", "draft_approved", default=False))
    if not files:
        if approved:
            report.error("sections-missing", "正文门已开启，但未找到章节文件。", root / "sections")
        else:
            report.warn("sections-missing", "尚未生成章节文件。", root / "sections")
        return files

    bibliography_path = resolve_path(root, config.get("bibliography"))
    bib_keys = parse_bib_keys(bibliography_path) if bibliography_path and bibliography_path.exists() else set()
    all_text: list[str] = []
    all_citations: set[str] = set()

    for section in files:
        if not section.exists():
            report.error("section-path-missing", "声明的章节文件不存在。", section)
            continue
        if section.stat().st_size == 0:
            report.error("section-empty", "章节文件为空。", section)
            continue
        if section.suffix.lower() not in {".md", ".tex", ".txt"}:
            report.warn("section-unchecked", "非文本章节无法自动检查占位符与引用。", section)
            continue
        text = read_text(section)
        all_text.append(text)
        for match in PLACEHOLDER_RE.finditer(text):
            line = text[: match.start()].count("\n") + 1
            report.error(
                "placeholder",
                f"发现未完成占位符“{match.group(0)}”（第 {line} 行）。",
                section,
            )
        check_figures(text, section, root, report)
        all_citations |= collect_citation_keys(text)

    if all_citations:
        if not bibliography_path:
            report.warn("bibliography-unset", "正文含引用，但 manuscript.yaml 未设置 bibliography。")
        elif not bibliography_path.exists():
            report.error("bibliography-missing", "bibliography 指向的文件不存在。", bibliography_path)
        else:
            missing = sorted(all_citations - bib_keys)
            if missing:
                report.error(
                    "citation-key-missing",
                    f"引用键在文献库中不存在：{', '.join(missing[:10])}",
                    bibliography_path,
                )

    if profile:
        merged = profile.get("merged") or {}
        required = merged.get("required_sections") or []
        combined = " ".join(all_text)
        for name in required:
            pattern = SECTION_PATTERNS.get(str(name).lower())
            if pattern and not re.search(pattern, combined, re.I):
                report.warn(
                    "required-section-missing",
                    f"模板要求的章节可能缺失：{name}",
                    root / "sections",
                )
    return files


def check_anonymity(config: dict, section_files: list[Path], report: Report) -> None:
    anonymous = config.get("anonymous")
    if anonymous not in {True, "yes", "true"}:
        return
    for section in section_files:
        if section.suffix.lower() not in {".md", ".tex", ".txt"} or not section.exists():
            continue
        text = read_text(section)
        for match in re.finditer(r"\\(?:author|affil|institute|affiliation)\s*\{([^{}]*)\}", text):
            value = match.group(1).strip()
            if value and not re.search(r"anonymous|匿名", value, re.I):
                report.error(
                    "anonymity-leak",
                    f"匿名投稿模式下发现作者/单位信息：{value[:60]}",
                    section,
                )


def check_outputs(root: Path, config: dict, report: Report) -> None:
    output = resolve_path(root, config.get("output"))
    verified = bool(nested(config, "gates", "compliance_verified", default=False))
    if output is None or not output.exists():
        if verified:
            report.error("output-missing", "合规门已开启，但成稿输出文件不存在。", output)
        else:
            report.warn("output-missing", "尚未生成成稿输出文件。", output)
    elif output.stat().st_size == 0:
        report.error("output-empty", "成稿输出文件为空。", output)

    compliance = resolve_path(root, nested(config, "reports", "compliance", default="reports/compliance.md"))
    if compliance is None or not compliance.exists():
        if verified:
            report.error("compliance-missing", "合规门已开启，但 compliance.md 不存在。", compliance)
        else:
            report.warn("compliance-missing", "尚未生成合规报告。", compliance)
        return
    content = read_text(compliance)
    if re.search(r"总体状态\s*[:：]\s*未通过", content):
        report.error("compliance-failed", "合规报告标记为未通过。", compliance)
    if re.search(r"\|\s*fail\s*\|", content, re.I):
        report.warn("compliance-items", "合规报告中仍有 fail 项。", compliance)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Paper Composer 论文工作区")
    parser.add_argument("--root", required=True, help="论文工作区根目录")
    parser.add_argument("--strict", action="store_true", help="把警告也视为失败")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出检查结果")
    args = parser.parse_args()

    if yaml is None:
        print("错误：缺少 PyYAML。请运行 python -m pip install -r requirements.txt", file=sys.stderr)
        return 2

    root = Path(args.root).expanduser().resolve()
    report = Report()
    config_path = root / "manuscript.yaml"
    if not config_path.exists():
        print(f"错误：未找到 manuscript.yaml：{config_path}", file=sys.stderr)
        return 2
    try:
        config = yaml.safe_load(read_text(config_path)) or {}
    except yaml.YAMLError as exc:
        print(f"错误：manuscript.yaml 解析失败：{exc}", file=sys.stderr)
        return 2
    if not isinstance(config, dict):
        print("错误：manuscript.yaml 顶层必须是映射。", file=sys.stderr)
        return 2

    for key in ("title", "language", "output_format"):
        if not config.get(key):
            report.error("config-missing", f"manuscript.yaml 缺少字段：{key}", config_path)
    if not config.get("venue"):
        report.warn("venue-missing", "未填写目标单位或期刊。", config_path)

    check_template_input(root, config, report)
    profile = check_profile(root, config, report)
    check_outline(root, config, report)
    check_evidence(root, config, report)
    sections = check_sections(root, config, profile, report)
    check_anonymity(config, sections, report)
    check_outputs(root, config, report)

    if args.json:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "errors": report.count("error"),
                    "warnings": report.count("warning"),
                    "items": report.items,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        report.print_human(root)

    if report.count("error"):
        return 1
    if args.strict and report.count("warning"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
