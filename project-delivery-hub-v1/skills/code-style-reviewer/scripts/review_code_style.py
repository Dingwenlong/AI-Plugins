from __future__ import annotations

import argparse
import datetime as dt
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0.0"
SKILL_NAME = "code-style-reviewer"
SOURCE_SUFFIX = ".cs"
EXCLUDED_DIRS = {".agent", ".git", ".vs", "bin", "obj", "__pycache__"}
TEST_DIRS = {"test", "tests", "unittesting", "integrationtesting"}
GENERATED_SUFFIXES = (
    ".g.cs",
    ".designer.cs",
    ".assemblyinfo.cs",
    ".globalusings.g.cs",
)
BACKUP_PATTERNS = (".bak", ".tmp", ".orig")
TAG_PATTERN = re.compile(r"^\s*//\s*\[(業務|意圖)\]：")
INTENT_TAG_PATTERN = re.compile(r"^\s*//\s*\[意圖\]：")


def clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp950", "big5", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        # A single malformed/corrupted JSON (e.g. a mojibake change-plan with an
        # unterminated string) must not abort the whole review. Skip it with a
        # visible warning and let the caller treat it as an empty / needs-review file.
        print(
            f"[code-style-reviewer] WARN: skipping unreadable JSON {path}: {exc}",
            file=sys.stderr,
        )
        return {}
    return payload if isinstance(payload, dict) else {}


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def find_plugin_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".codex-plugin" / "plugin.json").exists():
            return candidate
    raise SystemExit(f"Cannot find plugin root from {start}")


def resolve_path(raw: str | None, *, base: Path | None = None) -> Path | None:
    text = clean_text(raw)
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    return path.resolve()


def workspace_entry(plugin_root: Path, workspace_key: str) -> dict[str, Any]:
    config = read_json(plugin_root / "references" / "local-workspaces.json")
    workspaces = config.get("workspaces") if isinstance(config.get("workspaces"), dict) else {}
    key = workspace_key or clean_text(config.get("defaultWorkspace"))
    entry = workspaces.get(key) if key else None
    return entry if isinstance(entry, dict) else {}


def normalize_author(login: str) -> str:
    text = clean_text(login)
    return text[:1].upper() + text[1:] if text else ""


def project_relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def is_generated_or_excluded(path: Path, project_root: Path, *, explicit: bool = False) -> bool:
    if explicit:
        return False
    try:
        relative = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return True
    parts = [part.lower() for part in relative.parts]
    if any(part in EXCLUDED_DIRS for part in parts[:-1]):
        return True
    if any(part in TEST_DIRS for part in parts[:-1]):
        return True
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in GENERATED_SUFFIXES)


