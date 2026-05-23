#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PREPARE_SQL_FIXTURE = SKILL_DIR / "scripts" / "prepare_sql_fixture.py"
FUNCTION_CODE = "N.006"
API_ID = "N.006.setting.queryuserloginlog"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def no_sql_spec(api_id: str = API_ID) -> dict[str, Any]:
    return {
        "schemaVersion": "4.2.0",
        "apiId": api_id,
        "apiCategory": "Setting",
        "apiName": "QueryUserLoginLog",
        "backendApis": {},
        "businessLogic": {
            "steps": [{"step": 1, "title": "Read request", "details": "No database dependency."}],
            "sqlSpecs": [],
        },
        "codeHandoff": {
            "logicFlow": [],
            "queryContracts": [],
            "mappingRules": [],
            "dependencyHints": [],
            "legacyEvidence": [],
            "constraints": [],
            "unresolved": [],
        },
    }


def sql_spec(api_id: str = API_ID) -> dict[str, Any]:
    payload = no_sql_spec(api_id)
    payload["businessLogic"]["steps"] = [
        {
            "step": 1,
            "title": "Query login log",
            "details": "SELECT CUSTID, NAME FROM CustomerProfile WHERE CUSTID = @CustId",
        }
    ]
    payload["businessLogic"]["sqlSpecs"] = [
        {
            "id": "query_customer_profile",
            "sqlText": "SELECT CUSTID, NAME FROM CustomerProfile WHERE CUSTID = @CustId",
        }
    ]
    payload["codeHandoff"]["queryContracts"] = [
        {
            "id": "query_customer_profile",
            "sqlText": "SELECT CUSTID, NAME FROM CustomerProfile WHERE CUSTID = @CustId",
        }
    ]
    return payload


def setup_project(temp_dir: Path, api_spec: dict[str, Any]) -> dict[str, Path]:
    project_root = temp_dir / "FixtureProject"
    context_root = project_root / ".agent" / "context"
    execution_root = context_root / FUNCTION_CODE
    api_dir = execution_root / "apis" / API_ID
    project_root.mkdir()
    source_fingerprint = "sha256:fixture-spec"
    dump_json(
        context_root / "execution-batch.json",
        {
            "schemaVersion": "1.0.0",
            "activeFunctionCode": FUNCTION_CODE,
            "items": [{"functionCode": FUNCTION_CODE, "docxRef": ".agent/TSD/TSD.N.006_fixture_v1.0_20260408.docx", "order": 1}],
            "updatedAt": None,
            "updatedBy": "fixture",
        },
    )
    dump_json(
        execution_root / "execution-state.json",
        {
            "schemaVersion": "4.1.0",
            "executionId": FUNCTION_CODE,
            "specStatus": "done",
            "specPhase": "done",
            "codeStatus": "waiting_spec",
            "codePhase": "waiting_spec",
            "customExecutionValue": "keep-me",
        },
    )
    dump_json(
        execution_root / "api-checklist.json",
        {
            "schemaVersion": "4.1.0",
            "executionId": FUNCTION_CODE,
            "items": [
                {
                    "apiId": API_ID,
                    "apiCategory": "Setting",
                    "apiName": "QueryUserLoginLog",
                    "specStatus": "done",
                    "specPhase": "done",
                    "specSourceFingerprint": source_fingerprint,
                    "codeStatus": "pending",
                    "codePhase": "pending",
                    "customItemValue": "keep-me",
                }
            ],
        },
    )
    dump_json(
        api_dir / "manifest.json",
        {
            "schemaVersion": "4.1.0",
            "manifestType": "api",
            "apiId": API_ID,
            "apiCategory": "Setting",
            "apiName": "QueryUserLoginLog",
            "specStatus": "done",
            "specPhase": "done",
            "specSourceFingerprint": source_fingerprint,
            "codeStatus": "pending",
            "codePhase": "pending",
            "codeArtifacts": {
                "changePlan": None,
                "implementationReport": None,
                "diagnosisReport": None,
            },
            "customManifestValue": "keep-me",
            "lastMessage": None,
        },
    )
    dump_json(api_dir / f"{FUNCTION_CODE}_API_Spec.json", api_spec)
    return {
        "project_root": project_root,
        "context_root": context_root,
        "execution_root": execution_root,
        "api_dir": api_dir,
        "checklist_path": execution_root / "api-checklist.json",
        "execution_state_path": execution_root / "execution-state.json",
        "manifest_path": api_dir / "manifest.json",
        "db_fixture_report_path": api_dir / "db-fixture-report.json",
        "table_checks_path": api_dir / "table-checks.json",
        "seed_manifest_path": api_dir / "seed-manifest.json",
    }


