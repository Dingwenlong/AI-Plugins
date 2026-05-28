#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
WRITE_API_SPEC = SKILL_DIR / "scripts" / "write_api_spec.py"
SOURCE_AGENT = SCRIPT_DIR / "fixtures" / "agent"
EXECUTION_ID = "D.006"
API_ID_READY = "D.006.deposit.addexchangedepositinit"

sys.path.insert(0, str(SKILL_DIR / "scripts"))
from runtime import build_api_spec_filename, extract_function_code
from write_api_spec import (
    build_code_handoff,
    collect_excel_visual_warnings,
    extract_api_spec_sections,
    extract_business_logic_structure_from_rows,
    load_project_hard_constraints,
    select_representative_mock_examples,
)
from sequence_diagrams import build_sequence_context


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def setup_project(temp_dir: Path) -> dict[str, Path]:
    project_root = temp_dir / "SpecFixture"
    project_root.mkdir()
    shutil.copytree(SOURCE_AGENT, project_root / ".agent")
    context_root = project_root / ".agent" / "context"
    context_root.mkdir(parents=True, exist_ok=True)
    dump_json(
        context_root / "execution-batch.json",
        {
            "schemaVersion": "1.0.0",
            "activeFunctionCode": EXECUTION_ID,
            "items": [
                {
                    "functionCode": EXECUTION_ID,
                    "docxRef": ".agent/TSD/TSD.D.006_換匯優利定存_v1.0_20260408.docx",
                    "order": 1,
                }
            ],
            "updatedAt": None,
            "updatedBy": "fixture",
        },
    )
    return {
        "project_root": project_root,
        "context_root": context_root,
        "execution_root": context_root / EXECUTION_ID,
        "execution_state_path": context_root / EXECUTION_ID / "execution-state.json",
        "checklist_path": context_root / EXECUTION_ID / "api-checklist.json",
        "manifest_path": context_root / EXECUTION_ID / "apis" / API_ID_READY / "manifest.json",
        "api_spec_path": context_root / EXECUTION_ID / "apis" / API_ID_READY / "D.006_API_Spec.json",
        "batch_file": context_root / "execution-batch.json",
    }


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)


def test_excel_visual_detection_marks_handoff_unresolved() -> None:
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from PIL import Image as PILImage

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workbook_path = temp_path / "visual-risk.xlsx"
        image_path = temp_path / "note.png"

        PILImage.new("RGB", (12, 12), color="white").save(image_path)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "DepositInit"
        sheet["A1"] = "Request"
        sheet.add_image(XLImage(str(image_path)), "C3")
        workbook.save(workbook_path)

        notes, unresolved = collect_excel_visual_warnings(workbook_path, ["DepositInit"])
        handoff = build_code_handoff(
            project_root=temp_path,
            agent_dir=temp_path,
            function_code="D.999",
            api_category="Deposit",
            api_name="VisualRiskFixture",
            request_fields=[],
            response_fields=[],
            business_logic_payload={
                "steps": [],
                "fieldMappings": [],
                "errorCodeRules": [],
                "runtimeDependencies": [],
                "dataSources": [],
                "sqlSpecs": [],
                "legacyReferences": [],
                "prohibitedShortcuts": [],
            },
            additional_unresolved=unresolved,
        )

        assert_true(any("嵌入图片" in note for note in notes), "visual scan should report embedded images in workbook notes")
        assert_true(
            any(item.get("topic", "").startswith("excel_visual.") for item in handoff["unresolved"]),
            "codeHandoff should preserve Excel visual-risk unresolved items",
        )


def test_project_hard_constraints_schema_accepts_1x_forward_compatible_metadata() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        agent_dir = Path(temp_dir) / ".agent"
        common_dir = agent_dir / "Common"
        common_dir.mkdir(parents=True, exist_ok=True)

        constraint_file = common_dir / "project-hard-constraints.json"
        dump_json(
            constraint_file,
            {
                "schemaVersion": "1.1.0",
                "projectId": "fixture-project",
                "sourceDoc": ".agent/Common/EnterpriseAPI_CodeWriter_HardConstraints_20260416.md",
                "frameworkProfile": "newdawho.enterpriseapi",
                "language": "zh-TW",
                "appliesToSkills": [
                    "api-spec-writer"
                ],
                "lastReviewedDate": "2026-04-21",
                "evidenceSources": [
                    "Sinopac.DawhoEnterprise/API/EnterpriseAPI/EnterpriseAPI/Controllers/LoginController.cs"
                ],
                "rules": [
                    {
                        "ruleId": "enterpriseapi_external_name_keep_spec",
                        "scope": "api_behavior",
                        "fileRole": "shared",
                        "ruleType": "naming",
                        "instruction": "對外 API 名稱必須沿用 spec 名稱。",
                        "severity": "error",
                        "blocking": True,
                        "appliesTo": ["apiName"],
                        "examples": ["GetAnnounce"]
                    }
                ]
            },
        )

        payload, path = load_project_hard_constraints(agent_dir)

        assert_true(payload is not None, "project hard constraints 1.x payload should load successfully")
        assert_true(path == constraint_file.resolve(), "loader should return the resolved project hard constraints path")
        assert_true(payload["schemaVersion"] == "1.1.0", "loader should preserve 1.x schemaVersion values")
        assert_true("reviewNotesTemplate" not in payload, "forward-compatible 1.x payload should not require reviewNotesTemplate")