def is_backup_artifact(path: Path, project_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return False
    parts = [part.lower() for part in relative.parts]
    if any(part in {".git", "bin", "obj", ".vs"} for part in parts[:-1]):
        return False
    name = path.name.lower()
    return name.startswith(".before_") or ".before_" in name or any(name.endswith(suffix) for suffix in BACKUP_PATTERNS)


def previous_meaningful_line(lines: list[str], index: int) -> str:
    cursor = index - 1
    while cursor >= 0:
        text = lines[cursor].strip()
        if text and text not in {"{", "}", "};"}:
            return lines[cursor]
        cursor -= 1
    return ""


def has_tag_before(lines: list[str], index: int) -> bool:
    return bool(TAG_PATTERN.search(previous_meaningful_line(lines, index)))


def has_intent_tag_before(lines: list[str], index: int) -> bool:
    return bool(INTENT_TAG_PATTERN.search(previous_meaningful_line(lines, index)))


def is_defensive_if(line: str) -> bool:
    lowered = line.casefold()
    return bool(
        re.search(r"\bif\s*\(", line)
        and any(
            token in lowered
            for token in (
                "null",
                "isnullorwhitespace",
                "isempty",
                ".any(",
                ".count",
                ".length",
                "== 0",
                "<= 0",
                "string.isnull",
                "string.isempty",
            )
        )
    )


def is_external_await(line: str) -> bool:
    lowered = line.casefold()
    if "await " not in lowered:
        return False
    return any(
        token in lowered
        for token in (
            "query",
            "execute",
            "transaction",
            "commit",
            "rollback",
            "redis",
            "cache",
            "http",
            "send",
            "post",
            "get",
            "service",
            "commonfunc",
            "read",
            "write",
            "_sql",
            "_db",
        )
    )


def normalize_type(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("?", "")


def line_finding(
    *,
    severity: str,
    category: str,
    rule_id: str,
    source: str,
    file_path: str,
    line: int | None,
    message: str,
    evidence: str,
    expected: str,
    actual: str,
    fix_hint: str,
    confidence: str = "medium",
) -> dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "ruleId": rule_id,
        "source": source,
        "file": file_path,
        "line": line,
        "message": message,
        "evidence": evidence.strip(),
        "expected": expected,
        "actual": actual,
        "fixHint": fix_hint,
        "confidence": confidence,
    }


def scan_source_file(path: Path, project_root: Path, expected_author: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    text = read_text(path)
    lines = text.splitlines()
    relative = project_relative(path, project_root)

    header_window = "\n".join(lines[:80])
    author_match = re.search(r"新增人[员員]\s*[:：]\s*(?P<author>[^\r\n*]+)", header_window)
    if author_match:
        actual_author = clean_text(author_match.group("author")).strip("*/ ")
        if actual_author.casefold() in {"ai", "codex", "regression"} or actual_author != expected_author:
            findings.append(
                line_finding(
                    severity="warning",
                    category="header_author",
                    rule_id="new_author_windows_login",
                    source="external:common-style",
                    file_path=relative,
                    line=None,
                    message="文件头新增人员不符合当前 Windows 登录帐号规范化 author 规则。",
                    evidence=author_match.group(0),
                    expected=expected_author,
                    actual=actual_author,
                    fix_hint="将新增人员改为当前 Windows 登录帐号规范化后的 author。",
                    confidence="high",
                )
            )
    if ("文件说明" in header_window or "文件說明" in header_window) and "修改人员" not in header_window and "修改人員" not in header_window:
        findings.append(
            line_finding(
                severity="warning",
                category="header_update_record",
                rule_id="modified_header_record",
                source="external:common-style",
                file_path=relative,
                line=None,
                message="文件头缺少修改人员、修改时间、修改说明三行更新记录。",
                evidence="header without 修改人员/修改時間/修改說明",
                expected="修改人员 / 修改时间 / 修改说明",
                actual="missing",
                fix_hint="修改既有业务源码时补齐三行更新记录。",
                confidence="medium",
            )
        )

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()

        if re.match(r"^\s*namespace\s+[A-Za-z_][\w.]*\s*$", line):
            next_text = ""
            for follow in lines[index: min(index + 4, len(lines))]:
                if follow.strip():
                    next_text = follow.strip()
                    break
            if next_text == "{":
                findings.append(
                    line_finding(
                        severity="warning",
                        category="namespace_style",
                        rule_id="file_scoped_namespace",
                        source="api-code-writer",
                        file_path=relative,
                        line=index,
                        message="C# namespace 仍是 block-scoped 候选。",
                        evidence=line,
                        expected="namespace Foo.Bar;",
                        actual="block-scoped namespace",
                        fix_hint="若文件结构允许，改为 file-scoped namespace。",
                        confidence="high",
                    )
                )
        elif re.match(r"^\s*namespace\s+[A-Za-z_][\w.]*\s*\{", line):
            findings.append(
                line_finding(
                    severity="warning",
                    category="namespace_style",
                    rule_id="file_scoped_namespace",
                    source="api-code-writer",
                    file_path=relative,
                    line=index,
                    message="C# namespace 仍是 block-scoped 候选。",
                    evidence=line,
                    expected="namespace Foo.Bar;",
                    actual="block-scoped namespace",
                    fix_hint="若文件结构允许，改为 file-scoped namespace。",
                    confidence="high",
                )
            )

        new_match = re.match(
            r"^\s*(?:private|protected|internal|public|static|readonly|\s)*\s*(?P<type>[A-Za-z_][\w.<>,?\[\]]*)\s+"
            r"(?P<name>[A-Za-z_]\w*)\s*=\s*new\s+(?P<newtype>[A-Za-z_][\w.<>,?\[\]]*)\s*\(",
            line,
        )
        if new_match and normalize_type(new_match.group("type")) == normalize_type(new_match.group("newtype")):
            findings.append(
                line_finding(
                    severity="warning",
                    category="object_creation",
                    rule_id="simplified_new",
                    source="api-code-writer",
                    file_path=relative,
                    line=index,
                    message="对象建立可收敛为目标型别明确的 new() 候选。",
                    evidence=line,
                    expected=f"{new_match.group('type')} {new_match.group('name')} = new(...)",
                    actual=line.strip(),
                    fix_hint="目标型别明确且无歧义时使用 new()。",
                    confidence="medium",
                )
            )

        if re.search(r"\bnew\s+(?:List<[^>]+>|[A-Za-z_][\w.<>]*\[\]|string\[\])\s*\{", line) or "new[] {" in line:
            findings.append(
                line_finding(
                    severity="warning",
                    category="collection_initialization",
                    rule_id="collection_expression",
                    source="api-code-writer",
                    file_path=relative,
                    line=index,
                    message="集合或数组初始化可评估改为 collection expression。",
                    evidence=line,
                    expected="[] / [item1, item2]",
                    actual=line.strip(),
                    fix_hint="目标型别明确时优先使用 collection expression。",
                    confidence="medium",
                )
            )

        if is_defensive_if(line) and not has_tag_before(lines, index - 1):
            findings.append(
                line_finding(
                    severity="warning",
                    category="tagged_comment",
                    rule_id="tagged_defensive_branch",
                    source="api-code-writer",
                    file_path=relative,
                    line=index,
                    message="防呆 if / defensive branch 前缺少 [業務] 或 [意圖] 标签注释。",
                    evidence=line,
                    expected="// [意圖]：... 或 // [業務]：...",
                    actual="missing tagged comment",
                    fix_hint="在分支前说明为何短路、跳过或防误判。",
                    confidence="medium",
                )
            )

        if is_external_await(line) and not has_intent_tag_before(lines, index - 1):
            findings.append(
                line_finding(
                    severity="warning",
                    category="tagged_comment",
                    rule_id="await_intent_comment",
                    source="api-code-writer",
                    file_path=relative,
                    line=index,
                    message="访问外部状态或服务的 await 前缺少即时 [意圖] 注释。",
                    evidence=line,
                    expected="// [意圖]：...",
                    actual="missing [意圖]",
                    fix_hint="在 await 前说明外部查询、写入、缓存或服务调用意图。",
                    confidence="medium",
                )
            )

        field_match = re.search(r"\bprivate\s+readonly\s+[A-Za-z_][\w.<>,?\[\]]*\s+(?P<name>[A-Z][A-Za-z0-9_]*)\s*(?:=|;)", line)
        if field_match:
            findings.append(
                line_finding(
                    severity="warning",
                    category="dependency_injection",
                    rule_id="di_field_camel_case",
                    source="api-code-writer",
                    file_path=relative,
                    line=index,
                    message="依赖注入字段命名不是 _camelCase 候选。",
                    evidence=line,
                    expected="_camelCase field",
                    actual=field_match.group("name"),
                    fix_hint="将注入依赖字段统一为 _camelCase。",
                    confidence="medium",
                )
            )

        if re.search(r"^\s*(?:public|internal|private)\s+[A-Za-z_]\w+\s*\([^)]*\)", line) and " class " not in line:
            window = "\n".join(lines[max(0, index - 5): min(len(lines), index + 12)])
            if re.search(r"\b_[A-Za-z_]\w*\s*=", window) or re.search(r"\b[A-Z][A-Za-z0-9_]*\s*=", window):
                findings.append(
                    line_finding(
                        severity="needs_review",
                        category="dependency_injection",
                        rule_id="primary_constructor",
                        source="api-code-writer",
                        file_path=relative,
                        line=index,
                        message="发现传统构造函数注入候选，需要确认是否可改为 C# 主构造函数。",
                        evidence=line,
                        expected="primary constructor when supported",
                        actual="traditional constructor candidate",
                        fix_hint="若框架和 partial 结构允许，改用主构造函数；否则在 change-plan 说明原因。",
                        confidence="low",
                    )
                )

        if "switch" in stripped and re.search(r"\bswitch\s*\(", stripped):
            findings.append(
                line_finding(
                    severity="needs_review",
                    category="control_flow",
                    rule_id="switch_semantic_use",
                    source="api-code-writer",
                    file_path=relative,
                    line=index,
                    message="发现 switch，需要确认是否为同一判断维度、状态枚举或明确 pattern matching。",
                    evidence=line,
                    expected="switch only for same discriminator or clear pattern",
                    actual="switch candidate",
                    fix_hint="若是多字段业务判断，保留 if / else if。",
                    confidence="low",
                )
            )

        if re.search(r"\bSqlParameter\s+[A-Za-z_]\w+\s*\(", line) or re.search(r"\b(?:Build|Create|Make|To)SqlParameter\b", line):
            findings.append(
                line_finding(
                    severity="needs_review",
                    category="data_access",
                    rule_id="sql_parameter_helper",
                    source="external:common-style",
                    file_path=relative,
                    line=index,
                    message="发现 SQL 参数 helper 候选，需要确认是否只是为了缩短 new SqlParameter(...)。",
                    evidence=line,
                    expected="inline new SqlParameter unless helper carries metadata",
                    actual="helper candidate",
                    fix_hint="若 helper 没有统一型别、长度、精度或 metadata 价值，应回到调用处行内写。",
                    confidence="low",
                )
            )

    lowered_text = text.casefold()
    if "queryasync" in lowered_text and "firstordefault()" in lowered_text:
        for index, line in enumerate(lines, start=1):
            if "FirstOrDefault()" not in line:
                continue
            window = "\n".join(lines[max(0, index - 35): min(len(lines), index + 2)])
            if "QueryAsync" in window and "TOP (1)" not in window.upper() and "QueryFirstOrDefaultAsync" not in window:
                findings.append(
                    line_finding(
                        severity="warning",
                        category="data_access",
                        rule_id="single_row_query",
                        source="external:data-access",
                        file_path=relative,
                        line=index,
                        message="QueryAsync 后只取 FirstOrDefault()，但 SQL / API 未表达单笔查询意图。",
                        evidence=line,
                        expected="SELECT TOP (1) + QueryFirstOrDefaultAsync or repository single-row equivalent",
                        actual="QueryAsync(...).FirstOrDefault()",
                        fix_hint="在不改变业务语义前提下，把单笔意图推入 SQL 与数据访问 API。",
                        confidence="medium",
                    )
                )
                break

    return findings


def collect_files_from_change_plan(change_plan: dict[str, Any]) -> list[str]:
    analysis = change_plan.get("analysis") if isinstance(change_plan.get("analysis"), dict) else {}
    values: list[str] = []
    for key in ("controllerFile", "interfaceFile", "targetFile"):
        text = clean_text(analysis.get(key))
        if text:
            values.append(text)
    for key in ("serviceFiles", "entityFiles", "codeTargetFiles"):
        raw = analysis.get(key)
        if isinstance(raw, list):
            values.extend(clean_text(item) for item in raw if clean_text(item))
        elif clean_text(raw):
            values.append(clean_text(raw))
    return sorted(dict.fromkeys(path.replace("\\", "/") for path in values if path.replace("\\", "/").endswith(SOURCE_SUFFIX)))


def context_api_dirs(context_root: Path, function_code: str, api_id: str | None) -> list[Path]:
    apis_root = context_root / function_code / "apis"
    if api_id:
        return [apis_root / api_id]
    if not apis_root.exists():
        return []
    return sorted(path for path in apis_root.iterdir() if path.is_dir())


def collect_target_files(
    *,
    project_root: Path,
    context_root: Path,
    function_code: str,
    scope: str,
    api_id: str | None,
    explicit_files: list[str],
) -> tuple[list[Path], list[Path], list[dict[str, Any]]]:
    explicit_paths: list[Path] = []
    for raw_file in explicit_files:
        candidate = resolve_path(raw_file, base=project_root)
        if candidate:
            explicit_paths.append(candidate)

    api_dirs = context_api_dirs(context_root, function_code, api_id)
    change_plans: list[dict[str, Any]] = []

    if scope == "files":
        return sorted(dict.fromkeys(explicit_paths)), api_dirs, change_plans

    if scope == "project":
        all_files = [
            path
            for path in sorted(project_root.rglob(f"*{SOURCE_SUFFIX}"))
            if not is_generated_or_excluded(path, project_root)
        ]
        return sorted(dict.fromkeys([*all_files, *explicit_paths])), api_dirs, change_plans

    files: list[Path] = []
    for api_dir in api_dirs:
        plan_path = api_dir / "change-plan.json"
        if not plan_path.exists():
            continue
        plan = read_json(plan_path)
        change_plans.append(plan)
        for relative_file in collect_files_from_change_plan(plan):
            candidate = (project_root / relative_file).resolve()
            if candidate.exists() and not is_generated_or_excluded(candidate, project_root):
                files.append(candidate)
    files.extend(explicit_paths)
    return sorted(dict.fromkeys(files)), api_dirs, change_plans


def has_sql_evidence(change_plans: list[dict[str, Any]], target_files: list[Path]) -> bool:
    for plan in change_plans:
        analysis = plan.get("analysis") if isinstance(plan.get("analysis"), dict) else {}
        serialized = json.dumps(
            {
                "queryContractsSelected": analysis.get("queryContractsSelected"),
                "backendApis": analysis.get("backendApis"),
                "devGuidelineLoadHints": analysis.get("devGuidelineLoadHints"),
                "sqlFixturePlan": analysis.get("sqlFixturePlan"),
                "serviceRuntimeValidationPlan": analysis.get("serviceRuntimeValidationPlan"),
            },
            ensure_ascii=False,
        ).casefold()
        if any(token in serialized for token in ("data-access", "querycontracts", "sql", "database", "db")):
            return True
    for path in target_files[:50]:
        if path.exists():
            text = read_text(path).casefold()
            if "queryasync" in text or "sqlparameter" in text:
                return True
    return False


def run_rule_pack_resolver(plugin_root: Path, workspace_key: str, rules_root: Path | None) -> dict[str, Any]:
    resolver = plugin_root / "references" / "resolve_project_rule_pack.py"
    command = [sys.executable, str(resolver), "--pack", "apiCodeWriter", "--workspace-key", workspace_key]
    if rules_root is not None:
        command.extend(["--rules-root", str(rules_root)])
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"apiCodeWriter rule pack is not ready:\n{result.stdout}\n{result.stderr}")
    payload = json.loads(result.stdout)
    if clean_text(payload.get("status")) != "ready":
        raise SystemExit("apiCodeWriter rule pack status is not ready: " + result.stdout)
    return payload


def rule_sources(
    *,
    plugin_root: Path,
    rules_root: Path | None,
    rule_pack: dict[str, Any],
    include_data_access: bool,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []

    def add_source(kind: str, rule_id: str, path: Path | None, required: bool = True) -> None:
        if path is None:
            return
        exists = path.exists()
        sources.append(
            {
                "kind": kind,
                "ruleId": rule_id,
                "path": str(path),
                "required": required,
                "exists": exists,
                "sha256": sha256_file(path) if exists and path.is_file() else None,
            }
        )

    add_source("skill", "api-code-writer", plugin_root / "skills" / "api-code-writer" / "SKILL.md")
    catalog_path = Path(clean_text(rule_pack.get("catalogPath"))) if clean_text(rule_pack.get("catalogPath")) else None
    add_source("rule-pack", "apiCodeWriter", catalog_path)

    for rule in list(rule_pack.get("rules") or []):
        if not isinstance(rule, dict):
            continue
        rule_id = clean_text(rule.get("ruleId"))
        title = clean_text(rule.get("title"))
        if rule_id.endswith("common-style") or (include_data_access and rule_id.endswith("data-access")):
            add_source("external-rule", title or rule_id, Path(clean_text(rule.get("resolvedPath"))), required=bool(rule.get("required")))
    return sources


def summarize(findings: list[dict[str, Any]]) -> dict[str, Any]:
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for finding in findings:
        severity = clean_text(finding.get("severity")) or "unknown"
        category = clean_text(finding.get("category")) or "unknown"
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    return {
        "findingCount": len(findings),
        "bySeverity": by_severity,
        "byCategory": by_category,
    }


def build_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# 04 Code Style Review",
        "",
        f"- updatedAt: {payload['updatedAt']}",
        f"- projectRoot: {payload['projectRoot']}",
        f"- functionCode: {payload['functionCode']}",
        f"- apiId: {payload.get('apiId') or 'all'}",
        f"- scope: {payload['scope']}",
        f"- targetFiles: {len(payload['targetFiles'])}",
        f"- findingCount: {payload['summary']['findingCount']}",
        "",
        "## Rule Sources",
        "",
    ]
    for source in payload.get("ruleSources") or []:
        lines.append(f"- {source.get('kind')} {source.get('ruleId')}: `{source.get('path')}`")
    lines.extend(["", "## Findings", ""])
    findings = payload.get("findings") or []
    if not findings:
        lines.append("- No findings.")
    else:
        for finding in findings:
            location = finding["file"]
            if finding.get("line"):
                location += f":{finding['line']}"
            lines.append(
                f"- [{finding['severity']}] {finding['category']} / {finding['ruleId']} at `{location}` - {finding['message']}"
            )
            lines.append(f"  - evidence: `{finding['evidence']}`")
            lines.append(f"  - fixHint: {finding['fixHint']}")
    lines.append("")
    return "\n".join(lines)


def write_reports(payload: dict[str, Any], context_root: Path, function_code: str, api_id: str | None) -> list[str]:
    outputs: list[str] = []
    root = context_root / function_code
    for directory in [root, *( [root / "apis" / api_id] if api_id else [] )]:
        json_path = directory / "code-style-review.json"
        md_path = directory / "code-style-review.md"
        dump_json(json_path, payload)
        write_text(md_path, build_markdown_report(payload))
        outputs.extend([str(json_path), str(md_path)])
    return outputs


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review existing C# code against current 04 code style constraints.")
    parser.add_argument("--project-root", required=False)
    parser.add_argument("--workspace-root", required=False)
    parser.add_argument("--agent-root", required=False)
    parser.add_argument("--workspace-key", default="NEWDAWHO")
    parser.add_argument("--rules-root", required=False)
    parser.add_argument("--context-root", required=False)
    parser.add_argument("--function-code", required=True)
    parser.add_argument("--api-id", required=False)
    parser.add_argument("--scope", choices=("context", "project", "files"), default="context")
    parser.add_argument("--file", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    script_path = Path(__file__).resolve()
    plugin_root = find_plugin_root(script_path)
    workspace = workspace_entry(plugin_root, args.workspace_key)

    project_root = resolve_path(args.project_root) or resolve_path(workspace.get("defaultCodeRoot"))
    if project_root is None:
        raise SystemExit("--project-root is required when local-workspaces.json has no defaultCodeRoot")
    agent_root = resolve_path(args.agent_root) or resolve_path(workspace.get("agentRoot")) or (project_root / ".agent").resolve()
    context_root = resolve_path(args.context_root) or (agent_root / "context").resolve()
    rules_root = resolve_path(args.rules_root) or resolve_path(workspace.get("rulesRoot")) or (agent_root / "project-rules" / args.workspace_key).resolve()

    rule_pack = run_rule_pack_resolver(plugin_root, args.workspace_key, rules_root)
    target_files, api_dirs, change_plans = collect_target_files(
        project_root=project_root,
        context_root=context_root,
        function_code=args.function_code,
        scope=args.scope,
        api_id=args.api_id,
        explicit_files=args.file,
    )

    if not target_files and args.scope != "project":
        raise SystemExit("No target C# files found. Check function-code/api-id/change-plan or pass --file.")

    expected_author = normalize_author(getpass.getuser())
    findings: list[dict[str, Any]] = []
    for path in target_files:
        if path.exists() and path.suffix.lower() == SOURCE_SUFFIX:
            findings.extend(scan_source_file(path, project_root, expected_author))

    if args.scope in {"context", "project"}:
        for path in sorted(project_root.rglob("*")):
            if path.is_file() and is_backup_artifact(path, project_root):
                findings.append(
                    line_finding(
                        severity="warning",
                        category="repository_hygiene",
                        rule_id="no_project_backup_artifacts",
                        source="external:common-style",
                        file_path=project_relative(path, project_root),
                        line=None,
                        message="项目业务仓库内存在备份或临时副本。",
                        evidence=path.name,
                        expected="no .bak/.tmp/.orig/.before_* files",
                        actual=path.name,
                        fix_hint="确认不是交付物后清理，不要把备份文件留在项目仓库。",
                        confidence="high",
                    )
                )

    findings.sort(key=lambda item: (item["file"], item.get("line") or 0, item["category"]))
    include_data_access = has_sql_evidence(change_plans, target_files)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "skillName": SKILL_NAME,
        "updatedAt": now_iso(),
        "projectRoot": str(project_root),
        "functionCode": args.function_code,
        "apiId": args.api_id,
        "scope": args.scope,
        "ruleSources": rule_sources(
            plugin_root=plugin_root,
            rules_root=rules_root,
            rule_pack=rule_pack,
            include_data_access=include_data_access,
        ),
        "targetFiles": [project_relative(path, project_root) for path in target_files],
        "summary": summarize(findings),
        "findings": findings,
    }
    outputs = write_reports(payload, context_root, args.function_code, args.api_id)
    print(json.dumps({"status": "done", "findingCount": len(findings), "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