def run_fixture(project_root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [
            sys.executable,
            str(PREPARE_SQL_FIXTURE),
            "--project-root",
            str(project_root),
            "--function-code",
            FUNCTION_CODE,
            "--api-id",
            API_ID,
            *extra_args,
        ],
        cwd=SKILL_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def load_state(paths: dict[str, Path]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return load_json(paths["execution_state_path"]), load_json(paths["checklist_path"]), load_json(paths["manifest_path"])


def assert_preserved_non_fixture_fields(paths: dict[str, Path]) -> None:
    execution_state, checklist, manifest = load_state(paths)
    item = checklist["items"][0]
    assert_true(execution_state["specStatus"] == "done", "fixture run must preserve execution specStatus")
    assert_true(execution_state["codeStatus"] == "waiting_spec", "fixture run must preserve execution codeStatus")
    assert_true(execution_state["customExecutionValue"] == "keep-me", "fixture run must preserve unrelated execution fields")
    assert_true(item["specStatus"] == "done", "fixture run must preserve checklist specStatus")
    assert_true(item["codeStatus"] == "pending", "fixture run must preserve checklist codeStatus")
    assert_true(item["customItemValue"] == "keep-me", "fixture run must preserve unrelated checklist fields")
    assert_true(manifest["specStatus"] == "done", "fixture run must preserve manifest specStatus")
    assert_true(manifest["codeStatus"] == "pending", "fixture run must preserve manifest codeStatus")
    assert_true(manifest["customManifestValue"] == "keep-me", "fixture run must preserve unrelated manifest fields")


def test_no_sql_dependency_skips_and_preserves_non_fixture_state() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir), no_sql_spec())
        completed = run_fixture(paths["project_root"], "--execution-mode", "prepare")
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        execution_state, checklist, manifest = load_state(paths)
        item = checklist["items"][0]
        assert_true(execution_state["fixtureStatus"] == "done", "all skipped fixture items should aggregate to done")
        assert_true(item["fixtureStatus"] == "skipped", "no SQL API should be skipped")
        assert_true(manifest["fixtureStatus"] == "skipped", "manifest should record skipped fixture status")
        report = load_json(paths["db_fixture_report_path"])
        table_checks = load_json(paths["table_checks_path"])
        assert_true(report["sqlFixtureRequired"] is False, "report should mark SQL fixture as not required")
        assert_true(table_checks["tables"] == [], "no SQL fixture should produce no table checks")
        assert_preserved_non_fixture_fields(paths)


def test_sql_dependency_without_db_target_blocks_missing_db_target() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir), sql_spec())
        completed = run_fixture(paths["project_root"], "--execution-mode", "prepare")
        assert_true(completed.returncode == 1, completed.stdout + completed.stderr)
        _, checklist, manifest = load_state(paths)
        item = checklist["items"][0]
        assert_true(item["fixtureStatus"] == "blocked", "missing DB target should block fixture prepare")
        assert_true(item["fixtureBlockReason"] == "missing_db_target", "missing DB target should be explicit")
        assert_true(manifest["fixtureBlockReason"] == "missing_db_target", "manifest should mirror missing DB target")
        report = load_json(paths["db_fixture_report_path"])
        assert_true(report["status"] == "blocked", "report should be blocked")
        assert_true(report["findings"][0]["blockReason"] == "missing_db_target", "report should expose missing DB target")
        assert_preserved_non_fixture_fields(paths)