def test_mock_examples_preserve_all_excel_scenarios_even_when_codes_repeat() -> None:
    examples = [
        {
            "scenario": "正常結果返回",
            "responsePayload": {"isSuccess": True, "responseCode": "0000", "responseMessage": "成功"},
        },
        {
            "scenario": "IRIS請求失敗",
            "responsePayload": {"isSuccess": False, "responseCode": "9001", "responseMessage": "系統繁忙,請稍後再試！"},
        },
        {
            "scenario": "營業日判斷錯誤",
            "responsePayload": {"isSuccess": False, "responseCode": "9001", "responseMessage": "系統繁忙,請稍後再試！"},
        },
        {
            "scenario": "未輸入必填請求參數",
            "responsePayload": {"isSuccess": False, "responseCode": "9001", "responseMessage": "系統繁忙,請稍後再試！"},
        },
    ]

    selected = select_representative_mock_examples(examples)

    assert_true([item["scenario"] for item in selected] == [item["scenario"] for item in examples], "mockExamples should preserve every Excel scenario, even when responseCode repeats")


def test_business_logic_body_dependencies_are_structured_and_uncertain_db_is_unresolved() -> None:
    rows = [
        ["API 內部業務邏輯"],
        ["#", "邏輯說明"],
        [
            "涉及BackendAPI",
            "1.IRIS -> ID0018 取消預約定存\n2.DB->MMA.TX_STATISTIC 交易記錄\n3.DB->MMA.MMANTFXP7000 todo：待確認是否還需要\n4.CommonFunc->GetOperationHour 取營業日\n->SendToMonitorMail_Push 發送郵件和推播",
        ],
        [
            "1.取消預約定存邏輯",
            "INSERT INTO TX_STATISTIC (CUSTID, IP) VALUES (@CUSTID, @IP); 成功或者失敗都調用CommonFunc.SendToMonitorMail_Push()",
        ],
    ]

    sections = extract_api_spec_sections(rows)
    business_logic = extract_business_logic_structure_from_rows(rows)

    assert_true("TX_STATISTIC" in sections["backendApis"].get("DB", []), "confirmed DB table should be visible in backendApis")
    assert_true(
        not any("MMANTFXP7000" in target for target in sections["backendApis"].get("DB", [])),
        "uncertain DB dependency should not be treated as confirmed backendApis",
    )
    assert_true(any("TX_STATISTIC" in source for spec in business_logic["sqlSpecs"] for source in spec["dataSources"]), "SQL body should produce sqlSpecs for fixture detection")
    assert_true(
        any("sendtomonitormail_push" in item["id"] for item in business_logic["runtimeDependencies"]),
        "business logic body dependency should become runtime dependency",
    )
    assert_true(
        any("MMANTFXP7000" in item["reason"] for item in business_logic["dependencyUnresolved"]),
        "uncertain DB dependency should become handoff unresolved input",
    )


