#!/usr/bin/env python3
"""剖析机构投稿模板，生成结构化格式档案和可读报告。

支持 LaTeX 源码/类文件、Word 模板、Markdown/文本投稿指南以及模板压缩包。
PDF 只登记为待提取文本，不猜测版式。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SUPPORTED_SUFFIXES = {
    ".tex",
    ".cls",
    ".sty",
    ".docx",
    ".dotx",
    ".pdf",
    ".md",
    ".txt",
    ".zip",
}
TEXT_SUFFIXES = {".md", ".txt"}
CANONICAL_SECTIONS = (
    ("abstract", r"abstract|摘要"),
    ("introduction", r"introduction|引言|前言"),
    ("related work", r"related work|literature review|相关工作|文献综述"),
    ("method", r"method|methodology|方法"),
    ("results", r"results|experiment|实验|结果"),
    ("discussion", r"discussion|讨论"),
    ("conclusion", r"conclusion|结论"),
    ("acknowledgements", r"acknowledg|致谢"),
    ("references", r"references|bibliography|参考文献"),
    ("appendix", r"appendix|附录"),
)
FEATURE_PATTERNS = {
    "abstract": r"\\begin\{abstract\}|\\abstract\b|摘要|abstract",
    "keywords": r"\\keywords?\b|keywords?|关键词",
    "acknowledgements": r"acknowledg|致谢",
    "appendix": r"\\appendix\b|appendix|附录",
    "data_availability": r"data availability|数据可用性|数据获取",
    "code_availability": r"code availability|代码可用性|代码获取",
    "conflict_of_interest": r"conflict of interest|competing interest|利益冲突",
    "ethics": r"ethic|伦理",
    "author_contributions": r"author contribution|作者贡献",
}


def timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).isoformat()


def collapse(value: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def strip_latex(value: str) -> str:
    text = re.sub(
        r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?",
        lambda m: m.group(1) or "",
        value or "",
    )
    return collapse(text.replace("{", "").replace("}", ""))


def to_cm(value: str) -> float | None:
    match = re.fullmatch(r"\s*([\d.]+)\s*(cm|mm|in|pt)\s*", value or "", re.I)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2).lower()
    if unit == "cm":
        return round(number, 2)
    if unit == "mm":
        return round(number / 10, 2)
    if unit == "in":
        return round(number * 2.54, 2)
    return round(number / 28.3465, 2)


def parse_geometry(options: str) -> tuple[dict, list[str], int | None]:
    margins: dict[str, float] = {}
    notes: list[str] = []
    columns: int | None = None
    for raw in (options or "").split(","):
        item = raw.strip()
        if not item:
            continue
        if item in {"twocolumn", "twoside"}:
            if item == "twocolumn":
                columns = 2
            continue
        if item in {"a4paper", "letterpaper", "a5paper", "b5paper"}:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            key = key.strip().lower()
            value = value.strip()
            if key == "margin":
                cm = to_cm(value)
                if cm is not None:
                    for side in ("top", "bottom", "left", "right"):
                        margins[side] = cm
            elif key in {"top", "bottom", "left", "right", "inner", "outer"}:
                cm = to_cm(value)
                if cm is not None:
                    margins[key] = cm
            elif key in {"textwidth", "textheight", "columnsep"}:
                notes.append(f"{key}={value}")
            continue
        cm = to_cm(item)
        if cm is not None:
            notes.append(f"unnamed_length={item}")
    return margins, notes, columns


def detect_features(text: str) -> dict[str, bool]:
    return {
        key: bool(re.search(pattern, text, re.I)) for key, pattern in FEATURE_PATTERNS.items()
    }


def detect_required_sections(text: str) -> list[str]:
    found: list[str] = []
    for name, pattern in CANONICAL_SECTIONS:
        if re.search(pattern, text, re.I):
            found.append(name)
    return found


def detect_limits(text: str) -> tuple[dict, list[str]]:
    limits: dict[str, int | None] = {"pages": None, "words": None, "abstract_words": None}
    evidence: list[str] = []
    page_match = re.search(r"(\d+)\s*(?:[-–~to]\s*(\d+))?\s*(?:pages?|页)", text, re.I)
    if page_match:
        values = [int(v) for v in page_match.groups() if v]
        limits["pages"] = max(values) if values else None
        evidence.append(collapse(page_match.group(0)))

    remaining = text
    abstract_match = re.search(r"abstract[^.\n]{0,120}?(\d[\d,]*)\s*(?:words?|字|词)", text, re.I)
    if abstract_match:
        limits["abstract_words"] = int(abstract_match.group(1).replace(",", ""))
        evidence.append(collapse(abstract_match.group(0)))
        remaining = text[: abstract_match.start()] + text[abstract_match.end() :]

    word_match = re.search(r"(\d[\d,]*)\s*(?:words?|字|词)", remaining, re.I)
    if word_match:
        limits["words"] = int(word_match.group(1).replace(",", ""))
        evidence.append(collapse(word_match.group(0)))
    return limits, evidence


def detect_anonymity(text: str) -> str:
    if re.search(r"anonym|匿名|blind review|双盲", text, re.I):
        if re.search(r"not\s+anonym|不需要匿名|无需匿名", text, re.I):
            return "not_required"
        return "required"
    return "unknown"


def analyze_latex_text(text: str, label: str, is_class: bool = False) -> dict:
    document_class = None
    class_match = re.search(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}", text)
    if class_match:
        document_class = {
            "name": class_match.group(2).strip(),
            "options": class_match.group(1) or "",
        }
    elif is_class:
        provides = re.search(r"\\ProvidesClass\{([^}]+)\}", text)
        loads = re.search(r"\\LoadClass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}", text)
        if provides:
            document_class = {"name": provides.group(1), "options": ""}
        elif loads:
            document_class = {"name": loads.group(2), "options": loads.group(1) or ""}

    packages: list[dict] = []
    seen_packages: set[tuple[str, str]] = set()
    for match in re.finditer(r"\\(?:usepackage|RequirePackage)\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}", text):
        options = match.group(1) or ""
        for name in match.group(2).split(","):
            name = name.strip()
            key = (name, options)
            if name and key not in seen_packages:
                seen_packages.add(key)
                packages.append({"name": name, "options": options})

    package_names = {item["name"] for item in packages}
    page: dict = {"size": None, "margins_cm": {}, "columns": None, "notes": []}
    if re.search(r"\ba4paper\b", text, re.I):
        page["size"] = "A4"
    elif re.search(r"\bletterpaper\b", text, re.I):
        page["size"] = "Letter"
    for item in packages:
        if item["name"] == "geometry":
            margins, notes, columns = parse_geometry(item["options"])
            page["margins_cm"].update(margins)
            page["notes"].extend(notes)
            if columns:
                page["columns"] = columns
    if re.search(r"\btwocolumn\b", text):
        page["columns"] = page["columns"] or 2

    fonts: dict = {"body": None, "heading": None, "mono": None, "size_pt": None}
    body_match = re.search(
        r"\\setmainfont\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", text
    )
    mono_match = re.search(
        r"\\setmonofont\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", text
    )
    if body_match:
        fonts["body"] = body_match.group(1).strip()
    if mono_match:
        fonts["mono"] = mono_match.group(1).strip()
    known_font_packages = {
        "mathptmx": "Times",
        "newtxtext": "Times",
        "times": "Times",
        "palatino": "Palatino",
        "newpxtext": "Palatino",
        "helvet": "Helvetica",
        "lmodern": "Latin Modern",
        "libertine": "Linux Libertine",
    }
    if not fonts["body"]:
        for package, font in known_font_packages.items():
            if package in package_names:
                fonts["body"] = font
                break
    if {"ctex", "ctexart", "ctexrep", "ctexbook"} & package_names:
        fonts["body"] = fonts["body"] or "ctex 默认中文字体"
    size_match = re.search(
        r"\\(?:documentclass|LoadClass|PassOptionsToClass)\s*\[[^\]]*?(\d{1,2})pt",
        text,
    )
    if size_match:
        fonts["size_pt"] = int(size_match.group(1))

    levels = {"part": 0, "chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4}
    sections: list[dict] = []
    for match in re.finditer(
        r"\\(part|chapter|section|subsection|subsubsection)\*?\s*(?:\[[^\]]*\])?\s*\{([^{}]*)\}",
        text,
    ):
        command = match.group(1)
        sections.append(
            {
                "level": levels[command],
                "command": command,
                "title": strip_latex(match.group(2)),
                "numbered": "*" not in match.group(0)[: match.group(0).find("{")],
                "line": text[: match.start()].count("\n") + 1,
            }
        )

    citation: dict = {"style": None, "bibliography_style": None, "tool": None}
    style_match = re.search(r"\\bibliographystyle\{([^}]+)\}", text)
    if style_match:
        citation["bibliography_style"] = style_match.group(1).strip()
    biblatex = next((item for item in packages if item["name"] == "biblatex"), None)
    if biblatex:
        citation["tool"] = "biber"
        style_option = re.search(r"(?:^|,)\s*style\s*=\s*([^,]+)", biblatex["options"])
        if style_option:
            citation["style"] = style_option.group(1).strip()
        else:
            citation["style"] = "biblatex default"
    if "natbib" in package_names:
        citation["tool"] = citation["tool"] or "bibtex"
        natbib = next((item for item in packages if item["name"] == "natbib"), None)
        if natbib and natbib["options"]:
            citation["style"] = citation["style"] or natbib["options"]
    if not citation["style"] and citation["bibliography_style"]:
        citation["style"] = citation["bibliography_style"]

    limits, limit_evidence = detect_limits(text)
    anomalies: list[str] = []
    if re.search(r"lorem ipsum|TODO|TBD|XXX|\[\s*insert", text, re.I):
        anomalies.append("模板中存在占位文本，成稿前必须替换。")
    if not document_class:
        anomalies.append("未识别到文档类，请确认是否为完整 LaTeX 模板。")
    if not sections and not is_class:
        anomalies.append("未识别到章节命令，章节结构需人工确认。")

    return {
        "type": "latex-class" if is_class else "latex",
        "path": label,
        "document_class": document_class,
        "packages": packages,
        "page": page,
        "fonts": fonts,
        "line_spacing": "onehalf" if re.search(r"\\onehalfspacing|setstretch\{1\.5", text) else None,
        "sections": sections[:200],
        "citation": citation,
        "features": detect_features(text),
        "required_sections": detect_required_sections(text),
        "limits": limits,
        "limit_evidence": limit_evidence,
        "anonymity": detect_anonymity(text),
        "anomalies": anomalies,
    }


def analyze_latex_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    return analyze_latex_text(text, str(path), is_class=path.suffix.lower() in {".cls", ".sty"})


def analyze_docx(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        styles_bytes = archive.read("word/styles.xml") if "word/styles.xml" in names else b""
        document_bytes = archive.read("word/document.xml") if "word/document.xml" in names else b""

    styles_root = ET.fromstring(styles_bytes) if styles_bytes else None
    document_root = ET.fromstring(document_bytes) if document_bytes else None

    fonts: dict = {"body": None, "heading": None, "mono": None, "size_pt": None}
    style_names: dict[str, str] = {}
    styles: list[dict] = []
    if styles_root is not None:
        defaults = styles_root.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
        if defaults is not None:
            default_fonts = defaults.find(f"{W}rFonts")
            if default_fonts is not None:
                fonts["body"] = default_fonts.get(f"{W}eastAsia") or default_fonts.get(f"{W}ascii")
            default_size = defaults.find(f"{W}sz")
            if default_size is not None and default_size.get(f"{W}val"):
                fonts["size_pt"] = int(default_size.get(f"{W}val")) / 2
        for style in styles_root.findall(f"{W}style"):
            style_id = style.get(f"{W}styleId") or ""
            name_el = style.find(f"{W}name")
            name = name_el.get(f"{W}val") if name_el is not None else style_id
            if style_id:
                style_names[style_id] = name or style_id
            rpr = style.find(f"{W}rPr")
            ppr = style.find(f"{W}pPr")
            outline_el = ppr.find(f"{W}outlineLvl") if ppr is not None else None
            style_font = None
            style_size = None
            if rpr is not None:
                rfonts = rpr.find(f"{W}rFonts")
                if rfonts is not None:
                    style_font = rfonts.get(f"{W}eastAsia") or rfonts.get(f"{W}ascii")
                size_el = rpr.find(f"{W}sz")
                if size_el is not None and size_el.get(f"{W}val"):
                    style_size = int(size_el.get(f"{W}val")) / 2
            styles.append(
                {
                    "id": style_id,
                    "name": name,
                    "type": style.get(f"{W}type"),
                    "based_on": (style.find(f"{W}basedOn").get(f"{W}val") if style.find(f"{W}basedOn") is not None else None),
                    "font": style_font,
                    "size_pt": style_size,
                    "outline_level": int(outline_el.get(f"{W}val")) + 1 if outline_el is not None and outline_el.get(f"{W}val") else None,
                }
            )
        heading_font = next(
            (item["font"] for item in styles if item["name"].lower().startswith("heading 1") and item["font"]),
            None,
        )
        fonts["heading"] = heading_font

    page: dict = {"size": None, "margins_cm": {}, "columns": None, "notes": []}
    sections: list[dict] = []
    heading_texts: list[str] = []
    body_text: list[str] = []
    has_header_footer = False
    if document_root is not None:
        sect = document_root.find(f".//{W}sectPr")
        if sect is not None:
            pg_sz = sect.find(f"{W}pgSz")
            if pg_sz is not None:
                width = pg_sz.get(f"{W}w")
                height = pg_sz.get(f"{W}h")
                if width and height:
                    width_cm = round(int(width) / 1440 * 2.54, 2)
                    height_cm = round(int(height) / 1440 * 2.54, 2)
                    if abs(width_cm - 21.0) < 0.2 and abs(height_cm - 29.7) < 0.2:
                        page["size"] = "A4"
                    elif abs(width_cm - 21.59) < 0.2 and abs(height_cm - 27.94) < 0.2:
                        page["size"] = "Letter"
                    else:
                        page["size"] = f"{width_cm}x{height_cm} cm"
            pg_mar = sect.find(f"{W}pgMar")
            if pg_mar is not None:
                for side in ("top", "bottom", "left", "right"):
                    value = pg_mar.get(f"{W}{side}")
                    if value:
                        page["margins_cm"][side] = round(int(value) / 1440 * 2.54, 2)
            cols = sect.find(f"{W}cols")
            if cols is not None and cols.get(f"{W}num"):
                page["columns"] = int(cols.get(f"{W}num"))
            has_header_footer = bool(
                sect.find(f"{W}headerReference") is not None
                or sect.find(f"{W}footerReference") is not None
            )
        body = document_root.find(f"{W}body")
        if body is not None:
            for paragraph in body.findall(f"{W}p"):
                text = collapse("".join(node.text or "" for node in paragraph.iter(f"{W}t")))
                if not text:
                    continue
                body_text.append(text)
                ppr = paragraph.find(f"{W}pPr")
                style_el = ppr.find(f"{W}pStyle") if ppr is not None else None
                style_id = style_el.get(f"{W}val") if style_el is not None else ""
                style_name = style_names.get(style_id or "", style_id or "")
                level = None
                name_match = re.match(r"heading\s*([1-9])", style_name, re.I)
                if name_match:
                    level = int(name_match.group(1))
                elif style_id.lower().startswith("heading"):
                    digits = re.search(r"(\d+)", style_id)
                    level = int(digits.group(1)) if digits else None
                if level:
                    sections.append({"level": level, "title": text, "style": style_name})
                    heading_texts.append(text)

    features = detect_features(" ".join(heading_texts) + " " + " ".join(body_text[:200]))
    limits, limit_evidence = detect_limits(" ".join(body_text[:500]))
    anomalies: list[str] = []
    if document_root is None:
        anomalies.append("未能读取 word/document.xml，Word 模板可能损坏或格式不受支持。")
    if not page["margins_cm"]:
        anomalies.append("未读取到页边距，需人工确认。")
    if re.search(r"lorem ipsum|TODO|TBD|XXX|click here|insert", " ".join(body_text), re.I):
        anomalies.append("模板中存在占位文本，成稿前必须替换。")
    if not has_header_footer:
        anomalies.append("未识别到页眉页脚引用，请确认模板版式。")

    return {
        "type": "docx",
        "path": str(path),
        "page": page,
        "fonts": fonts,
        "styles": styles[:200],
        "sections": sections[:200],
        "citation": {"style": None, "bibliography_style": None, "tool": None},
        "features": features,
        "required_sections": detect_required_sections(" ".join(heading_texts)),
        "limits": limits,
        "limit_evidence": limit_evidence,
        "anonymity": detect_anonymity(" ".join(body_text[:300])),
        "has_header_footer": has_header_footer,
        "anomalies": anomalies,
    }


def analyze_guideline(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    keywords = re.compile(
        r"page|word|font|margin|template|format|citation|reference|anonym|blind|section|figure|table|"
        r"页|字|字体|字号|页边距|模板|格式|引用|参考文献|匿名|双盲|章节|图|表",
        re.I,
    )
    evidence_lines = [collapse(line.strip(), 220) for line in lines if keywords.search(line)]
    sections = [
        {"level": len(match.group(1)), "title": collapse(match.group(2), 120)}
        for match in re.finditer(r"^(#{1,4})\s+(.+)$", text, re.MULTILINE)
    ]
    limits, limit_evidence = detect_limits(text)
    anomalies: list[str] = []
    if not limits["pages"] and not limits["words"]:
        anomalies.append("未从指南中提取到页数或字数限制，需人工确认。")
    if not sections:
        anomalies.append("指南中没有可识别的 Markdown 标题，章节要求需人工整理。")
    return {
        "type": "guideline",
        "path": str(path),
        "page": {"size": None, "margins_cm": {}, "columns": None, "notes": []},
        "fonts": {"body": None, "heading": None, "mono": None, "size_pt": None},
        "sections": sections,
        "citation": {"style": None, "bibliography_style": None, "tool": None},
        "features": detect_features(text),
        "required_sections": detect_required_sections(text),
        "limits": limits,
        "limit_evidence": limit_evidence,
        "anonymity": detect_anonymity(text),
        "guideline_lines": evidence_lines[:60],
        "anomalies": anomalies,
    }


def analyze_archive(path: Path) -> dict:
    entries: list[str] = []
    analyses: list[dict] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist()[:200]:
                entries.append(info.filename)
                suffix = Path(info.filename).suffix.lower()
                if suffix in {".tex", ".cls", ".sty"}:
                    try:
                        text = archive.read(info).decode("utf-8", errors="replace")
                        analyses.append(
                            analyze_latex_text(
                                text,
                                f"{path}::{info.filename}",
                                is_class=suffix in {".cls", ".sty"},
                            )
                        )
                    except Exception as exc:  # noqa: BLE001 - 单文件失败不应中断整体剖析
                        analyses.append(
                            {
                                "type": "error",
                                "path": f"{path}::{info.filename}",
                                "error": str(exc),
                            }
                        )
    except zipfile.BadZipFile as exc:
        return {
            "type": "error",
            "path": str(path),
            "error": f"无法读取压缩包：{exc}",
            "anomalies": ["压缩包损坏或不是标准 ZIP。"],
        }
    result = {
        "type": "archive",
        "path": str(path),
        "entries": entries,
        "notes": ["压缩包内的 .docx 需解压后单独剖析。"],
    }
    if analyses:
        result["embedded_analyses"] = analyses
    return result


def analyze_file(path: Path) -> dict:
    suffix = path.suffix.lower()
    try:
        if suffix in {".tex", ".cls", ".sty"}:
            return analyze_latex_file(path)
        if suffix in {".docx", ".dotx"}:
            return analyze_docx(path)
        if suffix in TEXT_SUFFIXES:
            return analyze_guideline(path)
        if suffix == ".pdf":
            return {
                "type": "pdf",
                "path": str(path),
                "needs_text_extraction": True,
                "anomalies": [
                    "PDF 未自动解析。请先用 PDF 工具提取文字或提供官方可读指南，再重新剖析。"
                ],
            }
        if suffix == ".zip":
            return analyze_archive(path)
        return {"type": "unsupported", "path": str(path), "error": f"不支持的扩展名：{suffix}"}
    except Exception as exc:  # noqa: BLE001 - 保留单文件错误，便于报告
        return {"type": "error", "path": str(path), "error": str(exc)}


def collect_files(path: Path, max_files: int) -> list[Path]:
    if path.is_file():
        return [path]
    files: list[Path] = []
    for candidate in sorted(path.rglob("*")):
        if not candidate.is_file():
            continue
        if any(part in {".git", "__pycache__", "node_modules"} for part in candidate.parts):
            continue
        if candidate.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(candidate)
        if len(files) >= max_files:
            break
    return files


def flatten_results(results: list[dict]) -> list[dict]:
    flattened: list[dict] = []
    for item in results:
        if item.get("embedded_analyses"):
            flattened.extend(flatten_results(item["embedded_analyses"]))
        else:
            flattened.append(item)
    return flattened


def normalize_sections(sections: list[dict]) -> list[dict]:
    """把章节层级平移到从 1 开始，便于报告展示。"""
    if not sections:
        return []
    base = min(int(item.get("level", 1) or 1) for item in sections)
    normalized: list[dict] = []
    for item in sections:
        entry = dict(item)
        entry["level"] = max(1, int(entry.get("level", 1) or 1) - base + 1)
        normalized.append(entry)
    return normalized


def merge_results(results: list[dict]) -> dict:
    flat = [item for item in flatten_results(results) if item.get("type") not in {"error", "unsupported", "pdf", "archive"}]

    def first(key: str, default=None):
        for item in flat:
            value = item.get(key)
            if value not in (None, "", [], {}):
                return value
        return default

    def merge_dict(key: str) -> dict:
        merged: dict = {}
        for item in flat:
            for name, value in (item.get(key) or {}).items():
                if merged.get(name) in (None, "", [], {}) and value not in (None, "", [], {}):
                    merged[name] = value
        return merged

    sections: list[dict] = []
    sections_source = None
    for item in flat:
        if item.get("type") in {"latex", "latex-class", "docx"} and item.get("sections"):
            sections = normalize_sections(item["sections"])
            sections_source = item.get("path")
            break
    if not sections:
        for item in flat:
            if item.get("sections"):
                sections = normalize_sections(item["sections"])
                sections_source = item.get("path")
                break

    anonymity = "unknown"
    for item in flat:
        if item.get("anonymity") in {"required", "not_required"}:
            anonymity = item["anonymity"]
            break

    merged = {
        "document_class": first("document_class"),
        "packages": first("packages", []),
        "page": merge_dict("page"),
        "fonts": merge_dict("fonts"),
        "line_spacing": first("line_spacing"),
        "sections": sections,
        "sections_source": sections_source,
        "citation": merge_dict("citation"),
        "figures": merge_dict("figures"),
        "tables": merge_dict("tables"),
        "required_sections": [],
        "declarations": [],
        "limits": merge_dict("limits"),
        "anonymity": anonymity,
        "build": {},
    }
    seen_required: set[str] = set()
    for item in flat:
        for name in item.get("required_sections") or []:
            if name not in seen_required:
                seen_required.add(name)
                merged["required_sections"].append(name)
    for feature, enabled in merge_dict("features").items():
        if enabled:
            merged["declarations"].append(feature)

    unknowns: list[str] = []
    if not merged["page"].get("size"):
        unknowns.append("页面尺寸")
    if not merged["page"].get("margins_cm"):
        unknowns.append("页边距")
    if not merged["fonts"].get("body"):
        unknowns.append("正文字体")
    if not merged["citation"].get("style"):
        unknowns.append("引用样式")
    if not merged["sections"]:
        unknowns.append("章节结构")
    if not merged["limits"].get("pages") and not merged["limits"].get("words"):
        unknowns.append("页数/字数限制")
    if merged["anonymity"] == "unknown":
        unknowns.append("匿名要求")

    anomalies: list[str] = []
    for item in results:
        for note in item.get("anomalies") or []:
            if note not in anomalies:
                anomalies.append(note)

    template_like = [item for item in flat if item.get("type") in {"latex", "latex-class", "docx"}]
    if len(template_like) >= 2:
        confidence = "high"
    elif template_like:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "merged": merged,
        "unknowns": unknowns,
        "anomalies": anomalies,
        "confidence": confidence,
    }


def build_report(profile: dict) -> str:
    merged = profile["merged"]
    lines = [
        "# 机构模板剖析报告",
        "",
        f"- 生成时间：{profile['generated_at']}",
        f"- 置信度：`{profile['confidence']}`",
        f"- 输入数量：{len(profile['sources'])}",
        "",
        "## 核心约束",
        "",
        f"- 文档类：`{(merged.get('document_class') or {}).get('name') or 'unknown'}`",
        f"- 页面：`{merged['page'].get('size') or 'unknown'}`",
        f"- 页边距（cm）：`{merged['page'].get('margins_cm') or {}}`",
        f"- 分栏：`{merged['page'].get('columns') or 'unknown'}`",
        f"- 正文字体：`{merged['fonts'].get('body') or 'unknown'}`",
        f"- 字号：`{merged['fonts'].get('size_pt') or 'unknown'}`",
        f"- 引用样式：`{merged['citation'].get('style') or 'unknown'}`",
        f"- 页数限制：`{merged['limits'].get('pages') or 'unknown'}`",
        f"- 总字数限制：`{merged['limits'].get('words') or 'unknown'}`",
        f"- 摘要字数限制：`{merged['limits'].get('abstract_words') or 'unknown'}`",
        f"- 匿名要求：`{merged['anonymity']}`",
        f"- 章节来源：`{merged.get('sections_source') or 'unknown'}`",
        "",
        "## 章节骨架",
        "",
    ]
    if merged["sections"]:
        for section in merged["sections"]:
            indent = "  " * max(0, section["level"] - 1)
            lines.append(f"{indent}- {section.get('title', '')}")
    else:
        lines.append("- 未识别到章节结构，需人工确认。")
    lines.extend(["", "## 必需内容", ""])
    if merged["required_sections"]:
        lines.extend(f"- {name}" for name in merged["required_sections"])
    else:
        lines.append("- 未识别到必需章节。")
    lines.extend(["", "## 未知项", ""])
    if profile["unknowns"]:
        lines.extend(f"- {name}" for name in profile["unknowns"])
    else:
        lines.append("- 无")
    lines.extend(["", "## 异常与人工确认", ""])
    if profile["anomalies"]:
        lines.extend(f"- {note}" for note in profile["anomalies"])
    else:
        lines.append("- 无")
    lines.extend(["", "## 逐文件分析", ""])
    for analysis in profile["analyses"]:
        lines.append(f"### `{analysis.get('path', '')}`")
        lines.append("")
        lines.append(f"- 类型：`{analysis.get('type', 'unknown')}`")
        if analysis.get("error"):
            lines.append(f"- 错误：{analysis['error']}")
        if analysis.get("document_class"):
            doc = analysis["document_class"]
            lines.append(f"- 文档类：`{doc.get('name')}` `{doc.get('options') or ''}`")
        if analysis.get("guideline_lines"):
            lines.append("- 指南要点：")
            lines.extend(f"  - {line}" for line in analysis["guideline_lines"][:15])
        if analysis.get("limit_evidence"):
            lines.append(f"- 限制证据：{'; '.join(analysis['limit_evidence'])}")
        lines.append("")
    lines.extend(
        [
            "## 后续动作",
            "",
            "1. 对“未知项”回读原模板或投稿指南确认，不得猜测。",
            "2. 用本报告和 `profile.json` 生成章节骨架。",
            "3. 若只有 PDF 或指南文字，置信度较低，需人工核对版式。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="剖析机构投稿模板并生成格式档案")
    parser.add_argument("--path", required=True, help="模板文件或模板目录")
    parser.add_argument("--root", help="论文工作区根目录；用于默认输出位置")
    parser.add_argument("--output", help="profile.json 输出路径")
    parser.add_argument("--report", help="Markdown 报告输出路径")
    parser.add_argument("--max-files", type=int, default=200, help="目录扫描的最大文件数")
    args = parser.parse_args()

    source = Path(args.path).expanduser().resolve()
    if not source.exists():
        print(f"错误：模板路径不存在：{source}", file=sys.stderr)
        return 2

    files = collect_files(source, max_files=args.max_files)
    if not files:
        print(f"错误：未找到支持的模板文件：{source}", file=sys.stderr)
        return 1

    analyses = [analyze_file(path) for path in files]
    usable = [
        item
        for item in analyses
        if item.get("type") not in {"error", "unsupported"}
        or item.get("embedded_analyses")
    ]
    if not usable:
        print("错误：模板文件均无法解析，请检查格式或提供可读版本。", file=sys.stderr)
        return 1
    merged_bundle = merge_results(analyses)
    profile = {
        "schema_version": 1,
        "generated_at": timestamp(),
        "sources": [str(path) for path in files],
        "analyses": analyses,
        "merged": merged_bundle["merged"],
        "unknowns": merged_bundle["unknowns"],
        "anomalies": merged_bundle["anomalies"],
        "confidence": merged_bundle["confidence"],
    }

    root = Path(args.root).expanduser().resolve() if args.root else None
    output = Path(args.output).expanduser().resolve() if args.output else None
    if output is None and root is not None:
        output = root / "template" / "profile.json"
    report = Path(args.report).expanduser().resolve() if args.report else None
    if report is None and root is not None:
        report = root / "template" / "report.md"

    payload = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(f"已生成模板档案：{output}")
    else:
        print(payload)

    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(build_report(profile), encoding="utf-8")
        print(f"已生成模板报告：{report}", file=sys.stderr)

    print(
        f"剖析完成：{len(files)} 个输入，置信度 {profile['confidence']}，"
        f"{len(profile['unknowns'])} 个未知项。",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
