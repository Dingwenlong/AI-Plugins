#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from dev_guidelines import blocking_dev_guideline_gaps, select_dev_guidelines
from framework_plan import (
    ENTERPRISE_FRAMEWORK_PROFILE,
    PRIMARY_FRAMEWORK_GUIDELINE,
    FrameworkPlan,
    FrameworkProfile,
    collect_code_target_files,
    collect_test_handoff_files,
)
from chain_workspace import update_chain_status
from handoff_analysis import normalize_upstream_model
from reporting import (
    build_report_section_hints,
    build_report_source_files,
    collect_test_target_files,
    dedupe_strings,
    discover_test_names,
    read_text_with_fallback,
)
from runtime import (
    COMPATIBLE_UPSTREAM_API_SPEC_SCHEMA_VERSIONS,
    SKILL_NAME,
    STATE_SCHEMA_VERSION,
    TRACKED_SOURCE_SUFFIXES,
    UPSTREAM_API_SPEC_SCHEMA_VERSION,
    ExecutionContext,
    append_progress,
    configure_stdio,
    default_batch_file,
    dump_json,
    dump_text,
    load_json,
    load_batch_file,
    load_schema,
    normalize_persisted_path,
    now_iso,
    remove_file,
    resolve_agent_dir,
    resolve_context_root,
    resolve_project_root,
    resolve_solution_path,
    save_batch_file,
    sha256_file,
)
from state_io import stable_spec_manifest_hash
from validation_runner import (
    build_validation_summary,
    classify_validation_result,
    evaluate_validation_outcome,
    run_validation_checks,
    summarize_validation_failure,
    summarize_validation_retries,
)


WRITER_STATUSES = {
    "pending",
    "waiting_fixture",
    "in_progress",
    "tests_passed",
    "tests_failed",
    "blocked",
    "error",
}
UPSTREAM_READY_STATUS = "done"
REVIEW_NOTE_SCOPES = {"global_skill", "api_behavior", "controller", "service", "entity", "test", "reporting"}
REVIEW_NOTE_FILE_ROLES = {"controller", "service", "entity", "unit_test", "integration_test", "shared"}
PROJECT_HARD_CONSTRAINTS_FILENAME = "project-hard-constraints.json"


class SkillError(RuntimeError):
    def __init__(self, message: str, *, status: str = "error", diagnosis_type: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.diagnosis_type = diagnosis_type


class ZhArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)
        self._positionals.title = "位置参数"
        self._optionals.title = "可选参数"

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        text = super().format_help()
        return (
            text.replace("usage:", "用法：", 1)
            .replace("positional arguments:", "位置参数：")
            .replace("optional arguments:", "可选参数：")
            .replace("options:", "可选参数：")
            .replace("show this help message and exit", "显示此帮助并退出")
        )

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 错误：{message}\n")


@dataclass(frozen=True)
class UpstreamApiRecord:
    api_id: str
    api_category: str
    api_name: str
    status: str
    block_reason: str | None
    fixture_status: str | None
    fixture_phase: str | None
    fixture_block_reason: str | None
    fixture_source_fingerprint: str | None
    manifest_path: Path
    api_spec_path: Path | None
    manifest_payload: dict[str, Any]
    api_spec_payload: dict[str, Any] | None


def parse_args() -> argparse.Namespace:
    parser = ZhArgumentParser(description="读取共享 .agent/context execution，编排单支 API 的代码准备、验证与状态回写，不直接生成业务代码。")
    parser.add_argument("-h", "--help", action="help", help="显示此帮助并退出")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--solution-path", default=None)
    parser.add_argument("--agent-dir", default=".agent")
    parser.add_argument("--agent-root", help="集中 .agent 根目录；优先级高于环境变量与插件本地配置。")
    parser.add_argument("--workspace-root", help="共享工作区根目录，例如 D:\\Repo\\Project。")
    parser.add_argument("--workspace-key", help="插件 local-workspaces.json 中的工作区 key，例如 PROJECT。")
    parser.add_argument("--rules-root", help="专案规则库根目录；优先级高于环境变量与 workspace 配置。")
    parser.add_argument("--context-root", default=None)
    parser.add_argument("--function-code", default=None)
    parser.add_argument("--api-id", default=None)
    parser.add_argument("--execution-mode", choices=["auto", "prepare", "apply"], default="auto")
    parser.add_argument("--validation-check", action="append", default=[])
    parser.add_argument("--modified-file", action="append", default=[])
    parser.add_argument("--new-file", action="append", default=[])
    return parser.parse_args()


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def normalize_token(value: str) -> str:
    return "".join(clean_text(value).split()).casefold()


def to_posix_path(path: Path) -> str:
    return path.expanduser().resolve().as_posix()


def resolve_context_rules_root(agent_dir: Path) -> Path | None:
    snapshot_path = agent_dir / "config" / "chain-workspace.json"
    try:
        payload = load_json(snapshot_path)
    except Exception:
        payload = {}
    raw_path = clean_text(payload.get("rulesRoot") if isinstance(payload, dict) else None)
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = agent_dir / path
    return path.resolve()


def resolve_guideline_authority(agent_dir: Path) -> str:
    rules_root = resolve_context_rules_root(agent_dir)
    if rules_root is None:
        return "project rules catalog not resolved"
    catalog_path = rules_root / "catalog.json"
    try:
        catalog = load_json(catalog_path)
    except Exception:
        return "project rules catalog missing"
    defaults = catalog.get("defaults") if isinstance(catalog, dict) and isinstance(catalog.get("defaults"), dict) else {}
    return (
        clean_text(defaults.get("primaryFrameworkGuideline"))
        or clean_text(defaults.get("codeGuidelineCatalog"))
        or PRIMARY_FRAMEWORK_GUIDELINE
    )


def project_hard_constraints_path(agent_dir: Path) -> Path:
    return (agent_dir / "Common" / PROJECT_HARD_CONSTRAINTS_FILENAME).resolve()


def normalized_keyword_list(values: object) -> list[str]:
    if isinstance(values, str):
        candidates = [values]
    elif isinstance(values, list):
        candidates = [clean_text(value) for value in values]
    else:
        return []

    normalized_values: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = normalize_token(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)
    return normalized_values


def build_project_review_reference_text(normalized_model: dict[str, Any], *, function_code: str) -> str:
    parts: list[str] = [
        function_code,
        clean_text(normalized_model.get("apiCategory")),
        clean_text(normalized_model.get("apiName")),
    ]
    for field in list(normalized_model.get("requestFields") or []):
        if isinstance(field, dict):
            parts.extend([clean_text(field.get("path")), clean_text(field.get("description")), clean_text(field.get("notes"))])
    for field in list(normalized_model.get("responseFields") or []):
        if isinstance(field, dict):
            parts.extend([clean_text(field.get("path")), clean_text(field.get("description")), clean_text(field.get("notes"))])
    for step in list(normalized_model.get("businessSteps") or []):
        if isinstance(step, dict):
            parts.extend([clean_text(step.get("title")), clean_text(step.get("details"))])
    for dependency in list(normalized_model.get("runtimeDependencies") or []):
        if isinstance(dependency, dict):
            parts.extend([clean_text(dependency.get("id")), clean_text(dependency.get("description"))])
    for api_line in list(normalized_model.get("backendApis") or []):
        parts.append(clean_text(api_line))
    for contract in list(normalized_model.get("queryContracts") or []):
        if isinstance(contract, dict):
            parts.extend(
                [
                    clean_text(contract.get("purpose")),
                    clean_text(contract.get("sqlText")),
                    *[clean_text(value) for value in list(contract.get("mustContain") or []) if clean_text(value)],
                ]
            )
    return normalize_token("\n".join(part for part in parts if part))


def project_review_rule_matches(
    rule: dict[str, Any],
    *,
    function_code: str,
    api_category: str,
    api_name: str,
    normalized_reference_text: str,
) -> bool:
    conditions = rule.get("conditions")
    if not isinstance(conditions, dict):
        return True

    function_codes = normalized_keyword_list(conditions.get("functionCodes"))
    if function_codes and normalize_token(function_code) not in function_codes:
        return False

    api_categories = normalized_keyword_list(conditions.get("apiCategories"))
    if api_categories and normalize_token(api_category) not in api_categories:
        return False

    api_names = normalized_keyword_list(conditions.get("apiNames"))
    if api_names and normalize_token(api_name) not in api_names:
        return False

    business_keywords = normalized_keyword_list(conditions.get("businessKeywordsAny"))
    if business_keywords and not any(keyword in normalized_reference_text for keyword in business_keywords):
        return False

    return True


def synthesize_review_notes_from_project_constraints(
    context: ExecutionContext,
    api_id: str,
    normalized_model: dict[str, Any],
) -> dict[str, Any]:
    path = project_hard_constraints_path(context.agent_dir)
    if not path.exists():
        return {
            "path": None,
            "sourceDoc": None,
            "language": None,
            "items": [],
        }

    payload = require_json_object(PROJECT_HARD_CONSTRAINTS_FILENAME, path)
    validate_payload_against_schema(payload, "project-hard-constraints.schema.json", PROJECT_HARD_CONSTRAINTS_FILENAME)

    applies_to_skills = [clean_text(value) for value in list(payload.get("appliesToSkills") or []) if clean_text(value)]
    if applies_to_skills and SKILL_NAME not in applies_to_skills:
        return {
            "path": None,
            "sourceDoc": None,
            "language": None,
            "items": [],
        }

    function_code = context.execution_id
    api_category = clean_text(normalized_model.get("apiCategory"))
    api_name = clean_text(normalized_model.get("apiName"))
    normalized_reference_text = build_project_review_reference_text(normalized_model, function_code=function_code)
    items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(payload.get("rules") or []):
        if not isinstance(raw_item, dict):
            continue
        if not project_review_rule_matches(
            raw_item,
            function_code=function_code,
            api_category=api_category,
            api_name=api_name,
            normalized_reference_text=normalized_reference_text,
        ):
            continue

        scope = clean_text(raw_item.get("scope"))
        file_role = clean_text(raw_item.get("fileRole"))
        if scope not in REVIEW_NOTE_SCOPES:
            raise SkillError(
                f"project-hard-constraints.rules[{index}].scope is invalid: {scope or 'null'}",
                status="blocked",
                diagnosis_type="review_constraint_gap",
            )
        if file_role not in REVIEW_NOTE_FILE_ROLES:
            raise SkillError(
                f"project-hard-constraints.rules[{index}].fileRole is invalid: {file_role or 'null'}",
                status="blocked",
                diagnosis_type="review_constraint_gap",
            )
        items.append(
            {
                "reviewId": clean_text(raw_item.get("ruleId")) or f"review_{index + 1}",
                "scope": scope,
                "fileRole": file_role,
                "ruleType": clean_text(raw_item.get("ruleType")) or "review_note",
                "instruction": clean_text(raw_item.get("instruction")),
                "severity": clean_text(raw_item.get("severity")) or "warning",
                "blocking": bool(raw_item.get("blocking")),
                "appliesTo": [clean_text(value) for value in list(raw_item.get("appliesTo") or []) if clean_text(value)],
                "examples": [clean_text(value) for value in list(raw_item.get("examples") or []) if clean_text(value)],
                "source": "project_hard_constraints",
            }
        )

    return {
        "path": None,
        "sourceDoc": normalize_persisted_path(path, project_root=context.project_root) or path.name,
        "language": clean_text(payload.get("language")) or "zh-Hant",
        "items": items,
    }


def format_validation_path(path_items: Iterable[object]) -> str:
    rendered = "".join(
        f"[{item}]" if isinstance(item, int) else (f".{item}" if index else str(item))
        for index, item in enumerate(path_items)
    )
    return rendered or "$"


def validate_payload_against_schema(payload: dict[str, Any], schema_name: str, label: str) -> None:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        raise SkillError(f"{label} schema 校验失败：{format_validation_path(first.absolute_path)} - {first.message}")


def require_json_object(label: str, path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise SkillError(f"{label} must be a JSON object: {path.as_posix()}")
    return payload


def summarize_upstream_status(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(items), "pending": 0, "in_progress": 0, "done": 0, "blocked": 0, "error": 0, "retired": 0}
    for item in items:
        status = clean_text(item.get("status"))
        if status in counts:
            counts[status] += 1
    return counts


def summarize_writer_status(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(items),
        "pending": 0,
        "waiting_fixture": 0,
        "in_progress": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "blocked": 0,
        "error": 0,
        "upstream_not_ready": 0,
    }
    for item in items:
        status = clean_text(item.get("writerStatus"))
        if status in counts:
            counts[status] += 1
        elif status.startswith("upstream_"):
            counts["upstream_not_ready"] += 1
    return counts


def summarize_fixture_status(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(items),
        "pending": 0,
        "in_progress": 0,
        "done": 0,
        "skipped": 0,
        "blocked": 0,
        "error": 0,
    }
    for item in items:
        status = clean_text(item.get("fixtureStatus"))
        if status in counts:
            counts[status] += 1
    return counts


def derive_fixture_execution_status(items: list[dict[str, Any]]) -> str:
    statuses = [clean_text(item.get("fixtureStatus")) for item in items if item.get("upstreamStatus") == UPSTREAM_READY_STATUS]
    if not statuses:
        return "waiting_fixture"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "in_progress" for status in statuses):
        return "running"
    if all(status in {"done", "skipped"} for status in statuses):
        return "done"
    if any(status == "error" for status in statuses):
        return "error"
    return "waiting_fixture"


def derive_execution_status(items: list[dict[str, Any]]) -> str:
    ready_items = [item for item in items if item.get("upstreamStatus") == UPSTREAM_READY_STATUS]
    if any(item.get("writerStatus") == "in_progress" for item in ready_items):
        return "running"
    if any(item.get("writerStatus") in {"pending", "tests_failed", "error"} for item in ready_items):
        return "waiting_resume"
    if any(item.get("writerStatus") == "waiting_fixture" for item in ready_items):
        return "waiting_fixture"
    if ready_items and all(item.get("writerStatus") == "tests_passed" for item in ready_items):
        return "done"
    if any(item.get("writerStatus") == "blocked" for item in ready_items):
        return "blocked"
    if any(clean_text(item.get("upstreamStatus")) in {"pending", "in_progress"} for item in items):
        return "waiting_upstream"
    if not ready_items:
        return "blocked"
    return "idle"


def aggregate_execution_status(spec_status: str, code_status: str) -> str:
    if spec_status == "done" and code_status == "done":
        return "done"
    if spec_status != "done":
        if spec_status in {"running", "in_progress"} or code_status in {"running", "in_progress"}:
            return "running"
        if spec_status == "blocked" or code_status == "blocked":
            return "blocked"
        return "waiting_spec"
    if code_status in {"running", "in_progress"}:
        return "running"
    if code_status == "waiting_fixture":
        return "waiting_fixture"
    if code_status == "blocked":
        return "blocked"
    return "waiting_code"


def aggregate_execution_phase(spec_status: str, code_phase: str | None) -> str:
    phase = clean_text(code_phase)
    return phase or spec_status


def latest_timestamp(*values: object) -> str:
    parsed: list[tuple[str, dt.datetime]] = []
    for value in values:
        text = clean_text(value)
        if not text:
            continue
        try:
            parsed.append((text, dt.datetime.fromisoformat(text)))
        except ValueError:
            continue
    if not parsed:
        return now_iso()
    parsed.sort(key=lambda item: item[1])
    return parsed[-1][0]


def resolve_execution_root(context_root: Path, requested_function_code: str | None) -> tuple[Path, str, Path]:
    batch_file = default_batch_file(context_root)
    batch_payload = load_batch_file(batch_file)
    function_code = clean_text(requested_function_code) or clean_text(batch_payload.get("activeFunctionCode"))
    if function_code:
        execution_root = (context_root / function_code).resolve()
        if not execution_root.exists() or not execution_root.is_dir():
            raise SkillError(f"functionCode not found under context root: {function_code}")
        missing = [name for name in ("execution-state.json", "api-checklist.json") if not (execution_root / name).exists()]
        if missing:
            raise SkillError(f"execution {function_code} is missing {', '.join(missing)}")
        return execution_root, function_code, batch_file

    candidates = sorted(
        path.resolve()
        for path in context_root.iterdir()
        if path.is_dir() and (path / "execution-state.json").exists() and (path / "api-checklist.json").exists()
    )
    if not candidates:
        raise SkillError("context 目录下未找到可用 execution。")
    if len(candidates) > 1:
        rendered = "\n".join(f"- {path.name}" for path in candidates)
        raise SkillError(f"检测到多个 execution，请显式提供 --function-code 或设置 execution-batch.json.activeFunctionCode：\n{rendered}")
    return candidates[0], candidates[0].name, batch_file


def refresh_batch_pointer(context: ExecutionContext, *, preferred_function_code: str | None = None) -> None:
    payload = load_batch_file(context.batch_file)
    items = sorted(list(payload.get("items") or []), key=lambda item: (int(item.get("order") or 0), clean_text(item.get("functionCode"))))
    if not items:
        return

    def execution_status(function_code: str) -> str | None:
        path = context.context_root / function_code / "execution-state.json"
        if not path.exists():
            return None
        state = load_json(path)
        return clean_text(state.get("status")) or None

    active = clean_text(preferred_function_code) or clean_text(payload.get("activeFunctionCode"))
    if not active:
        active = clean_text(items[0].get("functionCode"))
    if active and execution_status(active) == "done":
        for item in items:
            candidate = clean_text(item.get("functionCode"))
            if candidate and execution_status(candidate) != "done":
                active = candidate
                break
    payload["activeFunctionCode"] = active or None
    save_batch_file(context.batch_file, payload, updated_by=SKILL_NAME)


def resolve_upstream_api_spec_path(api_dir: Path, api_id: str, require_exists: bool) -> Path | None:
    candidates = sorted(path.resolve() for path in api_dir.glob("*_API_Spec.json") if path.is_file())
    if len(candidates) == 1:
        return candidates[0]
    if not require_exists and not candidates:
        return None
    if not candidates:
        raise SkillError(f"API_Spec.json not found for upstream apiId: {api_id}")
    raise SkillError(f"multiple API_Spec.json files found for upstream apiId: {api_id}")


def validate_shared_execution_state(path: Path, execution_id: str) -> dict[str, Any]:
    payload = require_json_object("execution-state.json", path)
    actual = clean_text(payload.get("executionId"))
    if actual != execution_id:
        raise SkillError(f"execution-state.json.executionId mismatch: expected {execution_id}, found {actual or 'null'}")
    return payload