def test_shared_context_generation_with_batch() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir))
        completed = run_command(
            [
                sys.executable,
                str(WRITE_API_SPEC),
                "--project-root",
                str(paths["project_root"]),
                "--function-code",
                EXECUTION_ID,
            ]
        )
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)

        execution_state = load_json(paths["execution_state_path"])
        checklist = load_json(paths["checklist_path"])
        manifest = load_json(paths["manifest_path"])
        api_spec = load_json(paths["api_spec_path"])
        batch = load_json(paths["batch_file"])

        assert_true(paths["api_spec_path"].exists(), "spec writer should emit API_Spec.json into shared context execution")
        assert_true(api_spec["schemaVersion"] == "4.3.0", "spec writer should emit the upgraded API_Spec schemaVersion")
        assert_true("codeHandoff" in api_spec, "spec writer should emit machine-readable codeHandoff")
        assert_true("logicFlow" in api_spec["codeHandoff"], "codeHandoff should expose ordered logic flow")
        assert_true("queryContracts" in api_spec["codeHandoff"], "codeHandoff should expose query contracts")
        assert_true("mappingRules" in api_spec["codeHandoff"], "codeHandoff should expose mapping rules")
        assert_true(execution_state["specStatus"] == "waiting_resume", "spec execution state should track specStatus in merged file")
        assert_true(execution_state["codeStatus"] == "waiting_spec", "spec run should preserve codeStatus placeholder")
        assert_true(execution_state["artifacts"]["batchFile"] == ".agent/context/execution-batch.json", "execution state should expose shared batch file")
        assert_true(checklist["items"][0]["specStatus"] == "done", "merged checklist should write specStatus")
        assert_true(checklist["items"][0]["codeStatus"] == "pending", "done spec item should become pending for code stage")
        assert_true(manifest["specStatus"] == "done", "merged manifest should expose specStatus")
        assert_true("codeArtifacts" in manifest, "merged manifest should preserve codeArtifacts envelope")
        assert_true(batch["activeFunctionCode"] == EXECUTION_ID, "batch file should stay pinned to the current execution")


def test_sequence_diagram_native_spec_enriches_shared_generation() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir))
        sequence_dir = paths["project_root"] / ".agent" / "functions" / EXECUTION_ID / "analysis" / "sequence-diagrams"
        sequence_dir.mkdir(parents=True, exist_ok=True)
        dump_json(
            sequence_dir / "D.006_native_visio_spec.json",
            {
                "participants": [
                    {"id": "APP", "label": "APP"},
                    {"id": "Ent", "label": "Enterprise"},
                    {"id": "IRIS", "label": "IRIS"},
                ],
                "sections": [{"label": "AddExchangeDepositInit 初始化流程"}],
                "frames": [{"kind": "alt", "condition": "[查詢成功]"}],
                "messages": [
                    {"kind": "message", "from": "APP", "to": "Ent", "text": "AddExchangeDepositInit 呼叫 CommonFunc.GenFntTranSeq 取得交易序號"},
                    {"kind": "message", "from": "Ent", "to": "IRIS", "text": "AddExchangeDepositInit 呼叫 IRIS.EC0001 取得試算資料"},
                ],
            },
        )

        completed = run_command(
            [
                sys.executable,
                str(WRITE_API_SPEC),
                "--project-root",
                str(paths["project_root"]),
                "--function-code",
                EXECUTION_ID,
                "--api-id",
                API_ID_READY,
            ]
        )
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)

        api_spec = load_json(paths["api_spec_path"])
        manifest = load_json(paths["manifest_path"])

        assert_true(api_spec["source"]["sequenceDiagrams"], "API Spec source should include matched sequence diagram files")
        assert_true(manifest["specSource"]["sequenceDiagrams"], "manifest specSource should include sequence diagram hashes")
        assert_true(
            any(item.get("appliedToApi") for item in api_spec.get("rawAppendix", {}).get("sequenceDiagramExtracts", [])),
            "rawAppendix should retain applied sequence diagram extracts",
        )
        assert_true(
            any(item.get("kind") == "sequenceDiagram" for item in api_spec["codeHandoff"]["legacyEvidence"]),
            "codeHandoff legacyEvidence should include sequenceDiagram evidence",
        )
        assert_true(
            api_spec["codeHandoff"]["logicSummary"]["primarySource"] == "businessLogic+sequenceDiagram",
            "sequence evidence should be visible in logicSummary primarySource",
        )
        assert_true(
            any("commonfunc" in item.get("purpose", "").casefold() or "iris" in item.get("purpose", "").casefold() for item in api_spec["codeHandoff"]["dependencyHints"]),
            "sequence dependencies should enrich dependencyHints",
        )


