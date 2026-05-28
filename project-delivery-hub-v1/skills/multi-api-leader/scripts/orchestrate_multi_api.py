#!/usr/bin/env python3
"""Build multi-API workgroups, file claims, and final assessment state."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0.0"

CODE_FILE_KEYS = {
    "codeTargetFiles",
    "controllerFile",
    "interfaceFile",
    "serviceFile",
    "serviceFiles",
    "entityFile",
    "entityFiles",
    "targetFile",
    "targetFiles",
    "plannedFiles",
    "modifiedFiles",
    "newFiles",
}

TEST_FILE_KEYS = {
    "unitTestTargetFiles",
    "integrationTestTargetFiles",
    "testTargetFiles",
    "testFiles",
    "testCodeFiles",
    "testProjectFiles",
}

PASS_STATUSES = {"done", "passed", "success", "completed", "ready", "tests_passed", "skipped", "not_required"}
SPEC_PASS_STATUSES = {"done", "passed", "success", "completed", "ready"}
FIXTURE_PASS_STATUSES = {"done", "passed", "success", "completed", "ready", "skipped", "not_required"}
CODE_PASS_STATUSES = {"done", "passed", "success", "completed", "ready", "tests_passed"}
UT_PASS_STATUSES = {"done", "passed", "success", "completed", "ready", "tests_passed"}
BLOCK_STATUSES = {"blocked", "blocking", "failed", "fail", "error", "pending", "manual", "not_ready"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalize_claim_path(value: Any, project_root: str | Path | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    path = Path(text)
    if path.is_absolute() and project_root:
        try:
            text = str(path.resolve().relative_to(Path(project_root).resolve()))
        except ValueError:
            text = str(path)

    text = text.replace("\\", "/")
    text = re.sub(r"/+", "/", text).strip("/")
    return text or None


def _iter_file_values(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_file_values(item)
    elif isinstance(value, dict):
        for key in ("file", "path", "filePath", "targetFile"):
            if key in value:
                yield from _iter_file_values(value[key])


def collect_file_values(data: Any, key_names: set[str], project_root: str | Path | None = None) -> list[str]:
    files: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in key_names:
                    for raw_file in _iter_file_values(value):
                        normalized = normalize_claim_path(raw_file, project_root)
                        if normalized:
                            files.add(normalized)
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(data)
    return sorted(files, key=str.lower)


def discover_api_ids(function_context: Path) -> list[str]:
    checklist_path = function_context / "api-checklist.json"
    api_ids: list[str] = []
    if checklist_path.exists():
        checklist = read_json(checklist_path)
        candidates: Any
        if isinstance(checklist, dict):
            candidates = checklist.get("apis") or checklist.get("items") or checklist.get("apiChecklist") or []
        else:
            candidates = checklist
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, str):
                    api_ids.append(item)
                elif isinstance(item, dict):
                    api_id = item.get("apiId") or item.get("id") or item.get("name")
                    if api_id:
                        api_ids.append(str(api_id))

    apis_root = function_context / "apis"
    if apis_root.exists():
        for child in apis_root.iterdir():
            if child.is_dir() and child.name not in api_ids:
                api_ids.append(child.name)

    return sorted(dict.fromkeys(api_ids), key=str.lower)


def find_change_plan(function_context: Path, api_id: str) -> Path | None:
    candidates = [
        function_context / "apis" / api_id / "change-plan.json",
        function_context / api_id / "change-plan.json",
        function_context / "change-plan.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_api_plans(function_context: Path, project_root: str | Path | None, include_tests: bool) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    plans: list[dict[str, Any]] = []
    for api_id in discover_api_ids(function_context):
        change_plan_path = find_change_plan(function_context, api_id)
        if not change_plan_path:
            warnings.append(f"Missing change-plan.json for API {api_id}")
            plans.append({"apiId": api_id, "changePlanPath": None, "codeFiles": [], "testFiles": []})
            continue
        change_plan = read_json(change_plan_path)
        code_files = collect_file_values(change_plan, CODE_FILE_KEYS, project_root)
        test_files = collect_file_values(change_plan, TEST_FILE_KEYS, project_root) if include_tests else []
        plans.append(
            {
                "apiId": api_id,
                "changePlanPath": normalize_claim_path(change_plan_path, function_context),
                "codeFiles": code_files,
                "testFiles": test_files,
            }
        )
    return plans, warnings


def build_workgroups(api_plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    api_ids = [str(plan["apiId"]) for plan in api_plans]
    api_files = {
        str(plan["apiId"]): set(plan.get("codeFiles") or []) | set(plan.get("testFiles") or [])
        for plan in api_plans
    }

    file_to_apis: dict[str, set[str]] = defaultdict(set)
    for api_id, files in api_files.items():
        for file_path in files:
            file_to_apis[file_path.lower()].add(api_id)

    graph: dict[str, set[str]] = {api_id: set() for api_id in api_ids}
    for owners in file_to_apis.values():
        if len(owners) > 1:
            for owner in owners:
                graph[owner].update(owners - {owner})

    visited: set[str] = set()
    groups: list[dict[str, Any]] = []
    for api_id in sorted(api_ids, key=str.lower):
        if api_id in visited:
            continue
        queue: deque[str] = deque([api_id])
        visited.add(api_id)
        component: list[str] = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(graph[current], key=str.lower):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        component_files = sorted(set().union(*(api_files[item] for item in component)), key=str.lower)
        shared_files = []
        for file_path in component_files:
            owners = [item for item in component if file_path in api_files[item]]
            if len(owners) > 1:
                shared_files.append(file_path)

        groups.append(
            {
                "workGroupId": f"wg-{len(groups) + 1:03d}",
                "apiIds": sorted(component, key=str.lower),
                "claimFiles": component_files,
                "sharedFiles": shared_files,
                "executionMode": "serial-within-group" if len(component) > 1 or shared_files else "parallel-eligible",
            }
        )
    return groups


def build_claims(function_code: str, workgroups: list[dict[str, Any]], owner_prefix: str, lease_minutes: int) -> dict[str, Any]:
    now = utc_now()
    expires = now + timedelta(minutes=lease_minutes)
    claims = []
    for group in workgroups:
        owner = f"{owner_prefix}-{group['workGroupId']}"
        for file_path in group.get("claimFiles", []):
            claims.append(
                {
                    "filePath": file_path,
                    "owner": owner,
                    "workGroupId": group["workGroupId"],
                    "apiIds": group["apiIds"],
                    "status": "claimed",
                    "claimedAt": iso_z(now),
                    "expiresAt": iso_z(expires),
                }
            )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "functionCode": function_code,
        "generatedAt": iso_z(now),
        "claims": sorted(claims, key=lambda item: (item["workGroupId"], item["filePath"].lower())),
    }


def write_plan(
    context_root: str | Path,
    function_code: str,
    project_root: str | Path | None = None,
    include_tests: bool = False,
    owner_prefix: str = "worker",
    lease_minutes: int = 240,
) -> dict[str, Any]:
    function_context = Path(context_root) / function_code
    orchestration_root = function_context / "orchestration"
    api_plans, warnings = load_api_plans(function_context, project_root, include_tests)
    blocking_issues = list(warnings)
    workgroups = build_workgroups(api_plans)
    now = utc_now()

    workgroups_doc = {
        "schemaVersion": SCHEMA_VERSION,
        "functionCode": function_code,
        "generatedAt": iso_z(now),
        "includeTests": include_tests,
        "apiPlans": api_plans,
        "workGroups": workgroups,
        "blockingIssues": blocking_issues,
    }
    claims_doc = build_claims(function_code, workgroups, owner_prefix, lease_minutes)
    leader_run = {
        "schemaVersion": SCHEMA_VERSION,
        "functionCode": function_code,
        "runId": f"leader-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "phase": "04-plan" if not include_tests else "05-plan",
        "status": "blocked" if blocking_issues else "planned",
        "generatedAt": iso_z(now),
        "workGroups": [
            {
                "workGroupId": group["workGroupId"],
                "apiIds": group["apiIds"],
                "owner": f"{owner_prefix}-{group['workGroupId']}",
                "claimFileCount": len(group.get("claimFiles", [])),
                "executionMode": group["executionMode"],
            }
            for group in workgroups
        ],
        "warnings": [],
        "blockingIssues": blocking_issues,
    }

    write_json(orchestration_root / "api-workgroups.json", workgroups_doc)
    write_json(orchestration_root / "file-claims.json", claims_doc)
    write_json(orchestration_root / "leader-run.json", leader_run)
    return {"leaderRun": leader_run, "workGroups": workgroups_doc, "fileClaims": claims_doc}


def parse_datetime(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def is_claim_expired(claim: dict[str, Any], now: datetime | None = None) -> bool:
    expires_at = claim.get("expiresAt")
    if not expires_at:
        return True
    current = now or utc_now()
    try:
        expires = parse_datetime(str(expires_at))
    except ValueError:
        return True
    return expires <= current.astimezone(timezone.utc)


def validate_worker_modified_files(modified_files: Iterable[str], claims_doc: dict[str, Any], owner: str) -> dict[str, Any]:
    now = utc_now()
    owner_claims = [
        claim
        for claim in claims_doc.get("claims", [])
        if isinstance(claim, dict) and claim.get("owner") == owner and claim.get("status") == "claimed"
    ]
    expired_claims = [
        normalize_claim_path(claim.get("filePath"))
        for claim in owner_claims
        if is_claim_expired(claim, now)
    ]
    expired_claims = [file_path for file_path in expired_claims if file_path]
    allowed = set()
    for claim in owner_claims:
        if is_claim_expired(claim, now):
            continue
        normalized = normalize_claim_path(claim.get("filePath"))
        if normalized:
            allowed.add(normalized.lower())
    normalized_files = [normalize_claim_path(file_path) for file_path in modified_files]
    normalized_files = [file_path for file_path in normalized_files if file_path]
    violations = [file_path for file_path in normalized_files if file_path.lower() not in allowed]
    blocking_issues = []
    if expired_claims:
        blocking_issues.append(f"Expired file claims for {owner}: {', '.join(sorted(expired_claims, key=str.lower))}")
    if violations:
        blocking_issues.append(f"Unauthorized modifiedFiles for {owner}: {', '.join(sorted(violations, key=str.lower))}")
    return {
        "owner": owner,
        "allowed": len(violations) == 0 and len(expired_claims) == 0,
        "modifiedFiles": normalized_files,
        "violations": violations,
        "expiredClaims": sorted(expired_claims, key=str.lower),
        "blockingIssues": blocking_issues,
    }


def relative_status_source(function_context: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(function_context.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def find_status_files_in_dir(directory: Path, names: list[str]) -> list[Path]:
    paths = []
    for name in names:
        candidate = directory / name
        if candidate.exists() and candidate.is_file():
            paths.append(candidate)
    return paths


def read_status_documents(function_context: Path, names: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    documents: list[dict[str, Any]] = []
    root_paths = find_status_files_in_dir(function_context, names)
    seen: set[Path] = set()
    for path in root_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        documents.append({"apiId": None, "source": relative_status_source(function_context, path), "data": read_json(path)})

    missing_api_ids: list[str] = []
    apis_root = function_context / "apis"
    if apis_root.exists():
        for api_id in discover_api_ids(function_context):
            api_dir = apis_root / api_id
            matches = find_status_files_in_dir(api_dir, names)
            if not matches and not root_paths:
                missing_api_ids.append(api_id)
            for path in matches:
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                documents.append(
                    {
                        "apiId": api_id,
                        "source": relative_status_source(function_context, path),
                        "data": read_json(path),
                    }
                )
    return documents, missing_api_ids


def has_blocking_value(data: Any) -> bool:
    if isinstance(data, dict):
        for key, value in data.items():
            lowered = str(key).lower()
            if "blocking" in lowered and value not in (False, None, [], {}, "", 0):
                return True
            if has_blocking_value(value):
                return True
    elif isinstance(data, list):
        return any(has_blocking_value(item) for item in data)
    elif isinstance(data, str):
        return data.strip().lower() in BLOCK_STATUSES
    return False


def collect_status_values(data: Any) -> list[str]:
    values: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            lowered = str(key).lower()
            if lowered.endswith("status") or lowered in {"status", "result", "conclusion"}:
                if isinstance(value, str):
                    values.append(value.strip().lower())
            values.extend(collect_status_values(value))
    elif isinstance(data, list):
        for item in data:
            values.extend(collect_status_values(item))
    return values


def count_named(data: Any, names: set[str]) -> int:
    count = 0
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in names:
                if isinstance(value, bool):
                    count += int(value)
                elif isinstance(value, (int, float)):
                    count += int(value)
                elif isinstance(value, list):
                    count += len(value)
                elif value:
                    count += 1
            count += count_named(value, names)
    elif isinstance(data, list):
        for item in data:
            count += count_named(item, names)
    return count


def evaluate_status_gate(
    label: str,
    data: Any | None,
    allowed_statuses: set[str],
    *,
    sources: list[str] | None = None,
    missing_api_ids: list[str] | None = None,
) -> dict[str, Any]:
    sources = sources or []
    missing_api_ids = missing_api_ids or []
    if data is None or (isinstance(data, list) and not data):
        return {
            "label": label,
            "passed": False,
            "status": "missing",
            "sources": sources,
            "missingApiIds": missing_api_ids,
            "blockingIssues": [f"{label} status missing"],
        }
    statuses = collect_status_values(data)
    blocking = has_blocking_value(data)
    passed = bool(statuses) and all(status in allowed_statuses for status in statuses) and not blocking and not missing_api_ids
    issues = []
    if not statuses:
        issues.append(f"{label} has no status value")
    if blocking:
        issues.append(f"{label} contains blocking status")
    if statuses and not all(status in allowed_statuses for status in statuses):
        issues.append(f"{label} status not passing: {', '.join(sorted(set(statuses)))}")
    if missing_api_ids:
        issues.append(f"{label} missing for APIs: {', '.join(sorted(missing_api_ids, key=str.lower))}")
    return {
        "label": label,
        "passed": passed,
        "statuses": statuses,
        "sources": sources,
        "missingApiIds": missing_api_ids,
        "blockingIssues": issues,
    }


def evaluate_ut_gate(data: Any | None, *, sources: list[str] | None = None, missing_api_ids: list[str] | None = None) -> dict[str, Any]:
    gate = evaluate_status_gate("05-ut-report", data, UT_PASS_STATUSES, sources=sources, missing_api_ids=missing_api_ids)
    if data is None:
        return gate
    failed_count = count_named(data, {"failed", "failures", "failedcount"})
    pending_count = count_named(data, {"pending", "pendingcount"})
    manual_count = count_named(data, {"manual", "manualcount", "manualitems"})
    extra_issues = []
    if failed_count:
        extra_issues.append(f"05-ut-report failed count is {failed_count}")
    if pending_count:
        extra_issues.append(f"05-ut-report pending count is {pending_count}")
    if manual_count:
        extra_issues.append(f"05-ut-report manual count is {manual_count}")
    gate["failedCount"] = failed_count
    gate["pendingCount"] = pending_count
    gate["manualCount"] = manual_count
    gate["blockingIssues"].extend(extra_issues)
    gate["passed"] = gate["passed"] and failed_count == 0 and pending_count == 0 and manual_count == 0
    return gate


def read_status_bundle(function_context: Path, names: list[str]) -> tuple[list[Any] | None, list[str], list[str]]:
    documents, missing_api_ids = read_status_documents(function_context, names)
    if not documents:
        return None, [], missing_api_ids
    return [document["data"] for document in documents], [str(document["source"]) for document in documents], missing_api_ids


def evaluate_claim_gate(function_context: Path) -> dict[str, Any]:
    path = function_context / "orchestration" / "file-claims.json"
    if not path.exists():
        return {"label": "file-claims", "passed": True, "status": "not_required", "blockingIssues": [], "sources": []}
    claims_doc = read_json(path)
    claims = claims_doc.get("claims") if isinstance(claims_doc, dict) else []
    now = utc_now()
    expired = []
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict) or not is_claim_expired(claim, now):
                continue
            expired.append(
                {
                    "filePath": normalize_claim_path(claim.get("filePath")) or "",
                    "owner": str(claim.get("owner") or ""),
                    "expiresAt": str(claim.get("expiresAt") or ""),
                }
            )
    issues = [
        f"file claim expired: {item['filePath']} ({item['owner']})"
        for item in expired
    ]
    return {
        "label": "file-claims",
        "passed": not issues,
        "status": "passed" if not issues else "blocked",
        "sources": [relative_status_source(function_context, path)],
        "expiredClaims": expired,
        "blockingIssues": issues,
    }


def write_assessment(context_root: str | Path, function_code: str) -> dict[str, Any]:
    function_context = Path(context_root) / function_code
    orchestration_root = function_context / "orchestration"

    spec_status, spec_sources, spec_missing = read_status_bundle(function_context, ["spec-status.json", "specStatus.json", "spec-results.json"])
    fixture_status, fixture_sources, fixture_missing = read_status_bundle(function_context, ["fixture-status.json", "fixtureStatus.json", "db-fixture-report.json"])
    code_status, code_sources, code_missing = read_status_bundle(function_context, ["code-status.json", "codeStatus.json", "code-validation.json", "test-evidence.json"])
    ut_status, ut_sources, ut_missing = read_status_bundle(function_context, ["ut-results.json", "utResults.json", "report-results.json", "test-results.json"])

    gates = {
        "02-spec": evaluate_status_gate("02-spec", spec_status, SPEC_PASS_STATUSES, sources=spec_sources, missing_api_ids=spec_missing),
        "03-fixture": evaluate_status_gate("03-fixture", fixture_status, FIXTURE_PASS_STATUSES, sources=fixture_sources, missing_api_ids=fixture_missing),
        "04-code-validation": evaluate_status_gate("04-code-validation", code_status, CODE_PASS_STATUSES, sources=code_sources, missing_api_ids=code_missing),
        "05-ut-report": evaluate_ut_gate(ut_status, sources=ut_sources, missing_api_ids=ut_missing),
        "file-claims": evaluate_claim_gate(function_context),
    }
    blocking = []
    for gate in gates.values():
        blocking.extend(gate.get("blockingIssues", []))

    passed = all(gate.get("passed") for gate in gates.values())
    assessment = {
        "schemaVersion": SCHEMA_VERSION,
        "functionCode": function_code,
        "generatedAt": iso_z(utc_now()),
        "passed": passed,
        "conclusion": "符合需求" if passed else "不符合需求，存在 blocking 或未完成 gate",
        "gateResults": gates,
        "blockingIssues": blocking,
        "openItems": blocking,
    }
    write_json(orchestration_root / "final-assessment.json", assessment)
    return assessment


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--agent-root", default=None)
    parser.add_argument("--context-root", default=None)
    parser.add_argument("--function-code", required=True)
    parser.add_argument("--mode", choices=["plan", "assess"], default="plan")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--owner-prefix", default="worker")
    parser.add_argument("--lease-minutes", type=int, default=240)
    return parser


def resolve_context_root(args: argparse.Namespace) -> Path:
    if args.context_root:
        return Path(args.context_root)
    if args.agent_root:
        return Path(args.agent_root) / "context"
    if args.project_root:
        return Path(args.project_root) / ".agent" / "context"
    return Path(os.getcwd()) / ".agent" / "context"


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    context_root = resolve_context_root(args)

    if args.mode == "plan":
        result = write_plan(
            context_root=context_root,
            function_code=args.function_code,
            project_root=args.project_root,
            include_tests=args.include_tests,
            owner_prefix=args.owner_prefix,
            lease_minutes=args.lease_minutes,
        )
        print(json.dumps({"status": result["leaderRun"]["status"], "workGroupCount": len(result["workGroups"]["workGroups"])}, ensure_ascii=False))
    else:
        result = write_assessment(context_root=context_root, function_code=args.function_code)
        print(json.dumps({"passed": result["passed"], "conclusion": result["conclusion"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
