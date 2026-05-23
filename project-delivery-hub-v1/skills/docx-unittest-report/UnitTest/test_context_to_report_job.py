from __future__ import annotations

import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

from test_support import SKILL_ROOT, create_sample_docx, read_json, temp_dir, write_json


def create_api_context(
    workspace: Path,
    *,
    unit_test_names: list[str],
    integration_test_names: list[str],
) -> tuple[Path, Path]:
    repo_root = workspace / "repo"
    context_root = repo_root / ".agent" / "context" / "N.006"
    api_root = context_root / "apis" / "N.006.setting.queryuserloginlog"
    api_root.mkdir(parents=True, exist_ok=True)

    solution_path = repo_root / "Sinopac.DawhoEnterprise" / "Sinopac.DawhoEnterprise.sln"
    solution_path.parent.mkdir(parents=True, exist_ok=True)
    solution_path.write_text("", encoding="utf-8")

    controller_path = repo_root / "Sinopac.DawhoEnterprise" / "API" / "EnterpriseAPI" / "EnterpriseAPI" / "Controllers" / "SettingController.cs"
    controller_path.parent.mkdir(parents=True, exist_ok=True)
    controller_path.write_text(
        "[HttpGet]\n[Route(\"api/setting/query-user-login-log\")]\npublic class SettingController {}\n",
        encoding="utf-8",
    )

    service_path = repo_root / "Sinopac.DawhoEnterprise" / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "Setting" / "SettingService.QueryUserLoginLog.cs"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    service_path.write_text("public partial class SettingService {}", encoding="utf-8")

    unit_test_path = repo_root / "Sinopac.DawhoEnterprise" / "Test" / "UnitTesting" / "EnterpriseAPI" / "EnterpriseApiUnit" / "SettingServiceTests.cs"
    unit_test_path.parent.mkdir(parents=True, exist_ok=True)
    unit_test_path.write_text(
        "[Fact]\npublic void QueryUserLoginLog_UpdateAuditRecord() {}\n",
        encoding="utf-8",
    )

    integration_test_path = repo_root / "Sinopac.DawhoEnterprise" / "Test" / "IntegrationTesting" / "EnterpriseAPI" / "EnterpriseApiIntegration" / "SettingControllerTests.cs"
    integration_test_path.parent.mkdir(parents=True, exist_ok=True)
    integration_test_path.write_text(
        "[Fact]\npublic void QueryUserLoginLog_ReturnSuccessPayload() {}\n",
        encoding="utf-8",
    )

    write_json(
        context_root / "api-checklist.json",
        {
            "items": [
                {
                    "apiId": "N.006.setting.queryuserloginlog",
                    "apiCategory": "Setting",
                    "apiName": "QueryUserLoginLog",
                    "specStatus": "done",
                    "codeStatus": "tests_passed",
                    "codePhase": "validated",
                }
            ]
        },
    )
    write_json(
        context_root / "execution-state.json",
        {
            "functionCode": "N.006",
            "codeSolutionPath": "Sinopac.DawhoEnterprise/Sinopac.DawhoEnterprise.sln",
            "specDocxPath": ".agent/TSD/TSD.N.006.docx",
        },
    )
    write_json(
        api_root / "manifest.json",
        {
            "apiId": "N.006.setting.queryuserloginlog",
            "apiCategory": "Setting",
            "apiName": "QueryUserLoginLog",
            "specArtifacts": {
                "apiSpec": ".agent/context/N.006/apis/N.006.setting.queryuserloginlog/N.006_API_Spec.json"
            },
            "modifiedFiles": [
                "Sinopac.DawhoEnterprise/API/EnterpriseAPI/EnterpriseAPI/Controllers/SettingController.cs",
                "Sinopac.DawhoEnterprise/BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/Setting/SettingService.QueryUserLoginLog.cs",
                "Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/SettingServiceTests.cs",
                "Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/SettingControllerTests.cs",
            ],
            "codeArtifacts": {
                "changePlan": ".agent/context/N.006/apis/N.006.setting.queryuserloginlog/change-plan.json",
                "implementationReport": ".agent/context/N.006/apis/N.006.setting.queryuserloginlog/implementation-report.md",
            },
            "validationChecks": [],
        },
    )
    write_json(
        api_root / "change-plan.json",
        {
            "analysis": {
                "moduleName": "Setting",
                "controllerFile": "Sinopac.DawhoEnterprise/API/EnterpriseAPI/EnterpriseAPI/Controllers/SettingController.cs",
                "interfaceFile": "Sinopac.DawhoEnterprise/BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness.Interface/ISettingService.cs",
                "serviceFiles": [
                    "Sinopac.DawhoEnterprise/BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/Setting/SettingService.QueryUserLoginLog.cs"
                ],
                "entityFiles": [],
                "unitTestFiles": [
                    "Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/SettingServiceTests.cs"
                ],
                "integrationTestFiles": [
                    "Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/SettingControllerTests.cs"
                ],
            }
        },
    )
    write_json(
        api_root / "test-evidence.json",
        {
            "schemaVersion": "1.0.0",
            "executionId": "N.006",
            "apiId": "N.006.setting.queryuserloginlog",
            "projectRoot": repo_root.as_posix(),
            "solutionPath": solution_path.as_posix(),
            "moduleName": "Setting",
            "apiCategory": "Setting",
            "apiName": "QueryUserLoginLog",
            "apiDisplayName": "Setting/QueryUserLoginLog",
            "unitTestProject": "Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/EnterpriseAPIUnit.csproj",
            "integrationTestProject": "Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/EnterpriseAPIIntegration.csproj",
            "validationChecks": [],
            "validationResults": [],
            "trxHints": {
                "unit": (repo_root / ".agent" / "report-results" / "N.006" / "N.006.setting.queryuserloginlog" / "unit").as_posix(),
                "integration": (repo_root / ".agent" / "report-results" / "N.006" / "N.006.setting.queryuserloginlog" / "integration").as_posix(),
            },
            "testNames": {
                "unit": unit_test_names,
                "integration": integration_test_names,
            },
            "reportHints": {
                "recommendedSections": ["UT-01", "UT-03", "UT-04", "UT-10"],
                "sourceFiles": [
                    "Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/SettingServiceTests.cs",
                    "Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/SettingControllerTests.cs",
                ],
            },
        },
    )
    write_json(
        api_root / "N.006_API_Spec.json",
        {
            "apiId": "N.006.setting.queryuserloginlog",
            "apiCategory": "Setting",
            "apiName": "QueryUserLoginLog",
            "request": [],
            "response": [{"fieldName": "responseCode"}],
            "businessLogic": {
                "steps": [{"step": 1, "title": "查詢登入記錄"}],
                "errorCodeRules": [],
                "runtimeDependencies": [],
                "sqlSpecs": [{"queryText": "SELECT TOP 10 * FROM USER_LOGIN_LOG"}],
            },
            "backendApis": {},
            "source": {
                "tsdFile": "TSD.N.006.docx",
                "workbookFile": "NEWDA_API_DETAIL_Setting.xlsx",
                "sheetNames": ["QueryUserLoginLog"],
            },
        },
    )
    return repo_root, api_root


