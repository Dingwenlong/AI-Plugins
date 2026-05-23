from __future__ import annotations

import re
import unicodedata
from pathlib import Path


REFERENCE_SCHEMA_VERSION = "1.0.0"
REFERENCE_DIR_NAME = "reference"
REFERENCE_SCOPE_DIR = "global"
LEGACY_REFERENCE_DIR_NAME = "Reference"
REFERENCE_CATEGORY_DIRS = {
    "db_schema": "db-schema",
    "external_api": "external-api",
}
REFERENCE_INDEX_FILENAMES = {
    "db_schema": "db-schema-index.json",
    "external_api": "external-api-index.json",
}
FRAMEWORK_KEYWORD_MAP = {
    "redis": "Redis",
    "isqldbfactory": "ISqlDbFactory",
    "dbfactory": "DbFactory",
    "commonutil": "CommonUtil",
}
EXTERNAL_KEYWORD_MAP = {
    "iris": "IRIS",
    "openapi": "OpenAPI",
    "bsp": "BSP",
}
API_CODE_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:EC|ED|EF|EL|IC|ID|IF|IL)\d{4}(?![A-Za-z0-9])", re.IGNORECASE)
QUALIFIED_TABLE_PATTERN = re.compile(r"\b(?:[A-Za-z][A-Za-z0-9_]*\.){2}[A-Za-z][A-Za-z0-9_]*\b")
DBO_TABLE_PATTERN = re.compile(r"\bDBO\.([A-Za-z][A-Za-z0-9_]*)\b", re.IGNORECASE)
UPPER_TABLE_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")
FIELD_TOKEN_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b")
DATE_TOKEN_PATTERN = re.compile(r"(?<!\d)(20\d{6})(?!\d)")
SQL_STOPWORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "JOIN",
    "ORDER",
    "GROUP",
    "BY",
    "TOP",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "AS",
    "AND",
    "OR",
    "NULL",
    "IS",
    "ON",
    "DESC",
    "ASC",
    "COUNT",
    "SUM",
    "MIN",
    "MAX",
    "AVG",
    "DISTINCT",
    "VARCHAR",
    "CONVERT",
    "LTRIM",
    "RTRIM",
    "IN",
}
FIELD_STOPWORDS = SQL_STOPWORDS | {"TRUE", "FALSE", "JSON", "OBJECT", "STRING", "INT", "BOOL", "DATETIME"}
FIELD_LIKE_TABLE_SUFFIXES = ("_ID", "_NO", "_CODE", "_CD", "_SEQ", "_DT", "_TIME", "_AMT", "_CNT", "_FLAG", "_NAME")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def normalize_token(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = re.sub(r"\s+", "", text)
    return text.casefold()


def slugify(value: str) -> str:
    lowered = normalize_token(value)
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered)
    return lowered.strip("-") or "unnamed"


def extract_date_token(value: str) -> str | None:
    match = DATE_TOKEN_PATTERN.search(value)
    return match.group(1) if match else None


def version_sort_key(path: Path) -> tuple[int, float]:
    token = extract_date_token(path.name)
    return int(token) if token else 0, path.stat().st_mtime


def reference_root(agent_dir: Path) -> Path:
    return agent_dir / REFERENCE_DIR_NAME / REFERENCE_SCOPE_DIR


def legacy_reference_root(agent_dir: Path) -> Path:
    return agent_dir / LEGACY_REFERENCE_DIR_NAME


def reference_raw_dir(agent_dir: Path, category: str) -> Path:
    return reference_root(agent_dir) / "raw" / REFERENCE_CATEGORY_DIRS[category]


def reference_indexes_dir(agent_dir: Path) -> Path:
    return reference_root(agent_dir) / "indexes"


def reference_catalog_path(agent_dir: Path) -> Path:
    return reference_root(agent_dir) / "catalog.json"


def reference_index_path(agent_dir: Path, category: str) -> Path:
    return reference_indexes_dir(agent_dir) / REFERENCE_INDEX_FILENAMES[category]


def project_relative_path(project_root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return target.resolve().as_posix()


def find_api_codes(text: str) -> set[str]:
    return {match.group(0).upper() for match in API_CODE_PATTERN.finditer(clean_text(text))}


def find_external_keywords(text: str) -> set[str]:
    found: set[str] = set()
    token = normalize_token(text)
    for marker, display in EXTERNAL_KEYWORD_MAP.items():
        if marker in token:
            found.add(display)
    return found


def find_framework_keywords(text: str) -> set[str]:
    found: set[str] = set()
    token = normalize_token(text)
    for marker, display in FRAMEWORK_KEYWORD_MAP.items():
        if marker in token:
            found.add(display)
    return found


def find_table_keys(text: str) -> set[str]:
    rendered = clean_text(text)
    upper_text = rendered.upper()
    found: set[str] = set()
    for match in QUALIFIED_TABLE_PATTERN.finditer(rendered):
        full = match.group(0).upper()
        found.add(full)
        parts = full.split(".")
        if len(parts) >= 2:
            found.add(".".join(parts[-2:]))
            found.add(parts[-1])
    for match in DBO_TABLE_PATTERN.finditer(rendered):
        table_name = match.group(1).upper()
        found.add(f"DBO.{table_name}")
        found.add(table_name)
    for match in UPPER_TABLE_PATTERN.finditer(upper_text):
        token = match.group(0)
        if token in SQL_STOPWORDS or "_" not in token:
            continue
        if token.endswith(FIELD_LIKE_TABLE_SUFFIXES):
            continue
        found.add(token)
    return found


def find_field_names(text: str) -> set[str]:
    found: set[str] = set()
    for match in FIELD_TOKEN_PATTERN.finditer(clean_text(text)):
        token = match.group(0)
        upper = token.upper()
        if upper in FIELD_STOPWORDS:
            continue
        if API_CODE_PATTERN.fullmatch(token):
            continue
        if "." in token:
            continue
        if "_" not in token and token[:1].isupper():
            continue
        found.add(token)
    return found


def normalize_match_key(value: str) -> str:
    return clean_text(value).upper()


def format_reference_locator(locator: dict[str, object] | None) -> str:
    if not locator:
        return ""
    parts: list[str] = []
    sheet_name = clean_text(locator.get("sheetName"))
    if sheet_name:
        parts.append(f"sheetName={sheet_name}")
    section_title = clean_text(locator.get("sectionTitle"))
    if section_title:
        parts.append(f"sectionTitle={section_title}")
    page_hint = clean_text(locator.get("pageHint"))
    if page_hint:
        parts.append(f"pageHint={page_hint}")
    return "&".join(parts)