def validate_shared_checklist(path: Path, execution_id: str) -> list[dict[str, Any]]:
    payload = require_json_object("api-checklist.json", path)
    actual = clean_text(payload.get("executionId"))
    if actual != execution_id:
        raise SkillError(f"api-checklist.json.executionId mismatch: expected {execution_id}, found {actual or 'null'}")
    items = payload.get("items")
    if not isinstance(items, list):
        raise SkillError("api-checklist.json.items must be an array.")
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise SkillError("api-checklist.json.items must contain objects.")
        api_id = clean_text(item.get("apiId"))
        api_category = clean_text(item.get("apiCategory"))
        api_name = clean_text(item.get("apiName"))
        status = clean_text(item.get("specStatus"))
        if not api_id or not api_category or not api_name or not status:
            raise SkillError("api-checklist.json item is missing apiId/apiCategory/apiName/specStatus.")
        normalized.append(
            {
                "apiId": api_id,
                "apiCategory": api_category,
                "apiName": api_name,
                "status": status,
                "blockReason": clean_text(item.get("specBlockReason")) or None,
                "fixtureStatus": clean_text(item.get("fixtureStatus")) or ("pending" if status == UPSTREAM_READY_STATUS else "waiting_spec"),
                "fixturePhase": clean_text(item.get("fixturePhase")) or ("pending" if status == UPSTREAM_READY_STATUS else "waiting_spec"),
                "fixtureBlockReason": clean_text(item.get("fixtureBlockReason")) or None,
                "fixtureSourceFingerprint": clean_text(item.get("fixtureSourceFingerprint")) or None,
                "codeStatus": clean_text(item.get("codeStatus")) or ("pending" if status == UPSTREAM_READY_STATUS else "waiting_spec"),
                "codePhase": clean_text(item.get("codePhase")) or ("pending" if status == UPSTREAM_READY_STATUS else "waiting_spec"),
                "codeBlockReason": clean_text(item.get("codeBlockReason")) or None,
                "sourceFingerprint": clean_text(item.get("specSourceFingerprint")) or None,
            }
        )
    if not normalized:
        raise SkillError("api-checklist.json.items is empty.")
    return normalized


def load_shared_execution(execution_root: Path, execution_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, UpstreamApiRecord]]:
    execution_state = validate_shared_execution_state(execution_root / "execution-state.json", execution_id)
    checklist_items = validate_shared_checklist(execution_root / "api-checklist.json", execution_id)
    api_map: dict[str, UpstreamApiRecord] = {}
    for item in checklist_items:
        api_id = item["apiId"]
        api_dir = execution_root / "apis" / api_id
        manifest_path = api_dir / "manifest.json"
        if not manifest_path.exists():
            raise SkillError(f"manifest.json not found for {api_id}")
        manifest_payload = require_json_object("manifest.json", manifest_path)
        validate_payload_against_schema(manifest_payload, "upstream-manifest.schema.json", f"manifest {api_id}")
        if clean_text(manifest_payload.get("executionId")) != execution_id:
            raise SkillError(f"manifest.executionId mismatch for {api_id}")
        if clean_text(manifest_payload.get("apiId")) != api_id:
            raise SkillError(f"manifest.apiId mismatch for {api_id}")
        manifest_status = clean_text(manifest_payload.get("specStatus"))
        if manifest_status != item["status"]:
            raise SkillError(f"checklist/manifest specStatus mismatch for {api_id}: {item['status']} vs {manifest_status}")
        manifest_fixture_status = clean_text(manifest_payload.get("fixtureStatus"))
        if manifest_fixture_status and manifest_fixture_status != item["fixtureStatus"]:
            raise SkillError(f"checklist/manifest fixtureStatus mismatch for {api_id}: {item['fixtureStatus']} vs {manifest_fixture_status}")

        api_spec_path: Path | None = None
        api_spec_payload: dict[str, Any] | None = None
        if item["status"] == UPSTREAM_READY_STATUS:
            api_spec_path = resolve_upstream_api_spec_path(api_dir, api_id, require_exists=True)
            if api_spec_path is None:
                raise SkillError(f"API_Spec.json not found for upstream apiId: {api_id}")
            api_spec_payload = require_json_object("upstream API_Spec.json", api_spec_path)
            validate_payload_against_schema(api_spec_payload, "upstream-api-spec.schema.json", f"upstream API_Spec {api_id}")
            actual_api_id = clean_text(api_spec_payload.get("apiId"))
            if actual_api_id != api_id:
                raise SkillError(f"upstream API_Spec apiId mismatch for {api_id}: found {actual_api_id or 'null'}")
            if clean_text(api_spec_payload.get("schemaVersion")) not in COMPATIBLE_UPSTREAM_API_SPEC_SCHEMA_VERSIONS:
                supported = ", ".join(sorted(COMPATIBLE_UPSTREAM_API_SPEC_SCHEMA_VERSIONS))
                raise SkillError(f"upstream API_Spec schemaVersion mismatch for {api_id}; supported: {supported}")
        api_map[api_id] = UpstreamApiRecord(
            api_id=api_id,
            api_category=item["apiCategory"],
            api_name=item["apiName"],
            status=item["status"],
            block_reason=item["blockReason"],
            fixture_status=clean_text(manifest_payload.get("fixtureStatus")) or item["fixtureStatus"],
            fixture_phase=clean_text(manifest_payload.get("fixturePhase")) or item["fixturePhase"],
            fixture_block_reason=clean_text(manifest_payload.get("fixtureBlockReason")) or item["fixtureBlockReason"],
            fixture_source_fingerprint=clean_text(manifest_payload.get("fixtureSourceFingerprint")) or item["fixtureSourceFingerprint"],
            manifest_path=manifest_path.resolve(),
            api_spec_path=api_spec_path.resolve() if api_spec_path else None,
            manifest_payload=manifest_payload,
            api_spec_payload=api_spec_payload,
        )
    return execution_state, checklist_items, api_map


def build_context(args: argparse.Namespace) -> tuple[ExecutionContext, dict[str, Any], list[dict[str, Any]], dict[str, UpstreamApiRecord]]:
    project_root = resolve_project_root(args.project_root)
    agent_dir = resolve_agent_dir(project_root, args.agent_dir, args.agent_root, args.workspace_root, args.workspace_key, args.rules_root)
    solution_path = resolve_solution_path(project_root, args.solution_path)
    context_root = resolve_context_root(project_root, agent_dir, args.context_root)
    upstream_execution_root, execution_id, batch_file = resolve_execution_root(context_root, args.function_code)
    execution_state, checklist_items, api_map = load_shared_execution(upstream_execution_root, execution_id)
    state_root = upstream_execution_root
    context = ExecutionContext(
        project_root=project_root,
        solution_path=solution_path,
        agent_dir=agent_dir,
        context_root=context_root,
        batch_file=batch_file,
        state_root=state_root,
        execution_id=execution_id,
        validation_checks=tuple(args.validation_check),
    )
    return context, execution_state, checklist_items, api_map



def code_contract_review_path(context: ExecutionContext, api_id: str) -> Path:
    return context.paths.api_dir(api_id) / "code-contract-review.json"


def normalize_contract_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).casefold())