class ContextToReportJobTests(unittest.TestCase):
    def test_context_to_report_job_defaults_outputs_to_module_context_root(self) -> None:
        workspace = temp_dir()
        _, api_root = create_api_context(
            workspace,
            unit_test_names=["SettingServiceTests.QueryUserLoginLog_UpdateAuditRecord"],
            integration_test_names=["SettingControllerTests.QueryUserLoginLog_ReturnSuccessPayload"],
        )
        context_root = api_root.parent.parent
        docx_path = create_sample_docx(workspace / "source-report.docx")
        expected_docx = context_root / "ut-report" / f"{context_root.name}_API_UT 測試報告 {date.today():%Y%m%d}.docx"
        (api_root / "report-job.json").write_text("{}", encoding="utf-8")
        (api_root / "coverage-gap.json").write_text("{}", encoding="utf-8")
        (api_root / expected_docx.name).write_text("stale", encoding="utf-8")
        (api_root / "report-job.results.json").write_text("{}", encoding="utf-8")
        (api_root / "report-job.autofix-report.json").write_text("{}", encoding="utf-8")
        (api_root / "template-classification.json").write_text("{}", encoding="utf-8")
        (api_root / "module-scope.json").write_text("{}", encoding="utf-8")
        (api_root / "report-workspace").mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "context_to_report_job.py"),
                "--api-root",
                str(api_root),
                "--report-docx",
                str(docx_path),
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        report_job = read_json(context_root / "ut-report" / "report-job.json")
        self.assertTrue((context_root / "ut-report" / "report-job.json").exists())
        self.assertEqual(
            report_job["document"]["outputPath"],
            expected_docx.as_posix(),
        )
        self.assertTrue((context_root / "ut-report" / "coverage-gap.json").exists())
        self.assertTrue((context_root / "ut-report" / "module-scope.json").exists())
        self.assertFalse((api_root / "report-job.json").exists())
        self.assertFalse((api_root / "coverage-gap.json").exists())
        self.assertFalse((api_root / expected_docx.name).exists())
        self.assertFalse((api_root / "report-job.results.json").exists())
        self.assertFalse((api_root / "report-job.autofix-report.json").exists())
        self.assertFalse((api_root / "template-classification.json").exists())
        self.assertFalse((api_root / "module-scope.json").exists())
        self.assertFalse((api_root / "report-workspace").exists())

    def test_context_to_report_job_bootstraps_manifest_and_applies_strong_bindings(self) -> None:
        workspace = temp_dir()
        repo_root, api_root = create_api_context(
            workspace,
            unit_test_names=["SettingServiceTests.QueryUserLoginLog_UpdateAuditRecord"],
            integration_test_names=["SettingControllerTests.QueryUserLoginLog_ReturnSuccessPayload"],
        )
        docx_path = create_sample_docx(workspace / "source-report.docx")
        output_job = api_root / "report-job.json"

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "context_to_report_job.py"),
                "--api-root",
                str(api_root),
                "--report-docx",
                str(docx_path),
                "--output-job",
                str(output_job),
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        report_job = read_json(output_job)
        coverage_gap = read_json(api_root / "coverage-gap.json")
        autofix_report = read_json(api_root / "report-job.autofix-report.json")

        self.assertEqual(report_job["metadata"]["apiDisplayName"], "Setting/QueryUserLoginLog")
        self.assertIn("dotnet test", report_job["unitTest"]["command"])
        self.assertIn("EnterpriseAPIUnit.csproj", report_job["unitTest"]["command"])
        self.assertFalse(report_job["integrationTest"]["cleanWorkspace"]["enabled"])
        clean_workspace = report_job["integrationTest"]["cleanWorkspace"]
        self.assertEqual(Path(clean_workspace["sourceRoot"]).resolve(), repo_root.resolve())
        self.assertEqual(clean_workspace["targetRoot"], "")

        http_case = report_job["sections"][0]["items"][0]
        db_case = report_job["sections"][0]["items"][1]
        self.assertTrue(http_case["enabled"])
        self.assertEqual(http_case["mode"], "code_inspection")
        self.assertEqual(http_case["testBindings"]["testNames"], [])
        self.assertEqual(http_case["codeInspection"]["ruleId"], "http-contract")
        self.assertEqual(db_case["mode"], "unit_test")
        self.assertTrue(db_case["enabled"])
        self.assertEqual(
            db_case["testBindings"]["testNames"],
            ["SettingServiceTests.QueryUserLoginLog_UpdateAuditRecord"],
        )
        self.assertGreaterEqual(autofix_report["appliedChangeCount"], 2)
        self.assertIn("gapCount", coverage_gap["summary"])

    def test_context_to_report_job_keeps_items_disabled_when_test_names_are_missing(self) -> None:
        workspace = temp_dir()
        _, api_root = create_api_context(
            workspace,
            unit_test_names=[],
            integration_test_names=[],
        )
        docx_path = create_sample_docx(workspace / "source-report.docx")
        output_job = api_root / "report-job.json"

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "context_to_report_job.py"),
                "--api-root",
                str(api_root),
                "--report-docx",
                str(docx_path),
                "--output-job",
                str(output_job),
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        report_job = read_json(output_job)
        http_case = report_job["sections"][0]["items"][0]
        db_case = report_job["sections"][0]["items"][1]
        self.assertTrue(http_case["enabled"])
        self.assertEqual(http_case["mode"], "code_inspection")
        self.assertEqual(http_case["testBindings"]["testNames"], [])
        self.assertFalse(db_case["enabled"])
        self.assertEqual(db_case["testBindings"]["testNames"], [])


if __name__ == "__main__":
    unittest.main()