def test_sql_dependency_with_db_target_without_schema_authority_blocks() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir), sql_spec())
        db_path = paths["project_root"] / "fixture.sqlite"
        completed = run_fixture(paths["project_root"], "--execution-mode", "prepare", "--db-target", f"sqlite:///{db_path}")
        assert_true(completed.returncode == 1, completed.stdout + completed.stderr)
        _, checklist, manifest = load_state(paths)
        item = checklist["items"][0]
        assert_true(item["fixtureStatus"] == "blocked", "missing schema authority should block")
        assert_true(item["fixtureBlockReason"] == "missing_schema_authority", "schema authority gap should use contract reason")
        assert_true(manifest["fixtureBlockReason"] == "missing_schema_authority", "manifest should mirror schema authority gap")
        table_checks = load_json(paths["table_checks_path"])
        assert_true(table_checks["tables"][0]["blockReason"] == "missing_schema_authority", "table check should expose schema authority gap")
        assert_preserved_non_fixture_fields(paths)


def test_sqlite_apply_creates_seeds_and_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir), sql_spec())
        authority_root = paths["project_root"] / ".agent" / "Reference" / "db"
        dump_text(
            authority_root / "customerprofile.sql",
            """
CREATE TABLE IF NOT EXISTS CustomerProfile (
    CUSTID TEXT PRIMARY KEY,
    NAME TEXT NOT NULL
);
""".lstrip(),
        )
        dump_text(
            authority_root / "customerprofile.seed.sql",
            """
INSERT INTO CustomerProfile (CUSTID, NAME)
SELECT 'C123456789', 'Fixture User'
WHERE NOT EXISTS (
    SELECT 1 FROM CustomerProfile WHERE CUSTID = 'C123456789'
);
""".lstrip(),
        )
        db_path = paths["project_root"] / "fixture.sqlite"
        completed = run_fixture(
            paths["project_root"],
            "--execution-mode",
            "apply",
            "--db-target",
            f"sqlite:///{db_path}",
            "--schema-authority-root",
            str(authority_root),
            "--allow-create-table",
            "--allow-seed",
        )
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        with closing(sqlite3.connect(db_path)) as conn:
            row_count = conn.execute("SELECT COUNT(*) FROM CustomerProfile").fetchone()[0]
        assert_true(row_count == 1, "first apply should insert one deterministic fixture row")
        _, checklist, manifest = load_state(paths)
        item = checklist["items"][0]
        assert_true(item["fixtureStatus"] == "done", "successful apply should mark checklist done")
        assert_true(manifest["fixtureStatus"] == "done", "successful apply should mark manifest done")
        seed_manifest = load_json(paths["seed_manifest_path"])
        assert_true(seed_manifest["executedStatementCount"] == 2, "first apply should execute schema and seed SQL")

        second = run_fixture(
            paths["project_root"],
            "--execution-mode",
            "apply",
            "--db-target",
            f"sqlite:///{db_path}",
            "--schema-authority-root",
            str(authority_root),
            "--allow-create-table",
            "--allow-seed",
        )
        assert_true(second.returncode == 0, second.stdout + second.stderr)
        with closing(sqlite3.connect(db_path)) as conn:
            row_count = conn.execute("SELECT COUNT(*) FROM CustomerProfile").fetchone()[0]
        assert_true(row_count == 1, "second apply must not duplicate seed rows")
        table_checks = load_json(paths["table_checks_path"])
        assert_true(table_checks["tables"][0]["action"] == "reuse", "second apply should reuse existing fixture data")
        assert_preserved_non_fixture_fields(paths)


def main() -> int:
    test_no_sql_dependency_skips_and_preserves_non_fixture_state()
    print("[pass] test_no_sql_dependency_skips_and_preserves_non_fixture_state")
    test_sql_dependency_without_db_target_blocks_missing_db_target()
    print("[pass] test_sql_dependency_without_db_target_blocks_missing_db_target")
    test_sql_dependency_with_db_target_without_schema_authority_blocks()
    print("[pass] test_sql_dependency_with_db_target_without_schema_authority_blocks")
    test_sqlite_apply_creates_seeds_and_is_idempotent()
    print("[pass] test_sqlite_apply_creates_seeds_and_is_idempotent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