def pascalize_contract_name(value: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if re.search(r"[_\-\s]", text):
        parts = [segment for segment in re.split(r"[^A-Za-z0-9]+", text) if segment]
        return "".join(part[:1].upper() + part[1:] for part in parts)
    return text[:1].upper() + text[1:]


def find_contract_field(fields: list[dict[str, Any]], path: str) -> dict[str, Any] | None:
    target = clean_text(path)
    for field in fields:
        if clean_text(field.get("path")) == target:
            return field
    return None


def response_data_is_collection(response_fields: list[dict[str, Any]]) -> bool:
    response_data_field = find_contract_field(response_fields, "responseData")
    if response_data_field is None:
        return False
    return clean_text(response_data_field.get("dataType")).casefold() in {"array", "list"}


def extract_response_item_field_names(response_fields: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for field in response_fields:
        path = clean_text(field.get("path"))
        if path.startswith("responseData[]."):
            names.append(path.split(".", 1)[1])
        elif path.startswith("responseData."):
            names.append(path.split(".", 1)[1])
    return dedupe_strings(names)


def find_method_signature(path: Path, method_name: str) -> str:
    if not path.exists():
        return ""
    text = read_text_with_fallback(path)
    pattern = re.compile(rf"[^\n]*\b{re.escape(method_name)}\s*\([^)]*\)[^\n]*")
    match = pattern.search(text)
    return match.group(0).strip() if match else ""


def controller_method_represents_collection(path: Path, method_name: str) -> bool | None:
    if not path.exists():
        return None
    text = read_text_with_fallback(path)
    signature_pattern = re.compile(rf"[^\n]*\b{re.escape(method_name)}\s*\([^)]*\)[^\n]*")
    match = signature_pattern.search(text)
    if not match:
        return None
    window_start = max(0, match.start() - 600)
    window_end = min(len(text), match.end() + 1600)
    window_text = text[window_start:window_end]
    normalized_window = re.sub(r"\s+", "", window_text).casefold()
    if any(
        token in normalized_window
        for token in (
            "producesresponsetype(typeof(transactionresult<list<",
            "producesresponsetype(typeof(transactionresult<ireadonlylist<",
            "producesresponsetype(typeof(transactionresult<ienumerable<",
            "transactionresult<list<",
            "transactionresult<ireadonlylist<",
            "transactionresult<ienumerable<",
            "transactionresult<icollection<",
        )
    ):
        return True
    if "transactionresult<" in normalized_window:
        return False
    return None


def signature_represents_collection(signature: str) -> bool:
    normalized = re.sub(r"\s+", "", clean_text(signature)).casefold()
    if not normalized:
        return False
    if any(
        token in normalized
        for token in (
            "transactionresult<list<",
            "transactionresult<ireadonlylist<",
            "transactionresult<ienumerable<",
            "transactionresult<icollection<",
        )
    ):
        return True
    return bool(re.search(r"transactionresult<[^>]+\[\]>", normalized))


def find_line_number(path: Path, needle: str) -> int | None:
    text = clean_text(needle)
    if not text or not path.exists():
        return None
    for index, line in enumerate(read_text_with_fallback(path).splitlines(), start=1):
        if text in line:
            return index
    return None


def extract_public_property_names(paths: Iterable[Path]) -> set[str]:
    property_names: set[str] = set()
    pattern = re.compile(r"\bpublic\s+(?:required\s+)?(?:[A-Za-z_][A-Za-z0-9_<>,\.\?\[\]]*\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
    for path in paths:
        if not path.exists():
            continue
        for match in pattern.finditer(read_text_with_fallback(path)):
            property_names.add(normalize_contract_name(match.group(1)))
    return property_names


def expected_response_dt_format(response_fields: list[dict[str, Any]]) -> str:
    response_dt = find_contract_field(response_fields, "responseDT")
    if response_dt is None:
        return ""
    notes = clean_text(response_dt.get("notes"))
    match = re.search(r"yyyy[^\"'\n]+", notes)
    return clean_text(match.group(0)) if match else notes


def find_transaction_result_format(project_root: Path) -> tuple[str | None, str | None]:
    candidates = sorted(path for path in project_root.rglob("TransactionResult.cs") if path.is_file())
    for path in candidates:
        text = read_text_with_fallback(path)
        match = re.search(r'ResponseDT[\s\S]{0,200}?ToString\("([^"]+)"\)', text)
        if match:
            return relative_path_from_project(path, project_root), clean_text(match.group(1))
    return None, None


def build_code_contract_review_artifact(
    context: ExecutionContext,
    item: dict[str, Any],
    normalized_model: dict[str, Any],
    change_plan: dict[str, Any],
) -> dict[str, Any]:
    analysis = change_plan.get("analysis") if isinstance(change_plan.get("analysis"), dict) else {}
    response_fields = [entry for entry in list(normalized_model.get("responseFields") or []) if isinstance(entry, dict)]
    expected_collection = response_data_is_collection(response_fields)
    expected_item_fields = extract_response_item_field_names(response_fields)
    expected_item_properties = [pascalize_contract_name(path.split(".")[-1]) for path in expected_item_fields]
    findings: list[dict[str, Any]] = []

    def add_finding(
        *,
        severity: str,
        category: str,
        file_path: str,
        message: str,
        expected: str,
        actual: str,
        line: int | None = None,
    ) -> None:
        findings.append(
            {
                "severity": severity,
                "category": category,
                "file": file_path,
                "line": line,
                "message": message,
                "expected": expected,
                "actual": actual,
            }
        )

    target_method = clean_text(analysis.get("targetMethod"))
    review_files = {
        "controller": clean_text(analysis.get("controllerFile")),
        "interface": clean_text(analysis.get("interfaceFile")),
        "service": clean_text(analysis.get("targetFile")),
    }
    for role, relative_path in review_files.items():
        if not relative_path or not target_method:
            continue
        absolute_path = context.project_root / relative_path
        signature = find_method_signature(absolute_path, target_method)
        if not signature:
            add_finding(
                severity="warning",
                category="method_signature_missing",
                file_path=relative_path,
                line=None,
                message=f"找不到 {target_method} 方法簽名，無法驗證 {role} 與 spec 契約是否一致。",
                expected=target_method,
                actual="not found",
            )
            continue
        actual_is_collection = signature_represents_collection(signature)
        if role == "controller" and "task<iactionresult>" in re.sub(r"\s+", "", signature).casefold():
            controller_collection = controller_method_represents_collection(absolute_path, target_method)
            if controller_collection is not None:
                actual_is_collection = controller_collection
        if expected_collection and not actual_is_collection:
            add_finding(
                severity="blocking",
                category="response_shape",
                file_path=relative_path,
                line=find_line_number(absolute_path, target_method),
                message=f"{role} 的回傳簽名仍是單筆 response，但 spec 要求 responseData 為 array。",
                expected="TransactionResult<List<...>>",
                actual=signature,
            )
        if not expected_collection and actual_is_collection:
            add_finding(
                severity="blocking",
                category="response_shape",
                file_path=relative_path,
                line=find_line_number(absolute_path, target_method),
                message=f"{role} 的回傳簽名是集合，但 spec 沒有要求 responseData 為 array。",
                expected="TransactionResult<SingleResponse>",
                actual=signature,
            )

    entity_paths = [
        context.project_root / clean_text(path)
        for path in list(analysis.get("entityFiles") or [])
        if clean_text(path)
    ]
    actual_properties = extract_public_property_names(entity_paths)
    for property_name in expected_item_properties:
        normalized_property = normalize_contract_name(property_name)
        if normalized_property and normalized_property not in actual_properties:
            entity_file = clean_text((analysis.get("entityFiles") or [None])[0] or "")
            add_finding(
                severity="blocking",
                category="response_dto_fields",
                file_path=entity_file or "unknown",
                line=None,
                message=f"回應 DTO 缺少 spec 定義欄位 {property_name}。",
                expected=property_name,
                actual="missing",
            )

    service_path_text = clean_text(analysis.get("targetFile"))
    if expected_collection and service_path_text:
        service_path = context.project_root / service_path_text
        service_text = read_text_with_fallback(service_path) if service_path.exists() else ""
        if "FirstOrDefault()" in service_text:
            add_finding(
                severity="blocking",
                category="response_logic",
                file_path=service_path_text,
                line=find_line_number(service_path, "FirstOrDefault()"),
                message="spec 要求回傳列表，但 service 仍以 FirstOrDefault() 壓成單筆資料。",
                expected="project rows to list",
                actual="FirstOrDefault()",
            )

    expected_dt_format = expected_response_dt_format(response_fields)
    transaction_result_file, actual_dt_format = find_transaction_result_format(context.project_root)
    if expected_dt_format and actual_dt_format and expected_dt_format != actual_dt_format:
        add_finding(
            severity="blocking",
            category="response_dt_format",
            file_path=transaction_result_file or "TransactionResult.cs",
            line=None,
            message="共用 TransactionResult.ResponseDT 格式與 spec 不一致。",
            expected=expected_dt_format,
            actual=actual_dt_format,
        )

    blocking_count = sum(1 for finding in findings if clean_text(finding.get("severity")) == "blocking")
    warning_count = sum(1 for finding in findings if clean_text(finding.get("severity")) == "warning")
    status = "blocked" if blocking_count else ("warnings" if warning_count else "passed")
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "skillName": SKILL_NAME,
        "manifestType": "code-contract-review",
        "updatedAt": now_iso(),
        "executionId": context.execution_id,
        "apiId": item["apiId"],
        "status": status,
        "summary": {
            "findingCount": len(findings),
            "blockingCount": blocking_count,
            "warningCount": warning_count,
        },
        "contractSnapshot": {
            "requestFields": normalized_model.get("requestFields") or [],
            "responseFields": response_fields,
            "responseDataIsCollection": expected_collection,
            "responseItemFields": expected_item_fields,
        },
        "findings": findings,
    }


def load_review_notes(context: ExecutionContext, api_id: str, normalized_model: dict[str, Any] | None = None) -> dict[str, Any]:
    path = context.paths.api_dir(api_id) / "review-notes.json"
    if not path.exists():
        if isinstance(normalized_model, dict):
            synthesized = synthesize_review_notes_from_project_constraints(context, api_id, normalized_model)
            if synthesized.get("sourceDoc") or synthesized.get("items"):
                return synthesized
        return {
            "path": None,
            "sourceDoc": None,
            "language": None,
            "items": [],
        }
    payload = require_json_object("review-notes.json", path)
    validate_payload_against_schema(payload, "review-notes.schema.json", f"review-notes {api_id}")
    actual_api_id = clean_text(payload.get("apiId"))
    if actual_api_id != api_id:
        raise SkillError(
            f"review-notes.json.apiId mismatch: expected {api_id}, found {actual_api_id or 'null'}",
            status="blocked",
            diagnosis_type="review_constraint_gap",
        )
    source_doc = ensure_relative_persisted_path(payload.get("sourceDoc"), label="review-notes.json.sourceDoc")
    items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(payload.get("items") or []):
        if not isinstance(raw_item, dict):
            raise SkillError(
                f"review-notes.json.items[{index}] must be an object.",
                status="blocked",
                diagnosis_type="review_constraint_gap",
            )
        scope = clean_text(raw_item.get("scope"))
        file_role = clean_text(raw_item.get("fileRole"))
        if scope not in REVIEW_NOTE_SCOPES:
            raise SkillError(
                f"review-notes.json.items[{index}].scope is invalid: {scope or 'null'}",
                status="blocked",
                diagnosis_type="review_constraint_gap",
            )
        if file_role not in REVIEW_NOTE_FILE_ROLES:
            raise SkillError(
                f"review-notes.json.items[{index}].fileRole is invalid: {file_role or 'null'}",
                status="blocked",
                diagnosis_type="review_constraint_gap",
            )
        items.append(
            {
                "reviewId": clean_text(raw_item.get("reviewId")) or f"review_{index + 1}",
                "scope": scope,
                "fileRole": file_role,
                "ruleType": clean_text(raw_item.get("ruleType")) or "review_note",
                "instruction": clean_text(raw_item.get("instruction")),
                "severity": clean_text(raw_item.get("severity")) or "warning",
                "blocking": bool(raw_item.get("blocking")),
                "appliesTo": [clean_text(value) for value in list(raw_item.get("appliesTo") or []) if clean_text(value)],
                "examples": [clean_text(value) for value in list(raw_item.get("examples") or []) if clean_text(value)],
                "source": "review_notes",
            }
        )
    return {
        "path": normalize_persisted_path(path, project_root=context.project_root),
        "sourceDoc": source_doc,
        "language": clean_text(payload.get("language")) or "zh-Hant",
        "items": items,
    }


def build_default_review_items(normalized_model: dict[str, Any]) -> list[dict[str, Any]]:
    api_name = clean_text(normalized_model.get("apiName")) or "API"
    return [
        {
            "reviewId": "default_external_api_name",
            "scope": "global_skill",
            "fileRole": "shared",
            "ruleType": "naming",
            "instruction": f"對外 API 名稱、route 與需求說明必須沿用 {api_name}，不得額外追加 Async。",
            "severity": "warning",
            "blocking": True,
            "appliesTo": ["apiName"],
            "examples": [api_name],
            "source": "default_policy",
        },
        {
            "reviewId": "default_traditional_chinese_code",
            "scope": "global_skill",
            "fileRole": "shared",
            "ruleType": "language",
            "instruction": "AI 寫入的中文註解、字串、檔案說明與角色要求統一使用繁體中文。",
            "severity": "warning",
            "blocking": False,
            "appliesTo": ["code_comments", "code_strings", "file_headers"],
            "examples": ["繁體中文"],
            "source": "default_policy",
        },
        {
            "reviewId": "default_dependency_field_naming",
            "scope": "global_skill",
            "fileRole": "shared",
            "ruleType": "naming_style",
            "instruction": "凡是依賴注入後賦值到欄位的成員，命名一律使用 _camelCase，首字固定底線，例如 _service、_ctxAccessor、_sqlExecutor、_logger；不得使用 CtxAccessor、Logger 這類 PascalCase 欄位名。",
            "severity": "warning",
            "blocking": False,
            "appliesTo": ["constructor_injected_fields", "controller_fields", "service_fields", "fixture_fields"],
            "examples": ["_service", "_ctxAccessor", "_sqlExecutor", "_logger"],
            "source": "default_policy",
        },
    ]


def merge_review_items(review_notes: dict[str, Any], default_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    review_items = [item for item in list(review_notes.get("items") or []) if isinstance(item, dict)]
    merged: list[dict[str, Any]] = list(review_items)
    seen = {(clean_text(item.get("ruleType")), clean_text(item.get("fileRole"))) for item in review_items}
    for item in default_items:
        signature = (clean_text(item.get("ruleType")), clean_text(item.get("fileRole")))
        if signature in seen:
            continue
        merged.append(item)
    return merged


def target_roles_for_review_item(item: dict[str, Any]) -> list[str]:
    file_role = clean_text(item.get("fileRole"))
    if file_role == "controller":
        return ["controller"]
    if file_role == "service":
        return ["service"]
    if file_role == "entity":
        return ["entity"]
    if file_role == "unit_test":
        return ["unitTest"]
    if file_role == "integration_test":
        return ["integrationTest"]
    return ["controller", "service", "entity", "unitTest", "integrationTest"]


def select_review_constraints(normalized_model: dict[str, Any], framework_plan: FrameworkPlan) -> dict[str, Any]:
    review_notes = normalized_model.get("reviewNotes") if isinstance(normalized_model.get("reviewNotes"), dict) else {}
    selected_items = merge_review_items(review_notes, build_default_review_items(normalized_model))
    request_paths = {f"request.{clean_text(field.get('path'))}" for field in normalized_model.get("requestFields") or [] if clean_text(field.get("path"))}
    response_paths = {f"response.{clean_text(field.get('path'))}" for field in normalized_model.get("responseFields") or [] if clean_text(field.get("path"))}
    validation_errors: list[str] = []
    api_name = clean_text(normalized_model.get("apiName"))

    for item in selected_items:
        if not bool(item.get("blocking")):
            continue
        rule_type = clean_text(item.get("ruleType"))
        applies_to = [clean_text(value) for value in list(item.get("appliesTo") or []) if clean_text(value)]
        if rule_type == "naming" and api_name.endswith("Async"):
            validation_errors.append(f"{item['reviewId']}: spec apiName already ends with Async.")
        if rule_type in {"contract_type", "nullability_required"}:
            for target in applies_to:
                if target.startswith("request.") and target not in request_paths:
                    validation_errors.append(f"{item['reviewId']}: unknown request field {target}.")
                if target.startswith("response.") and target not in response_paths:
                    validation_errors.append(f"{item['reviewId']}: unknown response field {target}.")
    if validation_errors:
        raise SkillError(
            "Review constraints conflict with spec/handoff: " + "; ".join(validation_errors),
            status="blocked",
            diagnosis_type="review_constraint_gap",
        )

    file_requirements: dict[str, list[dict[str, Any]]] = {
        "controller": [],
        "service": [],
        "entity": [],
        "unitTest": [],
        "integrationTest": [],
    }
    for item in selected_items:
        requirement = {
            "reviewId": item["reviewId"],
            "ruleType": item["ruleType"],
            "instruction": item["instruction"],
            "severity": item["severity"],
            "blocking": item["blocking"],
            "appliesTo": list(item.get("appliesTo") or []),
            "examples": list(item.get("examples") or []),
            "source": item.get("source") or "review_notes",
        }
        for role in target_roles_for_review_item(item):
            file_requirements[role].append(dict(requirement))

    response_rules = [
        {
            "reviewId": item["reviewId"],
            "ruleType": item["ruleType"],
            "instruction": item["instruction"],
            "blocking": item["blocking"],
            "source": item.get("source") or "review_notes",
        }
        for item in selected_items
        if clean_text(item.get("ruleType")) in {"response_lifecycle", "failure_payload"}
    ]
    review_sources: list[dict[str, Any]] = []
    if review_notes.get("path") or review_notes.get("sourceDoc"):
        review_sources.append(
            {
                "reviewNotes": review_notes.get("path"),
                "sourceDoc": review_notes.get("sourceDoc"),
                "language": clean_text(review_notes.get("language")) or "zh-Hant",
            }
        )
    return {
        "reviewSources": review_sources,
        "reviewConstraintsSelected": selected_items,
        "fileRequirements": file_requirements,
        "responseLifecycleRules": response_rules,
        "failureDisposition": {
            "mode": "rollback_after_validation_failure",
            "preserveFailedCode": False,
            "resumeStrategy": "retry_from_prepare",
            "source": "default_policy",
        },
        "languagePolicy": {
            "mode": "traditional_chinese_for_ai_code",
            "appliesTo": ["code_comments", "code_strings", "file_headers", "file_requirements"],
            "source": "review_notes" if review_sources else "default_policy",
        },
        "externalApiName": api_name,
        "internalAsyncMethod": framework_plan.target_method,
    }


def existing_writer_manifest_map(context: ExecutionContext) -> dict[str, dict[str, Any]]:
    manifest_map: dict[str, dict[str, Any]] = {}
    apis_root = context.paths.root / "apis"
    if not apis_root.exists():
        return manifest_map
    for path in sorted(apis_root.glob("*/manifest.json")):
        try:
            payload = require_json_object("writer manifest.json", path)
        except Exception:
            continue
        api_id = clean_text(payload.get("apiId"))
        if api_id:
            manifest_map[api_id] = payload
    return manifest_map


def should_exclude_relative_path(relative_path: str, excluded_prefixes: list[str]) -> bool:
    return any(relative_path == prefix or relative_path.startswith(prefix + "/") for prefix in excluded_prefixes)


NON_SOURCE_DIRECTORY_NAMES = {
    ".git",
    ".vs",
    "bin",
    "obj",
    "packages",
    "testresults",
}

NON_SOURCE_FILE_NAMES = {
    "project.assets.json",
}

NON_SOURCE_FILE_SUFFIXES = (
    ".assemblyinfo.cs",
    ".deps.json",
    ".filelistabsolute.txt",
    ".globalusings.g.cs",
    ".mvcapplicationpartsassemblyinfo.cs",
    ".nuget.dgspec.json",
    ".nuget.g.props",
    ".nuget.g.targets",
    ".runtimeconfig.json",
    ".staticwebassets.endpoints.json",
)


def is_source_level_relative_path(relative_path: str, excluded_prefixes: list[str]) -> bool:
    normalized = relative_path.replace("\\", "/").strip("/")
    if not normalized:
        return False
    if should_exclude_relative_path(normalized, excluded_prefixes):
        return False
    parts = [segment.lower() for segment in normalized.split("/")]
    if any(segment in NON_SOURCE_DIRECTORY_NAMES for segment in parts[:-1]):
        return False
    path = Path(normalized)
    filename = path.name.lower()
    if filename in NON_SOURCE_FILE_NAMES:
        return False
    if any(filename.endswith(suffix) for suffix in NON_SOURCE_FILE_SUFFIXES):
        return False
    return path.suffix.lower() in TRACKED_SOURCE_SUFFIXES


def filter_source_level_snapshot(files: dict[str, str], excluded_prefixes: list[str]) -> dict[str, str]:
    return {
        relative_path: digest
        for relative_path, digest in files.items()
        if is_source_level_relative_path(relative_path, excluded_prefixes)
    }


def build_repo_snapshot(project_root: Path, excluded_prefixes: list[str]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(project_root).as_posix()
        if not is_source_level_relative_path(relative_path, excluded_prefixes):
            continue
        snapshot[relative_path] = sha256_file(path) or ""
    return snapshot


def load_snapshot(snapshot_path: Path) -> dict[str, str]:
    if not snapshot_path.exists():
        return {}
    payload = require_json_object("repo-snapshot.json", snapshot_path)
    files = payload.get("files")
    return files if isinstance(files, dict) else {}


def diff_snapshot_files(before: dict[str, str], after: dict[str, str], excluded_prefixes: list[str]) -> list[str]:
    filtered_before = filter_source_level_snapshot(before, excluded_prefixes)
    filtered_after = filter_source_level_snapshot(after, excluded_prefixes)
    changed: list[str] = []
    for relative_path in sorted(set(filtered_before) | set(filtered_after)):
        if filtered_before.get(relative_path) != filtered_after.get(relative_path):
            changed.append(relative_path)
    return changed


def write_snapshot(snapshot_path: Path, files: dict[str, str], *, reason: str) -> None:
    dump_json(
        snapshot_path,
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "skillName": SKILL_NAME,
            "updatedAt": now_iso(),
            "reason": reason,
            "files": files,
        },
    )


def normalize_phase(value: str | None, fallback: str) -> str:
    text = clean_text(value)
    return text or fallback


def build_writer_item(upstream_api: UpstreamApiRecord, previous_manifest: dict[str, Any] | None) -> dict[str, Any]:
    input_hashes = {
        "upstreamManifest": stable_spec_manifest_hash(upstream_api.manifest_payload),
        "apiSpec": sha256_file(upstream_api.api_spec_path) if upstream_api.api_spec_path else None,
    }
    source_fingerprint = clean_text(upstream_api.manifest_payload.get("specSourceFingerprint") or upstream_api.manifest_payload.get("sourceFingerprint")) or None
    previous_hashes = previous_manifest.get("inputHashes") if isinstance(previous_manifest, dict) else {}
    previous_source_fingerprint = clean_text(previous_manifest.get("specSourceFingerprint")) or None if isinstance(previous_manifest, dict) else None
    previous_code_status = clean_text(previous_manifest.get("codeStatus")) if isinstance(previous_manifest, dict) else ""
    same_inputs = bool(
        previous_manifest
        and previous_hashes.get("upstreamManifest") == input_hashes["upstreamManifest"]
        and previous_hashes.get("apiSpec") == input_hashes["apiSpec"]
        and previous_source_fingerprint == source_fingerprint
    )
    if upstream_api.status != UPSTREAM_READY_STATUS:
        writer_status = "waiting_spec"
        block_reason = upstream_api.block_reason or f"Spec API status is {upstream_api.status}."
        return {
            "apiId": upstream_api.api_id,
            "apiCategory": upstream_api.api_category,
            "apiName": upstream_api.api_name,
            "upstreamStatus": upstream_api.status,
            "writerStatus": writer_status,
            "phase": "waiting_spec",
            "blockReason": block_reason,
            "specBlockReason": upstream_api.block_reason,
            "fixtureStatus": upstream_api.fixture_status,
            "fixturePhase": upstream_api.fixture_phase,
            "fixtureBlockReason": upstream_api.fixture_block_reason,
            "fixtureSourceFingerprint": upstream_api.fixture_source_fingerprint,
            "inputHashes": input_hashes,
            "sourceFingerprint": source_fingerprint,
            "newAuthor": clean_text(previous_manifest.get("newAuthor")) or getpass.getuser() if previous_manifest else getpass.getuser(),
            "preserveHistory": False,
            "cleanupArtifacts": bool(previous_manifest),
            "resetReason": "upstream_not_ready",
            "lastMessage": clean_text(previous_manifest.get("lastMessage")) if previous_manifest else "",
        }

    if same_inputs and previous_code_status == "tests_passed":
        return {
            "apiId": upstream_api.api_id,
            "apiCategory": upstream_api.api_category,
            "apiName": upstream_api.api_name,
            "upstreamStatus": upstream_api.status,
            "writerStatus": "tests_passed",
            "phase": normalize_phase(clean_text(previous_manifest.get("codePhase")), "validated"),
            "blockReason": clean_text(previous_manifest.get("codeBlockReason")) or None,
            "specBlockReason": upstream_api.block_reason,
            "fixtureStatus": upstream_api.fixture_status,
            "fixturePhase": upstream_api.fixture_phase,
            "fixtureBlockReason": upstream_api.fixture_block_reason,
            "fixtureSourceFingerprint": upstream_api.fixture_source_fingerprint,
            "inputHashes": input_hashes,
            "sourceFingerprint": source_fingerprint,
            "newAuthor": clean_text((upstream_api.api_spec_payload or {}).get("newAuthor")) or getpass.getuser(),
            "preserveHistory": True,
            "cleanupArtifacts": False,
            "resetReason": None,
            "lastMessage": clean_text(previous_manifest.get("lastMessage")),
        }

    if same_inputs and clean_text(previous_manifest.get("codeStatus")) in WRITER_STATUSES:
        if previous_code_status == "waiting_fixture":
            writer_status = "pending"
            phase = "pending"
            block_reason = None
            preserve_history = False
            cleanup_artifacts = False
            reset_reason = "fixture_ready"
            last_message = ""
        else:
            writer_status = clean_text(previous_manifest.get("codeStatus"))
            phase = normalize_phase(clean_text(previous_manifest.get("codePhase")), "pending")
            block_reason = clean_text(previous_manifest.get("codeBlockReason")) or None
            preserve_history = True
            cleanup_artifacts = False
            reset_reason = None
            last_message = clean_text(previous_manifest.get("lastMessage"))
    else:
        writer_status = "pending"
        phase = "pending"
        block_reason = None
        preserve_history = False
        cleanup_artifacts = bool(previous_manifest)
        reset_reason = "upstream_changed" if previous_manifest else "new_upstream_api"
        last_message = ""

    return {
        "apiId": upstream_api.api_id,
        "apiCategory": upstream_api.api_category,
        "apiName": upstream_api.api_name,
        "upstreamStatus": upstream_api.status,
        "writerStatus": writer_status,
        "phase": phase,
        "blockReason": block_reason,
        "specBlockReason": upstream_api.block_reason,
        "fixtureStatus": upstream_api.fixture_status,
        "fixturePhase": upstream_api.fixture_phase,
        "fixtureBlockReason": upstream_api.fixture_block_reason,
        "fixtureSourceFingerprint": upstream_api.fixture_source_fingerprint,
        "inputHashes": input_hashes,
        "sourceFingerprint": source_fingerprint,
        "newAuthor": clean_text((upstream_api.api_spec_payload or {}).get("newAuthor")) or getpass.getuser(),
        "preserveHistory": preserve_history,
        "cleanupArtifacts": cleanup_artifacts,
        "resetReason": reset_reason,
        "lastMessage": last_message,
    }


def cleanup_api_artifacts(context: ExecutionContext, api_id: str) -> None:
    remove_file(context.paths.change_plan_path(api_id))
    remove_file(context.paths.implementation_report_path(api_id))
    remove_file(context.paths.diagnosis_path(api_id))
    remove_file(context.paths.test_evidence_path(api_id))
    remove_file(code_contract_review_path(context, api_id))


def build_writer_checklist_payload(context: ExecutionContext, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "executionId": context.execution_id,
        "updatedAt": now_iso(),
        "items": [
            {
                "apiId": item["apiId"],
                "apiCategory": item["apiCategory"],
                "apiName": item["apiName"],
                "specStatus": item["upstreamStatus"],
                "specBlockReason": item.get("specBlockReason", item["blockReason"] if item["upstreamStatus"] != UPSTREAM_READY_STATUS else None),
                "specSourceFingerprint": item.get("sourceFingerprint"),
                "fixtureStatus": item.get("fixtureStatus"),
                "fixturePhase": item.get("fixturePhase"),
                "fixtureBlockReason": item.get("fixtureBlockReason"),
                "fixtureSourceFingerprint": item.get("fixtureSourceFingerprint"),
                "codeStatus": item["writerStatus"],
                "codePhase": item["phase"],
                "codeBlockReason": item["blockReason"],
            }
            for item in items
        ],
    }


def build_execution_state_payload(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    upstream_summary: dict[str, int],
    *,
    current_api_id: str | None,
    message: str,
    phase: str,
    status_override: str | None = None,
) -> dict[str, Any]:
    existing_payload = require_json_object("execution-state.json", context.paths.execution_state_path) if context.paths.execution_state_path.exists() else {}
    spec_status = clean_text(existing_payload.get("specStatus") or existing_payload.get("status")) or "waiting_spec"
    spec_updated_at = clean_text(existing_payload.get("specUpdatedAt") or existing_payload.get("updatedAt")) or None
    code_status = status_override or derive_execution_status(items)
    code_updated_at = now_iso()
    fixture_status = clean_text(existing_payload.get("fixtureStatus")) or derive_fixture_execution_status(items)
    fixture_phase = clean_text(existing_payload.get("fixturePhase")) or ""
    if fixture_status == "done" and fixture_phase in {"", "pending", "waiting_spec", "waiting_fixture"}:
        fixture_phase = "applied"
    elif fixture_status == "waiting_fixture" and fixture_phase in {"", "pending", "waiting_spec", "applied"}:
        fixture_phase = "pending"
    elif not fixture_phase:
        fixture_phase = fixture_status
    fixture_summary = existing_payload.get("fixtureSummary")
    if not isinstance(fixture_summary, dict):
        fixture_summary = summarize_fixture_status(items)
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "executionId": context.execution_id,
        "functionCode": context.execution_id,
        "status": aggregate_execution_status(spec_status, code_status),
        "phase": aggregate_execution_phase(spec_status, phase),
        "updatedAt": latest_timestamp(spec_updated_at, code_updated_at),
        "specStatus": spec_status,
        "specUpdatedAt": spec_updated_at,
        "specSummary": existing_payload.get("specSummary") or upstream_summary,
        "specDocxPath": existing_payload.get("specDocxPath"),
        "specLastMessage": existing_payload.get("specLastMessage"),
        "codeStatus": code_status,
        "codePhase": phase,
        "codeUpdatedAt": code_updated_at,
        "codeCurrentApiId": current_api_id,
        "codeSummary": summarize_writer_status(items),
        "codeProjectRoot": context.project_root.as_posix(),
        "codeSolutionPath": normalize_persisted_path(context.solution_path, project_root=context.project_root),
        "codeLastMessage": message,
        "fixtureStatus": fixture_status,
        "fixturePhase": fixture_phase,
        "fixtureUpdatedAt": existing_payload.get("fixtureUpdatedAt"),
        "fixtureCurrentApiId": existing_payload.get("fixtureCurrentApiId"),
        "fixtureSummary": fixture_summary,
        "fixtureLastMessage": existing_payload.get("fixtureLastMessage"),
        "artifacts": {
            "batchFile": normalize_persisted_path(context.batch_file, project_root=context.project_root),
            "checklist": normalize_persisted_path(context.paths.checklist_path, project_root=context.project_root),
            "specProgress": normalize_persisted_path(context.paths.root / "spec-progress.md", project_root=context.project_root),
            "codeProgress": normalize_persisted_path(context.paths.progress_path, project_root=context.project_root),
            "repoSnapshot": normalize_persisted_path(context.paths.snapshot_path, project_root=context.project_root),
        },
    }


def safe_previous_list(previous_manifest: dict[str, Any] | None, key: str, preserve_history: bool) -> list[Any]:
    if not preserve_history or not isinstance(previous_manifest, dict):
        return []
    value = previous_manifest.get(key)
    return list(value) if isinstance(value, list) else []


def safe_previous_text(previous_manifest: dict[str, Any] | None, key: str, preserve_history: bool) -> str | None:
    if not preserve_history or not isinstance(previous_manifest, dict):
        return None
    value = clean_text(previous_manifest.get(key))
    return value or None


def build_api_manifest_payload(
    context: ExecutionContext,
    item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    *,
    status: str | None = None,
    phase: str | None = None,
    block_reason: str | None = None,
    modified_files: list[str] | None = None,
    validation_checks: list[str] | None = None,
    validation_results: list[dict[str, Any]] | None = None,
    repo_drift_files: list[str] | None = None,
    last_message: str | None = None,
) -> dict[str, Any]:
    preserve_history = bool(item.get("preserveHistory"))
    api_id = item["apiId"]
    change_plan_path = context.paths.change_plan_path(api_id)
    implementation_report_path = context.paths.implementation_report_path(api_id)
    diagnosis_path = context.paths.diagnosis_path(api_id)
    upstream_payload = upstream_api.api_spec_payload or {}
    existing_payload = previous_manifest if isinstance(previous_manifest, dict) else {}
    fixture_artifacts = upstream_api.manifest_payload.get("fixtureArtifacts")
    if not isinstance(fixture_artifacts, dict):
        fixture_artifacts = existing_payload.get("fixtureArtifacts")
    if not isinstance(fixture_artifacts, dict):
        fixture_artifacts = {
            "dbFixtureReport": None,
            "tableChecks": None,
            "seedPlan": None,
            "seedExecuted": None,
            "seedManifest": None,
        }
    code_status = status or item["writerStatus"]
    code_phase = phase or item["phase"]
    spec_updated_at = clean_text(existing_payload.get("specUpdatedAt") or upstream_api.manifest_payload.get("specUpdatedAt") or upstream_api.manifest_payload.get("updatedAt")) or None
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "manifestType": "api",
        "executionId": context.execution_id,
        "apiId": api_id,
        "apiCategory": item["apiCategory"],
        "apiName": item["apiName"],
        "status": upstream_api.status if code_status == "waiting_spec" else code_status,
        "phase": code_phase or upstream_api.status,
        "updatedAt": latest_timestamp(spec_updated_at, now_iso()),
        "newAuthor": item["newAuthor"],
        "specStatus": upstream_api.status,
        "specUpdatedAt": spec_updated_at,
        "specBlockReason": upstream_api.block_reason,
        "specSourceFingerprint": item["sourceFingerprint"],
        "specSource": upstream_payload.get("source") or upstream_api.manifest_payload.get("specSource") or upstream_api.manifest_payload.get("source") or {},
        "specArtifacts": {
            "apiSpec": normalize_persisted_path(upstream_api.api_spec_path, project_root=context.project_root),
        },
        "fixtureStatus": upstream_api.manifest_payload.get("fixtureStatus") or item.get("fixtureStatus"),
        "fixturePhase": upstream_api.manifest_payload.get("fixturePhase") or item.get("fixturePhase"),
        "fixtureUpdatedAt": upstream_api.manifest_payload.get("fixtureUpdatedAt"),
        "fixtureBlockReason": upstream_api.manifest_payload.get("fixtureBlockReason") or item.get("fixtureBlockReason"),
        "fixtureSourceFingerprint": upstream_api.manifest_payload.get("fixtureSourceFingerprint") or item.get("fixtureSourceFingerprint"),
        "fixtureArtifacts": fixture_artifacts,
        "codeStatus": code_status,
        "codePhase": code_phase,
        "codeUpdatedAt": now_iso(),
        "codeBlockReason": block_reason if block_reason is not None else item["blockReason"],
        "codeProjectRoot": normalize_persisted_path(context.project_root, project_root=context.project_root),
        "codeSolutionPath": normalize_persisted_path(context.solution_path, project_root=context.project_root),
        "inputHashes": item["inputHashes"],
        "modifiedFiles": modified_files if modified_files is not None else safe_previous_list(previous_manifest, "modifiedFiles", preserve_history),
        "validationChecks": validation_checks if validation_checks is not None else safe_previous_list(previous_manifest, "validationChecks", preserve_history),
        "validationResults": validation_results if validation_results is not None else safe_previous_list(previous_manifest, "validationResults", preserve_history),
        "repoDriftFiles": repo_drift_files if repo_drift_files is not None else safe_previous_list(previous_manifest, "repoDriftFiles", preserve_history),
        "codeArtifacts": {
            "changePlan": normalize_persisted_path(change_plan_path, project_root=context.project_root) if change_plan_path.exists() else None,
            "implementationReport": normalize_persisted_path(implementation_report_path, project_root=context.project_root) if implementation_report_path.exists() else None,
            "diagnosisReport": normalize_persisted_path(diagnosis_path, project_root=context.project_root) if diagnosis_path.exists() else None,
        },
        "lastMessage": last_message if last_message is not None else safe_previous_text(previous_manifest, "lastMessage", preserve_history),
    }


def dump_queue_manifests(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    api_map: dict[str, UpstreamApiRecord],
    previous_manifest_map: dict[str, dict[str, Any]],
) -> None:
    for item in items:
        api_id = item["apiId"]
        if item.get("cleanupArtifacts"):
            cleanup_api_artifacts(context, api_id)
        dump_json(
            context.paths.manifest_path(api_id),
            build_api_manifest_payload(
                context,
                item,
                api_map[api_id],
                previous_manifest_map.get(api_id),
            ),
        )


def persist_execution_view(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    upstream_summary: dict[str, int],
    *,
    message: str,
    current_api_id: str | None,
    phase: str,
    status_override: str | None = None,
    append_message: bool,
) -> None:
    dump_json(context.paths.checklist_path, build_writer_checklist_payload(context, items))
    execution_payload = build_execution_state_payload(
        context,
        items,
        upstream_summary,
        current_api_id=current_api_id,
        message=message,
        phase=phase,
        status_override=status_override,
    )
    dump_json(context.paths.execution_state_path, execution_payload)
    update_chain_status(
        agent_root=context.agent_dir,
        function_code=context.execution_id,
        stage="code",
        status=execution_payload.get("codeStatus"),
        phase=execution_payload.get("codePhase"),
        message=execution_payload.get("codeLastMessage") or execution_payload.get("status"),
        project_root=context.project_root,
        artifacts={
            "solutionPath": normalize_persisted_path(context.solution_path, project_root=context.project_root),
            "executionState": normalize_persisted_path(context.paths.execution_state_path, project_root=context.agent_dir),
            "apiChecklist": normalize_persisted_path(context.paths.checklist_path, project_root=context.agent_dir),
            "codeProgress": normalize_persisted_path(context.paths.progress_path, project_root=context.agent_dir),
        },
    )
    if append_message:
        append_progress(context.paths.progress_path, message)


def tokenize_text(value: str) -> list[str]:
    if not value:
        return []
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    expanded = re.sub(r"[^0-9A-Za-z]+", " ", expanded).lower()
    return [token for token in expanded.split() if len(token) >= 3]


def list_csharp_files(project_root: Path, excluded_prefixes: list[str]) -> list[str]:
    files: list[str] = []
    for path in sorted(project_root.rglob("*.cs")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(project_root).as_posix()
        if should_exclude_relative_path(relative_path, excluded_prefixes):
            continue
        files.append(relative_path)
    return files


def build_candidate_keywords(item: dict[str, Any], normalized_model: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    keywords.append(item["apiCategory"].lower())
    keywords.append(item["apiName"].lower())
    keywords.append(item["apiId"].split(".")[-1].lower())
    for line in normalized_model.get("backendApis") or []:
        keywords.extend(tokenize_text(line))
    for dependency in normalized_model.get("runtimeDependencies") or []:
        keywords.extend(tokenize_text(clean_text(dependency.get("id"))))
        keywords.extend(tokenize_text(clean_text(dependency.get("description"))))
    for mapping in normalized_model.get("fieldMappings") or []:
        keywords.extend(tokenize_text(clean_text(mapping.get("target"))))
        keywords.extend(tokenize_text(clean_text(mapping.get("source"))))
    seen: set[str] = set()
    ordered: list[str] = []
    for keyword in keywords:
        if keyword and keyword not in seen:
            ordered.append(keyword)
            seen.add(keyword)
    return ordered


def score_source_candidate(relative_path: str, item: dict[str, Any], normalized_model: dict[str, Any]) -> int:
    lowered = relative_path.lower()
    stem = Path(relative_path).stem.lower()
    api_category = item["apiCategory"].lower()
    api_name = item["apiName"].lower()
    last_segment = item["apiId"].split(".")[-1].lower()
    score = 0
    if stem == f"{api_category}service":
        score += 260
    if api_category in stem and "service" in stem:
        score += 160
    if api_name == stem:
        score += 200
    if api_name in lowered:
        score += 120
    if last_segment in lowered:
        score += 60
    if "service" in stem:
        score += 25
    for keyword in build_candidate_keywords(item, normalized_model):
        if keyword in lowered:
            score += 12
    return score


def discover_source_candidates(project_root: Path, excluded_prefixes: list[str], item: dict[str, Any], normalized_model: dict[str, Any]) -> list[str]:
    csharp_files = list_csharp_files(project_root, excluded_prefixes)
    if not csharp_files:
        return []
    return sorted(
        csharp_files,
        key=lambda relative_path: (score_source_candidate(relative_path, item, normalized_model), -len(relative_path)),
        reverse=True,
    )


def pick_target_file(candidates: list[str]) -> str | None:
    return candidates[0] if candidates else None


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    for index in range(open_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("No matching closing brace found.")


def sanitize_identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]", "", value or "")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def to_pascal_case(value: str, fallback: str = "Generated") -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value or "")
    if not parts:
        return fallback
    rendered: list[str] = []
    for part in parts:
        if len(part) > 1 and any(char.isupper() for char in part[1:]):
            rendered.append(part[0].upper() + part[1:])
        else:
            rendered.append(part.capitalize())
    return "".join(rendered) or fallback


def singularize_identifier(value: str) -> str:
    if value.endswith("ies") and len(value) > 3:
        return value[:-3] + "y"
    if value.endswith("ses") and len(value) > 3:
        return value[:-2]
    if value.endswith("s") and not value.endswith("ss") and len(value) > 1:
        return value[:-1]
    return value


def relative_path_from_project(path: Path, project_root: Path) -> str:
    return normalize_persisted_path(path, project_root=project_root) or path.name


def ensure_relative_persisted_path(value: object, *, label: str) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    path = Path(text)
    if path.is_absolute() or re.match(r"^[A-Za-z]:[\\/]", text):
        raise SkillError(f"{label} must be relative to project root: {text}", status="blocked", diagnosis_type="review_constraint_gap")
    return path.as_posix()


def read_xml_property(path: Path, property_name: str) -> str | None:
    if not path.exists():
        return None
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except ET.ParseError:
        return None
    for element in root.iter():
        if element.tag.split("}")[-1] != property_name:
            continue
        text = clean_text(element.text)
        if text:
            return text
    return None


def infer_repo_root(project_root: Path, solution_path: Path) -> Path:
    primary = solution_path.parent.resolve()
    if (primary / "API" / "EnterpriseAPI" / "EnterpriseAPI").exists():
        return primary
    for candidate in sorted(project_root.rglob("EnterpriseAPI.csproj")):
        resolved = candidate.resolve()
        if resolved.parts[-4:-1] == ("API", "EnterpriseAPI", "EnterpriseAPI"):
            return resolved.parents[3]
    return primary


def detect_framework_profile(context: ExecutionContext) -> FrameworkProfile:
    repo_root = infer_repo_root(context.project_root, context.solution_path)
    api_project_path = repo_root / "API" / "EnterpriseAPI" / "EnterpriseAPI" / "EnterpriseAPI.csproj"
    business_interface_project_path = (
        repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness.Interface" / "EnterpriseApiBusiness.Interface.csproj"
    )
    business_project_path = repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "EnterpriseApiBusiness.csproj"
    entity_project_path = repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiEntity" / "EnterpriseApiEntity.csproj"
    unit_test_project_path = repo_root / "Test" / "UnitTesting" / "EnterpriseAPI" / "EnterpriseApiUnit" / "EnterpriseAPIUnit.csproj"
    integration_test_project_path = (
        repo_root / "Test" / "IntegrationTesting" / "EnterpriseAPI" / "EnterpriseApiIntegration" / "EnterpriseAPIIntegration.csproj"
    )

    required_paths = {
        "API/EnterpriseAPI/EnterpriseAPI/EnterpriseAPI.csproj": api_project_path,
        "BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness.Interface/EnterpriseApiBusiness.Interface.csproj": business_interface_project_path,
        "BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/EnterpriseApiBusiness.csproj": business_project_path,
        "BusinessLogicLayout/EnterpriseApi/EnterpriseApiEntity/EnterpriseApiEntity.csproj": entity_project_path,
        "Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/EnterpriseAPIUnit.csproj": unit_test_project_path,
        "Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/EnterpriseAPIIntegration.csproj": integration_test_project_path,
    }
    missing_slots = [slot for slot, path in required_paths.items() if not path.exists()]
    if missing_slots:
        raise SkillError(
            "EnterpriseAPI framework slots are missing: " + ", ".join(missing_slots),
            status="blocked",
            diagnosis_type="framework_gap",
        )

    root_namespace = read_xml_property(api_project_path, "RootNamespace") or f"{context.solution_path.stem}.API.EnterpriseAPI.EnterpriseAPI"
    api_namespace_suffix = ".API.EnterpriseAPI.EnterpriseAPI"
    if root_namespace.endswith(api_namespace_suffix):
        namespace_root = root_namespace[: -len(api_namespace_suffix)]
    else:
        namespace_root = read_xml_property(api_project_path, "AssemblyName") or context.solution_path.stem

    program_extensions_path = repo_root / "Libray" / "Common" / "CommonStatic" / "ProgramExtensions.cs"
    registration_strategy = "manual_registration_review"
    if program_extensions_path.exists() and "AddBusinessScoped" in program_extensions_path.read_text(encoding="utf-8", errors="replace"):
        registration_strategy = "existing_add_business_scoped"

    return FrameworkProfile(
        profile_name=ENTERPRISE_FRAMEWORK_PROFILE,
        repo_root=repo_root,
        api_project_path=api_project_path,
        business_interface_project_path=business_interface_project_path,
        business_project_path=business_project_path,
        entity_project_path=entity_project_path,
        unit_test_project_path=unit_test_project_path,
        integration_test_project_path=integration_test_project_path,
        controller_dir=api_project_path.parent / "Controllers",
        business_interface_dir=business_interface_project_path.parent,
        business_dir=business_project_path.parent,
        entity_dir=entity_project_path.parent,
        unit_test_dir=unit_test_project_path.parent,
        integration_test_dir=integration_test_project_path.parent,
        root_namespace=namespace_root,
        registration_strategy=registration_strategy,
    )


def requires_authenticated_identity_context(normalized_model: dict[str, Any]) -> bool:
    runtime_dependencies = [entry for entry in list(normalized_model.get("runtimeDependencies") or []) if isinstance(entry, dict)]
    dependency_hints = [entry for entry in list(normalized_model.get("dependencyHints") or []) if isinstance(entry, dict)]
    backend_apis = [clean_text(entry) for entry in list(normalized_model.get("backendApis") or []) if clean_text(entry)]
    reference_hints = [entry for entry in list(normalized_model.get("referenceHints") or []) if isinstance(entry, dict)]

    dependency_text = "\n".join(
        " ".join(
            part
            for part in (
                clean_text(entry.get("id")),
                clean_text(entry.get("type")),
                clean_text(entry.get("description")),
            )
            if part
        )
        for entry in runtime_dependencies
    ).casefold()
    hint_text = "\n".join(
        " ".join(
            part
            for part in (
                clean_text(entry.get("dependencyType")),
                " ".join(clean_text(value) for value in list(entry.get("preferredAbstractions") or []) if clean_text(value)),
                clean_text(entry.get("purpose")),
            )
            if part
        )
        for entry in dependency_hints
    ).casefold()
    backend_text = "\n".join(backend_apis).casefold()
    reference_text = "\n".join(
        f"{clean_text(entry.get('title'))}\n{clean_text(entry.get('reason'))}\n{clean_text(entry.get('matchKey'))}"
        for entry in reference_hints
    ).casefold()

    current_context_required = any(
        token in dependency_text or token in hint_text
        for token in ("current_customer_context", "current request context", "custid", "keyid", "runtime context")
    )
    redis_session_required = "redis" in backend_text or "jwt_redis" in reference_text or "member-hash" in reference_text or "session" in reference_text
    return current_context_required and redis_session_required


def enterprise_repo_has_identity_wiring(profile: FrameworkProfile) -> bool:
    candidate_files = [
        profile.api_project_path.parent / "Program.cs",
        profile.repo_root / "Libray" / "Common" / "CommonStatic" / "ProgramExtensions.cs",
    ]
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in candidate_files
        if path.exists()
    ).casefold()
    has_auth_pipeline = "useauthentication" in combined
    has_auth_registration = "addauthentication" in combined or "addjwtbearer" in combined

    identity_support_roots = [
        profile.api_project_path.parent,
        profile.business_dir,
        profile.business_interface_dir,
        profile.entity_dir,
    ]
    has_identity_accessor = False
    for root in identity_support_roots:
        for path in root.rglob("*.cs"):
            text = path.read_text(encoding="utf-8", errors="replace").casefold()
            if any(token in text for token in ("auth_sn", "ihttpcontextaccessor", "currentruntimecontextaccessor", "requestcontextaccessor", "usercontextaccessor")):
                has_identity_accessor = True
                break
        if has_identity_accessor:
            break

    return has_auth_pipeline and has_auth_registration and has_identity_accessor


def ensure_identity_contract_supported(normalized_model: dict[str, Any], framework_profile: FrameworkProfile) -> None:
    if not requires_authenticated_identity_context(normalized_model):
        return
    if enterprise_repo_has_identity_wiring(framework_profile):
        return
    raise SkillError(
        "EnterpriseAPI 目前缺少已接線的認證 / Session 身分上下文，無法安全解析 access_token.auth_sn -> Member Hash -> CustId。"
        " 依技能規則，禁止以 Header 候選或臨時 Redis key 腦補目前使用者來源。",
        status="blocked",
        diagnosis_type="framework_gap",
    )


def build_framework_plan(
    context: ExecutionContext,
    item: dict[str, Any],
    normalized_model: dict[str, Any],
) -> tuple[FrameworkProfile, FrameworkPlan]:
    profile = detect_framework_profile(context)
    controller_module_name = to_pascal_case(item["apiCategory"], fallback="Common")
    module_name = controller_module_name
    method_stem = sanitize_identifier(clean_text(item["apiName"]), "GeneratedApi")
    target_method = method_stem if method_stem.endswith("Async") else f"{method_stem}Async"
    request_type = f"{method_stem}Request" if normalized_model.get("requestFields") else None
    response_type = f"{method_stem}Response"

    controller_path = profile.controller_dir / f"{controller_module_name}Controller.cs"
    if controller_path.exists():
        controller_text = read_text_with_fallback(controller_path)
        service_match = re.search(r"\bI([A-Z][A-Za-z0-9_]*)Service\b", controller_text)
        if service_match:
            candidate_module_name = service_match.group(1)
            candidate_interface_path = profile.business_interface_dir / f"I{candidate_module_name}Service.cs"
            candidate_service_dir = profile.business_dir / candidate_module_name
            if candidate_interface_path.exists() or candidate_service_dir.exists():
                module_name = candidate_module_name

    interface_path = profile.business_interface_dir / f"I{module_name}Service.cs"
    service_module_dir = profile.business_dir / module_name
    service_root_path = service_module_dir / f"{module_name}Service.cs"
    service_method_path = service_module_dir / f"{module_name}Service.{method_stem}.cs"
    entity_path = profile.entity_dir / module_name / f"{method_stem}Info.cs"
    unit_controller_test_path = profile.unit_test_dir / f"{controller_module_name}ControllerTest.cs"
    controller_named_service_test_path = profile.unit_test_dir / f"{controller_module_name}ServiceTests.cs"
    unit_service_test_path = (
        controller_named_service_test_path
        if controller_module_name != module_name and controller_named_service_test_path.exists()
        else profile.unit_test_dir / f"{module_name}ServiceTests.cs"
    )
    integration_test_path = profile.integration_test_dir / f"{controller_module_name}ControllerTests.cs"

    if service_root_path.exists():
        service_text = service_root_path.read_text(encoding="utf-8", errors="replace")
        uses_partial_service = bool(re.search(rf"\bpartial\s+class\s+{re.escape(module_name)}Service\b", service_text))
        creation_mode = "extend_partial" if uses_partial_service else "reuse"
        service_files = (
            relative_path_from_project(service_root_path, context.project_root),
            relative_path_from_project(service_method_path, context.project_root),
        ) if uses_partial_service else (relative_path_from_project(service_root_path, context.project_root),)
        target_file = service_files[-1]
    else:
        creation_mode = "create_module"
        service_files = (
            relative_path_from_project(service_root_path, context.project_root),
            relative_path_from_project(service_method_path, context.project_root),
        )
        target_file = service_files[-1]

    controller_file = relative_path_from_project(controller_path, context.project_root)
    interface_file = relative_path_from_project(interface_path, context.project_root)
    entity_files = (relative_path_from_project(entity_path, context.project_root),)
    unit_test_files = (
        relative_path_from_project(unit_controller_test_path, context.project_root),
        relative_path_from_project(unit_service_test_path, context.project_root),
    )
    integration_test_files = (relative_path_from_project(integration_test_path, context.project_root),)

    source_candidates = (
        controller_file,
        interface_file,
        *service_files,
        *entity_files,
        *unit_test_files,
        *integration_test_files,
    )
    return profile, FrameworkPlan(
        framework_profile=profile.profile_name,
        module_name=module_name,
        controller_file=controller_file,
        interface_file=interface_file,
        service_files=service_files,
        entity_files=entity_files,
        unit_test_files=unit_test_files,
        integration_test_files=integration_test_files,
        creation_mode=creation_mode,
        target_file=target_file,
        target_method=target_method,
        request_type=request_type,
        response_type=response_type,
        source_candidates=source_candidates,
        registration_strategy=profile.registration_strategy,
    )


def analyze_target_file(target_path: Path, method_name: str) -> dict[str, Any]:
    text = target_path.read_text(encoding="utf-8")
    newline = detect_newline(text)
    method_pattern = re.compile(
        rf"(?P<indent>^[ \t]*)(?P<signature>(?:public|protected|internal|private)\s+"
        rf"(?:(?:static|virtual|override|sealed|new|async|partial|extern)\s+)*"
        rf"(?P<return>[A-Za-z0-9_<>\[\],?.]+)\s+{re.escape(method_name)}\s*\([^\)]*\))\s*(?P<brace>\{{)",
        re.M,
    )
    method_match = method_pattern.search(text)
    if method_match:
        brace_start = method_match.start("brace")
        brace_end = find_matching_brace(text, brace_start)
        return {
            "action": "replace_existing_method",
            "text": text,
            "newline": newline,
            "indent": method_match.group("indent"),
            "returnType": method_match.group("return"),
            "signature": method_match.group("signature"),
            "methodName": method_name,
            "braceStart": brace_start,
            "braceEnd": brace_end,
        }

    class_pattern = re.compile(
        r"(?P<indent>^[ \t]*)(?:(?:public|protected|internal|private)\s+)?"
        r"(?:(?:abstract|sealed|partial)\s+)*class\s+(?P<name>[A-Za-z0-9_]+)[^{]*\{",
        re.M,
    )
    class_match = class_pattern.search(text)
    if not class_match:
        raise ValueError(f"无法在 {target_path.as_posix()} 中定位 class 定义。")
    class_open = class_match.end() - 1
    class_close = find_matching_brace(text, class_open)
    return {
        "action": "append_method_stub",
        "text": text,
        "newline": newline,
        "classIndent": class_match.group("indent"),
        "className": class_match.group("name"),
        "insertAt": class_close,
        "methodName": method_name,
    }


def build_default_expression(return_type: str, api_id: str) -> str:
    trimmed = return_type.strip()
    lowered = trimmed.lower()
    if lowered in {"string", "system.string"}:
        return "apiId"
    if lowered in {"bool", "boolean", "system.boolean"}:
        return "true"
    if lowered in {"byte", "short", "int", "long", "sbyte", "ushort", "uint", "ulong", "nint", "nuint"}:
        return "0"
    if lowered in {"float", "system.single"}:
        return "0f"
    if lowered in {"double", "system.double"}:
        return "0d"
    if lowered in {"decimal", "system.decimal"}:
        return "0m"
    if lowered in {"char", "system.char"}:
        return "'\\0'"
    if lowered in {"object", "dynamic", "system.object"}:
        return "new object()"
    if trimmed.endswith("[]"):
        return f"System.Array.Empty<{trimmed[:-2]}>()"

    generic_match = re.match(r"(?P<type>[A-Za-z0-9_.]+)<(?P<inner>.+)>$", trimmed)
    if generic_match:
        outer = generic_match.group("type").split(".")[-1]
        inner = generic_match.group("inner")
        if outer in {"Task", "ValueTask"}:
            return f"System.Threading.Tasks.Task.FromResult({build_default_expression(inner, api_id)})"
        if outer in {"IEnumerable", "IReadOnlyList", "IReadOnlyCollection", "ICollection", "IList", "List"}:
            return f"new System.Collections.Generic.List<{inner}>()"
    if lowered in {"task", "system.threading.tasks.task", "valuetask"}:
        return "System.Threading.Tasks.Task.CompletedTask"
    return "default!"


def build_return_statement(return_type: str, api_id: str) -> str | None:
    trimmed = return_type.strip()
    if trimmed.lower() == "void":
        return None
    return f"return {build_default_expression(trimmed, api_id)};"


def summarize_field_paths(fields: list[dict[str, Any]], limit: int = 8) -> str:
    if not fields:
        return "none"
    paths = [field["path"] for field in fields]
    if len(paths) <= limit:
        return ", ".join(paths)
    return f"{', '.join(paths[:limit])}, ... (+{len(paths) - limit} more)"


def summarize_runtime_dependencies(runtime_dependencies: list[dict[str, Any]], limit: int = 4) -> str:
    if not runtime_dependencies:
        return "none"
    rendered: list[str] = []
    for dependency in runtime_dependencies[:limit]:
        identity = clean_text(dependency.get("id")) or clean_text(dependency.get("type")) or "dependency"
        description = clean_text(dependency.get("description"))
        rendered.append(f"{identity}: {description}" if description else identity)
    if len(runtime_dependencies) > limit:
        rendered.append(f"... (+{len(runtime_dependencies) - limit} more)")
    return " | ".join(rendered)


def summarize_business_steps(steps: list[dict[str, Any]], limit: int = 4) -> str:
    if not steps:
        return "none"
    rendered: list[str] = []
    for step in steps[:limit]:
        index_text = clean_text(step.get("step"))
        title = clean_text(step.get("title")) or clean_text(step.get("details")) or "step"
        rendered.append(f"{index_text}. {title}" if index_text else title)
    if len(steps) > limit:
        rendered.append(f"... (+{len(steps) - limit} more)")
    return " | ".join(rendered)


def summarize_reference_hints(reference_hints: list[dict[str, Any]], limit: int = 3) -> str:
    if not reference_hints:
        return "none"
    titles = [clean_text(hint.get("title")) for hint in reference_hints[:limit] if clean_text(hint.get("title"))]
    if len(reference_hints) > limit:
        titles.append(f"... (+{len(reference_hints) - limit} more)")
    return ", ".join(titles) if titles else "none"


def summarize_query_contracts(query_contracts: list[dict[str, Any]], limit: int = 3) -> str:
    if not query_contracts:
        return "none"
    rendered = [clean_text(contract.get("purpose")) or clean_text(contract.get("contractId")) for contract in query_contracts[:limit]]
    if len(query_contracts) > limit:
        rendered.append(f"... (+{len(query_contracts) - limit} more)")
    return ", ".join(item for item in rendered if item) or "none"


def summarize_mapping_rules(mapping_rules: list[dict[str, Any]], limit: int = 4) -> str:
    if not mapping_rules:
        return "none"
    rendered: list[str] = []
    for rule in mapping_rules[:limit]:
        source = clean_text(rule.get("sourceField")) or "source"
        target = clean_text(rule.get("targetField")) or "target"
        mapping_type = clean_text(rule.get("mappingType")) or "mapping"
        rendered.append(f"{mapping_type}:{source}->{target}")
    if len(mapping_rules) > limit:
        rendered.append(f"... (+{len(mapping_rules) - limit} more)")
    return ", ".join(rendered) or "none"


def summarize_legacy_evidence(legacy_evidence: list[dict[str, Any]], limit: int = 3) -> str:
    if not legacy_evidence:
        return "none"
    rendered = [clean_text(entry.get("summary")) or clean_text(entry.get("evidenceId")) for entry in legacy_evidence[:limit]]
    if len(legacy_evidence) > limit:
        rendered.append(f"... (+{len(legacy_evidence) - limit} more)")
    return ", ".join(item for item in rendered if item) or "none"


def summarize_constraints(constraints: list[dict[str, Any]], limit: int = 3) -> str:
    if not constraints:
        return "none"
    rendered = [clean_text(entry.get("rule")) for entry in constraints[:limit] if clean_text(entry.get("rule"))]
    if len(constraints) > limit:
        rendered.append(f"... (+{len(constraints) - limit} more)")
    return ", ".join(rendered) if rendered else "none"


def extract_text_element_limit(text: str) -> int | None:
    match = re.search(r"最多\s*(\d+)\s*(?:個)?(?:字元|字符|字|位)", clean_text(text))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def infer_request_validation_candidates(normalized_model: dict[str, Any]) -> list[dict[str, Any]]:
    request_fields = [entry for entry in list(normalized_model.get("requestFields") or []) if isinstance(entry, dict)]
    business_steps = [entry for entry in list(normalized_model.get("businessSteps") or []) if isinstance(entry, dict)]
    business_text = "\n".join(
        clean_text(step.get("title")) + "\n" + clean_text(step.get("details"))
        for step in business_steps
    )
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for field in request_fields:
        field_path = clean_text(field.get("path"))
        if not field_path:
            continue
        if bool(field.get("required")) and (field_path, "required") not in seen:
            candidates.append({"field": field_path, "validationType": "required"})
            seen.add((field_path, "required"))
        notes_text = "\n".join(
            part
            for part in [
                clean_text(field.get("description")),
                clean_text(field.get("notes")),
                business_text,
            ]
            if part
        )
        text_limit = extract_text_element_limit(notes_text)
        if text_limit is not None and (field_path, "text_element_max_length") not in seen:
            candidates.append(
                {
                    "field": field_path,
                    "validationType": "text_element_max_length",
                    "maxTextElements": text_limit,
                }
            )
            seen.add((field_path, "text_element_max_length"))
    return candidates


def resolve_request_validation_plan(normalized_model: dict[str, Any]) -> dict[str, Any]:
    request_fields = [entry for entry in list(normalized_model.get("requestFields") or []) if isinstance(entry, dict)]
    constraints = [entry for entry in list(normalized_model.get("constraints") or []) if isinstance(entry, dict)]
    if not request_fields:
        return {
            "requestValidationPlan": [],
            "dtoAttributeRules": [],
            "customValidationAttributesNeeded": [],
            "validationResponseMappingMode": "not_applicable",
            "serviceValidationsRetained": [],
            "validationInfrastructureGap": [],
        }

    structured_rules = [
        entry
        for entry in constraints
        if clean_text(entry.get("constraintType")) == "request_field_validation"
    ]
    rule_index = {
        (clean_text(entry.get("field")), clean_text(entry.get("validationType"))): entry
        for entry in structured_rules
        if clean_text(entry.get("field")) and clean_text(entry.get("validationType"))
    }
    inferred_candidates = infer_request_validation_candidates(normalized_model)
    validation_gaps: list[str] = []
    plan_entries: list[dict[str, Any]] = []

    for candidate in inferred_candidates:
        key = (clean_text(candidate.get("field")), clean_text(candidate.get("validationType")))
        matched_rule = rule_index.get(key)
        if matched_rule is None:
            validation_gaps.append(f"missing structured validation handoff for {key[0]}::{key[1]}")
            continue
        missing_keys = [
            name
            for name in ("validationLayer", "expectedCode", "expectedMessage", "customValidationAttributeNeeded")
            if matched_rule.get(name) in (None, "")
        ]
        if missing_keys:
            validation_gaps.append(
                f"incomplete structured validation handoff for {key[0]}::{key[1]} missing {', '.join(missing_keys)}"
            )
            continue
        plan_entry = {
            "field": key[0],
            "validationType": key[1],
            "validationLayer": clean_text(matched_rule.get("validationLayer")),
            "expectedCode": clean_text(matched_rule.get("expectedCode")),
            "expectedMessage": clean_text(matched_rule.get("expectedMessage")),
            "customValidationAttributeNeeded": bool(matched_rule.get("customValidationAttributeNeeded")),
        }
        if matched_rule.get("maxTextElements") is not None:
            plan_entry["maxTextElements"] = matched_rule.get("maxTextElements")
        plan_entries.append(plan_entry)

    if validation_gaps:
        raise SkillError(
            "Request validation handoff is incomplete: " + "; ".join(validation_gaps),
            status="blocked",
            diagnosis_type="spec_handoff_gap",
        )

    dto_attribute_rules = [entry for entry in plan_entries if entry["validationLayer"] == "dto_attribute"]
    service_validations_retained = [entry for entry in plan_entries if entry["validationLayer"] == "service_business"]
    custom_validation_attributes_needed = [
        {
            "field": entry["field"],
            "validationType": entry["validationType"],
            "maxTextElements": entry.get("maxTextElements"),
        }
        for entry in plan_entries
        if entry.get("customValidationAttributeNeeded")
    ]
    validation_infrastructure_gap: list[dict[str, Any]] = []
    if dto_attribute_rules:
        validation_infrastructure_gap.append(
            {
                "topic": "validation_response_mapping",
                "requiredCapability": "attribute_validation_to_spec_transaction_result",
                "mode": "shared_commonstatic",
            }
        )

    return {
        "requestValidationPlan": plan_entries,
        "dtoAttributeRules": dto_attribute_rules,
        "customValidationAttributesNeeded": custom_validation_attributes_needed,
        "validationResponseMappingMode": "spec_code_message" if dto_attribute_rules else "not_applicable",
        "serviceValidationsRetained": service_validations_retained,
        "validationInfrastructureGap": validation_infrastructure_gap,
    }


def get_payload_object(example: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        value = example.get(key)
        if isinstance(value, dict):
            return value
    return None


def build_test_scenario_plan(mock_examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scenario_plan: list[dict[str, Any]] = []
    for index, example in enumerate(mock_examples, start=1):
        if not isinstance(example, dict):
            continue
        scenario = clean_text(example.get("scenario")) or f"example-{index}"
        request_payload = get_payload_object(example, "requestPayload", "request", "requestExample")
        response_payload = get_payload_object(example, "responsePayload", "response", "responseExample")
        expected_code = ""
        expected_message = ""
        expected_is_success: bool | None = None
        if response_payload is not None:
            expected_code = clean_text(response_payload.get("responseCode") or response_payload.get("code"))
            expected_message = clean_text(response_payload.get("responseMessage") or response_payload.get("message"))
            if isinstance(response_payload.get("isSuccess"), bool):
                expected_is_success = bool(response_payload.get("isSuccess"))

        scenario_plan.append(
            {
                "source": "mockExamples",
                "sourceIndex": index,
                "scenario": scenario,
                "requestPayload": request_payload if request_payload is not None else {},
                "expectedResponsePayload": response_payload if response_payload is not None else {},
                "expectedResponseCode": expected_code,
                "expectedResponseMessage": expected_message,
                "expectedIsSuccess": expected_is_success,
                "coverageTargets": ["unit_test", "integration_test"],
                "preserveScenarioName": True,
            }
        )
    return scenario_plan


def summarize_test_scenarios(scenarios: list[dict[str, Any]], *, limit: int = 6) -> str:
    names = [clean_text(entry.get("scenario")) for entry in scenarios if isinstance(entry, dict) and clean_text(entry.get("scenario"))]
    if not names:
        return "none"
    visible = names[:limit]
    if len(names) > limit:
        visible.append(f"+{len(names) - limit} more")
    return ", ".join(visible)


def resolve_logic_contract(normalized_model: dict[str, Any]) -> dict[str, Any]:
    query_contracts = [entry for entry in list(normalized_model.get("queryContracts") or []) if isinstance(entry, dict)]
    mapping_rules = [entry for entry in list(normalized_model.get("mappingRules") or []) if isinstance(entry, dict)]
    dependency_hints = [entry for entry in list(normalized_model.get("dependencyHints") or []) if isinstance(entry, dict)]
    legacy_evidence = [entry for entry in list(normalized_model.get("legacyEvidence") or []) if isinstance(entry, dict)]
    constraints = [entry for entry in list(normalized_model.get("constraints") or []) if isinstance(entry, dict)]
    unresolved_logic = [entry for entry in list(normalized_model.get("unresolvedLogic") or []) if isinstance(entry, dict)]
    mock_examples = [entry for entry in list(normalized_model.get("mockExamples") or []) if isinstance(entry, dict)]
    test_scenario_plan = build_test_scenario_plan(mock_examples)
    blocking_unresolved = [entry for entry in unresolved_logic if bool(entry.get("blocking"))]
    logic_sources_used = [clean_text(normalized_model.get("handoffSource")) or "unknown"]
    if query_contracts:
        logic_sources_used.append("queryContracts")
    if mapping_rules:
        logic_sources_used.append("mappingRules")
    if dependency_hints:
        logic_sources_used.append("dependencyHints")
    if legacy_evidence:
        logic_sources_used.append("legacyEvidence")
    if constraints:
        logic_sources_used.append("constraints")
    if test_scenario_plan:
        logic_sources_used.append("mockExamples")
    logic_sources_used = list(dict.fromkeys(source for source in logic_sources_used if source))

    sql_like_dependency = any(
        "sql" in clean_text(entry.get("dependencyType")).casefold()
        or "sqlqueryexecutor" in " ".join(entry.get("preferredAbstractions") or []).casefold()
        for entry in dependency_hints
    )
    if blocking_unresolved:
        topics = ", ".join(clean_text(entry.get("topic")) or "unresolved" for entry in blocking_unresolved)
        raise SkillError(
            f"Business logic handoff is unresolved: {topics}",
            status="blocked",
            diagnosis_type="spec_handoff_gap",
        )
    if sql_like_dependency and not query_contracts:
        raise SkillError(
            "Business logic handoff is missing required query contracts for SQL-oriented dependencies.",
            status="blocked",
            diagnosis_type="spec_handoff_gap",
        )
    if not query_contracts and not mapping_rules and not legacy_evidence:
        raise SkillError(
            "Business logic handoff is missing structured query, mapping, or legacy evidence.",
            status="blocked",
            diagnosis_type="spec_handoff_gap",
        )
    validation_plan = resolve_request_validation_plan(normalized_model)

    return {
        "logicSourcesUsed": logic_sources_used,
        "queryContractsSelected": query_contracts,
        "mappingRulesSelected": mapping_rules,
        "dependencyHintsSelected": dependency_hints,
        "legacyEvidenceUsed": legacy_evidence,
        "constraintsApplied": constraints,
        "unresolvedLogic": unresolved_logic,
        "testScenarioPlan": test_scenario_plan,
        "testScenarioSource": "mockExamples" if test_scenario_plan else "none",
        "testScenarioCoverageRequired": bool(test_scenario_plan),
        "requestValidationPlan": validation_plan.get("requestValidationPlan") or [],
        "dtoAttributeRules": validation_plan.get("dtoAttributeRules") or [],
        "customValidationAttributesNeeded": validation_plan.get("customValidationAttributesNeeded") or [],
        "validationResponseMappingMode": validation_plan.get("validationResponseMappingMode") or "not_applicable",
        "serviceValidationsRetained": validation_plan.get("serviceValidationsRetained") or [],
        "validationInfrastructureGap": validation_plan.get("validationInfrastructureGap") or [],
    }

def build_change_plan_payload(
    context: ExecutionContext,
    item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    normalized_model: dict[str, Any],
    *,
    framework_profile: FrameworkProfile,
    framework_plan: FrameworkPlan,
    validation_commands: list[str],
    repo_drift_files: list[str],
    before_hashes: dict[str, str | None],
    resumed_from_phase: str | None,
    logic_resolution: dict[str, Any],
    review_resolution: dict[str, Any],
) -> dict[str, Any]:
    code_target_files = collect_code_target_files(framework_plan)
    unit_test_target_files, integration_test_target_files, test_target_files = collect_test_handoff_files(framework_plan)
    dev_guideline_resolution = select_dev_guidelines(
        skill_root=Path(__file__).resolve().parents[1],
        rules_root=resolve_context_rules_root(context.agent_dir),
        item=item,
        normalized_model=normalized_model,
        framework_plan=framework_plan,
    )
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "skillName": SKILL_NAME,
        "manifestType": "change-plan",
        "status": "planned",
        "updatedAt": now_iso(),
        "executionId": context.execution_id,
        "apiId": item["apiId"],
        "projectRoot": normalize_persisted_path(context.project_root, project_root=context.project_root),
        "solutionPath": normalize_persisted_path(context.solution_path, project_root=context.project_root),
        "upstream": {
            "manifest": normalize_persisted_path(upstream_api.manifest_path, project_root=context.project_root),
            "apiSpec": normalize_persisted_path(upstream_api.api_spec_path, project_root=context.project_root),
            "sourceFingerprint": item["sourceFingerprint"],
            "source": normalized_model.get("source") or {},
        },
        "sourceCandidates": list(framework_plan.source_candidates),
        "repoDriftDetected": bool(repo_drift_files),
        "repoDriftFiles": repo_drift_files,
        "beforeHashes": before_hashes,
        "analysis": {
            "frameworkProfile": framework_plan.framework_profile,
            "guidelineAuthority": resolve_guideline_authority(context.agent_dir),
            "repoRoot": relative_path_from_project(framework_profile.repo_root, context.project_root),
            "moduleName": framework_plan.module_name,
            "controllerFile": framework_plan.controller_file,
            "interfaceFile": framework_plan.interface_file,
            "serviceFiles": list(framework_plan.service_files),
            "entityFiles": list(framework_plan.entity_files),
            "codeTargetFiles": code_target_files,
            "unitTestTargetFiles": unit_test_target_files,
            "integrationTestTargetFiles": integration_test_target_files,
            "testTargetFiles": test_target_files,
            "testCodeHandoff": {
                "ownerStep": "05 docx-unittest-report",
                "writerPolicy": "handoff_only",
                "unitTestTargetFiles": unit_test_target_files,
                "integrationTestTargetFiles": integration_test_target_files,
                "note": "Step 04 records test targets and scenarios only; UnitTest, IntegrationTest, and service runtime validation source code belong to step 05.",
            },
            "creationMode": framework_plan.creation_mode,
            "registrationStrategy": framework_plan.registration_strategy,
            "targetFile": framework_plan.target_file,
            "targetClass": f"{framework_plan.module_name}Service",
            "targetMethod": framework_plan.target_method,
            "action": "ai_orchestrated_implementation",
            "requestFields": normalized_model.get("requestFields") or [],
            "responseFields": normalized_model.get("responseFields") or [],
            "businessSteps": normalized_model.get("businessSteps") or [],
            "fieldMappings": normalized_model.get("fieldMappings") or [],
            "errorCodes": normalized_model.get("errorCodes") or [],
            "runtimeDependencies": normalized_model.get("runtimeDependencies") or [],
            "referenceHints": normalized_model.get("referenceHints") or [],
            "backendApis": normalized_model.get("backendApis") or [],
            "mockExamples": normalized_model.get("mockExamples") or [],
            "handoffSource": clean_text(normalized_model.get("handoffSource")) or "unknown",
            "logicSummary": normalized_model.get("logicSummary") or {},
            "logicFlow": normalized_model.get("logicFlow") or [],
            "audienceProfile": dev_guideline_resolution.get("audienceProfile") or {},
            "devGuidelineProfile": dev_guideline_resolution.get("devGuidelineProfile") or {},
            "devGuidelineRulesSelected": dev_guideline_resolution.get("devGuidelineRulesSelected") or [],
            "devGuidelineLoadHints": dev_guideline_resolution.get("devGuidelineLoadHints") or [],
            "devGuidelineGaps": dev_guideline_resolution.get("devGuidelineGaps") or [],
            "logicSourcesUsed": logic_resolution.get("logicSourcesUsed") or [],
            "queryContractsSelected": logic_resolution.get("queryContractsSelected") or [],
            "mappingRulesSelected": logic_resolution.get("mappingRulesSelected") or [],
            "dependencyHintsSelected": logic_resolution.get("dependencyHintsSelected") or [],
            "legacyEvidenceUsed": logic_resolution.get("legacyEvidenceUsed") or [],
            "constraintsApplied": logic_resolution.get("constraintsApplied") or [],
            "unresolvedLogic": logic_resolution.get("unresolvedLogic") or [],
            "testScenarioPlan": logic_resolution.get("testScenarioPlan") or [],
            "testScenarioSource": logic_resolution.get("testScenarioSource") or "none",
            "testScenarioCoverageRequired": bool(logic_resolution.get("testScenarioCoverageRequired")),
            "requestValidationPlan": logic_resolution.get("requestValidationPlan") or [],
            "dtoAttributeRules": logic_resolution.get("dtoAttributeRules") or [],
            "customValidationAttributesNeeded": logic_resolution.get("customValidationAttributesNeeded") or [],
            "validationResponseMappingMode": logic_resolution.get("validationResponseMappingMode") or "not_applicable",
            "serviceValidationsRetained": logic_resolution.get("serviceValidationsRetained") or [],
            "validationInfrastructureGap": logic_resolution.get("validationInfrastructureGap") or [],
            "reviewSources": review_resolution.get("reviewSources") or [],
            "reviewConstraintsSelected": review_resolution.get("reviewConstraintsSelected") or [],
            "fileRequirements": review_resolution.get("fileRequirements") or {},
            "responseLifecycleRules": review_resolution.get("responseLifecycleRules") or [],
            "failureDisposition": review_resolution.get("failureDisposition") or {},
            "languagePolicy": review_resolution.get("languagePolicy") or {},
            "externalApiName": clean_text(review_resolution.get("externalApiName")) or clean_text(normalized_model.get("apiName")) or "",
            "internalAsyncMethod": clean_text(review_resolution.get("internalAsyncMethod")) or framework_plan.target_method,
            "resumedFromPhase": resumed_from_phase,
        },
        "validationChecks": validation_commands,
        "steps": [
            {"id": "precheck", "status": "done", "note": "Resolved EnterpriseAPI framework profile and module slots."},
            {
                "id": "write_code",
                "status": "pending",
                "note": f"AI must directly modify controller/interface/service/entity business files for {framework_plan.module_name}; test targets are handoff-only for step 05 and the script must not generate stubs.",
            },
            {"id": "validate", "status": "pending", "note": "After real code is written, run EnterpriseAPI build, unit test, and integration test validation."},
        ],
    }

def build_validation_commands(context: ExecutionContext, framework_profile: FrameworkProfile) -> list[str]:
    if context.validation_checks:
        return list(context.validation_checks)
    api_project = relative_path_from_project(framework_profile.api_project_path, context.project_root)
    unit_test_project = relative_path_from_project(framework_profile.unit_test_project_path, context.project_root)
    integration_test_project = relative_path_from_project(framework_profile.integration_test_project_path, context.project_root)
    return [
        f'dotnet build "{api_project}" -m:1',
        f'dotnet test "{unit_test_project}" -m:1',
        f'dotnet test "{integration_test_project}" -m:1',
    ]


def summarize_blocking_dev_guideline_gaps(change_plan: dict[str, Any]) -> str | None:
    analysis = change_plan.get("analysis") if isinstance(change_plan.get("analysis"), dict) else {}
    gaps = blocking_dev_guideline_gaps({"devGuidelineGaps": analysis.get("devGuidelineGaps") or []})
    if not gaps:
        return None
    descriptions = []
    for gap in gaps:
        rule_id = clean_text(gap.get("ruleId"))
        message = clean_text(gap.get("message")) or clean_text(gap.get("gapType")) or "dev guideline gap"
        descriptions.append(f"{rule_id}: {message}" if rule_id else message)
    return "V6.2 dev-guideline selection blocked: " + "; ".join(descriptions)


def build_diagnosis_payload(
    context: ExecutionContext,
    item: dict[str, Any],
    *,
    status: str,
    phase: str,
    diagnosis_type: str,
    target_file: str | None,
    modified_files: list[str],
    validation_checks: list[str],
    validation_results: list[dict[str, Any]],
    repo_drift_files: list[str],
    unresolved_logic: list[dict[str, Any]] | None = None,
    failure_kind: str | None = None,
    failure_classifications: list[dict[str, Any]] | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "skillName": SKILL_NAME,
        "executionId": context.execution_id,
        "apiId": item["apiId"],
        "status": status,
        "phase": phase,
        "updatedAt": now_iso(),
        "diagnosisType": diagnosis_type,
        "detail": detail,
        "targetFile": target_file,
        "modifiedFiles": modified_files,
        "validationChecks": validation_checks,
        "validationResults": validation_results,
        "failureKind": failure_kind,
        "failureClassifications": failure_classifications or [],
        "unresolvedLogic": unresolved_logic or [],
        "repoDriftFiles": repo_drift_files,
    }


def build_implementation_report(
    context: ExecutionContext,
    item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    normalized_model: dict[str, Any],
    change_plan: dict[str, Any],
    *,
    status: str,
    phase: str,
    message: str,
    block_reason: str | None,
    modified_files: list[str],
    validation_results: list[dict[str, Any]],
    repo_drift_files: list[str],
    validation_note: str = "",
    code_contract_review: dict[str, Any] | None = None,
) -> str:
    analysis = change_plan.get("analysis") or {}
    validation_checks = change_plan.get("validationChecks") or []
    source = normalized_model.get("source") or {}
    lines = [
        "# Implementation Report",
        "",
        "## Upstream Source",
        f"- executionId: {context.execution_id}",
        f"- apiId: {item['apiId']}",
        f"- upstreamManifest: {normalize_persisted_path(upstream_api.manifest_path, project_root=context.project_root)}",
        f"- upstreamApiSpec: {normalize_persisted_path(upstream_api.api_spec_path, project_root=context.project_root) or 'none'}",
        f"- tsdFile: {clean_text(source.get('tsdFile')) or 'none'}",
        f"- workbookFile: {clean_text(source.get('workbookFile')) or 'none'}",
        f"- sheetNames: {', '.join(source.get('sheetNames') or []) or 'none'}",
        f"- designDraft: not_used",
        "",
        "## Contract Summary",
        f"- requestFields: {summarize_field_paths(normalized_model.get('requestFields') or [])}",
        f"- responseFields: {summarize_field_paths(normalized_model.get('responseFields') or [], limit=12)}",
        f"- businessSteps: {summarize_business_steps(normalized_model.get('businessSteps') or [], limit=6)}",
        f"- runtimeDependencies: {summarize_runtime_dependencies(normalized_model.get('runtimeDependencies') or [], limit=6)}",
        f"- fieldMappingCount: {len(normalized_model.get('fieldMappings') or [])}",
        f"- errorCodeCount: {len(normalized_model.get('errorCodes') or [])}",
        f"- handoffSource: {clean_text(normalized_model.get('handoffSource')) or 'unknown'}",
        f"- queryContracts: {summarize_query_contracts((analysis.get('queryContractsSelected') or normalized_model.get('queryContracts') or []), limit=5)}",
        f"- mappingRules: {summarize_mapping_rules((analysis.get('mappingRulesSelected') or normalized_model.get('mappingRules') or []), limit=5)}",
        f"- legacyEvidence: {summarize_legacy_evidence((analysis.get('legacyEvidenceUsed') or normalized_model.get('legacyEvidence') or []), limit=5)}",
        f"- constraints: {summarize_constraints((analysis.get('constraintsApplied') or normalized_model.get('constraints') or []), limit=5)}",
        f"- testScenarios: {summarize_test_scenarios(analysis.get('testScenarioPlan') or [], limit=8)}",
        f"- referenceHints: {summarize_reference_hints(normalized_model.get('referenceHints') or [], limit=5)}",
        "",
        "## Writer Result",
        f"- status: {status}",
        f"- phase: {phase}",
        f"- message: {message}",
        f"- frameworkProfile: {clean_text(analysis.get('frameworkProfile')) or 'n/a'}",
        f"- guidelineAuthority: {clean_text(analysis.get('guidelineAuthority')) or 'n/a'}",
        f"- audienceProfile: {json.dumps(analysis.get('audienceProfile') or {}, ensure_ascii=False)}",
        f"- devGuidelineRulesSelected: {json.dumps(analysis.get('devGuidelineRulesSelected') or [], ensure_ascii=False)}",
        f"- devGuidelineLoadHints: {json.dumps(analysis.get('devGuidelineLoadHints') or [], ensure_ascii=False)}",
        f"- devGuidelineGaps: {json.dumps(analysis.get('devGuidelineGaps') or [], ensure_ascii=False)}",
        f"- moduleName: {clean_text(analysis.get('moduleName')) or 'n/a'}",
        f"- creationMode: {clean_text(analysis.get('creationMode')) or 'n/a'}",
        f"- implementationBoundary: AI writes repository code directly; script only reconciles/validates",
        f"- controllerFile: {clean_text(analysis.get('controllerFile')) or 'n/a'}",
        f"- interfaceFile: {clean_text(analysis.get('interfaceFile')) or 'n/a'}",
        f"- serviceFiles: {', '.join(analysis.get('serviceFiles') or []) or 'none'}",
        f"- entityFiles: {', '.join(analysis.get('entityFiles') or []) or 'none'}",
        f"- codeTargetFiles: {', '.join(analysis.get('codeTargetFiles') or []) or 'none'}",
        f"- unitTestTargetFiles(handoffOnly): {', '.join(analysis.get('unitTestTargetFiles') or []) or 'none'}",
        f"- integrationTestTargetFiles(handoffOnly): {', '.join(analysis.get('integrationTestTargetFiles') or []) or 'none'}",
        f"- testCodeHandoff: {json.dumps(analysis.get('testCodeHandoff') or {}, ensure_ascii=False)}",
        f"- targetFile: {clean_text(analysis.get('targetFile')) or 'n/a'}",
        f"- targetMethod: {clean_text(analysis.get('targetMethod')) or 'n/a'}",
        f"- action: {clean_text(analysis.get('action')) or 'n/a'}",
        f"- logicSourcesUsed: {', '.join(analysis.get('logicSourcesUsed') or []) or 'none'}",
        f"- queryContractsSelected: {', '.join(clean_text(entry.get('contractId')) for entry in analysis.get('queryContractsSelected') or [] if clean_text(entry.get('contractId'))) or 'none'}",
        f"- mappingRulesSelected: {', '.join(clean_text(entry.get('ruleId')) for entry in analysis.get('mappingRulesSelected') or [] if clean_text(entry.get('ruleId'))) or 'none'}",
        f"- legacyEvidenceUsed: {', '.join(clean_text(entry.get('evidenceId')) for entry in analysis.get('legacyEvidenceUsed') or [] if clean_text(entry.get('evidenceId'))) or 'none'}",
        f"- reviewConstraintsSelected: {', '.join(clean_text(entry.get('reviewId')) for entry in analysis.get('reviewConstraintsSelected') or [] if clean_text(entry.get('reviewId'))) or 'none'}",
        f"- reviewSources: {json.dumps(analysis.get('reviewSources') or [], ensure_ascii=False)}",
        f"- testScenarioSource: {clean_text(analysis.get('testScenarioSource')) or 'none'}",
        f"- testScenarioCoverageRequired: {bool(analysis.get('testScenarioCoverageRequired'))}",
        f"- testScenarioPlan: {json.dumps(analysis.get('testScenarioPlan') or [], ensure_ascii=False)}",
        f"- fileRequirements: {json.dumps(analysis.get('fileRequirements') or {}, ensure_ascii=False)}",
        f"- responseLifecycleRules: {json.dumps(analysis.get('responseLifecycleRules') or [], ensure_ascii=False)}",
        f"- failureDisposition: {json.dumps(analysis.get('failureDisposition') or {}, ensure_ascii=False)}",
        f"- languagePolicy: {json.dumps(analysis.get('languagePolicy') or {}, ensure_ascii=False)}",
        f"- externalApiName: {clean_text(analysis.get('externalApiName')) or 'n/a'}",
        f"- internalAsyncMethod: {clean_text(analysis.get('internalAsyncMethod')) or 'n/a'}",
        f"- unresolvedLogic: {json.dumps(analysis.get('unresolvedLogic') or [], ensure_ascii=False)}",
        f"- modifiedFiles: {', '.join(modified_files) if modified_files else 'none'}",
        f"- repoDriftFiles: {', '.join(repo_drift_files) if repo_drift_files else 'none'}",
        "",
        "## Validation",
        f"- validationChecks: {', '.join(validation_checks) if validation_checks else 'none'}",
        f"- validationSummary: {build_validation_summary(validation_results)}",
        f"- validationRetries: {summarize_validation_retries(validation_results)}",
    ]
    if isinstance(code_contract_review, dict):
        review_summary = code_contract_review.get("summary") if isinstance(code_contract_review.get("summary"), dict) else {}
        lines.extend(
            [
                "",
                "## Contract Review",
                f"- contractReviewStatus: {clean_text(code_contract_review.get('status')) or 'unknown'}",
                f"- contractReviewFindings: {int(review_summary.get('findingCount') or 0)}",
                f"- contractReviewBlocking: {int(review_summary.get('blockingCount') or 0)}",
                f"- contractReviewWarnings: {int(review_summary.get('warningCount') or 0)}",
                f"- contractReviewArtifact: {normalize_persisted_path(code_contract_review_path(context, item['apiId']), project_root=context.project_root)}",
            ]
        )
    if validation_note:
        lines.append(f"- validationNote: {validation_note}")
    if block_reason:
        lines.append(f"- blockReason: {block_reason}")
    return "\n".join(lines) + "\n"



def build_test_evidence_payload(
    context: ExecutionContext,
    item: dict[str, Any],
    change_plan: dict[str, Any],
    framework_profile: FrameworkProfile,
    *,
    modified_files: list[str],
    validation_commands: list[str],
    validation_results: list[dict[str, Any]],
) -> dict[str, Any]:
    analysis = change_plan.get("analysis") or {}
    module_name = clean_text(analysis.get("moduleName")) or clean_text(item.get("apiCategory"))
    category_name = module_name or clean_text(item.get("apiCategory"))
    api_name = clean_text(item.get("apiName"))
    report_root = context.project_root / ".agent" / "report-results" / context.execution_id / item["apiId"]
    unit_project = relative_path_from_project(framework_profile.unit_test_project_path, context.project_root)
    integration_project = relative_path_from_project(framework_profile.integration_test_project_path, context.project_root)
    unit_test_files, integration_test_files = collect_test_target_files(analysis)

    return {
        "schemaVersion": "1.0.0",
        "executionId": context.execution_id,
        "apiId": item["apiId"],
        "projectRoot": to_posix_path(context.project_root),
        "solutionPath": to_posix_path(context.solution_path),
        "moduleName": module_name,
        "apiCategory": clean_text(item.get("apiCategory")),
        "apiName": api_name,
        "apiDisplayName": f"{category_name}/{api_name}" if category_name else api_name,
        "unitTestProject": unit_project,
        "integrationTestProject": integration_project,
        "validationChecks": list(validation_commands),
        "validationResults": list(validation_results),
        "trxHints": {
            "unit": to_posix_path(report_root / "unit"),
            "integration": to_posix_path(report_root / "integration"),
        },
        "testTargetFiles": {
            "unit": list(unit_test_files),
            "integration": list(integration_test_files),
            "ownerStep": "05 docx-unittest-report",
            "writerPolicy": "handoff_only",
        },
        "testNames": {
            "unit": discover_test_names(context.project_root, unit_test_files),
            "integration": discover_test_names(context.project_root, integration_test_files),
        },
        "reportHints": {
            "recommendedSections": build_report_section_hints(api_name),
            "sourceFiles": build_report_source_files(change_plan, modified_files),
        },
    }


def update_item(items: list[dict[str, Any]], updated_item: dict[str, Any]) -> None:
    for index, item in enumerate(items):
        if item["apiId"] == updated_item["apiId"]:
            items[index] = updated_item
            return
    raise SkillError(f"Unknown apiId in writer checklist: {updated_item['apiId']}")


def persist_selected_api(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    upstream_summary: dict[str, int],
    *,
    execution_message: str,
    execution_phase: str,
    execution_status: str,
    manifest_status: str,
    manifest_phase: str,
    block_reason: str | None,
    change_plan: dict[str, Any] | None,
    implementation_report: str | None,
    modified_files: list[str],
    validation_commands: list[str],
    validation_results: list[dict[str, Any]],
    repo_drift_files: list[str],
    diagnosis_payload: dict[str, Any] | None,
    test_evidence_payload: dict[str, Any] | None = None,
    code_contract_review_payload: dict[str, Any] | None = None,
) -> None:
    api_id = item["apiId"]
    if change_plan is not None:
        dump_json(context.paths.change_plan_path(api_id), change_plan)
    if implementation_report is not None:
        dump_text(context.paths.implementation_report_path(api_id), implementation_report)
    if diagnosis_payload is not None:
        dump_json(context.paths.diagnosis_path(api_id), diagnosis_payload)
    else:
        remove_file(context.paths.diagnosis_path(api_id))
    if test_evidence_payload is not None:
        dump_json(context.paths.test_evidence_path(api_id), test_evidence_payload)
    if code_contract_review_payload is not None:
        dump_json(code_contract_review_path(context, api_id), code_contract_review_payload)
    else:
        remove_file(code_contract_review_path(context, api_id))

    dump_json(
        context.paths.manifest_path(api_id),
        build_api_manifest_payload(
            context,
            item,
            upstream_api,
            previous_manifest,
            status=manifest_status,
            phase=manifest_phase,
            block_reason=block_reason,
            modified_files=modified_files,
            validation_checks=validation_commands,
            validation_results=validation_results,
            repo_drift_files=repo_drift_files,
            last_message=execution_message,
        ),
    )
    dump_json(context.paths.checklist_path, build_writer_checklist_payload(context, items))
    execution_payload = build_execution_state_payload(
        context,
        items,
        upstream_summary,
        current_api_id=api_id,
        message=execution_message,
        phase=execution_phase,
        status_override=execution_status,
    )
    dump_json(context.paths.execution_state_path, execution_payload)
    update_chain_status(
        agent_root=context.agent_dir,
        function_code=context.execution_id,
        stage="code",
        status=execution_payload.get("codeStatus"),
        phase=execution_payload.get("codePhase"),
        message=execution_payload.get("codeLastMessage") or execution_payload.get("status"),
        project_root=context.project_root,
        artifacts={
            "solutionPath": normalize_persisted_path(context.solution_path, project_root=context.project_root),
            "currentApiId": api_id,
            "executionState": normalize_persisted_path(context.paths.execution_state_path, project_root=context.agent_dir),
            "apiChecklist": normalize_persisted_path(context.paths.checklist_path, project_root=context.agent_dir),
            "codeProgress": normalize_persisted_path(context.paths.progress_path, project_root=context.agent_dir),
        },
    )
    append_progress(context.paths.progress_path, execution_message)


def clone_change_plan(change_plan: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(change_plan, ensure_ascii=False))


def update_change_plan_progress(
    change_plan: dict[str, Any],
    *,
    status: str,
    write_code_status: str,
    validate_status: str,
) -> dict[str, Any]:
    updated = clone_change_plan(change_plan)
    updated["status"] = status
    updated["updatedAt"] = now_iso()
    steps = []
    for step in list(updated.get("steps") or []):
        if not isinstance(step, dict):
            continue
        step_copy = dict(step)
        if clean_text(step_copy.get("id")) == "write_code":
            step_copy["status"] = write_code_status
        elif clean_text(step_copy.get("id")) == "validate":
            step_copy["status"] = validate_status
        steps.append(step_copy)
    updated["steps"] = steps
    return updated


def extract_planned_files(change_plan: dict[str, Any]) -> list[str]:
    analysis = change_plan.get("analysis") if isinstance(change_plan.get("analysis"), dict) else {}
    files: list[str] = []
    for key in ("controllerFile", "interfaceFile", "targetFile"):
        candidate = clean_text(analysis.get(key))
        if candidate and candidate not in files:
            files.append(candidate)
    for key in ("codeTargetFiles", "serviceFiles", "entityFiles"):
        values = analysis.get(key)
        if not isinstance(values, list):
            continue
        for candidate in values:
            rendered = clean_text(candidate)
            if rendered and rendered not in files:
                files.append(rendered)
    return files


def normalize_declared_relative_path(project_root: Path, raw_path: str) -> str:
    text = clean_text(raw_path)
    if not text:
        raise SkillError("modified-file/new-file contains an empty path.")
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = (project_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    try:
        return candidate.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise SkillError(f"Declared file is outside project-root: {candidate.as_posix()}") from exc


def collect_declared_changes(project_root: Path, declared_paths: list[str], excluded_prefixes: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw_path in declared_paths:
        relative_path = normalize_declared_relative_path(project_root, raw_path)
        candidate = project_root / relative_path
        if not candidate.exists():
            raise SkillError(f"Declared file does not exist yet: {relative_path}")
        if not is_source_level_relative_path(relative_path, excluded_prefixes):
            raise SkillError(f"Declared file is not a source-level repository file: {relative_path}")
        if relative_path not in normalized:
            normalized.append(relative_path)
    return normalized


def detect_ai_authored_changes(
    context: ExecutionContext,
    *,
    excluded_prefixes: list[str],
    declared_paths: list[str],
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    snapshot_payload = require_json_object("repo-snapshot.json", context.paths.snapshot_path)
    baseline_snapshot = snapshot_payload.get("files")
    if not isinstance(baseline_snapshot, dict):
        raise SkillError("repo-snapshot.json does not contain a valid files baseline; run prepare first.")
    current_snapshot = build_repo_snapshot(context.project_root, excluded_prefixes)
    changed_files = diff_snapshot_files(baseline_snapshot, current_snapshot, excluded_prefixes)
    for declared_file in collect_declared_changes(context.project_root, declared_paths, excluded_prefixes):
        if declared_file not in changed_files:
            changed_files.append(declared_file)
    after_hashes: dict[str, str] = {}
    for relative_path in changed_files:
        candidate = context.project_root / relative_path
        after_hashes[relative_path] = (sha256_file(candidate) or "") if candidate.exists() else ""
    changed_files.sort()
    return changed_files, after_hashes, current_snapshot


def resolve_execution_mode(
    requested_mode: str,
    *,
    previous_manifest: dict[str, Any] | None,
    previous_change_plan: dict[str, Any] | None,
    snapshot_path: Path,
    current_snapshot: dict[str, str],
    excluded_prefixes: list[str],
) -> str:
    if requested_mode in {"prepare", "apply"}:
        return requested_mode
    previous_phase = clean_text(previous_manifest.get("codePhase")) if isinstance(previous_manifest, dict) else ""
    if previous_change_plan and snapshot_path.exists() and previous_phase in {"planned", "implemented", "validation_failed"}:
        snapshot_payload = require_json_object("repo-snapshot.json", snapshot_path)
        baseline_snapshot = snapshot_payload.get("files")
        if isinstance(baseline_snapshot, dict) and diff_snapshot_files(baseline_snapshot, current_snapshot, excluded_prefixes):
            return "apply"
    return "prepare"


def choose_target_item(items: list[dict[str, Any]], requested_api_id: str | None) -> tuple[dict[str, Any] | None, str, int]:
    if requested_api_id:
        for item in items:
            if item["apiId"] != requested_api_id:
                continue
            if item["upstreamStatus"] != UPSTREAM_READY_STATUS:
                raise SkillError(f"指定的 apiId 尚未在上游完成：{requested_api_id}")
            if item["writerStatus"] == "tests_passed":
                return None, f"{requested_api_id} already completed; no new writer work was scheduled.", 0
            return item, "", 0
        raise SkillError(f"api-id not found in upstream checklist: {requested_api_id}")

    for status in ("in_progress", "tests_failed", "error", "pending", "waiting_fixture"):
        for item in items:
            if item["upstreamStatus"] == UPSTREAM_READY_STATUS and item["writerStatus"] == status:
                return item, "", 0

    ready_items = [item for item in items if item["upstreamStatus"] == UPSTREAM_READY_STATUS]
    if ready_items and all(item["writerStatus"] == "tests_passed" for item in ready_items):
        return None, "No eligible API to process; all upstream-ready APIs are already completed by writer.", 0
    if not ready_items:
        return None, "No eligible API to process; upstream execution has no ready API_Spec outputs.", 1
    return None, "No eligible API to process; remaining upstream-ready APIs are currently blocked.", 1


def build_repository_excluded_prefixes(context: ExecutionContext) -> list[str]:
    excluded_prefixes: list[str] = []
    try:
        agent_prefix = context.agent_dir.resolve().relative_to(context.project_root).as_posix()
        excluded_prefixes.append(agent_prefix)
    except ValueError:
        pass
    return excluded_prefixes


def reconcile_writer_queue(
    context: ExecutionContext,
    upstream_checklist_items: list[dict[str, Any]],
    upstream_api_map: dict[str, UpstreamApiRecord],
) -> tuple[dict[str, int], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    upstream_summary = summarize_upstream_status(upstream_checklist_items)
    previous_manifest_map = existing_writer_manifest_map(context)
    items = [build_writer_item(upstream_api_map[item["apiId"]], previous_manifest_map.get(item["apiId"])) for item in upstream_checklist_items]
    dump_queue_manifests(context, items, upstream_api_map, previous_manifest_map)
    persist_execution_view(
        context,
        items,
        upstream_summary,
        message=f"Reconciled writer execution with upstream {context.execution_id}.",
        current_api_id=None,
        phase="reconciled",
        append_message=False,
    )
    return upstream_summary, previous_manifest_map, items


def persist_idle_result(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    upstream_summary: dict[str, int],
    *,
    message: str,
    exit_code: int,
) -> int:
    persist_execution_view(
        context,
        items,
        upstream_summary,
        message=message,
        current_api_id=None,
        phase="idle",
        status_override=None,
        append_message=True,
    )
    refresh_batch_pointer(context, preferred_function_code=context.execution_id)
    print(message)
    return exit_code


def load_existing_change_plan(context: ExecutionContext, api_id: str) -> dict[str, Any] | None:
    change_plan_path = context.paths.change_plan_path(api_id)
    if change_plan_path.exists():
        return require_json_object("existing change-plan.json", change_plan_path)
    return None


def build_planned_file_before_hashes(
    planned_files: list[str],
    previous_change_plan: dict[str, Any] | None,
    current_snapshot: dict[str, str],
    *,
    resumed_from_phase: str,
) -> dict[str, str | None]:
    before_hashes: dict[str, str | None] = {}
    previous_hashes = previous_change_plan.get("beforeHashes") if previous_change_plan else None
    for relative_path in planned_files:
        if (
            isinstance(previous_hashes, dict)
            and relative_path in previous_hashes
            and resumed_from_phase in {"prechecked", "planned", "implemented", "validation_failed"}
        ):
            before_hashes[relative_path] = previous_hashes[relative_path]
        else:
            before_hashes[relative_path] = current_snapshot.get(relative_path)
    return before_hashes


def persist_precheck_progress(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    selected_item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    upstream_summary: dict[str, int],
    prepared_change_plan: dict[str, Any],
    *,
    validation_commands: list[str],
    repo_drift_files: list[str],
) -> None:
    persist_selected_api(
        context,
        items,
        selected_item,
        upstream_api,
        previous_manifest,
        upstream_summary,
        execution_message=f"{selected_item['apiId']} precheck completed.",
        execution_phase="prechecked",
        execution_status="running",
        manifest_status="in_progress",
        manifest_phase="prechecked",
        block_reason=None,
        change_plan=prepared_change_plan,
        implementation_report=None,
        modified_files=[],
        validation_commands=validation_commands,
        validation_results=[],
        repo_drift_files=repo_drift_files,
        diagnosis_payload=None,
    )


def persist_terminal_api_state(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    selected_item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    upstream_summary: dict[str, int],
    normalized_model: dict[str, Any],
    *,
    status: str,
    phase: str,
    message: str,
    block_reason: str,
    diagnosis_type: str,
    target_file: str | None,
    change_plan: dict[str, Any] | None,
    validation_commands: list[str],
    validation_results: list[dict[str, Any]] | None,
    repo_drift_files: list[str],
    unresolved_logic: list[Any],
    snapshot: dict[str, str],
    snapshot_reason: str,
    modified_files: list[str] | None = None,
    report_change_plan: dict[str, Any] | None = None,
    execution_status: str | None = None,
    manifest_status: str | None = None,
    manifest_phase: str | None = None,
    preserve_history: bool | None = None,
    code_contract_review: dict[str, Any] | None = None,
    print_message: str | None = None,
) -> int:
    modified_files = modified_files or []
    validation_results = validation_results or []
    updated_item = {**selected_item, "writerStatus": status, "phase": phase, "blockReason": block_reason}
    if preserve_history is not None:
        updated_item["preserveHistory"] = preserve_history
    update_item(items, updated_item)

    diagnosis_payload = build_diagnosis_payload(
        context,
        updated_item,
        status=status,
        phase=phase,
        diagnosis_type=diagnosis_type,
        target_file=target_file,
        modified_files=modified_files,
        validation_checks=validation_commands,
        validation_results=validation_results,
        repo_drift_files=repo_drift_files,
        unresolved_logic=unresolved_logic,
        detail=block_reason,
    )
    report_payload = report_change_plan if report_change_plan is not None else change_plan
    if report_payload is None:
        report_payload = {"analysis": {}, "validationChecks": validation_commands}
    implementation_report = build_implementation_report(
        context,
        updated_item,
        upstream_api,
        normalized_model,
        report_payload,
        status=status,
        phase=phase,
        message=message,
        block_reason=block_reason,
        modified_files=modified_files,
        validation_results=validation_results,
        repo_drift_files=repo_drift_files,
        code_contract_review=code_contract_review,
    )
    persist_selected_api(
        context,
        items,
        updated_item,
        upstream_api,
        previous_manifest,
        upstream_summary,
        execution_message=message,
        execution_phase=phase,
        execution_status=execution_status or status,
        manifest_status=manifest_status or status,
        manifest_phase=manifest_phase or phase,
        block_reason=block_reason,
        change_plan=change_plan,
        implementation_report=implementation_report,
        modified_files=modified_files,
        validation_commands=validation_commands,
        validation_results=validation_results,
        repo_drift_files=repo_drift_files,
        diagnosis_payload=diagnosis_payload,
        code_contract_review_payload=code_contract_review,
    )
    write_snapshot(context.paths.snapshot_path, snapshot, reason=snapshot_reason)
    refresh_batch_pointer(context, preferred_function_code=context.execution_id)
    print(print_message or block_reason)
    return 1


def persist_prepare_result(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    selected_item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    upstream_summary: dict[str, int],
    prepared_change_plan: dict[str, Any],
    framework_plan: FrameworkPlan,
    *,
    validation_commands: list[str],
    repo_drift_files: list[str],
    current_snapshot: dict[str, str],
) -> int:
    selected_item = {**selected_item, "writerStatus": "pending", "phase": "planned", "blockReason": None}
    update_item(items, selected_item)
    prepare_plan = update_change_plan_progress(
        prepared_change_plan,
        status="planned",
        write_code_status="pending",
        validate_status="pending",
    )
    prepare_message = (
        f"{selected_item['apiId']} change-plan generated for {framework_plan.target_file}; "
        "waiting for AI-authored code changes."
    )
    persist_selected_api(
        context,
        items,
        selected_item,
        upstream_api,
        previous_manifest,
        upstream_summary,
        execution_message=prepare_message,
        execution_phase="planned",
        execution_status=derive_execution_status(items),
        manifest_status="pending",
        manifest_phase="planned",
        block_reason=None,
        change_plan=prepare_plan,
        implementation_report=None,
        modified_files=[],
        validation_commands=validation_commands,
        validation_results=[],
        repo_drift_files=repo_drift_files,
        diagnosis_payload=None,
    )
    write_snapshot(context.paths.snapshot_path, current_snapshot, reason="prepared")
    refresh_batch_pointer(context, preferred_function_code=context.execution_id)
    print(prepare_message)
    return 0


def persist_implemented_progress(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    selected_item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    upstream_summary: dict[str, int],
    normalized_model: dict[str, Any],
    change_plan: dict[str, Any],
    *,
    effective_modified_files: list[str],
    validation_commands: list[str],
    repo_drift_files: list[str],
    code_contract_review: dict[str, Any],
    contract_review_warnings: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    code_note = f"Detected {len(effective_modified_files)} AI-authored modified file(s)."
    if contract_review_warnings > 0:
        code_note += f" Contract review warnings={contract_review_warnings}."
    selected_item = {**selected_item, "writerStatus": "in_progress", "phase": "implemented", "blockReason": None}
    update_item(items, selected_item)
    implemented_plan = update_change_plan_progress(
        change_plan,
        status="implemented",
        write_code_status="done",
        validate_status="pending",
    )
    implementation_report = build_implementation_report(
        context,
        selected_item,
        upstream_api,
        normalized_model,
        implemented_plan,
        status="in_progress",
        phase="implemented",
        message=f"{selected_item['apiId']} code implemented. {code_note}",
        block_reason=None,
        modified_files=effective_modified_files,
        validation_results=[],
        repo_drift_files=repo_drift_files,
        code_contract_review=code_contract_review,
    )
    persist_selected_api(
        context,
        items,
        selected_item,
        upstream_api,
        previous_manifest,
        upstream_summary,
        execution_message=f"{selected_item['apiId']} code implemented.",
        execution_phase="implemented",
        execution_status="running",
        manifest_status="in_progress",
        manifest_phase="implemented",
        block_reason=None,
        change_plan=implemented_plan,
        implementation_report=implementation_report,
        modified_files=effective_modified_files,
        validation_commands=validation_commands,
        validation_results=[],
        repo_drift_files=repo_drift_files,
        diagnosis_payload=None,
        code_contract_review_payload=code_contract_review,
    )
    return selected_item, implemented_plan


def persist_validation_result(
    context: ExecutionContext,
    items: list[dict[str, Any]],
    selected_item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    upstream_summary: dict[str, int],
    normalized_model: dict[str, Any],
    implemented_plan: dict[str, Any],
    framework_profile: FrameworkProfile,
    framework_plan: FrameworkPlan,
    logic_resolution: dict[str, Any],
    *,
    effective_modified_files: list[str],
    validation_commands: list[str],
    validation_results: list[dict[str, Any]],
    validation_outcome: dict[str, Any],
    repo_drift_files: list[str],
    current_snapshot_after: dict[str, str],
    code_contract_review: dict[str, Any],
) -> int:
    effective_passed = validation_outcome["effectivePassed"]
    final_status = validation_outcome["status"]
    final_phase = validation_outcome["phase"]
    validation_note = validation_outcome["note"]
    selected_item = {**selected_item, "writerStatus": final_status, "phase": final_phase, "blockReason": None}
    update_item(items, selected_item)

    diagnosis_payload = None
    if not effective_passed:
        validation_failure = validation_outcome["validationFailure"] or summarize_validation_failure(validation_results)
        diagnosis_payload = build_diagnosis_payload(
            context,
            selected_item,
            status=final_status,
            phase=final_phase,
            diagnosis_type="environment_issue" if validation_failure["kind"] == "environment" else "code_issue",
            target_file=framework_plan.target_file,
            modified_files=effective_modified_files,
            validation_checks=validation_commands,
            validation_results=validation_results,
            repo_drift_files=repo_drift_files,
            unresolved_logic=logic_resolution.get("unresolvedLogic") or [],
            failure_kind=validation_failure["kind"],
            failure_classifications=validation_failure["classifications"],
            detail=f"{selected_item['apiId']} validation failed.",
        )

    final_plan = update_change_plan_progress(
        implemented_plan,
        status=final_status,
        write_code_status="done",
        validate_status="done" if effective_passed else "failed",
    )
    final_message = f"{selected_item['apiId']} => {final_status}{f' ({validation_note})' if validation_note else ''}"
    implementation_report = build_implementation_report(
        context,
        selected_item,
        upstream_api,
        normalized_model,
        final_plan,
        status=final_status,
        phase=final_phase,
        message=final_message,
        block_reason=None,
        modified_files=effective_modified_files,
        validation_results=validation_results,
        repo_drift_files=repo_drift_files,
        validation_note=validation_note,
        code_contract_review=code_contract_review,
    )
    test_evidence_payload = build_test_evidence_payload(
        context,
        selected_item,
        final_plan,
        framework_profile,
        modified_files=effective_modified_files,
        validation_commands=validation_commands,
        validation_results=validation_results,
    )
    persist_selected_api(
        context,
        items,
        selected_item,
        upstream_api,
        previous_manifest,
        upstream_summary,
        execution_message=final_message,
        execution_phase=final_phase,
        execution_status=derive_execution_status(items),
        manifest_status=final_status,
        manifest_phase=final_phase,
        block_reason=None,
        change_plan=final_plan,
        implementation_report=implementation_report,
        modified_files=effective_modified_files,
        validation_commands=validation_commands,
        validation_results=validation_results,
        repo_drift_files=repo_drift_files,
        diagnosis_payload=diagnosis_payload,
        test_evidence_payload=test_evidence_payload,
        code_contract_review_payload=code_contract_review,
    )
    write_snapshot(context.paths.snapshot_path, current_snapshot_after, reason=final_status)
    refresh_batch_pointer(context, preferred_function_code=context.execution_id)
    print(f"{selected_item['apiId']} => {final_status}")
    return 0 if effective_passed else 1


def run_apply_mode(
    args: argparse.Namespace,
    context: ExecutionContext,
    items: list[dict[str, Any]],
    selected_item: dict[str, Any],
    upstream_api: UpstreamApiRecord,
    previous_manifest: dict[str, Any] | None,
    upstream_summary: dict[str, int],
    normalized_model: dict[str, Any],
    previous_change_plan: dict[str, Any] | None,
    prepared_change_plan: dict[str, Any],
    framework_profile: FrameworkProfile,
    framework_plan: FrameworkPlan,
    logic_resolution: dict[str, Any],
    *,
    validation_commands: list[str],
    repo_drift_files: list[str],
    current_snapshot_before: dict[str, str],
    excluded_prefixes: list[str],
) -> int:
    if previous_change_plan is None:
        block_reason = "Apply requires an existing change-plan from a prepare run. Re-run with --execution-mode prepare first."
        blocked_plan = update_change_plan_progress(
            prepared_change_plan,
            status="blocked",
            write_code_status="pending",
            validate_status="pending",
        )
        return persist_terminal_api_state(
            context,
            items,
            selected_item,
            upstream_api,
            previous_manifest,
            upstream_summary,
            normalized_model,
            status="blocked",
            phase="blocked",
            message=f"{selected_item['apiId']} blocked: {block_reason}",
            block_reason=block_reason,
            diagnosis_type="code_issue",
            target_file=framework_plan.target_file,
            change_plan=blocked_plan,
            validation_commands=validation_commands,
            validation_results=[],
            repo_drift_files=repo_drift_files,
            unresolved_logic=logic_resolution.get("unresolvedLogic") or [],
            snapshot=current_snapshot_before,
            snapshot_reason="blocked",
            preserve_history=False,
        )

    change_plan = clone_change_plan(previous_change_plan)
    change_plan["updatedAt"] = now_iso()
    change_plan["validationChecks"] = validation_commands
    repo_drift_files = list(change_plan.get("repoDriftFiles") or repo_drift_files)

    if clean_text(upstream_api.fixture_status) not in {"done", "skipped"}:
        block_reason = upstream_api.fixture_block_reason or (
            f"Apply requires SQL fixture readiness, but fixture status is {upstream_api.fixture_status or 'pending'}."
        )
        return persist_terminal_api_state(
            context,
            items,
            selected_item,
            upstream_api,
            previous_manifest,
            upstream_summary,
            normalized_model,
            status="waiting_fixture",
            phase="waiting_fixture",
            message=f"{selected_item['apiId']} waiting_fixture: {block_reason}",
            block_reason=block_reason,
            diagnosis_type="environment_issue",
            target_file=framework_plan.target_file,
            change_plan=change_plan,
            validation_commands=validation_commands,
            validation_results=[],
            repo_drift_files=repo_drift_files,
            unresolved_logic=logic_resolution.get("unresolvedLogic") or [],
            snapshot=current_snapshot_before,
            snapshot_reason="waiting_fixture",
            execution_status="waiting_fixture",
            manifest_status="waiting_fixture",
            print_message=block_reason,
        )

    effective_modified_files, _after_hashes, current_snapshot_after = detect_ai_authored_changes(
        context,
        excluded_prefixes=excluded_prefixes,
        declared_paths=[*args.modified_file, *args.new_file],
    )
    planned_files = set(extract_planned_files(change_plan))
    touched_planned_files = [path for path in effective_modified_files if path in planned_files]

    if not effective_modified_files or (not touched_planned_files and not args.modified_file and not args.new_file):
        if not effective_modified_files:
            block_reason = "No AI-authored code changes detected. Run prepare, modify the target repository files, then rerun apply."
        else:
            block_reason = (
                "Detected repository changes, but none match the planned framework slots. "
                "If extra helper files are intentional, rerun apply with --modified-file/--new-file."
            )
        blocked_plan = update_change_plan_progress(
            change_plan,
            status="blocked",
            write_code_status="pending",
            validate_status="pending",
        )
        return persist_terminal_api_state(
            context,
            items,
            selected_item,
            upstream_api,
            previous_manifest,
            upstream_summary,
            normalized_model,
            status="blocked",
            phase="blocked",
            message=f"{selected_item['apiId']} blocked: {block_reason}",
            block_reason=block_reason,
            diagnosis_type="code_issue",
            target_file=framework_plan.target_file,
            change_plan=blocked_plan,
            validation_commands=validation_commands,
            validation_results=[],
            repo_drift_files=repo_drift_files,
            unresolved_logic=logic_resolution.get("unresolvedLogic") or [],
            snapshot=current_snapshot_after,
            snapshot_reason="blocked",
            modified_files=effective_modified_files,
            preserve_history=False,
        )

    code_contract_review = build_code_contract_review_artifact(
        context,
        selected_item,
        normalized_model,
        change_plan,
    )
    contract_review_summary = code_contract_review.get("summary") if isinstance(code_contract_review.get("summary"), dict) else {}
    contract_review_blocking = int(contract_review_summary.get("blockingCount") or 0)
    contract_review_warnings = int(contract_review_summary.get("warningCount") or 0)
    if contract_review_blocking > 0:
        block_reason = (
            f"{selected_item['apiId']} code/spec contract drift detected before build; "
            f"blockingFindings={contract_review_blocking}"
        )
        blocked_plan = update_change_plan_progress(
            change_plan,
            status="blocked",
            write_code_status="done",
            validate_status="pending",
        )
        return persist_terminal_api_state(
            context,
            items,
            selected_item,
            upstream_api,
            previous_manifest,
            upstream_summary,
            normalized_model,
            status="blocked",
            phase="contract_review_failed",
            message=block_reason,
            block_reason=block_reason,
            diagnosis_type="code_contract_drift",
            target_file=framework_plan.target_file,
            change_plan=blocked_plan,
            validation_commands=validation_commands,
            validation_results=[],
            repo_drift_files=repo_drift_files,
            unresolved_logic=logic_resolution.get("unresolvedLogic") or [],
            snapshot=current_snapshot_after,
            snapshot_reason="blocked",
            modified_files=effective_modified_files,
            manifest_phase="contract_review_failed",
            preserve_history=False,
            code_contract_review=code_contract_review,
        )

    selected_item, implemented_plan = persist_implemented_progress(
        context,
        items,
        selected_item,
        upstream_api,
        previous_manifest,
        upstream_summary,
        normalized_model,
        change_plan,
        effective_modified_files=effective_modified_files,
        validation_commands=validation_commands,
        repo_drift_files=repo_drift_files,
        code_contract_review=code_contract_review,
        contract_review_warnings=contract_review_warnings,
    )

    validation_results = run_validation_checks(context.project_root, validation_commands)
    validation_outcome = evaluate_validation_outcome(validation_results)
    return persist_validation_result(
        context,
        items,
        selected_item,
        upstream_api,
        previous_manifest,
        upstream_summary,
        normalized_model,
        implemented_plan,
        framework_profile,
        framework_plan,
        logic_resolution,
        effective_modified_files=effective_modified_files,
        validation_commands=validation_commands,
        validation_results=validation_results,
        validation_outcome=validation_outcome,
        repo_drift_files=repo_drift_files,
        current_snapshot_after=current_snapshot_after,
        code_contract_review=code_contract_review,
    )


def main() -> int:
    configure_stdio()
    args = parse_args()
    try:
        context, _, upstream_checklist_items, upstream_api_map = build_context(args)
        upstream_summary, previous_manifest_map, items = reconcile_writer_queue(context, upstream_checklist_items, upstream_api_map)

        selected_item, no_op_message, no_op_code = choose_target_item(items, args.api_id)
        if selected_item is None:
            return persist_idle_result(context, items, upstream_summary, message=no_op_message, exit_code=no_op_code)

        upstream_api = upstream_api_map[selected_item["apiId"]]
        normalized_model = normalize_upstream_model(upstream_api)
        normalized_model = {**normalized_model, "reviewNotes": load_review_notes(context, selected_item["apiId"], normalized_model)}
        previous_manifest = previous_manifest_map.get(selected_item["apiId"])
        validation_commands = list(context.validation_checks)
        excluded_prefixes = build_repository_excluded_prefixes(context)

        current_snapshot_before = build_repo_snapshot(context.project_root, excluded_prefixes)
        baseline_snapshot = load_snapshot(context.paths.snapshot_path)
        repo_drift_files = diff_snapshot_files(baseline_snapshot, current_snapshot_before, excluded_prefixes) if baseline_snapshot else []

        selected_item = {**selected_item, "writerStatus": "in_progress", "phase": "prechecked", "blockReason": None}
        update_item(items, selected_item)

        try:
            framework_profile, framework_plan = build_framework_plan(context, selected_item, normalized_model)
            ensure_identity_contract_supported(normalized_model, framework_profile)
            logic_resolution = resolve_logic_contract(normalized_model)
            review_resolution = select_review_constraints(normalized_model, framework_plan)
            normalized_model = {**normalized_model, "logicResolution": logic_resolution, "reviewResolution": review_resolution}
            validation_commands = build_validation_commands(context, framework_profile)
        except SkillError as exc:
            block_reason = str(exc)
            return persist_terminal_api_state(
                context,
                items,
                selected_item,
                upstream_api,
                previous_manifest,
                upstream_summary,
                normalized_model,
                status="blocked",
                phase="blocked",
                message=f"{selected_item['apiId']} blocked: {block_reason}",
                block_reason=block_reason,
                diagnosis_type=exc.diagnosis_type or "framework_gap",
                target_file=None,
                change_plan=None,
                validation_commands=validation_commands,
                validation_results=[],
                repo_drift_files=repo_drift_files,
                unresolved_logic=normalized_model.get("unresolvedLogic") or [],
                snapshot=current_snapshot_before,
                snapshot_reason="blocked",
                report_change_plan={"analysis": {}, "validationChecks": validation_commands},
                preserve_history=False,
            )

        resumed_from_phase = clean_text(previous_manifest.get("codePhase")) if previous_manifest else ""
        previous_change_plan = load_existing_change_plan(context, selected_item["apiId"])
        planned_files = [
            framework_plan.controller_file,
            framework_plan.interface_file,
            *framework_plan.service_files,
            *framework_plan.entity_files,
        ]
        before_hashes = build_planned_file_before_hashes(
            planned_files,
            previous_change_plan,
            current_snapshot_before,
            resumed_from_phase=resumed_from_phase,
        )

        prepared_change_plan = build_change_plan_payload(
            context,
            selected_item,
            upstream_api,
            normalized_model,
            framework_profile=framework_profile,
            framework_plan=framework_plan,
            validation_commands=validation_commands,
            repo_drift_files=repo_drift_files,
            before_hashes=before_hashes,
            resumed_from_phase=resumed_from_phase or None,
            logic_resolution=logic_resolution,
            review_resolution=review_resolution,
        )
        guideline_block_reason = summarize_blocking_dev_guideline_gaps(prepared_change_plan)
        if guideline_block_reason:
            blocked_plan = update_change_plan_progress(
                prepared_change_plan,
                status="blocked",
                write_code_status="blocked",
                validate_status="pending",
            )
            return persist_terminal_api_state(
                context,
                items,
                selected_item,
                upstream_api,
                previous_manifest,
                upstream_summary,
                normalized_model,
                status="blocked",
                phase="blocked",
                message=f"{selected_item['apiId']} blocked: {guideline_block_reason}",
                block_reason=guideline_block_reason,
                diagnosis_type="dev_guideline_gap",
                target_file=framework_plan.target_file,
                change_plan=blocked_plan,
                validation_commands=validation_commands,
                validation_results=[],
                repo_drift_files=repo_drift_files,
                unresolved_logic=[
                    *(logic_resolution.get("unresolvedLogic") or []),
                    *(blocked_plan.get("analysis", {}).get("devGuidelineGaps") or []),
                ],
                snapshot=current_snapshot_before,
                snapshot_reason="blocked",
                report_change_plan=blocked_plan,
                preserve_history=False,
            )
        effective_mode = resolve_execution_mode(
            args.execution_mode,
            previous_manifest=previous_manifest,
            previous_change_plan=previous_change_plan,
            snapshot_path=context.paths.snapshot_path,
            current_snapshot=current_snapshot_before,
            excluded_prefixes=excluded_prefixes,
        )

        persist_precheck_progress(
            context,
            items,
            selected_item,
            upstream_api,
            previous_manifest,
            upstream_summary,
            prepared_change_plan,
            validation_commands=validation_commands,
            repo_drift_files=repo_drift_files,
        )

        if effective_mode == "prepare":
            return persist_prepare_result(
                context,
                items,
                selected_item,
                upstream_api,
                previous_manifest,
                upstream_summary,
                prepared_change_plan,
                framework_plan,
                validation_commands=validation_commands,
                repo_drift_files=repo_drift_files,
                current_snapshot=current_snapshot_before,
            )

        return run_apply_mode(
            args,
            context,
            items,
            selected_item,
            upstream_api,
            previous_manifest,
            upstream_summary,
            normalized_model,
            previous_change_plan,
            prepared_change_plan,
            framework_profile,
            framework_plan,
            logic_resolution,
            validation_commands=validation_commands,
            repo_drift_files=repo_drift_files,
            current_snapshot_before=current_snapshot_before,
            excluded_prefixes=excluded_prefixes,
        )
    except SkillError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
