from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from project_rules import resolve_asset_path


TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "cp950", "gb18030", "latin-1")


def normalize_text(text: Any) -> str:
    return " ".join(str(text or "").split()).strip()


def dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = normalize_text(value)
        if not token or token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_code_inspection_rules(binding_rules_path: Path | None = None) -> list[dict[str, Any]]:
    path = binding_rules_path or resolve_asset_path("utBindingRules", fallback=skill_root() / "assets" / "binding-rules.json")
    if path is None:
        return []
    payload = load_json(path)
    return list(payload.get("codeInspectionRules") or [])


def absolutize_path(raw_path: str, repo_root: str | Path | None) -> str:
    candidate = Path(str(raw_path)).expanduser()
    if candidate.is_absolute() or not normalize_text(repo_root):
        return candidate.resolve().as_posix() if candidate.is_absolute() else candidate.as_posix()
    return (Path(repo_root) / candidate).resolve().as_posix()


def aggregate_path_groups(
    apis: list[dict[str, Any]],
    repo_root: str | Path | None = None,
) -> dict[str, list[str]]:
    buckets = {
        "controller": [],
        "service": [],
        "entity": [],
        "common": [],
        "unitTest": [],
        "integrationTest": [],
        "other": [],
    }
    for api in apis:
        for bucket, values in (api.get("codePaths") or {}).items():
            buckets.setdefault(bucket, [])
            buckets[bucket].extend(
                absolutize_path(value, repo_root)
                for value in values or []
                if normalize_text(value)
            )
    return {bucket: dedupe(values) for bucket, values in buckets.items()}


