from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


TEST_ATTRIBUTE_TOKENS = ("fact", "theory", "testmethod", "datatestmethod", "test")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def dedupe_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def infer_report_operation_section(api_name: str) -> str | None:
    token = clean_text(api_name).lower()
    if any(keyword in token for keyword in ("get", "query", "search", "list", "detail", "fetch")):
        return "UT-04"
    if any(keyword in token for keyword in ("create", "add", "insert", "register")):
        return "UT-05"
    if any(keyword in token for keyword in ("update", "edit", "set", "change", "modify")):
        return "UT-06"
    if any(keyword in token for keyword in ("delete", "remove")):
        return "UT-07"
    if any(keyword in token for keyword in ("download", "export")):
        return "UT-08"
    if any(keyword in token for keyword in ("notify", "message", "send", "push", "mail", "sms")):
        return "UT-09"
    return None


def build_report_section_hints(api_name: str) -> list[str]:
    sections = ["UT-01", "UT-03", "UT-10"]
    operation_section = infer_report_operation_section(api_name)
    if operation_section:
        sections.append(operation_section)
    return dedupe_strings(sections)


def read_text_with_fallback(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")


def discover_test_names_from_file(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []

    current_class = ""
    pending_attribute = False
    discovered: list[str] = []
    class_pattern = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)")
    method_pattern = re.compile(
        r"\b(?:public|internal|protected|private)\s+(?:async\s+)?(?:[A-Za-z_][A-Za-z0-9_<>,\.\?\[\]]*\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*\("
    )

    for raw_line in read_text_with_fallback(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        class_match = class_pattern.search(line)
        if class_match:
            current_class = class_match.group(1)

        if line.startswith("["):
            if any(token in line.lower() for token in TEST_ATTRIBUTE_TOKENS):
                pending_attribute = True
            elif pending_attribute:
                pending_attribute = True
            continue

        method_match = method_pattern.search(line)
        if pending_attribute and method_match:
            method_name = method_match.group(1)
            discovered.append(f"{current_class}.{method_name}" if current_class else method_name)
            pending_attribute = False
            continue

        if pending_attribute and line not in {"{", "}"}:
            pending_attribute = False

    return dedupe_strings(discovered)


def discover_test_names(project_root: Path, relative_paths: Iterable[str]) -> list[str]:
    discovered: list[str] = []
    for relative_path in relative_paths:
        relative = clean_text(relative_path)
        if not relative:
            continue
        discovered.extend(discover_test_names_from_file(project_root / relative))
    return dedupe_strings(discovered)


def collect_test_target_files(analysis: dict[str, Any]) -> tuple[list[str], list[str]]:
    unit_test_files = [
        clean_text(path)
        for path in (analysis.get("unitTestTargetFiles") or [])
        if clean_text(path)
    ]
    integration_test_files = [
        clean_text(path)
        for path in (analysis.get("integrationTestTargetFiles") or [])
        if clean_text(path)
    ]
    return unit_test_files, integration_test_files


def build_report_source_files(change_plan: dict[str, Any], modified_files: list[str]) -> list[str]:
    analysis = change_plan.get("analysis") or {}
    source_files: list[str] = []
    for key in ("controllerFile", "interfaceFile", "targetFile"):
        candidate = clean_text(analysis.get(key))
        if candidate:
            source_files.append(candidate)
    for key in ("codeTargetFiles", "serviceFiles", "entityFiles"):
        source_files.extend(str(item) for item in analysis.get(key) or [])
    source_files.extend(modified_files)
    return dedupe_strings(source_files)
