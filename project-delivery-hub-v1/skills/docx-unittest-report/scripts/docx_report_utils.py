from __future__ import annotations

import getpass
import json
import os
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

SECTION_RE = re.compile(r"^(UT-\d{2})\s*(.*)$", re.IGNORECASE)
AUTO_STATUS_RE = re.compile(r"\n?狀態：.*$", re.MULTILINE)
PLACEHOLDER_API_DISPLAY_NAMES = {
    "(api/endpoint/method)",
    "api/endpoint/method",
}
PLACEHOLDER_TESTERS = {
    "姓名",
    "name",
    "tester",
}
PLACEHOLDER_DATES = {
    "yyyy/mm/dd",
}
STATUS_LABELS = {
    "passed": "通過",
    "failed": "失敗",
    "manual": "人工",
    "pending": "待補",
    "skipped": "不適用",
    "not_in_run": "接口未涉及",
}

MANUAL_HINTS = (
    "DB",
    "資料庫",
    "audit",
    "審計",
    "來源 IP",
    "第三方",
    "告警",
    "背景任務",
    "建立者",
    "更新者",
    "刪除權限",
    "被引用",
    "級聯",
    "並發",
    "rowversion",
    "ETag",
)

INTEGRATION_SECTION_IDS = {
    "UT-01",
}

