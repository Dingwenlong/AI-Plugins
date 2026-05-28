#!/usr/bin/env python3
"""Package project delivery artifacts from a frozen function-design summary."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FILE_EXTS = ("docx", "xlsx", "vsdx", "svg", "puml")
CONFIG_FILENAME = "local-workspaces.json"
SEQUENCE_EXTS = {".vsdx", ".svg"}
LEGACY_SEQUENCE_SEGMENT = ("output", "sequence_diagram")
NEGATIVE_GLOBAL = [
    "不建议直接",
    "不建議直接",
    "不可进行",
    "不可進行",
    "不能进入开发",
    "不能進入開發",
    "不建议进入开发",
    "不建議進入開發",
    "需补齐后再开发",
    "需補齊後再開發",
    "未达到冻版",
    "未達到凍版",
]
NEGATIVE_ROW = [
    "未发现",
    "未發現",
    "未确认",
    "未確認",
    "未确认引用",
    "未確認引用",
    "历史参考",
    "歷史參考",
    "本次未作为冻版",
    "本次未作為凍版",
    "不应视为当前冻版",
    "不應視為當前凍版",
]
SKIP_CATEGORY_WORDS = [
    "备份",
    "備份",
    "视觉",
    "視覺",
    "Visual",
    "QA",
    "PRD",
    "IT SPEC",
    "旧代码",
    "舊代碼",
    "格式",
]
TSD_VERSION_PATTERN = re.compile(r"(?i)(?:^|[_\s-])(?P<version>v\d+(?:\.\d+)*)(?=[_\s-]|\.docx$)")


@dataclass(frozen=True)
class FunctionGroup:
    raw: str
    display: str
    folder_key: str
    tokens: tuple[str, ...]


@dataclass
class Artifact:
    category: str
    source: Path
    destination: Path
    reason: str


@dataclass(frozen=True)
class CommonRef:
    display: str
    ref_name: str
    method: str | None


@dataclass
class SequenceValidation:
    source_root: Path | None
    function_files: list[Path]
    required_common_refs: list[CommonRef]
    confirmed_common_refs: dict[str, list[Path]]
    missing_common_refs: list[dict[str, object]]
    skipped_unsafe_files: list[Path]


class PackageError(RuntimeError):
    pass


def clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def find_plugin_root(start: Path | None = None) -> Path | None:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".codex-plugin" / "plugin.json").exists():
            return candidate
    return None


def load_workspace_config() -> dict:
    plugin_root = find_plugin_root()
    if plugin_root is None:
        return {}
    config_path = plugin_root / "references" / CONFIG_FILENAME
    if not config_path.exists():
        return {}
    payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def resolve_agent_root(agent_root_arg: str | None, workspace_key: str | None) -> Path | None:
    explicit = clean_text(agent_root_arg) or clean_text(os.environ.get("PROJECT_AGENT_ROOT"))
    if explicit:
        return Path(explicit).expanduser().resolve()

    config = load_workspace_config()
    workspaces = config.get("workspaces") if isinstance(config.get("workspaces"), dict) else {}
    selected_key = clean_text(workspace_key) or clean_text(os.environ.get("PROJECT_WORKSPACE_KEY")) or clean_text(config.get("defaultWorkspace"))
    selected = workspaces.get(selected_key) if selected_key else None
    if isinstance(selected, dict):
        raw_agent_root = clean_text(selected.get("agentRoot"))
        if raw_agent_root:
            return Path(raw_agent_root).expanduser().resolve()
    return None


def normalize_function(raw: str) -> FunctionGroup:
    tokens = tuple(re.findall(r"[A-Za-z]\.\d+(?:\.\d+)*", raw))
    if not tokens:
        cleaned = re.sub(r"[^A-Za-z0-9]+", "", raw).upper()
        tokens = (cleaned,)
    folder_key = "_".join(t.replace(".", "").upper() for t in tokens)
    display = " ".join(tokens)
    return FunctionGroup(raw=raw, display=display, folder_key=folder_key, tokens=tokens)


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp950"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def section(text: str, heading_names: Iterable[str]) -> str:
    names = "|".join(re.escape(name) for name in heading_names)
    pattern = re.compile(rf"^##\s*(?:\d+[.、]\s*)?(?:{names})\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    next_match = re.search(r"^##\s+", text[match.end() :], re.M)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end].strip()


def parse_tables(md: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
                continue
            current.append(cells)
        elif current:
            if len(current) > 1:
                tables.append(current)
            current = []
    if current and len(current) > 1:
        tables.append(current)
    return tables


def extract_paths(text: str, workspace: Path) -> list[Path]:
    values: list[str] = []
    for match in re.finditer(r"`([^`]+?\.(?:" + "|".join(FILE_EXTS) + r"))`", text, re.I):
        values.append(match.group(1).strip())

    # Fallback for unquoted paths in table cells.
    ext_pattern = "|".join(FILE_EXTS)
    for match in re.finditer(r"([A-Za-z]:\\[^|\r\n]+?\.(?:" + ext_pattern + r"))", text, re.I):
        values.append(match.group(1).strip())
    for match in re.finditer(
        r"((?:v1\.x Reference|v1\.x|TSD共用相關|output|舊大戶代碼邏輯理清)[^|\r\n]+?\.(?:"
        + ext_pattern
        + r"))",
        text,
        re.I,
    ):
        values.append(match.group(1).strip())

    paths: list[Path] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip().strip("，,。；; ")
        p = Path(value)
        if not p.is_absolute():
            p = workspace / value
        key = str(p).lower()
        if key not in seen:
            paths.append(p)
            seen.add(key)
    return paths


def summary_search_keys(group: FunctionGroup) -> list[str]:
    keys = [token for token in group.tokens]
    if len(group.tokens) > 1:
        keys.append("_".join(group.tokens))
    keys.append(group.folder_key)
    result: list[str] = []
    seen: set[str] = set()
    for key in keys:
        normalized = clean_text(key)
        if normalized and normalized.lower() not in seen:
            result.append(normalized)
            seen.add(normalized.lower())
    return result


def add_analysis_candidates(candidates: list[Path], agent_root: Path | None, group: FunctionGroup) -> None:
    if agent_root is None:
        return
    functions_root = agent_root / "functions"
    for key in summary_search_keys(group):
        analysis = functions_root / key / "analysis"
        if analysis.exists():
            candidates.extend(analysis.glob("*功能*梳理*.md"))
            candidates.extend(analysis.glob("*功能*設計*.md"))


def find_summary(workspace: Path, group: FunctionGroup, explicit: str | None, agent_root: Path | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = workspace / path
        if not path.exists():
            raise PackageError(f"指定梳理文件不存在: {path}")
        return path

    output = workspace / "output"
    candidates: list[Path] = []
    add_analysis_candidates(candidates, agent_root, group)
    folders = [
        output / f"{group.folder_key}_api_design",
        output / f"{group.folder_key.replace('_', '')}_api_design",
    ]
    for folder in folders:
        if folder.exists():
            candidates.extend(folder.glob("*功能*梳理*.md"))
            candidates.extend(folder.glob("*功能*設計*.md"))

    if output.exists():
        folded = group.folder_key.replace("_", "")
        for path in output.rglob("*功能*梳理*.md"):
            probe = (path.name + " " + path.parent.name).upper().replace(".", "").replace("_", "")
            if folded in probe:
                candidates.append(path)

    unique = sorted({p.resolve(): p for p in candidates if p.is_file()}.values(), key=summary_sort_key, reverse=True)
    if not unique:
        searched = []
        if agent_root is not None:
            searched.append(str(agent_root / "functions" / "<functionCode>" / "analysis"))
        searched.append(str(output))
        raise PackageError(f"未找到 {group.display} 的功能设计梳理文件，停止打包。已查找: {', '.join(searched)}")
    return unique[0]


def summary_sort_key(path: Path) -> tuple[str, float]:
    dates = re.findall(r"20\d{6}", path.name)
    return (max(dates) if dates else "", path.stat().st_mtime)


def assess_summary(text: str) -> tuple[bool, str]:
    confirmed = section(text, ["已确认交付物", "已確認交付物"])
    if not confirmed:
        return False, "梳理文件缺少 已确认交付物 / 已確認交付物 section"

    judgment = section(text, ["总体判断", "總體判斷"])
    if not judgment:
        return False, "梳理文件缺少 总体判断 / 總體判斷 section"

    if any(word in judgment for word in NEGATIVE_GLOBAL):
        return False, "总体判断存在未冻版或不建议进入开发的阻断语句"

    percent_values = [int(v) for v in re.findall(r"(\d{1,3})\s*%", judgment)]
    if percent_values and max(percent_values) < 90:
        return False, f"完成度 {max(percent_values)}% 低于 90% 打包门槛"

    can_dev = any(word in judgment for word in ["可进入开发", "可進入開發", "可進入開發"])
    frozen = any(word in judgment for word in ["冻版", "凍版", "近冻版", "近凍版", "接近冻版", "接近凍版"])
    if not can_dev or not frozen:
        return False, "总体判断未同时说明可进入开发与冻版/近冻版状态"

    return True, "通过冻版/近冻版打包门槛"


def evidence_paths(text: str, workspace: Path) -> dict[str, list[Path]]:
    basis = section(text, ["依据文件", "依據文件"])
    result: dict[str, list[Path]] = {}
    for table in parse_tables(basis):
        for row in table[1:]:
            if len(row) < 2:
                continue
            key = row[0].strip().lower()
            paths = extract_paths(" | ".join(row), workspace)
            if paths:
                result.setdefault(key, []).extend(paths)
    return result


def classify_category(name: str) -> str | None:
    compact = name.replace(" ", "").lower()
    if compact in {"tsd"} or "tsd" in compact:
        return "tsd"
    if "apidetail" in compact or "api規格" in compact or "api规格" in compact:
        return "api_detail"
    if "responsecode" in compact or "response code" in name.lower():
        return "response_code"
    if "commonfunc" in compact:
        return "common_func"
    if "commonutil" in compact:
        return "common_util"
    if "时序图" in name or "時序圖" in name or "循序圖" in name or "sequence" in compact:
        if "外部" in name or "共用" in name:
            return "common_diagram"
        return "function_diagram"
    return None


def row_is_skip(category: str, row_text: str) -> str | None:
    if any(word in category for word in SKIP_CATEGORY_WORDS):
        return "非正式交付物类别"
    if any(word in row_text for word in NEGATIVE_ROW):
        return "该行标记为未确认、历史参考或非冻版图"
    return None


def collect_artifacts(text: str, workspace: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    confirmed = section(text, ["已确认交付物", "已確認交付物"])
    basis = evidence_paths(text, workspace)
    tables = parse_tables(confirmed)
    if not tables:
        raise PackageError("已确认交付物 section 中未找到可解析的 Markdown 表格。")

    artifacts: list[tuple[str, Path]] = []
    skipped: list[str] = []
    seen: set[str] = set()

    basis_key = {
        "tsd": ["tsd"],
        "api_detail": ["api detail", "api規格", "api规格"],
        "response_code": ["response code", "responsecode"],
        "common_func": ["commonfunc"],
        "common_util": ["commonutil"],
    }

    for table in tables:
        for row in table[1:]:
            if not row:
                continue
            category_label = row[0].strip()
            row_text = " | ".join(row)
            category = classify_category(category_label)
            if not category:
                skipped.append(f"{category_label}: 不属于默认交付物类别")
                continue

            skip_reason = row_is_skip(category_label, row_text)
            if skip_reason:
                skipped.append(f"{category_label}: {skip_reason}")
                continue

            paths = extract_paths(row_text, workspace)
            if not paths:
                for key in basis_key.get(category, []):
                    paths.extend(basis.get(key, []))

            if not paths:
                if category == "function_diagram":
                    continue
                skipped.append(f"{category_label}: 未解析到文件路径")
                continue

            for path in paths:
                if path.suffix.lower() == ".bak":
                    skipped.append(f"{category_label}: 跳过备份文件 {path.name}")
                    continue
                key = str(path.resolve()).lower() if path.exists() else str(path).lower()
                if key in seen:
                    continue
                artifacts.append((category, path))
                seen.add(key)

    if not artifacts:
        raise PackageError("已确认交付物未解析到任何可打包文件。")
    return artifacts, skipped


def has_active_confirmed_row(text: str, target_category: str) -> bool:
    confirmed = section(text, ["已确认交付物", "已確認交付物"])
    for table in parse_tables(confirmed):
        for row in table[1:]:
            if not row:
                continue
            category_label = row[0].strip()
            category = classify_category(category_label)
            if category == target_category and not row_is_skip(category_label, " | ".join(row)):
                return True
    return False


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_legacy_sequence_path(path: Path, workspace: Path) -> bool:
    try:
        relative = path.resolve().relative_to(workspace.resolve())
    except ValueError:
        return False
    parts = tuple(part.lower() for part in relative.parts)
    for index in range(len(parts) - 1):
        if parts[index] == LEGACY_SEQUENCE_SEGMENT[0] and parts[index + 1] == LEGACY_SEQUENCE_SEGMENT[1]:
            return True
    return False


def is_unsafe_delivery_file(path: Path) -> bool:
    name = path.name
    lower_name = name.lower()
    return (
        name.startswith("~$")
        or name.startswith("~$$")
        or lower_name.endswith(".bak")
        or ".before_" in lower_name
        or "preview" in lower_name
        or "visual_qa" in lower_name
        or lower_name.endswith(".tmp")
        or lower_name.endswith(".log")
    )


def function_prefixes(group: FunctionGroup) -> tuple[str, ...]:
    dotted = "_".join(group.tokens)
    compact = "_".join(token.replace(".", "").upper() for token in group.tokens)
    prefixes: list[str] = []
    for value in (dotted, compact, group.folder_key):
        if value and value not in prefixes:
            prefixes.append(value)
    return tuple(prefixes)


def matches_function_diagram(path: Path, group: FunctionGroup) -> bool:
    if path.suffix.lower() not in SEQUENCE_EXTS or is_unsafe_delivery_file(path):
        return False
    lower_name = path.name.lower()
    return any(lower_name.startswith(prefix.lower()) for prefix in function_prefixes(group))


def sequence_analysis_dirs(agent_root: Path | None, group: FunctionGroup) -> list[Path]:
    if agent_root is None:
        return []
    result: list[Path] = []
    for key in summary_search_keys(group):
        candidate = agent_root / "functions" / key / "analysis" / "sequence-diagrams"
        if candidate.exists() and candidate not in result:
            result.append(candidate)
    return result


def scan_sequence_dir(root: Path, group: FunctionGroup) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    skipped: list[Path] = []
    scan_roots = [root]
    if (root / "vsdx").exists():
        scan_roots.insert(0, root / "vsdx")
    for scan_root in scan_roots:
        for path in sorted(scan_root.glob("*")):
            if not path.is_file():
                continue
            if is_unsafe_delivery_file(path):
                skipped.append(path)
                continue
            if matches_function_diagram(path, group):
                files.append(path)
    unique: dict[str, Path] = {}
    for path in files:
        unique[str(path.resolve()).lower()] = path
    return list(unique.values()), skipped


def resolve_function_sequence_files(
    workspace: Path,
    agent_root: Path | None,
    group: FunctionGroup,
) -> tuple[Path | None, list[Path], list[Path]]:
    skipped: list[Path] = []
    legacy_root = workspace / "output" / "sequence_diagram"
    legacy_files = []
    if legacy_root.exists():
        for path in legacy_root.rglob("*"):
            if path.is_file() and matches_function_diagram(path, group):
                legacy_files.append(path)

    for root in sequence_analysis_dirs(agent_root, group):
        files, unsafe = scan_sequence_dir(root, group)
        skipped.extend(unsafe)
        if files:
            return root, files, skipped

    reference_root = workspace / "v1.x Reference"
    if reference_root.exists():
        files, unsafe = scan_sequence_dir(reference_root, group)
        skipped.extend(unsafe)
        if files:
            return reference_root, files, skipped

    if legacy_files:
        raise PackageError(
            "只找到 legacy output/sequence_diagram 時序圖，但該路徑已禁止作為正式打包來源: "
            + ", ".join(str(path) for path in legacy_files)
        )
    return None, [], skipped


def read_artifact_text(path: Path) -> str:
    if path.suffix.lower() == ".vsdx":
        chunks: list[str] = []
        try:
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    lower_name = name.lower()
                    if lower_name.endswith(".xml") and (
                        lower_name.startswith("visio/pages/")
                        or lower_name.startswith("visio/masters/")
                        or lower_name.startswith("docprops/")
                    ):
                        chunks.append(archive.read(name).decode("utf-8", errors="ignore"))
        except zipfile.BadZipFile:
            return ""
        return "\n".join(chunks)
    if path.suffix.lower() in {".svg", ".puml", ".json", ".md"}:
        return read_text(path)
    return ""


def common_method_from_text(value: str) -> str | None:
    match = re.search(r"(CommonFunc|CommonUtil)[./][A-Za-z0-9_]+", value)
    if not match:
        return None
    return match.group(0).replace("/", ".")


def normalize_common_basename(value: str) -> str:
    stem = Path(value.strip()).stem
    stem = re.sub(r"_01$", "", stem, flags=re.I)
    return stem.lower()


def collect_common_refs(function_files: list[Path], source_root: Path | None = None) -> list[CommonRef]:
    texts: list[str] = []
    for path in function_files:
        texts.append(read_artifact_text(path))
    if source_root and source_root.name == "sequence-diagrams":
        for path in sorted(source_root.glob("*")):
            if path.is_file() and path.suffix.lower() in {".json", ".puml", ".md"}:
                texts.append(read_artifact_text(path))

    refs: dict[str, CommonRef] = {}
    joined = "\n".join(texts)
    for match in re.finditer(r"循序圖請參考[:：]?\s*([0-9A-Za-z_./-]*(?:CommonFunc|CommonUtil)[A-Za-z0-9_./-]*)", joined):
        basename = match.group(1).strip().strip(" .。；;,，")
        method = common_method_from_text(basename)
        refs[normalize_common_basename(basename)] = CommonRef(display=basename, ref_name=basename, method=method)

    existing_methods = {ref.method for ref in refs.values() if ref.method}
    for match in re.finditer(r"\b(?:\d+_)?(?:CommonFunc|CommonUtil)[./][A-Za-z0-9_]+", joined):
        value = match.group(0).strip()
        method = common_method_from_text(value)
        if method and method in existing_methods:
            continue
        key = normalize_common_basename(value)
        refs.setdefault(key, CommonRef(display=value, ref_name=value, method=method))
        if method:
            existing_methods.add(method)

    return sorted(refs.values(), key=lambda item: item.display.lower())


def common_path_matches_ref(path: Path, ref: CommonRef) -> bool:
    normalized_stem = normalize_common_basename(path.stem)
    normalized_base = normalize_common_basename(ref.ref_name)
    if normalized_stem == normalized_base:
        return True
    if ref.method:
        return ref.method.lower() in normalized_stem
    return False


def validate_common_refs(
    refs: list[CommonRef],
    common_paths: list[Path],
) -> tuple[dict[str, list[Path]], list[dict[str, object]]]:
    confirmed: dict[str, list[Path]] = {}
    missing: list[dict[str, object]] = []
    for ref in refs:
        matched = [path for path in common_paths if common_path_matches_ref(path, ref)]
        confirmed[ref.display] = matched
        svg_matches = [path for path in matched if path.suffix.lower() == ".svg"]
        vsdx_matches = [path for path in matched if path.suffix.lower() == ".vsdx"]
        missing_formats = [fmt for fmt, paths in (("svg", svg_matches), ("vsdx", vsdx_matches)) if not paths]
        ambiguous_formats = [
            {
                "format": fmt,
                "matches": [str(path) for path in paths],
            }
            for fmt, paths in (("svg", svg_matches), ("vsdx", vsdx_matches))
            if len(paths) > 1
        ]
        if missing_formats or ambiguous_formats:
            missing.append(
                {
                    "ref": ref.display,
                    "method": ref.method,
                    "missingFormats": missing_formats,
                    "ambiguousFormats": ambiguous_formats,
                    "matched": [str(path) for path in matched],
                }
            )
    return confirmed, missing


def apply_sequence_constraints(
    group: FunctionGroup,
    text: str,
    workspace: Path,
    agent_root: Path | None,
    artifacts: list[tuple[str, Path]],
) -> SequenceValidation:
    diagram_paths = [path for category, path in artifacts if category in {"function_diagram", "common_diagram"}]
    legacy_paths = [path for path in diagram_paths if is_legacy_sequence_path(path, workspace)]
    if legacy_paths:
        raise PackageError(
            "時序圖正式打包禁止使用 output/sequence_diagram，請改列 .agent/functions 或 v1.x Reference: "
            + ", ".join(str(path) for path in legacy_paths)
        )

    has_function_row = has_active_confirmed_row(text, "function_diagram")
    function_files = [path for category, path in artifacts if category == "function_diagram" and path.suffix.lower() in SEQUENCE_EXTS]
    source_root: Path | None = None
    skipped_unsafe: list[Path] = []

    if has_function_row and not function_files:
        source_root, resolved_files, skipped_unsafe = resolve_function_sequence_files(workspace, agent_root, group)
        if not resolved_files:
            raise PackageError(
                f"{group.display} 已確認本功能時序圖，但未在允許來源找到 VSDX/SVG。"
                "允許來源僅有 .agent/functions/<functionCode>/analysis/sequence-diagrams 與 v1.x Reference。"
            )
        for path in resolved_files:
            artifacts.append(("function_diagram", path))
        function_files = resolved_files
    elif function_files:
        source_root = function_files[0].parent

    refs = collect_common_refs(function_files, source_root) if function_files else []
    common_paths = [path for category, path in artifacts if category == "common_diagram"]
    confirmed, missing = validate_common_refs(refs, common_paths)
    if missing:
        details = "; ".join(
            f"{item['ref']} 缺少 {','.join(item['missingFormats']) or '無'}"
            f" 多重匹配 {','.join(entry['format'] for entry in item['ambiguousFormats']) or '無'}"
            for item in missing
        )
        raise PackageError(
            "本功能時序圖引用了共用時序圖，但 已确认交付物 未完整列出對應共用 SVG/VSDX，停止打包: "
            + details
        )

    return SequenceValidation(
        source_root=source_root,
        function_files=function_files,
        required_common_refs=refs,
        confirmed_common_refs=confirmed,
        missing_common_refs=missing,
        skipped_unsafe_files=skipped_unsafe,
    )


def destination_for(
    package_dir: Path,
    category: str,
    source: Path,
    package_date: str,
    rename_dates: bool,
) -> Path:
    name = source.name
    if rename_dates:
        name = re.sub(r"(20\d{6})(?=[^0-9]*\.[^.]+$)", package_date, name)

    suffix = source.suffix.lower()
    lower_name = source.name.lower()
    if suffix == ".vsdx":
        if category == "common_diagram" or "common" in lower_name:
            return package_dir / "vsdx源文件" / "共用vsdx" / name
        return package_dir / "vsdx源文件" / name
    if suffix == ".svg":
        return package_dir / "共用svg" / name
    return package_dir / name


def extract_tsd_version(path: Path) -> str | None:
    if path.suffix.lower() != ".docx":
        return None
    match = TSD_VERSION_PATTERN.search(path.name)
    if not match:
        return None
    version = match.group("version")
    return "v" + version[1:] if version[:1].lower() == "v" else version


def infer_tsd_version(artifacts: list[tuple[str, Path]]) -> str:
    tsd_paths = [path for category, path in artifacts if category == "tsd" and path.suffix.lower() == ".docx"]
    if not tsd_paths:
        raise PackageError("已确认交付物中没有 TSD .docx，无法生成带版本号的交付目录。")

    versions_by_file: dict[Path, str | None] = {path: extract_tsd_version(path) for path in tsd_paths}
    missing = [path.name for path, version in versions_by_file.items() if not version]
    if missing:
        raise PackageError("无法从 TSD .docx 文件名读取版本号: " + ", ".join(missing))

    versions = sorted({version for version in versions_by_file.values() if version})
    if len(versions) != 1:
        details = ", ".join(f"{path.name}={version}" for path, version in versions_by_file.items())
        raise PackageError(f"同一功能的 TSD .docx 版本号不一致，无法生成唯一交付目录: {details}")
    return versions[0]


def build_plan(
    artifacts: list[tuple[str, Path]],
    output_root: Path,
    package_date: str,
    version: str,
    rename_dates: bool,
) -> list[Artifact]:
    package_dir = output_root / f"TSD 交付 {package_date}" / f"TSD 交付 {version} {package_date}"
    plan: list[Artifact] = []
    for category, source in artifacts:
        destination = destination_for(package_dir, category, source, package_date, rename_dates)
        plan.append(Artifact(category=category, source=source, destination=destination, reason="confirmed"))
    return plan


def execute_plan(plan: list[Artifact], dry_run: bool, overwrite: bool) -> list[str]:
    copied: list[str] = []
    for item in plan:
        if not item.source.exists():
            raise PackageError(f"来源文件不存在: {item.source}")
        if item.destination.exists() and not overwrite:
            raise PackageError(f"目标文件已存在，未覆盖: {item.destination}")
        if not dry_run:
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source, item.destination)
        copied.append(str(item.destination))
    return copied


def parse_args() -> argparse.Namespace:
    today = _dt.datetime.now().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Project system-design workspace root")
    parser.add_argument("--function", dest="functions", action="append", required=True, help="Function code, e.g. L.005")
    parser.add_argument("--summary", help="Explicit summary note path; only valid for one --function")
    parser.add_argument("--agent-root", help="Central .agent root, for example D:\\Repo\\Project\\.agent")
    parser.add_argument("--workspace-key", help="Workspace key from references/local-workspaces.json")
    parser.add_argument("--date", default=today, help="Package date yyyymmdd; default today")
    parser.add_argument("--output-root", help="Default: <workspace>\\TSD 交付客戶版本")
    parser.add_argument("--dry-run", action="store_true", help="List the copy plan without copying")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing destination files")
    parser.add_argument("--keep-source-dates", action="store_true", help="Do not replace final date suffixes in filenames")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        raise PackageError(f"workspace 不存在: {workspace}")
    if args.summary and len(args.functions) != 1:
        raise PackageError("--summary 只能搭配单一 --function 使用")

    output_root = Path(args.output_root).resolve() if args.output_root else workspace / "TSD 交付客戶版本"
    agent_root = resolve_agent_root(args.agent_root, args.workspace_key)
    all_plan: list[Artifact] = []
    summaries: list[str] = []
    skipped: list[str] = []
    sequence_validations: list[dict[str, object]] = []

    for raw in args.functions:
        group = normalize_function(raw)
        summary = find_summary(workspace, group, args.summary, agent_root)
        text = read_text(summary)
        ok, reason = assess_summary(text)
        if not ok:
            raise PackageError(f"{group.display} 不可打包: {reason}。梳理文件: {summary}")
        artifacts, row_skips = collect_artifacts(text, workspace)
        sequence_validation = apply_sequence_constraints(group, text, workspace, agent_root, artifacts)
        plan = build_plan(
            artifacts,
            output_root,
            args.date,
            infer_tsd_version(artifacts),
            rename_dates=not args.keep_source_dates,
        )
        all_plan.extend(plan)
        summaries.append(str(summary))
        skipped.extend([f"{group.display}: {s}" for s in row_skips])
        sequence_validations.append(
            {
                "function": group.display,
                "sourceRoot": str(sequence_validation.source_root) if sequence_validation.source_root else None,
                "functionFiles": [str(path) for path in sequence_validation.function_files],
                "requiredCommonRefs": [
                    {
                        "display": ref.display,
                        "basename": ref.ref_name,
                        "method": ref.method,
                    }
                    for ref in sequence_validation.required_common_refs
                ],
                "confirmedCommonRefs": {
                    key: [str(path) for path in paths]
                    for key, paths in sequence_validation.confirmed_common_refs.items()
                },
                "missingCommonRefs": sequence_validation.missing_common_refs,
                "skippedUnsafeFiles": [str(path) for path in sequence_validation.skipped_unsafe_files],
            }
        )

    # Deduplicate by destination. Same source/destination is harmless; conflicting source is unsafe.
    deduped: list[Artifact] = []
    by_destination: dict[str, Artifact] = {}
    for item in all_plan:
        key = str(item.destination).lower()
        existing = by_destination.get(key)
        if existing:
            if existing.source.resolve() != item.source.resolve():
                raise PackageError(f"不同来源将写入同一目标: {existing.source} / {item.source} -> {item.destination}")
            continue
        by_destination[key] = item
        deduped.append(item)

    copied = execute_plan(deduped, dry_run=args.dry_run, overwrite=args.overwrite)
    package_dirs = sorted({str(item.destination.parent) for item in deduped})

    payload = {
        "dryRun": args.dry_run,
        "summaries": summaries,
        "packageDate": args.date,
        "outputRoot": str(output_root),
        "packageDirs": package_dirs,
        "files": [
            {
                "category": item.category,
                "source": str(item.source),
                "destination": str(item.destination),
            }
            for item in deduped
        ],
        "skipped": skipped,
        "sequenceValidation": sequence_validations,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("DRY RUN" if args.dry_run else "COPIED")
        print(f"Summary files: {len(summaries)}")
        for summary in summaries:
            print(f"  - {summary}")
        print(f"Files: {len(deduped)}")
        for item in deduped:
            print(f"  - [{item.category}] {item.source} -> {item.destination}")
        if skipped:
            print("Skipped:")
            for item in skipped:
                print(f"  - {item}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
