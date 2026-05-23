from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


TRX_NS = {"trx": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
OUTCOME_TO_STATUS = {
    "Passed": "passed",
    "Failed": "failed",
    "NotExecuted": "skipped",
    "Timeout": "failed",
    "Aborted": "failed",
    "Error": "failed",
}


@dataclass
class ParsedTrx:
    trx_path: str
    tests: list[dict[str, Any]]
    summary: dict[str, int]


def parse_duration_seconds(raw_value: str) -> float:
    if not raw_value:
        return 0.0
    parts = raw_value.split(":")
    if len(parts) != 3:
        return 0.0
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def first_line(text: str) -> str:
    lines = (text or "").splitlines()
    if not lines:
        return ""
    return lines[0].strip()


def _findall(node: ET.Element, query: str) -> list[ET.Element]:
    return list(node.findall(query, TRX_NS))


def _findtext(node: ET.Element, query: str) -> str:
    value = node.findtext(query, default="", namespaces=TRX_NS)
    return value or ""


def _resolve_attachment_path(trx_path: Path, raw_path: str) -> str:
    candidate = Path(raw_path)
    if not raw_path:
        return ""
    if candidate.is_absolute():
        return candidate.resolve().as_posix()
    return (trx_path.parent / candidate).resolve().as_posix()


def parse_trx(trx_path: str | Path) -> dict[str, Any]:
    source = Path(trx_path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"TRX not found: {source.as_posix()}")

    try:
        root = ET.fromstring(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        root = ET.fromstring(source.read_text(encoding="utf-8-sig"))
    except ET.ParseError as exc:
        raise ValueError(f"Invalid TRX file: {source.as_posix()}") from exc

    tests: list[dict[str, Any]] = []
    for result in _findall(root, ".//trx:UnitTestResult"):
        test_name = result.attrib.get("testName", "").strip()
        outcome = result.attrib.get("outcome", "").strip()
        status = OUTCOME_TO_STATUS.get(outcome, "pending")
        error_message = _findtext(result, "./trx:Output/trx:ErrorInfo/trx:Message")
        stack_trace = _findtext(result, "./trx:Output/trx:ErrorInfo/trx:StackTrace")
        std_out = _findtext(result, "./trx:Output/trx:StdOut")
        attachments = [
            _resolve_attachment_path(source, file_node.attrib.get("path", ""))
            for file_node in _findall(result, "./trx:ResultFiles/trx:ResultFile")
            if file_node.attrib.get("path")
        ]
        tests.append(
            {
                "testName": test_name,
                "outcome": outcome,
                "status": status,
                "duration": result.attrib.get("duration", ""),
                "durationSeconds": parse_duration_seconds(result.attrib.get("duration", "")),
                "errorMessage": error_message,
                "errorSummary": first_line(error_message),
                "stackTrace": stack_trace,
                "stdOut": std_out,
                "attachments": attachments,
            }
        )

    summary = {
        "total": len(tests),
        "passed": sum(1 for test in tests if test["status"] == "passed"),
        "failed": sum(1 for test in tests if test["status"] == "failed"),
        "skipped": sum(1 for test in tests if test["status"] == "skipped"),
        "pending": sum(1 for test in tests if test["status"] == "pending"),
    }
    return {
        "trxPath": source.as_posix(),
        "tests": tests,
        "summary": summary,
    }


def find_latest_trx(results_dir: str | Path) -> str | None:
    directory = Path(results_dir).expanduser().resolve()
    if not directory.exists():
        return None
    trx_files = sorted(directory.rglob("*.trx"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not trx_files:
        return None
    return trx_files[0].as_posix()


def build_test_lookup(tests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    ambiguous_aliases: set[str] = set()

    def register(name: str, test: dict[str, Any]) -> None:
        normalized = (name or "").strip()
        if not normalized or normalized in ambiguous_aliases:
            return
        existing = lookup.get(normalized)
        if existing is None or existing.get("testName") == test.get("testName"):
            lookup[normalized] = test
            return
        ambiguous_aliases.add(normalized)
        lookup.pop(normalized, None)

    for test in tests:
        full_name = str(test.get("testName") or "").strip()
        if not full_name:
            continue
        register(full_name, test)
        name_parts = [part for part in full_name.split(".") if part]
        if len(name_parts) >= 2:
            register(".".join(name_parts[-2:]), test)

    return lookup
