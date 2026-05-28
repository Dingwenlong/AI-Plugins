#!/usr/bin/env python3
"""Regression tests for multi-api leader orchestration."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from datetime import timedelta
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "orchestrate_multi_api.py"
SPEC = importlib.util.spec_from_file_location("orchestrate_multi_api", SCRIPT_PATH)
assert SPEC and SPEC.loader
orchestrate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrate)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_groups_overlapping_code_files() -> None:
    groups = orchestrate.build_workgroups(
        [
            {"apiId": "A", "codeFiles": ["Controllers/OrderController.cs", "Services/OrderService.cs"], "testFiles": []},
            {"apiId": "B", "codeFiles": ["Controllers/OrderController.cs", "Services/RefundService.cs"], "testFiles": []},
            {"apiId": "C", "codeFiles": ["Controllers/ProfileController.cs"], "testFiles": []},
        ]
    )
    assert len(groups) == 2
    merged = [group for group in groups if set(group["apiIds"]) == {"A", "B"}][0]
    assert merged["executionMode"] == "serial-within-group"
    assert merged["sharedFiles"] == ["Controllers/OrderController.cs"]


def test_plan_writes_claims_and_leader_run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        context = root / ".agent" / "context" / "D.001"
        write_json(context / "api-checklist.json", {"apis": [{"apiId": "api.one"}, {"apiId": "api.two"}]})
        write_json(context / "apis" / "api.one" / "change-plan.json", {"analysis": {"controllerFile": "Controllers/A.cs"}})
        write_json(context / "apis" / "api.two" / "change-plan.json", {"analysis": {"controllerFile": "Controllers/B.cs"}})

        result = orchestrate.write_plan(root / ".agent" / "context", "D.001", project_root=root, owner_prefix="agent")

        orchestration = context / "orchestration"
        assert (orchestration / "leader-run.json").exists()
        assert (orchestration / "api-workgroups.json").exists()
        assert (orchestration / "file-claims.json").exists()
        assert len(result["workGroups"]["workGroups"]) == 2
        claims = json.loads((orchestration / "file-claims.json").read_text(encoding="utf-8"))
        assert {claim["owner"] for claim in claims["claims"]} == {"agent-wg-001", "agent-wg-002"}


def test_missing_change_plan_blocks_plan() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        context = root / ".agent" / "context" / "D.001"
        write_json(context / "api-checklist.json", {"apis": [{"apiId": "api.one"}, {"apiId": "api.two"}]})
        write_json(context / "apis" / "api.one" / "change-plan.json", {"analysis": {"controllerFile": "Controllers/A.cs"}})

        result = orchestrate.write_plan(root / ".agent" / "context", "D.001", project_root=root, owner_prefix="agent")

        assert result["leaderRun"]["status"] == "blocked"
        assert any("api.two" in issue for issue in result["leaderRun"]["blockingIssues"])
        assert any(plan["apiId"] == "api.two" and plan["changePlanPath"] is None for plan in result["workGroups"]["apiPlans"])


def test_expired_claim_and_worker_output_validation() -> None:
    now = orchestrate.utc_now()
    claim = {
        "filePath": "Controllers/A.cs",
        "owner": "worker-wg-001",
        "status": "claimed",
        "expiresAt": orchestrate.iso_z(now - timedelta(minutes=1)),
    }
    assert orchestrate.is_claim_expired(claim, now)

    claims_doc = {
        "claims": [
            {
                "filePath": "Controllers/A.cs",
                "owner": "worker-wg-001",
                "status": "claimed",
                "expiresAt": orchestrate.iso_z(now + timedelta(minutes=30)),
            }
        ]
    }
    ok = orchestrate.validate_worker_modified_files(["Controllers/A.cs"], claims_doc, "worker-wg-001")
    bad = orchestrate.validate_worker_modified_files(["Controllers/B.cs"], claims_doc, "worker-wg-001")
    assert ok["allowed"]
    assert not bad["allowed"]
    assert bad["violations"] == ["Controllers/B.cs"]

    expired_doc = {
        "claims": [
            {
                "filePath": "Controllers/A.cs",
                "owner": "worker-wg-001",
                "status": "claimed",
                "expiresAt": orchestrate.iso_z(now - timedelta(minutes=5)),
            }
        ]
    }
    expired = orchestrate.validate_worker_modified_files(["Controllers/A.cs"], expired_doc, "worker-wg-001")
    assert not expired["allowed"]
    assert expired["expiredClaims"] == ["Controllers/A.cs"]


def test_final_assessment_blocks_without_ut_results_and_passes_with_results() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        function_context = Path(temp_dir) / "context" / "D.002"
        write_json(function_context / "spec-status.json", {"status": "done"})
        write_json(function_context / "fixture-status.json", {"status": "skipped"})
        write_json(function_context / "code-status.json", {"status": "tests_passed"})

        blocked = orchestrate.write_assessment(Path(temp_dir) / "context", "D.002")
        assert not blocked["passed"]
        assert any("05-ut-report" in issue for issue in blocked["blockingIssues"])

        write_json(function_context / "ut-results.json", {"status": "passed", "failed": 0, "pending": 0, "manual": 0})
        passed = orchestrate.write_assessment(Path(temp_dir) / "context", "D.002")
        assert passed["passed"]
        assert passed["conclusion"] == "符合需求"


def test_final_assessment_aggregates_all_api_status_files() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        function_context = Path(temp_dir) / "context" / "D.003"
        write_json(function_context / "api-checklist.json", {"apis": [{"apiId": "api.one"}, {"apiId": "api.two"}]})
        for api_id in ("api.one", "api.two"):
            api_dir = function_context / "apis" / api_id
            write_json(api_dir / "spec-status.json", {"status": "done"})
            write_json(api_dir / "fixture-status.json", {"status": "skipped"})
            write_json(api_dir / "ut-results.json", {"status": "passed", "failed": 0, "pending": 0, "manual": 0})
        write_json(function_context / "apis" / "api.one" / "code-status.json", {"status": "tests_passed"})
        write_json(function_context / "apis" / "api.two" / "code-status.json", {"status": "failed"})

        assessment = orchestrate.write_assessment(Path(temp_dir) / "context", "D.003")

        assert not assessment["passed"]
        code_gate = assessment["gateResults"]["04-code-validation"]
        assert "failed" in code_gate["statuses"]
        assert len(code_gate["sources"]) == 2
        assert any("04-code-validation" in issue for issue in assessment["blockingIssues"])


def test_final_assessment_blocks_expired_claims() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        function_context = Path(temp_dir) / "context" / "D.004"
        write_json(function_context / "spec-status.json", {"status": "done"})
        write_json(function_context / "fixture-status.json", {"status": "skipped"})
        write_json(function_context / "code-status.json", {"status": "tests_passed"})
        write_json(function_context / "ut-results.json", {"status": "passed", "failed": 0, "pending": 0, "manual": 0})
        write_json(
            function_context / "orchestration" / "file-claims.json",
            {
                "claims": [
                    {
                        "filePath": "Controllers/A.cs",
                        "owner": "worker-wg-001",
                        "status": "claimed",
                        "expiresAt": orchestrate.iso_z(orchestrate.utc_now() - timedelta(minutes=1)),
                    }
                ]
            },
        )

        assessment = orchestrate.write_assessment(Path(temp_dir) / "context", "D.004")

        assert not assessment["passed"]
        assert not assessment["gateResults"]["file-claims"]["passed"]
        assert any("file claim expired" in issue for issue in assessment["blockingIssues"])


def run() -> None:
    tests = [
        test_groups_overlapping_code_files,
        test_plan_writes_claims_and_leader_run,
        test_missing_change_plan_blocks_plan,
        test_expired_claim_and_worker_output_validation,
        test_final_assessment_blocks_without_ut_results_and_passes_with_results,
        test_final_assessment_aggregates_all_api_status_files,
        test_final_assessment_blocks_expired_claims,
    ]
    for test in tests:
        test()
        print(f"[ok] {test.__name__}")
    print(f"[ok] {len(tests)} multi-api leader regression tests passed")


if __name__ == "__main__":
    run()