def configured_code_inspection_rules(
    check_item: str,
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    check_text = normalize_text(check_item).casefold()
    matched_rules: list[dict[str, Any]] = []
    for rule in rules:
        triggers = [
            normalize_text(token).casefold()
            for token in rule.get("whenCheckItemContainsAny", [])
            if normalize_text(token)
        ]
        if triggers and not any(trigger in check_text for trigger in triggers):
            continue
        matched_rules.append(rule)
    return matched_rules


def build_code_inspection_plan(
    check_item: str,
    traceability: dict[str, Any],
    repo_root: str | Path | None = None,
    rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active_rules = rules if rules is not None else load_code_inspection_rules()
    matched_rules = configured_code_inspection_rules(check_item, active_rules)
    if not matched_rules:
        return {}

    selected_rule = matched_rules[0]
    path_groups = traceability.get("pathGroups") or {}
    evidence_paths: list[str] = []
    for bucket in selected_rule.get("pathBuckets", []) or []:
        evidence_paths.extend(
            absolutize_path(path, repo_root)
            for path in path_groups.get(bucket, [])
            if normalize_text(path)
        )
    if not evidence_paths:
        evidence_paths.extend(
            absolutize_path(path, repo_root)
            for path in traceability.get("codePaths", [])
            if normalize_text(path)
        )

    return {
        "ruleId": normalize_text(selected_rule.get("id", "")),
        "evidencePaths": dedupe(evidence_paths),
        "mustContainAny": dedupe(list(selected_rule.get("mustContainAny") or [])),
        "mustContainAll": dedupe(list(selected_rule.get("mustContainAll") or [])),
        "mustNotContainAny": dedupe(list(selected_rule.get("mustNotContainAny") or [])),
        "passActualResult": normalize_text(
            selected_rule.get("passActualResult") or "通過，已由代碼定位檢查確認。"
        ),
        "pendingActualResult": normalize_text(
            selected_rule.get("pendingActualResult") or "待補，尚未定位到充分代碼證據。"
        ),
        "failActualResult": normalize_text(
            selected_rule.get("failActualResult") or "失敗，代碼定位檢查發現衝突證據。"
        ),
    }


def render_path_token(raw_value: str, runtime_context: dict[str, Path], manifest_dir: Path) -> str:
    workspace_root = runtime_context.get("workspaceRoot", manifest_dir)
    repo_root = runtime_context.get("repoRoot", workspace_root)
    return (
        raw_value.replace("{workspaceRoot}", workspace_root.as_posix())
        .replace("{repoRoot}", repo_root.as_posix())
        .replace("{manifestDir}", manifest_dir.as_posix())
    )


def resolve_code_paths(
    manifest_dir: Path,
    evidence_paths: list[str],
    runtime_context: dict[str, Path],
) -> list[Path]:
    resolved_paths: list[Path] = []
    for raw_path in evidence_paths:
        rendered = render_path_token(str(raw_path), runtime_context, manifest_dir)
        candidate = Path(rendered).expanduser()
        if not candidate.is_absolute():
            candidate = (manifest_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if candidate.is_dir():
            resolved_paths.extend(path for path in candidate.rglob("*") if path.is_file())
            continue
        if candidate.exists():
            resolved_paths.append(candidate)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in resolved_paths:
        token = path.as_posix()
        if token in seen:
            continue
        seen.add(token)
        unique.append(path)
    return unique


def read_text_with_fallback(path: Path) -> str:
    for encoding in TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def inspect_code_paths(
    manifest_path: Path,
    item: dict[str, Any],
    runtime_context: dict[str, Path],
) -> tuple[dict[str, Any], list[str]]:
    code_inspection = item.get("codeInspection") or {}
    base_payload = {
        "caseId": item.get("caseId", ""),
        "checkItem": item.get("checkItem", ""),
        "status": "pending",
        "actualResult": item.get("actualResult", ""),
        "notes": item.get("notes", ""),
        "boundTests": [],
        "missingTests": [],
        "failureDetails": [],
        "attachmentPaths": [],
        "trxPath": "",
        "sourceKind": "codeInspection",
    }
    blocking_issues: list[str] = []
    evidence_paths = [
        normalize_text(path)
        for path in code_inspection.get("evidencePaths", [])
        if normalize_text(path)
    ]
    if not evidence_paths:
        blocking_issues.append(
            f"{item.get('caseId', '<unknown>')} missing codeInspection.evidencePaths"
        )
        base_payload["actualResult"] = (
            normalize_text(code_inspection.get("pendingActualResult")) or "待補，尚未配置代碼定位路徑。"
        )
        return base_payload, blocking_issues

    resolved_paths = resolve_code_paths(manifest_path.parent, evidence_paths, runtime_context)
    existing_paths = [path.as_posix() for path in resolved_paths]
    base_payload["attachmentPaths"] = existing_paths
    if not resolved_paths:
        base_payload["actualResult"] = (
            normalize_text(code_inspection.get("pendingActualResult")) or "待補，尚未找到可檢查的代碼檔案。"
        )
        return base_payload, blocking_issues

    combined_text = "\n".join(read_text_with_fallback(path) for path in resolved_paths)
    haystack = combined_text.casefold()
    must_contain_any = [
        normalize_text(token)
        for token in code_inspection.get("mustContainAny", [])
        if normalize_text(token)
    ]
    must_contain_all = [
        normalize_text(token)
        for token in code_inspection.get("mustContainAll", [])
        if normalize_text(token)
    ]
    must_not_contain_any = [
        normalize_text(token)
        for token in code_inspection.get("mustNotContainAny", [])
        if normalize_text(token)
    ]

    forbidden_hits = [token for token in must_not_contain_any if token.casefold() in haystack]
    missing_all = [token for token in must_contain_all if token.casefold() not in haystack]
    matched_any = [token for token in must_contain_any if token.casefold() in haystack]

    if forbidden_hits:
        base_payload["status"] = "failed"
        base_payload["actualResult"] = (
            normalize_text(code_inspection.get("failActualResult")) or "失敗，代碼定位檢查發現衝突證據。"
        )
        base_payload["failureDetails"] = [
            {
                "testName": code_inspection.get("ruleId", "code_inspection"),
                "message": f"Found forbidden tokens: {', '.join(forbidden_hits)}",
                "attachments": existing_paths,
            }
        ]
        return base_payload, blocking_issues

    if missing_all or (must_contain_any and not matched_any):
        base_payload["status"] = "pending"
        base_payload["actualResult"] = (
            normalize_text(code_inspection.get("pendingActualResult")) or "待補，尚未定位到充分代碼證據。"
        )
        return base_payload, blocking_issues

    base_payload["status"] = "passed"
    base_payload["actualResult"] = (
        normalize_text(code_inspection.get("passActualResult")) or "通過，已由代碼定位檢查確認。"
    )
    return base_payload, blocking_issues
