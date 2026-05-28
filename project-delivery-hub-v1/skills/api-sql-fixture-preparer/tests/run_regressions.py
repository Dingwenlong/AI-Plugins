#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import importlib.util
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
PREPARE_SQL_FIXTURE = SKILL_DIR / "scripts" / "prepare_sql_fixture.py"
FUNCTION_CODE = "N.006"
API_ID = "N.006.setting.queryuserloginlog"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("prepare_sql_fixture", PREPARE_SQL_FIXTURE)
assert SPEC and SPEC.loader
prepare_sql_fixture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prepare_sql_fixture
SPEC.loader.exec_module(prepare_sql_fixture)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_appsettings(project_root: Path, connection_name: str, connection_string: str) -> None:
    dump_json(
        project_root / "Api" / "appsettings.json",
        {"ConnectionStrings": {connection_name: connection_string}},
    )


def write_sql_fixture_target_config(
    agent_dir: Path,
    *,
    target_database: str = "DAWHO",
    initial_catalog: str = "MMA",
    allow_create_table: bool = False,
    allow_seed: bool = False,
) -> None:
    dump_json(
        agent_dir / "config" / "sql-fixture-targets.local.json",
        {
            "schemaVersion": "1.0.0",
            "defaultTarget": "develop",
            "targets": {
                "develop": {
                    "provider": "sqlserver",
                    "environment": "develop",
                    "connectionString": (
                        f"Server=fixture-sql.example;Initial Catalog={initial_catalog};"
                        "User ID=fixture_user;Password=secret;TrustServerCertificate=True;"
                    ),
                    "targetDatabase": target_database,
                    "allowCreateTable": allow_create_table,
                    "allowSeed": allow_seed,
                }
            },
        },
    )


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def no_sql_spec(api_id: str = API_ID) -> dict[str, Any]:
    return {
        "schemaVersion": "4.3.0",
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


def test_sqlite_target_is_disabled_without_creating_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir), sql_spec())
        db_path = paths["project_root"] / "fixture.sqlite"
        completed = run_fixture(paths["project_root"], "--execution-mode", "prepare", "--db-target", f"sqlite:///{db_path}")
        assert_true(completed.returncode == 1, completed.stdout + completed.stderr)
        _, checklist, manifest = load_state(paths)
        item = checklist["items"][0]
        assert_true(item["fixtureStatus"] == "blocked", "SQLite target should block")
        assert_true(item["fixtureBlockReason"] == "sqlite_target_disabled", "SQLite target should use explicit block reason")
        assert_true(manifest["fixtureBlockReason"] == "sqlite_target_disabled", "manifest should mirror SQLite block")
        table_checks = load_json(paths["table_checks_path"])
        report = load_json(paths["db_fixture_report_path"])
        assert_true(table_checks["tables"][0]["blockReason"] == "sqlite_target_disabled", "table check should expose disabled SQLite target")
        assert_true(report["dbTarget"] == "sqlite:///<disabled>", "report should not persist a local SQLite path")
        assert_true(not db_path.exists(), "disabled SQLite target must not create a local database file")
        assert_preserved_non_fixture_fields(paths)


def assert_unsafe_sqlserver_target_blocks(extra_args: list[str], connection_string: str | None = None) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir), sql_spec())
        if connection_string:
            write_appsettings(paths["project_root"], "ProdConnection", connection_string)
        completed = run_fixture(paths["project_root"], "--execution-mode", "prepare", *extra_args)
        assert_true(completed.returncode == 1, completed.stdout + completed.stderr)
        _, checklist, manifest = load_state(paths)
        item = checklist["items"][0]
        assert_true(item["fixtureStatus"] == "blocked", "unsafe SQL Server target should block fixture prepare")
        assert_true(item["fixtureBlockReason"] == "unsafe_database_target", "unsafe target must use contract block reason")
        assert_true(manifest["fixtureBlockReason"] == "unsafe_database_target", "manifest should mirror unsafe target")
        report = load_json(paths["db_fixture_report_path"])
        table_checks = load_json(paths["table_checks_path"])
        assert_true(report["status"] == "blocked", "unsafe target report should be blocked")
        assert_true(report["findings"][0]["blockReason"] == "unsafe_database_target", "report should expose unsafe target")
        assert_true(table_checks["tables"][0]["blockReason"] == "unsafe_database_target", "table checks should expose unsafe target")


