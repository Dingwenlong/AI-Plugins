from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from code_inspection_utils import inspect_code_paths
from docx_report_utils import load_json, normalize_text, write_json
from postman_mcp_evidence import (
    expected_status_codes,
    validate_api_runtime_call_artifacts,
)
from trx_result_utils import build_test_lookup, find_latest_trx, parse_trx


def resolve_path(agent_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (agent_dir / candidate).resolve()


def render_path_token(raw_value: str, workspace_root: Path, manifest_dir: Path) -> str:
    return (
        raw_value
        .replace("{workspaceRoot}", workspace_root.as_posix())
        .replace("{manifestDir}", manifest_dir.as_posix())
    )


def resolve_path_with_workspace(agent_dir: Path, workspace_root: Path, raw_path: str) -> Path:
    rendered = render_path_token(raw_path, workspace_root, agent_dir)
    return resolve_path(agent_dir, rendered)


def resolve_runtime_context_path(raw_path: str, runtime_context: dict[str, Path]) -> Path:
    manifest_path = Path(
        normalize_text(str(runtime_context.get("manifestPath", ""))) or "."
    ).expanduser().resolve()
    manifest_dir = manifest_path.parent
    rendered = normalize_text(str(raw_path))
    replacements = {
        "{workspaceRoot}": runtime_context.get("workspaceRoot", manifest_dir).as_posix(),
        "{manifestDir}": manifest_dir.as_posix(),
        "{repoRoot}": runtime_context.get("repoRoot", manifest_dir).as_posix(),
    }
    context_root = runtime_context.get("contextRoot")
    if context_root is not None:
        replacements["{contextRoot}"] = context_root.as_posix()
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return resolve_path(manifest_dir, rendered)


def is_reparse_point(path: Path) -> bool:
    try:
        file_attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(file_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def safe_copytree(source_root: Path, target_root: Path, exclude_dir_names: list[str]) -> None:
    visited_dirs: set[str] = set()
    target_root.mkdir(parents=True, exist_ok=True)

    def _copy_dir(current_source: Path, current_target: Path) -> None:
        real_source = str(current_source.resolve())
        if real_source in visited_dirs:
            return
        visited_dirs.add(real_source)
        current_target.mkdir(parents=True, exist_ok=True)

        with os.scandir(current_source) as entries:
            for entry in entries:
                entry_source = Path(entry.path)
                entry_target = current_target / entry.name
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                except OSError:
                    continue

                if is_dir and entry.name in exclude_dir_names:
                    continue
                if is_reparse_point(entry_source):
                    continue
                if is_dir:
                    _copy_dir(entry_source, entry_target)
                else:
                    entry_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(entry_source, entry_target)

    _copy_dir(source_root, target_root)


def prepare_clean_workspace(agent_dir: Path, config: dict[str, Any]) -> Path:
    source_root_text = normalize_text(str(config.get("sourceRoot", "")))
    target_root_text = normalize_text(str(config.get("targetRoot", "")))
    if not source_root_text or not target_root_text:
        raise SystemExit("integrationTest.cleanWorkspace requires sourceRoot and targetRoot when enabled.")

    source_root = resolve_path(agent_dir, source_root_text)
    target_root = resolve_path(agent_dir, target_root_text)
    exclude_dir_names = [normalize_text(str(name)) for name in config.get("excludeDirNames", []) if normalize_text(str(name))]

    if not source_root.exists():
        raise SystemExit(f"integrationTest.cleanWorkspace sourceRoot does not exist: {source_root.as_posix()}")
    try:
        target_root.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise SystemExit(
            "integrationTest.cleanWorkspace targetRoot must be outside sourceRoot to avoid recursive copies."
        )

    if target_root.exists():
        shutil.rmtree(target_root)

    safe_copytree(source_root, target_root, exclude_dir_names)
    return target_root


def run_manifest_command(command: str, working_directory: Path, timeout_seconds: int) -> None:
    subprocess.run(
        command,
        cwd=str(working_directory),
        timeout=timeout_seconds,
        shell=True,
        check=True,
    )


def evaluate_case(
    item: dict[str, Any],
    test_sources: dict[str, dict[str, Any]],
    runtime_context: dict[str, Path] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    mode = item.get("mode", "unit_test")
    if mode == "integration_test":
        source_key = "integrationTest"
    elif mode == "api_runtime_call":
        source_key = "apiRuntimeCall"
    else:
        source_key = "unitTest"
    source_payload = test_sources.get(source_key, {"trxPath": "", "tests": [], "summary": {}})
    test_lookup = build_test_lookup(source_payload.get("tests", []))
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
        "trxPath": source_payload.get("trxPath", ""),
        "sourceKind": source_key,
    }
    blocking_issues: list[str] = []

    if mode == "skip":
        base_payload["status"] = "skipped"
        base_payload["actualResult"] = item.get("actualResult") or "不適用"
        return base_payload, blocking_issues

    if not item.get("enabled", False):
        base_payload["status"] = "not_in_run"
        base_payload["actualResult"] = item.get("actualResult") or "接口未涉及"
        return base_payload, blocking_issues

    if mode == "manual":
        base_payload["status"] = "manual"
        base_payload["actualResult"] = item.get("actualResult") or "人工確認"
        base_payload["attachmentPaths"] = [
            str(path) for path in item.get("manualEvidencePaths", []) if normalize_text(str(path))
        ]
        return base_payload, blocking_issues

    if mode == "code_inspection":
        manifest_path = Path(
            normalize_text(str((runtime_context or {}).get("manifestPath", ""))) or "."
        ).expanduser().resolve()
        return inspect_code_paths(manifest_path, item, runtime_context or {})

    if mode == "api_runtime_call":
        return evaluate_api_runtime_call_case(item, runtime_context or {})

    if mode not in {"unit_test", "integration_test"}:
        blocking_issues.append(
            f"{item.get('caseId', '<unknown>')} uses unsupported mode: {mode}"
        )
        return base_payload, blocking_issues

    bindings = item.get("testBindings") or {}
    test_names = [normalize_text(str(name)) for name in bindings.get("testNames", []) if normalize_text(str(name))]
    allow_missing = bool(bindings.get("allowMissing", False))
    match_mode = normalize_text(str(bindings.get("matchMode", "all_pass"))) or "all_pass"

    if not test_names:
        blocking_issues.append(
            f"{item.get('caseId', '<unknown>')} missing explicit testBindings.testNames"
        )
        base_payload["actualResult"] = "待補"
        return base_payload, blocking_issues

    if match_mode != "all_pass":
        blocking_issues.append(
            f"{item.get('caseId', '<unknown>')} uses unsupported matchMode: {match_mode}"
        )
        return base_payload, blocking_issues

    matched_tests: list[dict[str, Any]] = []
    missing_tests: list[str] = []
    for test_name in test_names:
        matched = test_lookup.get(test_name)
        if matched is None:
            missing_tests.append(test_name)
            continue
        matched_tests.append(matched)

    base_payload["boundTests"] = test_names
    base_payload["missingTests"] = missing_tests

    if missing_tests and not allow_missing:
        blocking_issues.append(
            f"{item.get('caseId', '<unknown>')} missing test results: {', '.join(missing_tests)}"
        )

    attachment_paths: list[str] = []
    failure_details: list[dict[str, Any]] = []
    has_failed = False
    has_incomplete = bool(missing_tests)
    for matched in matched_tests:
        attachment_paths.extend(matched.get("attachments", []))
        if matched.get("status") == "failed":
            has_failed = True
            failure_details.append(
                {
                    "testName": matched.get("testName", ""),
                    "message": matched.get("errorSummary", "") or matched.get("errorMessage", ""),
                    "attachments": matched.get("attachments", []),
                }
            )
        elif matched.get("status") != "passed":
            has_incomplete = True

    base_payload["attachmentPaths"] = list(dict.fromkeys(attachment_paths))
    base_payload["failureDetails"] = failure_details

    if has_failed:
        base_payload["status"] = "failed"
        detail_label = "IntegrationTest" if mode == "integration_test" else "UnitTest"
        base_payload["actualResult"] = item.get("actualResult") or f"失敗，詳見{detail_label}失敗摘要與附件"
    elif matched_tests and all(matched.get("status") == "skipped" for matched in matched_tests):
        base_payload["status"] = "skipped"
        base_payload["actualResult"] = item.get("actualResult") or "不適用"
    elif has_incomplete:
        base_payload["status"] = "pending"
        base_payload["actualResult"] = item.get("actualResult") or "待補"
    else:
        base_payload["status"] = "passed"
        detail_label = "IntegrationTest" if mode == "integration_test" else "UnitTest"
        base_payload["actualResult"] = item.get("actualResult") or f"通過，詳見 {detail_label} 結果"

    return base_payload, blocking_issues


def evaluate_api_runtime_call_case(
    item: dict[str, Any],
    runtime_context: dict[str, Path],
) -> tuple[dict[str, Any], list[str]]:
    config = item.get("apiRuntimeCall") or {}
    request_path_text = normalize_text(str(config.get("requestPath", "")))
    response_path_text = normalize_text(str(config.get("responsePath", "")))
    screenshot_path_text = normalize_text(str(config.get("screenshotPath", "")))
    blocking_issues: list[str] = []
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
        "sourceKind": "apiRuntimeCall",
        "apiRuntimeCall": {},
    }

    missing_fields = [
        field_name
        for field_name, field_value in {
            "apiRuntimeCall.requestPath": request_path_text,
            "apiRuntimeCall.responsePath": response_path_text,
            "apiRuntimeCall.screenshotPath": screenshot_path_text,
        }.items()
        if not field_value
    ]
    if missing_fields:
        blocking_issues.extend(
            f"{item.get('caseId', '<unknown>')} missing {field_name}"
            for field_name in missing_fields
        )
        base_payload["actualResult"] = "待補，缺少 Postman MCP / 真实接口调用证据路径。"
        return base_payload, blocking_issues

    expected_codes = expected_status_codes(config.get("expectedStatusCodes"))
    request_path = resolve_runtime_context_path(request_path_text, runtime_context)
    response_path = resolve_runtime_context_path(response_path_text, runtime_context)
    screenshot_path = resolve_runtime_context_path(screenshot_path_text, runtime_context)
    call_record, validation_issues = validate_api_runtime_call_artifacts(
        request_path=request_path,
        response_path=response_path,
        screenshot_path=screenshot_path,
        expected_codes=expected_codes,
    )
    base_payload["apiRuntimeCall"] = call_record
    base_payload["attachmentPaths"] = [
        path
        for path in [
            call_record.get("requestPath", ""),
            call_record.get("responsePath", ""),
            call_record.get("screenshotPath", ""),
        ]
        if normalize_text(str(path))
    ]

    if validation_issues:
        blocking_issues.extend(
            f"{item.get('caseId', '<unknown>')} {issue}" for issue in validation_issues
        )
        base_payload["actualResult"] = "待補，Postman MCP / 真实接口调用证据未完整或需先遮蔽敏感信息。"
        return base_payload, blocking_issues

    status_code = call_record.get("statusCode")
    expected_text = "、".join(str(code) for code in expected_codes)
    if call_record.get("status") == "passed":
        base_payload["status"] = "passed"
        base_payload["actualResult"] = (
            normalize_text(str(config.get("passActualResult", "")))
            or f"通過，Postman MCP / 真实接口调用返回 HTTP {status_code}，符合预期状态 {expected_text}。"
        )
    else:
        base_payload["status"] = "failed"
        base_payload["failureDetails"] = call_record.get("failureDetails", [])
        base_payload["actualResult"] = (
            normalize_text(str(config.get("failActualResult", "")))
            or f"失敗，Postman MCP / 真实接口调用返回 HTTP {status_code}，不在预期状态 {expected_text} 内。"
        )
    return base_payload, blocking_issues


def collect_source_results(
    manifest_path: Path,
    source_name: str,
    config: dict[str, Any],
    require_execution: bool,
) -> dict[str, Any]:
    agent_dir = manifest_path.parent
    command = normalize_text(str(config.get("command", "")))
    trx_path_text = normalize_text(str(config.get("trxPath", "")))
    results_dir_text = normalize_text(str(config.get("resultsDir", "")))
    timeout_seconds = int(config.get("timeoutSeconds", 600) or 600)
    fail_if_trx_missing = bool(config.get("failIfTrxMissing", True))
    has_locator = bool(command or trx_path_text or results_dir_text)

    if not require_execution and not has_locator:
        return {
            "trxPath": "",
            "tests": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "pending": 0},
            "sourceKind": source_name,
        }

    workspace_root = agent_dir
    clean_workspace = config.get("cleanWorkspace") or {}
    if bool(clean_workspace.get("enabled", False)):
        workspace_root = prepare_clean_workspace(agent_dir, clean_workspace)
    elif normalize_text(str(config.get("workingDirectory", ""))):
        workspace_root = resolve_path_with_workspace(
            agent_dir,
            agent_dir,
            str(config.get("workingDirectory", "")),
        )

    working_directory = (
        resolve_path_with_workspace(agent_dir, workspace_root, str(config.get("workingDirectory", "")))
        if normalize_text(str(config.get("workingDirectory", "")))
        else workspace_root
    )

    if command and require_execution:
        run_manifest_command(
            render_path_token(command, workspace_root, agent_dir),
            working_directory,
            timeout_seconds,
        )
    elif require_execution and fail_if_trx_missing:
        pass

    resolved_trx_path: Path | None = None
    if trx_path_text:
        resolved_trx_path = resolve_path_with_workspace(agent_dir, workspace_root, trx_path_text)
    elif results_dir_text:
        latest_trx = find_latest_trx(resolve_path_with_workspace(agent_dir, workspace_root, results_dir_text))
        if latest_trx:
            resolved_trx_path = Path(latest_trx)

    if resolved_trx_path is None:
        if fail_if_trx_missing:
            raise SystemExit(f"No TRX could be resolved from {source_name}.trxPath or {source_name}.resultsDir.")
        return {
            "trxPath": "",
            "tests": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "pending": 0},
            "sourceKind": source_name,
        }
    trx_payload = parse_trx(resolved_trx_path)
    trx_payload["sourceKind"] = source_name
    return trx_payload


