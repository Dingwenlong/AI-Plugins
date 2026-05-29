from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from analyze_module_scope import build_module_scope
from apply_manifest_gap_fixes import apply_gap_fixes, load_binding_rules
from build_coverage_gap import build_gap_payload
from classify_template_items import build_classification
from collect_unittest_results import build_runtime_context, evaluate_case
from docx_report_utils import (
    build_manifest_from_outline,
    load_report_outline,
    today_slash,
)
from feature_tester_map import resolve_feature_tester_name


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def delete_path_if_exists(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def resolve_api_root(raw_path: str) -> Path:
    api_root = Path(raw_path).expanduser().resolve()
    if not api_root.exists():
        raise SystemExit(f"api root not found: {api_root.as_posix()}")
    if not (api_root / "manifest.json").exists():
        raise SystemExit(f"manifest.json not found under api root: {api_root.as_posix()}")
    return api_root


def infer_context_root(api_root: Path) -> Path:
    if api_root.parent.name != "apis":
        raise SystemExit(f"api root must be .agent/context/<functionCode>/apis/<apiId>: {api_root.as_posix()}")
    return api_root.parent.parent


def infer_agent_root(context_root: Path) -> Path:
    if context_root.parent.name != "context":
        raise SystemExit(f"context root must be .agent/context/<functionCode>: {context_root.as_posix()}")
    return context_root.parent.parent.resolve()


def ensure_required_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(f"{label} not found: {path.as_posix()}")
    return path


def default_output_job(context_root: Path) -> Path:
    return context_root / "ut-report" / "report-job.json"


def default_output_docx(context_root: Path, report_docx: Path) -> Path:
    report_date = date.today().strftime("%Y%m%d")
    return context_root / "ut-report" / f"{context_root.name}_API_UT 測試報告 {report_date}.docx"


def resolve_repo_root(project_root: str, context_root: Path) -> Path:
    project_root_text = normalize_text(project_root)
    if project_root_text:
        return Path(project_root_text).expanduser().resolve()
    return context_root.parents[1].resolve()


def sanitize_path_segment(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return "unknown"
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)


def build_clean_workspace_target(repo_root: Path, api_id: str) -> Path:
    repo_root = repo_root.resolve()
    candidate = repo_root.parent / ".codex-report-workspaces" / repo_root.name / sanitize_path_segment(api_id) / "integration"
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        return candidate
    return Path(tempfile.gettempdir()) / "codex-report-workspaces" / repo_root.name / sanitize_path_segment(api_id) / "integration"


def make_test_entry(name: str, source_kind: str) -> dict[str, Any]:
    return {
        "testName": name,
        "status": "passed",
        "durationMs": 0,
        "errorSummary": "",
        "errorMessage": "",
        "attachments": [],
        "sourceKind": source_kind,
    }


def summarize_tests(names: list[str]) -> dict[str, int]:
    return {
        "total": len(names),
        "passed": len(names),
        "failed": 0,
        "skipped": 0,
        "pending": 0,
    }


def build_seed_source_results(test_evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    unit_names = [
        normalize_text(name)
        for name in ((test_evidence.get("testNames") or {}).get("unit") or [])
        if normalize_text(name)
    ]
    integration_names = [
        normalize_text(name)
        for name in ((test_evidence.get("testNames") or {}).get("integration") or [])
        if normalize_text(name)
    ]
    return {
        "unitTest": {
            "trxPath": "",
            "tests": [make_test_entry(name, "unitTest") for name in unit_names],
            "summary": summarize_tests(unit_names),
            "sourceKind": "unitTest",
        },
        "integrationTest": {
            "trxPath": "",
            "tests": [make_test_entry(name, "integrationTest") for name in integration_names],
            "summary": summarize_tests(integration_names),
            "sourceKind": "integrationTest",
        },
    }


def build_seed_results(
    manifest: dict[str, Any],
    source_results: dict[str, dict[str, Any]],
    manifest_path: Path,
) -> dict[str, Any]:
    runtime_context = build_runtime_context(manifest_path, manifest)
    cases: list[dict[str, Any]] = []
    blocking_issues: list[str] = []
    for section in manifest.get("sections") or []:
        for item in section.get("items") or []:
            case_result, case_issues = evaluate_case(item, source_results, runtime_context=runtime_context)
            cases.append(case_result)
            blocking_issues.extend(case_issues)

    summary = {
        "passed": sum(1 for case in cases if case.get("status") == "passed"),
        "failed": sum(1 for case in cases if case.get("status") == "failed"),
        "manual": sum(1 for case in cases if case.get("status") == "manual"),
        "pending": sum(1 for case in cases if case.get("status") == "pending"),
        "skipped": sum(1 for case in cases if case.get("status") == "skipped"),
        "not_in_run": sum(1 for case in cases if case.get("status") == "not_in_run"),
    }
    return {
        "manifestPath": manifest_path.as_posix(),
        "trxPath": "",
        "unitTestSummary": source_results["unitTest"]["summary"],
        "integrationTestSummary": source_results["integrationTest"]["summary"],
        "sourceResults": source_results,
        "summary": summary,
        "tests": source_results["unitTest"]["tests"],
        "cases": cases,
        "blockingIssues": blocking_issues,
    }


def configure_unit_test_block(manifest: dict[str, Any], test_evidence: dict[str, Any], repo_root: Path) -> None:
    unit_project = normalize_text(test_evidence.get("unitTestProject"))
    unit_results_dir = normalize_text(((test_evidence.get("trxHints") or {}).get("unit")))
    manifest["unitTest"]["trxPath"] = ""
    manifest["unitTest"]["resultsDir"] = unit_results_dir
    manifest["unitTest"]["workingDirectory"] = repo_root.as_posix()
    manifest["unitTest"]["timeoutSeconds"] = 900
    manifest["unitTest"]["failIfTrxMissing"] = True
    if unit_project:
        project_path = (repo_root / unit_project).resolve().as_posix()
        manifest["unitTest"]["command"] = (
            f'dotnet test "{project_path}" '
            '--no-build '
            f'--logger "trx;LogFileName={Path(unit_project).stem}.trx" '
            f'--results-directory "{unit_results_dir}" '
            '-p:UseSharedCompilation=false -nodeReuse:false -p:ProduceReferenceAssembly=false /m:1'
        )
    else:
        manifest["unitTest"]["command"] = ""


def configure_integration_test_block(
    manifest: dict[str, Any],
    test_evidence: dict[str, Any],
    repo_root: Path,
) -> None:
    integration_project = normalize_text(test_evidence.get("integrationTestProject"))
    integration_results_dir = normalize_text(((test_evidence.get("trxHints") or {}).get("integration")))
    manifest["integrationTest"]["trxPath"] = ""
    manifest["integrationTest"]["resultsDir"] = integration_results_dir
    manifest["integrationTest"]["workingDirectory"] = repo_root.as_posix()
    manifest["integrationTest"]["timeoutSeconds"] = 1200
    manifest["integrationTest"]["failIfTrxMissing"] = bool(integration_project)
    manifest["integrationTest"]["cleanWorkspace"] = {
        "enabled": False,
        "sourceRoot": repo_root.as_posix(),
        "targetRoot": "",
        "excludeDirNames": ["bin", "obj", ".vs", "TestResults"],
    }
    if integration_project:
        project_path = (repo_root / integration_project).resolve().as_posix()
        manifest["integrationTest"]["command"] = (
            f'dotnet test "{project_path}" '
            '--no-build '
            f'--logger "trx;LogFileName={Path(integration_project).stem}.trx" '
            f'--results-directory "{integration_results_dir}" '
            '-p:UseSharedCompilation=false -nodeReuse:false -p:ProduceReferenceAssembly=false /m:1'
        )
    else:
        manifest["integrationTest"]["command"] = ""


def aggregate_autofix_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    for report in reports:
        changes.extend(report.get("changes") or [])
        suggestions.extend(report.get("suggestions") or [])

    module_code = ""
    for report in reports:
        module_code = normalize_text(report.get("moduleCode"))
        if module_code:
            break
    return {
        "moduleCode": module_code,
        "passCount": len(reports),
        "appliedChangeCount": len(changes),
        "changes": changes,
        "suggestions": suggestions,
    }


def cleanup_api_report_artifacts(api_root: Path, output_job: Path, output_docx: Path) -> None:
    if output_job.parent.resolve() == api_root.resolve():
        return

    stale_paths = [
        api_root / "module-scope.json",
        api_root / "template-classification.json",
        api_root / "coverage-gap.json",
        api_root / "report-job.json",
        api_root / "report-job.results.json",
        api_root / "report-job.autofix-report.json",
        api_root / output_docx.name,
        api_root / "report-workspace",
    ]
    for stale_path in stale_paths:
        delete_path_if_exists(stale_path)


def bootstrap_report_job(
    api_root: Path,
    report_docx: Path,
    output_job: Path,
    output_docx: Path,
) -> None:
    ensure_required_file(api_root / "manifest.json", "manifest")
    ensure_required_file(api_root / "change-plan.json", "change-plan")
    test_evidence_path = ensure_required_file(api_root / "test-evidence.json", "test-evidence")
    context_root = infer_context_root(api_root)
    test_evidence = load_json(test_evidence_path)
    repo_root = resolve_repo_root(test_evidence.get("projectRoot", ""), context_root)

    outline = load_report_outline(report_docx)
    report_job = build_manifest_from_outline(outline, output_docx=output_docx.as_posix())
    report_job["analysisContext"] = {
        "repoRoot": repo_root.as_posix(),
        "contextRoot": context_root.as_posix(),
    }
    report_job["metadata"]["apiDisplayName"] = (
        normalize_text(test_evidence.get("apiDisplayName")) or report_job["metadata"]["apiDisplayName"]
    )
    report_job["metadata"]["functionCode"] = context_root.name
    report_job["metadata"]["tester"] = resolve_feature_tester_name(context_root.name, agent_root=infer_agent_root(context_root))
    report_job["metadata"]["testDate"] = normalize_text(report_job["metadata"].get("testDate")) or today_slash()

    configure_unit_test_block(report_job, test_evidence, repo_root)
    configure_integration_test_block(report_job, test_evidence, repo_root)

    module_scope = build_module_scope(context_root)
    classification = build_classification(module_scope, report_job)
    binding_rules = load_binding_rules()
    source_results = build_seed_source_results(test_evidence)
    autofix_passes: list[dict[str, Any]] = []

    for _ in range(2):
        seed_results = build_seed_results(report_job, source_results, output_job)
        coverage_gap = build_gap_payload(classification, report_job, seed_results)
        fix_report = apply_gap_fixes(report_job, coverage_gap, seed_results, binding_rules)
        autofix_passes.append(fix_report)
        if int(fix_report.get("appliedChangeCount") or 0) <= 0:
            break

    final_seed_results = build_seed_results(report_job, source_results, output_job)
    final_coverage_gap = build_gap_payload(classification, report_job, final_seed_results)
    autofix_report = aggregate_autofix_reports(autofix_passes)

    output_job.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_job, report_job)
    write_json(output_job.parent / "module-scope.json", module_scope)
    write_json(output_job.parent / "template-classification.json", classification)
    write_json(output_job.parent / "coverage-gap.json", final_coverage_gap)
    write_json(output_job.with_name(f"{output_job.stem}.autofix-report.json"), autofix_report)
    cleanup_api_report_artifacts(api_root, output_job, output_docx)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Bootstrap a module-level DOCX report-job.json from .agent/context API execution artifacts.",
    )
    parser.add_argument("--api-root", required=True, help="Path to .agent/context/<functionCode>/apis/<apiId>.")
    parser.add_argument("--report-docx", required=True, help="Path to the source report DOCX.")
    parser.add_argument("--output-job", help="Optional output path for report-job.json.")
    parser.add_argument("--output-docx", help="Optional output path for the revised DOCX.")
    args = parser.parse_args()

    api_root = resolve_api_root(args.api_root)
    context_root = infer_context_root(api_root)
    report_docx = ensure_required_file(Path(args.report_docx).expanduser().resolve(), "report DOCX")
    output_job = Path(args.output_job).expanduser().resolve() if args.output_job else default_output_job(context_root)
    output_docx = (
        Path(args.output_docx).expanduser().resolve()
        if args.output_docx
        else default_output_docx(context_root, report_docx)
    )

    bootstrap_report_job(api_root, report_docx, output_job, output_docx)
    print(f"Report job created: {output_job.as_posix()}")
    print(f"Output DOCX: {output_docx.as_posix()}")


if __name__ == "__main__":
    main()