INTEGRATION_HINTS = (
    "HTTP",
    "route",
    "method",
    "version",
    "content-type",
    "content type",
    "header",
    "schema",
    "json contract",
    "model binding",
    "validation",
    "middleware",
    "狀態碼",
    "路由",
    "版本",
    "內容格式",
    "回應標頭",
    "回應頭",
    "回應格式",
    "回應結構",
    "欄位命名",
    "型別符合規格",
    "參數驗證",
    "模型驗證",
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\r", " ").replace("\n", " ").replace("\u3000", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def ensure_absolute_posix(raw_path: str | Path) -> str:
    return Path(raw_path).expanduser().resolve().as_posix()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def today_slash() -> str:
    return date.today().strftime("%Y/%m/%d")


def coalesce_text(*values: Any) -> str:
    for value in values:
        text = normalize_text(str(value or ""))
        if text:
            return text
    return ""


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def humanize_account_name(raw_value: str) -> str:
    token = normalize_text(raw_value)
    if not token:
        return ""

    if "\\" in token:
        token = token.rsplit("\\", 1)[-1]
    if "@" in token:
        token = token.split("@", 1)[0]

    token = re.sub(r"[_\-.]+", " ", token)
    token = re.sub(r"\s+", " ", token).strip()
    if not token:
        return ""

    return " ".join(part[:1].upper() + part[1:].lower() for part in token.split(" "))


def resolve_current_login_display_name() -> str:
    candidates = [
        os.environ.get("CODEx_TESTER_NAME", ""),
        os.environ.get("USERNAME", ""),
        getpass.getuser(),
        os.environ.get("USER", ""),
    ]
    for candidate in candidates:
        display_name = humanize_account_name(candidate)
        if display_name:
            return display_name
    return "Tester"


def is_placeholder_tester(raw_value: str) -> bool:
    return normalize_text(raw_value).casefold() in PLACEHOLDER_TESTERS


def is_placeholder_date(raw_value: str) -> bool:
    return normalize_text(raw_value).casefold() in PLACEHOLDER_DATES


def resolve_effective_metadata(
    metadata: dict[str, Any] | None,
    fallback_header: dict[str, Any] | None = None,
) -> dict[str, str]:
    metadata = metadata or {}
    fallback_header = fallback_header or {}

    raw_api_name = coalesce_text(
        metadata.get("apiDisplayName"),
        metadata.get("apiName"),
        fallback_header.get("apiDisplayName"),
        fallback_header.get("apiName"),
    )
    raw_tester = coalesce_text(metadata.get("tester"), fallback_header.get("tester"))
    raw_test_date = coalesce_text(metadata.get("testDate"), fallback_header.get("testDate"))

    if is_placeholder_date(raw_test_date):
        raw_test_date = ""

    tester = raw_tester
    if not tester or is_placeholder_tester(tester):
        tester = resolve_current_login_display_name()

    return {
        "apiDisplayName": normalize_text(raw_api_name)
        if normalize_text(raw_api_name).casefold() not in PLACEHOLDER_API_DISPLAY_NAMES
        else "",
        "tester": tester,
        "testDate": raw_test_date or today_slash(),
        "actualSummary": normalize_text(str(metadata.get("actualSummary", ""))),
        "overallStatus": normalize_text(str(metadata.get("overallStatus", ""))),
    }


def iter_block_items(parent: DocumentObject | _Cell) -> Iterator[Paragraph | Table]:
    if isinstance(parent, DocumentObject):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise TypeError(f"Unsupported parent type: {type(parent)!r}")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def unique_row_cells(row: Any) -> list[tuple[int, _Cell]]:
    seen: set[int] = set()
    unique_cells: list[tuple[int, _Cell]] = []
    for index, cell in enumerate(row.cells):
        cell_id = id(cell._tc)
        if cell_id in seen:
            continue
        seen.add(cell_id)
        unique_cells.append((index, cell))
    return unique_cells


def read_value_after_label(row: Any, label: str) -> str:
    cells = unique_row_cells(row)
    for index, (_, cell) in enumerate(cells):
        if normalize_text(cell.text) == normalize_text(label):
            if index + 1 < len(cells):
                return normalize_text(cells[index + 1][1].text)
    return ""


def parse_header_table(table: Table) -> dict[str, str]:
    rows = list(table.rows)
    return {
        "apiDisplayName": read_value_after_label(rows[0], "API 名稱") if len(rows) > 0 else "",
        "tester": read_value_after_label(rows[0], "測試人員") if len(rows) > 0 else "",
        "testDate": read_value_after_label(rows[0], "測試日期") if len(rows) > 0 else "",
        "actualSummary": read_value_after_label(rows[2], "實際測試結果") if len(rows) > 2 else "",
        "overallStatusLabel": read_value_after_label(rows[3], "實際測試結果") if len(rows) > 3 else "",
    }


def is_header_table(table: Table) -> bool:
    merged = " ".join(normalize_text(cell.text) for row in table.rows for cell in row.cells)
    return "實際測試結果" in merged and (
        "API 名稱" in merged or "個案名稱" in merged or "測試人員" in merged
    )


def looks_like_title_row(table: Table, row_index: int) -> bool:
    if row_index >= len(table.rows):
        return False
    cells = unique_row_cells(table.rows[row_index])
    if len(cells) == 1:
        return bool(SECTION_RE.match(normalize_text(cells[0][1].text)))
    if len(cells) >= 2:
        left = normalize_text(cells[0][1].text)
        right = normalize_text(cells[1][1].text)
        return bool(left and left == right and SECTION_RE.match(left))
    return False


def parse_section_title(
    table: Table,
    fallback_section_id: str,
    fallback_title: str,
) -> tuple[str, str]:
    if looks_like_title_row(table, 0):
        cells = unique_row_cells(table.rows[0])
        title_text = normalize_text(cells[0][1].text)
    else:
        title_text = fallback_title or fallback_section_id or ""

    match = SECTION_RE.match(title_text)
    if match:
        return match.group(1).upper(), title_text
    if fallback_section_id:
        title_suffix = title_text or fallback_title or fallback_section_id
        return fallback_section_id.upper(), title_suffix
    return "SECTION", title_text or "Section"


def section_layout(table: Table) -> str:
    if len(table.columns) == 3:
        return "three-column-matrix"
    return "two-column-checklist"


def guess_mode(section_id: str, check_item: str) -> str:
    item = normalize_text(check_item)
    if any(hint.lower() in item.lower() for hint in MANUAL_HINTS):
        return "manual"
    if section_id.upper() in INTEGRATION_SECTION_IDS:
        return "integration_test"
    if any(hint.lower() in item.lower() for hint in INTEGRATION_HINTS):
        return "integration_test"
    return "unit_test"


def build_default_item(section_id: str, case_id: str, row_index: int, check_item: str) -> dict[str, Any]:
    mode = guess_mode(section_id, check_item)
    payload: dict[str, Any] = {
        "caseId": case_id,
        "rowIndex": row_index,
        "checkItem": check_item,
        "mode": mode,
        "enabled": False,
        "actualResult": "",
        "notes": (
            "補齊 testBindings.testNames 後再把 enabled 改成 true。"
            if mode in {"unit_test", "integration_test"}
            else ""
        ),
        "manualEvidencePaths": [],
        "apiRuntimeCall": {
            "requestPath": "",
            "responsePath": "",
            "screenshotPath": "",
            "expectedStatusCodes": [],
            "passActualResult": "",
            "failActualResult": "",
        },
        "codeInspection": {
            "ruleId": "",
            "evidencePaths": [],
            "mustContainAny": [],
            "mustContainAll": [],
            "mustNotContainAny": [],
            "passActualResult": "",
            "pendingActualResult": "",
            "failActualResult": "",
        },
        "testBindings": {
            "testNames": [],
            "matchMode": "all_pass",
            "allowMissing": False,
        },
    }
    return payload


def parse_section_table(
    table: Table,
    table_index: int,
    fallback_section_id: str,
    fallback_title: str,
) -> dict[str, Any]:
    section_id, title = parse_section_title(table, fallback_section_id, fallback_title)
    layout = section_layout(table)
    items: list[dict[str, Any]] = []
    item_counter = 0

    for row_index, row in enumerate(table.rows):
        if row_index == 0 and looks_like_title_row(table, row_index):
            continue

        row_cells = unique_row_cells(row)
        row_texts = [normalize_text(cell.text) for _, cell in row_cells]
        if not any(row_texts):
            continue

        if layout == "three-column-matrix":
            joined = " | ".join(row_texts)
            if "預期輸出/行為" in joined and "實際輸出/行為" in joined:
                continue
            check_item = row_texts[0] or row_texts[-1]
            if not check_item:
                continue
        else:
            left = row_texts[0] if len(row_texts) > 0 else ""
            right = row_texts[1] if len(row_texts) > 1 else ""
            merged = row_texts[0] if row_texts else ""

            if merged.startswith("自動化證據"):
                continue
            if "證據：" in left and not right:
                continue
            if "證據：" in merged and len(row_texts) == 1:
                continue
            check_item = right or merged
            if not check_item:
                continue

        item_counter += 1
        case_id = f"{section_id.lower()}-{item_counter:03d}"
        items.append(build_default_item(section_id, case_id, row_index, check_item))

    return {
        "sectionId": section_id,
        "title": title,
        "tableIndex": table_index,
        "layout": layout,
        "items": items,
    }


def load_report_outline(docx_path: str | Path) -> dict[str, Any]:
    source = Path(docx_path).expanduser().resolve()
    document = Document(str(source))
    first_table = True
    header: dict[str, str] = {}
    sections: list[dict[str, Any]] = []
    pending_section_id = ""
    pending_title = ""
    visible_title = ""
    table_index = -1

    for block in iter_block_items(document):
        if isinstance(block, Paragraph):
            text = normalize_text(block.text)
            if not text:
                continue
            if not visible_title and "報告" in text:
                visible_title = text
            match = SECTION_RE.match(text)
            if match:
                pending_section_id = match.group(1).upper()
                pending_title = text
            continue

        table_index += 1
        if first_table and is_header_table(block):
            header = parse_header_table(block)
            first_table = False
            continue
        if first_table:
            continue
        sections.append(
            parse_section_table(
                block,
                table_index=table_index,
                fallback_section_id=pending_section_id,
                fallback_title=pending_title,
            )
        )

    return {
        "sourcePath": source.as_posix(),
        "reportTitle": visible_title or source.stem,
        "header": header,
        "sections": sections,
    }


def default_output_docx(input_path: str | Path) -> str:
    source = Path(input_path).expanduser().resolve()
    return source.with_name(f"{source.stem}.report{source.suffix}").as_posix()


def default_manifest_path(input_path: str | Path) -> str:
    source = Path(input_path).expanduser().resolve()
    return source.with_name(f"{source.stem}.job.json").as_posix()


def default_results_path(manifest_path: str | Path) -> str:
    source = Path(manifest_path).expanduser().resolve()
    return source.with_name(f"{source.stem}.results.json").as_posix()


def build_manifest_from_outline(
    outline: dict[str, Any],
    output_docx: str | None = None,
) -> dict[str, Any]:
    input_path = outline["sourcePath"]
    metadata = resolve_effective_metadata(outline.get("header", {}))
    return {
        "document": {
            "inputPath": input_path,
            "outputPath": output_docx or default_output_docx(input_path),
            "reportTitle": outline.get("reportTitle", ""),
        },
        "metadata": {
            "apiDisplayName": metadata["apiDisplayName"],
            "tester": metadata["tester"],
            "testDate": metadata["testDate"],
            "actualSummary": "",
            "overallStatus": "",
        },
        "analysisContext": {
            "repoRoot": "",
            "contextRoot": "",
        },
        "unitTest": {
            "trxPath": "",
            "resultsDir": "",
            "command": "",
            "workingDirectory": "",
            "timeoutSeconds": 600,
            "failIfTrxMissing": True,
        },
        "integrationTest": {
            "trxPath": "",
            "resultsDir": "",
            "command": "",
            "workingDirectory": "",
            "timeoutSeconds": 900,
            "failIfTrxMissing": False,
            "cleanWorkspace": {
                "enabled": False,
                "sourceRoot": "",
                "targetRoot": "",
                "excludeDirNames": ["bin", "obj", ".vs", "TestResults"],
            },
        },
        "sections": outline["sections"],
    }


def strip_auto_status(text: str) -> str:
    cleaned = AUTO_STATUS_RE.sub("", text or "")
    return cleaned.strip()


def result_summary(cases: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(case.get("status", "pending") for case in cases)
    return {
        "passed": counter.get("passed", 0),
        "failed": counter.get("failed", 0),
        "manual": counter.get("manual", 0),
        "pending": counter.get("pending", 0),
        "skipped": counter.get("skipped", 0),
        "not_in_run": counter.get("not_in_run", 0),
    }


def overall_status_from_summary(summary: dict[str, int]) -> str:
    if summary.get("failed", 0) > 0:
        return "failed"
    if summary.get("pending", 0) > 0:
        return "pending"
    executed = summary.get("passed", 0) + summary.get("manual", 0) + summary.get("skipped", 0)
    if executed > 0 and summary.get("not_in_run", 0) > 0:
        return "partial"
    if executed == 0 and summary.get("not_in_run", 0) > 0:
        return "not_in_run"
    return "passed"


def overall_status_label(status: str) -> str:
    if status == "passed":
        return "符合需求"
    if status == "failed":
        return "不符合需求"
    if status == "partial":
        return "部分完成"
    if status == "not_in_run":
        return "接口未涉及"
    return "尚未完成"