def build_runtime_context(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    manifest_dir = manifest_path.parent.resolve()
    workspace_root = manifest_dir
    repo_root_text = normalize_text(
        str(((manifest.get("analysisContext") or {}).get("repoRoot") or ""))
    )
    context_root_text = normalize_text(
        str(((manifest.get("analysisContext") or {}).get("contextRoot") or ""))
    )
    repo_root = Path(repo_root_text).expanduser().resolve() if repo_root_text else workspace_root
    runtime_context = {
        "manifestPath": manifest_path.resolve(),
        "workspaceRoot": workspace_root,
        "repoRoot": repo_root,
    }
    if context_root_text:
        runtime_context["contextRoot"] = Path(context_root_text).expanduser().resolve()
    return runtime_context


def summarize_api_runtime_calls(calls: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(calls),
        "passed": sum(1 for call in calls if call.get("status") == "passed"),
        "failed": sum(1 for call in calls if call.get("status") == "failed"),
        "pending": sum(1 for call in calls if call.get("status") == "pending"),
        "skipped": 0,
    }


def collect_results(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    runtime_context = build_runtime_context(manifest_path, manifest)
    enabled_modes = {
        normalize_text(str(item.get("mode", "")))
        for section in manifest.get("sections", [])
        for item in section.get("items", [])
        if item.get("enabled", False)
    }

    test_sources = {
        "unitTest": collect_source_results(
            manifest_path,
            "unitTest",
            manifest.get("unitTest") or {},
            require_execution="unit_test" in enabled_modes,
        )
    }
    if "integration_test" in enabled_modes or manifest.get("integrationTest"):
        test_sources["integrationTest"] = collect_source_results(
            manifest_path,
            "integrationTest",
            manifest.get("integrationTest") or {},
            require_execution="integration_test" in enabled_modes,
        )
    if "api_runtime_call" in enabled_modes:
        test_sources["apiRuntimeCall"] = {
            "calls": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "pending": 0, "skipped": 0},
            "sourceKind": "apiRuntimeCall",
        }

    cases: list[dict[str, Any]] = []
    blocking_issues: list[str] = []
    for section in manifest.get("sections", []):
        for item in section.get("items", []):
            case_result, case_issues = evaluate_case(item, test_sources, runtime_context=runtime_context)
            cases.append(case_result)
            blocking_issues.extend(case_issues)

    api_runtime_calls = [
        case.get("apiRuntimeCall", {})
        for case in cases
        if case.get("sourceKind") == "apiRuntimeCall" and case.get("apiRuntimeCall")
    ]
    api_runtime_summary = summarize_api_runtime_calls(api_runtime_calls)
    if "api_runtime_call" in enabled_modes:
        test_sources["apiRuntimeCall"] = {
            "calls": api_runtime_calls,
            "summary": api_runtime_summary,
            "sourceKind": "apiRuntimeCall",
        }

    summary = {
        "passed": sum(1 for case in cases if case["status"] == "passed"),
        "failed": sum(1 for case in cases if case["status"] == "failed"),
        "manual": sum(1 for case in cases if case["status"] == "manual"),
        "pending": sum(1 for case in cases if case["status"] == "pending"),
        "skipped": sum(1 for case in cases if case["status"] == "skipped"),
        "not_in_run": sum(1 for case in cases if case["status"] == "not_in_run"),
    }

    payload = {
        "manifestPath": manifest_path.resolve().as_posix(),
        "trxPath": test_sources["unitTest"].get("trxPath", ""),
        "unitTestSummary": test_sources["unitTest"].get("summary", {}),
        "integrationTestSummary": test_sources.get("integrationTest", {}).get("summary", {}),
        "apiRuntimeCallSummary": api_runtime_summary,
        "sourceResults": test_sources,
        "summary": summary,
        "tests": test_sources["unitTest"].get("tests", []),
        "cases": cases,
        "blockingIssues": blocking_issues,
    }

    if blocking_issues:
        raise SystemExit("Report evidence validation failed: " + "; ".join(blocking_issues))
    return payload


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Collect UnitTest/TRX results for a DOCX report job.",
    )
    parser.add_argument("manifest_path", help="Path to the JSON manifest.")
    parser.add_argument("--output", required=True, help="Path to the results JSON to emit.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_path).expanduser().resolve()
    payload = collect_results(manifest_path)
    write_json(args.output, payload)
    print(f"Results written: {Path(args.output).expanduser().resolve().as_posix()}")


if __name__ == "__main__":
    main()