def test_external_sequence_root_svg_and_vsdx_are_discoverable() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        agent_dir = temp_path / ".agent"
        agent_dir.mkdir()
        sequence_root = temp_path / "external-sequence"
        sequence_root.mkdir()
        (sequence_root / "E.999_01.svg").write_text(
            "<svg xmlns=\"http://www.w3.org/2000/svg\"><title>E.999</title><text>AddWidgetFlow 呼叫 CommonUtil/GetFoo</text></svg>",
            encoding="utf-8",
        )
        vsdx_path = sequence_root / "E.999_01.vsdx"
        with __import__("zipfile").ZipFile(vsdx_path, "w") as archive:
            archive.writestr("visio/pages/page1.xml", "<Page><Text>AddWidgetFlow 呼叫 Backend/GetRate</Text></Page>")

        context = build_sequence_context(
            agent_dir=agent_dir,
            function_code="E.999",
            api_name="AddWidgetFlow",
            request_fields=[],
            response_fields=[],
            known_response_codes=[],
            sequence_root=sequence_root,
        )

        kinds = {item["kind"] for item in context["sourceEntries"]}
        assert_true({"svg", "vsdx"}.issubset(kinds), "explicit sequence root should discover matching SVG and VSDX files")
        assert_true(any(item.get("appliedToApi") for item in context["extracts"]), "external sequence text should apply to matching apiName")


def test_sequence_diagram_contract_conflicts_are_blocking_unresolved() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        agent_dir = temp_path / ".agent"
        sequence_dir = agent_dir / "functions" / "B.001" / "analysis" / "sequence-diagrams"
        sequence_dir.mkdir(parents=True)
        dump_json(
            sequence_dir / "B.001_native_visio_spec.json",
            {
                "sections": [{"label": "ConflictApi 流程"}],
                "messages": [{"text": "ConflictApi 使用 missingField 並回傳 Response 7777"}],
            },
        )

        context = build_sequence_context(
            agent_dir=agent_dir,
            function_code="B.001",
            api_name="ConflictApi",
            request_fields=[{"fieldName": "knownField"}],
            response_fields=[],
            known_response_codes=["0000"],
        )

        topics = {item.get("topic") for item in context["unresolved"]}
        assert_true("sequenceDiagram.fieldContract" in topics, "unknown sequence field should become blocking unresolved")
        assert_true("sequenceDiagram.responseCodeContract" in topics, "unknown sequence response code should become blocking unresolved")


def test_missing_sequence_diagram_is_review_note_not_blocking() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        agent_dir = Path(temp_dir) / ".agent"
        agent_dir.mkdir()
        context = build_sequence_context(
            agent_dir=agent_dir,
            function_code="Z.999",
            api_name="NoDiagramApi",
            request_fields=[],
            response_fields=[],
            known_response_codes=[],
        )

        assert_true(not context["sourceEntries"], "missing sequence diagram should not create sources")
        assert_true(not context["unresolved"], "missing sequence diagram should not block spec generation")
        assert_true(context["notes"], "missing sequence diagram should leave a review note")


def test_extract_function_code_preserves_full_tsd_code() -> None:
    full_tsd_name = "TSD.N.001.001_頭像與暱稱設定_v1.5_20260408.docx"
    function_code = extract_function_code(full_tsd_name)

    assert_true(function_code == "N.001.001", "functionCode should preserve the full TSD code instead of truncating to the parent code")
    assert_true(
        build_api_spec_filename(None, full_tsd_name) == "N.001.001_API_Spec.json",
        "API_Spec file name should use the full functionCode extracted from the TSD file name",
    )