def test_sqlserver_target_forms_block_when_not_proven_safe() -> None:
    raw = "Server=prod-sql.example;Database=CoreBank;User Id=fixture;Password=secret;"
    assert_unsafe_sqlserver_target_blocks(["--db-target", raw])
    assert_unsafe_sqlserver_target_blocks(["--db-target", f"connstr:{raw}"])
    assert_unsafe_sqlserver_target_blocks(["--db-target", "connection-name:ProdConnection"], raw)


def test_agent_local_config_proves_sqlserver_target_safe_and_forces_target_database() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        project_root = root / "FixtureProject"
        project_root.mkdir()
        agent_dir = root / ".agent"
        rules_root = root / "project-rules" / "default"
        dump_json(agent_dir / "config" / "chain-workspace.json", {"rulesRoot": str(rules_root)})
        dump_json(
            rules_root / "rules" / "sql-fixture" / "defaults.json",
            {"defaultSqlServerDatabase": "DAWHO"},
        )
        write_sql_fixture_target_config(agent_dir, target_database="DAWHO", initial_catalog="MMA", allow_create_table=True, allow_seed=True)
        prepare_sql_fixture.configure_project_sql_defaults(agent_dir)
        try:
            target = prepare_sql_fixture.parse_db_target(None, project_root, agent_dir=agent_dir)
            assert_true(
                isinstance(target, prepare_sql_fixture.SqlServerTarget),
                ".agent local config should prove SQL Server fixture target safe",
            )
            assert_true(target.database == "DAWHO", "configured targetDatabase should override connection Initial Catalog")
            assert_true(target.allow_create_table is True, "allowCreateTable should be read from local config")
            assert_true(target.allow_seed is True, "allowSeed should be read from local config")
            report_label = prepare_sql_fixture.db_target_for_report(None, target)
            assert_true("Password=" not in report_label, "report label must not expose the connection string password")
            assert_true("database=DAWHO" in report_label, "report label should expose only the effective target database")
        finally:
            prepare_sql_fixture.reset_project_sql_defaults()


def test_not_required_is_terminal_fixture_status() -> None:
    items = [{"apiId": API_ID, "specStatus": "done", "fixtureStatus": "not_required"}]
    state = prepare_sql_fixture.update_execution_state_payload(
        {},
        items,
        current_api_id=None,
        message="fixture not required",
        phase="not_required",
    )
    summary = prepare_sql_fixture.summarize_fixture_status(items)
    assert_true(state["fixtureStatus"] == "done", "not_required should aggregate as terminal fixture status")
    assert_true(summary["not_required"] == 1, "fixture summary should count not_required explicitly")


def test_agent_local_config_rejects_database_outside_project_rules() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        project_root = root / "FixtureProject"
        project_root.mkdir()
        agent_dir = root / ".agent"
        rules_root = root / "project-rules" / "default"
        dump_json(agent_dir / "config" / "chain-workspace.json", {"rulesRoot": str(rules_root)})
        dump_json(
            rules_root / "rules" / "sql-fixture" / "defaults.json",
            {"defaultSqlServerDatabase": "DAWHO"},
        )
        write_sql_fixture_target_config(agent_dir, target_database="MMA", initial_catalog="MMA")
        prepare_sql_fixture.configure_project_sql_defaults(agent_dir)
        try:
            target = prepare_sql_fixture.parse_db_target(None, project_root, agent_dir=agent_dir)
            assert_true(isinstance(target, prepare_sql_fixture.BlockedDbTarget), "targetDatabase outside project rules should block")
            assert_true(target.block_reason == "unsafe_database_target", "database mismatch should use unsafe target reason")
        finally:
            prepare_sql_fixture.reset_project_sql_defaults()


def main() -> int:
    test_no_sql_dependency_skips_and_preserves_non_fixture_state()
    print("[pass] test_no_sql_dependency_skips_and_preserves_non_fixture_state")
    test_sql_dependency_without_db_target_blocks_missing_db_target()
    print("[pass] test_sql_dependency_without_db_target_blocks_missing_db_target")
    test_sqlite_target_is_disabled_without_creating_file()
    print("[pass] test_sqlite_target_is_disabled_without_creating_file")
    test_sqlserver_target_forms_block_when_not_proven_safe()
    print("[pass] test_sqlserver_target_forms_block_when_not_proven_safe")
    test_agent_local_config_proves_sqlserver_target_safe_and_forces_target_database()
    print("[pass] test_agent_local_config_proves_sqlserver_target_safe_and_forces_target_database")
    test_not_required_is_terminal_fixture_status()
    print("[pass] test_not_required_is_terminal_fixture_status")
    test_agent_local_config_rejects_database_outside_project_rules()
    print("[pass] test_agent_local_config_rejects_database_outside_project_rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