def test_source_change_resets_code_manifest_and_execution_state() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_project(Path(temp_dir))
        first = run_command(
            [
                sys.executable,
                str(WRITE_API_SPEC),
                "--project-root",
                str(paths["project_root"]),
                "--function-code",
                EXECUTION_ID,
            ]
        )
        assert_true(first.returncode == 0, first.stdout + first.stderr)

        execution_state = load_json(paths["execution_state_path"])
        checklist = load_json(paths["checklist_path"])
        manifest = load_json(paths["manifest_path"])
        api_dir = paths["manifest_path"].parent

        (api_dir / "change-plan.json").write_text("{\"plan\":[]}\n", encoding="utf-8")
        (api_dir / "implementation-report.md").write_text("old report\n", encoding="utf-8")
        (api_dir / "diagnosis-report.json").write_text("{\"issues\":[]}\n", encoding="utf-8")

        execution_state["codeStatus"] = "done"
        execution_state["codePhase"] = "validated"
        execution_state["codeUpdatedAt"] = "2026-04-09T10:00:00+08:00"
        execution_state["codeSummary"] = {
            "total": len(checklist["items"]),
            "waiting_spec": 1,
            "pending": 0,
            "in_progress": 0,
            "tests_passed": 1,
            "tests_failed": 0,
            "blocked": 0,
            "error": 0,
        }
        dump_json(paths["execution_state_path"], execution_state)

        checklist["items"][0]["codeStatus"] = "tests_passed"
        checklist["items"][0]["codePhase"] = "validated"
        dump_json(paths["checklist_path"], checklist)

        manifest["codeStatus"] = "tests_passed"
        manifest["codePhase"] = "validated"
        manifest["codeUpdatedAt"] = "2026-04-09T10:00:00+08:00"
        manifest["modifiedFiles"] = ["src/Foo.cs"]
        manifest["validationChecks"] = ["dotnet test"]
        manifest["validationResults"] = [{"passed": True}]
        manifest["repoDriftFiles"] = ["src/Foo.cs"]
        manifest["codeArtifacts"] = {
            "changePlan": ".agent/context/D.006/apis/D.006.deposit.addexchangedepositinit/change-plan.json",
            "implementationReport": ".agent/context/D.006/apis/D.006.deposit.addexchangedepositinit/implementation-report.md",
            "diagnosisReport": ".agent/context/D.006/apis/D.006.deposit.addexchangedepositinit/diagnosis-report.json",
        }
        manifest["specSourceFingerprint"] = "sha256:stale-spec-fingerprint"
        dump_json(paths["manifest_path"], manifest)

        second = run_command(
            [
                sys.executable,
                str(WRITE_API_SPEC),
                "--project-root",
                str(paths["project_root"]),
                "--function-code",
                EXECUTION_ID,
            ]
        )
        assert_true(second.returncode == 0, second.stdout + second.stderr)

        execution_state = load_json(paths["execution_state_path"])
        checklist = load_json(paths["checklist_path"])
        manifest = load_json(paths["manifest_path"])

        assert_true(execution_state["codeStatus"] == "waiting_resume", "execution code status should fall back after spec source changes")
        assert_true(execution_state["codePhase"] == "pending", "execution code phase should return to pending after spec source changes")
        assert_true(checklist["items"][0]["codeStatus"] == "pending", "changed spec source should reset API checklist codeStatus")
        assert_true(checklist["items"][0]["codePhase"] == "pending", "changed spec source should reset API checklist codePhase")
        assert_true(manifest["codeStatus"] == "pending", "changed spec source should reset manifest codeStatus")
        assert_true(manifest["codePhase"] == "pending", "changed spec source should reset manifest codePhase")
        assert_true(manifest["modifiedFiles"] == [], "changed spec source should clear stale modified files")
        assert_true(manifest["validationChecks"] == [], "changed spec source should clear stale validation checks")
        assert_true(manifest["validationResults"] == [], "changed spec source should clear stale validation results")
        assert_true(manifest["repoDriftFiles"] == [], "changed spec source should clear stale repo drift files")
        assert_true(
            manifest["codeArtifacts"] == {
                "changePlan": None,
                "implementationReport": None,
                "diagnosisReport": None,
            },
            "changed spec source should clear stale code artifact paths",
        )


def main() -> int:
    test_extract_function_code_preserves_full_tsd_code()
    print("[pass] test_extract_function_code_preserves_full_tsd_code")
    test_excel_visual_detection_marks_handoff_unresolved()
    print("[pass] test_excel_visual_detection_marks_handoff_unresolved")
    test_project_hard_constraints_schema_accepts_1x_forward_compatible_metadata()
    print("[pass] test_project_hard_constraints_schema_accepts_1x_forward_compatible_metadata")
    test_mock_examples_preserve_all_excel_scenarios_even_when_codes_repeat()
    print("[pass] test_mock_examples_preserve_all_excel_scenarios_even_when_codes_repeat")
    test_business_logic_body_dependencies_are_structured_and_uncertain_db_is_unresolved()
    print("[pass] test_business_logic_body_dependencies_are_structured_and_uncertain_db_is_unresolved")
    test_shared_context_generation_with_batch()
    print("[pass] test_shared_context_generation_with_batch")
    test_sequence_diagram_native_spec_enriches_shared_generation()
    print("[pass] test_sequence_diagram_native_spec_enriches_shared_generation")
    test_external_sequence_root_svg_and_vsdx_are_discoverable()
    print("[pass] test_external_sequence_root_svg_and_vsdx_are_discoverable")
    test_sequence_diagram_contract_conflicts_are_blocking_unresolved()
    print("[pass] test_sequence_diagram_contract_conflicts_are_blocking_unresolved")
    test_missing_sequence_diagram_is_review_note_not_blocking()
    print("[pass] test_missing_sequence_diagram_is_review_note_not_blocking")
    test_source_change_resets_code_manifest_and_execution_state()
    print("[pass] test_source_change_resets_code_manifest_and_execution_state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
