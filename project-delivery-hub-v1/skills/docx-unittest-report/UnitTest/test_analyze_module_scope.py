from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from test_support import SKILL_ROOT, read_json, temp_dir, write_json


class AnalyzeModuleScopeTests(unittest.TestCase):
    def test_analyze_module_scope_emits_module_summary_and_paths(self) -> None:
        workspace = temp_dir()
        repo_root = workspace / "repo"
        context_root = repo_root / ".agent" / "context" / "N.001.001"
        api_root = context_root / "apis" / "N.001.001.setting.updateuseralias"
        api_root.mkdir(parents=True, exist_ok=True)

        solution_path = repo_root / "Sinopac.DawhoEnterprise" / "Sinopac.DawhoEnterprise.sln"
        solution_path.parent.mkdir(parents=True, exist_ok=True)
        solution_path.write_text("", encoding="utf-8")

        controller_path = repo_root / "Sinopac.DawhoEnterprise" / "API" / "EnterpriseAPI" / "EnterpriseAPI" / "Controllers" / "SettingController.cs"
        controller_path.parent.mkdir(parents=True, exist_ok=True)
        controller_path.write_text("public class SettingController {}", encoding="utf-8")

        service_path = repo_root / "Sinopac.DawhoEnterprise" / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "Setting" / "SettingService.UpdateUserAlias.cs"
        service_path.parent.mkdir(parents=True, exist_ok=True)
        service_path.write_text("public partial class SettingService {}", encoding="utf-8")

        unit_test_path = repo_root / "Sinopac.DawhoEnterprise" / "Test" / "UnitTesting" / "EnterpriseAPI" / "EnterpriseApiUnit" / "SettingServiceTests.cs"
        unit_test_path.parent.mkdir(parents=True, exist_ok=True)
        unit_test_path.write_text("public class SettingServiceTests { void UpdateUserAlias_ShouldPass() {} }", encoding="utf-8")

        integration_test_path = repo_root / "Sinopac.DawhoEnterprise" / "Test" / "IntegrationTesting" / "EnterpriseAPI" / "EnterpriseApiIntegration" / "SettingControllerTests.cs"
        integration_test_path.parent.mkdir(parents=True, exist_ok=True)
        integration_test_path.write_text("public class SettingControllerTests { void UpdateUserAlias_ShouldReturnSuccessPayload() {} }", encoding="utf-8")

        write_json(
            context_root / "api-checklist.json",
            {
                "items": [
                    {
                        "apiId": "N.001.001.setting.updateuseralias",
                        "apiCategory": "Setting",
                        "apiName": "UpdateUserAlias",
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
                "functionCode": "N.001.001",
                "codeSolutionPath": "Sinopac.DawhoEnterprise/Sinopac.DawhoEnterprise.sln",
                "specDocxPath": ".agent/TSD/TSD.N.001.001.docx",
            },
        )
        write_json(
            api_root / "manifest.json",
            {
                "apiId": "N.001.001.setting.updateuseralias",
                "apiCategory": "Setting",
                "apiName": "UpdateUserAlias",
                "specArtifacts": {
                    "apiSpec": ".agent/context/N.001.001/apis/N.001.001.setting.updateuseralias/N.001.001_API_Spec.json"
                },
                "modifiedFiles": [
                    "Sinopac.DawhoEnterprise/API/EnterpriseAPI/EnterpriseAPI/Controllers/SettingController.cs",
                    "Sinopac.DawhoEnterprise/BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/Setting/SettingService.UpdateUserAlias.cs",
                ],
                "codeArtifacts": {
                    "changePlan": ".agent/context/N.001.001/apis/N.001.001.setting.updateuseralias/change-plan.json",
                    "implementationReport": ".agent/context/N.001.001/apis/N.001.001.setting.updateuseralias/implementation-report.md",
                },
                "validationChecks": [
                    "dotnet test \"Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/EnterpriseAPIUnit.csproj\" --no-build",
                    "dotnet test \"Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/EnterpriseAPIIntegration.csproj\" --no-build",
                ],
            },
        )
        write_json(
            api_root / "N.001.001_API_Spec.json",
            {
                "apiId": "N.001.001.setting.updateuseralias",
                "apiCategory": "Setting",
                "apiName": "UpdateUserAlias",
                "request": [
                    {
                        "fieldName": "alias",
                        "required": True,
                    }
                ],
                "response": [
                    {
                        "fieldName": "responseCode",
                    }
                ],
                "businessLogic": {
                    "steps": [
                        {
                            "step": 1,
                            "title": "操作邏輯",
                        }
                    ],
                    "errorCodeRules": [
                        {
                            "code": "9999",
                            "message": "請輸入alias！",
                        }
                    ],
                    "runtimeDependencies": [
                        {
                            "id": "current_customer_context",
                            "type": "service",
                            "description": "Resolve custId from Redis.",
                        }
                    ],
                    "sqlSpecs": [
                        {
                            "queryText": "UPDATE DAWHO.DA_USER_ALIAS SET ALIAS = @ALIAS WHERE CUSTID = @CUSTID",
                        }
                    ],
                },
                "backendApis": {
                    "Redis": ["[Ent:Set:{CustId}:UserAlias]"],
                },
            },
        )

        output_path = workspace / "module-scope.json"
        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "analyze_module_scope.py"),
                str(context_root),
                "--output",
                str(output_path),
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        result = read_json(output_path)
        self.assertEqual(result["moduleCode"], "N.001.001")
        self.assertEqual(result["summary"]["apiCount"], 1)
        self.assertTrue(result["summary"]["moduleTraits"]["hasUpdateApi"])
        self.assertTrue(result["summary"]["moduleTraits"]["usesRedis"])
        self.assertTrue(result["summary"]["moduleTraits"]["hasDbWrite"])

        api_entry = result["apis"][0]
        self.assertEqual(api_entry["operationType"], "update")
        self.assertIn(
            "Sinopac.DawhoEnterprise/API/EnterpriseAPI/EnterpriseAPI/Controllers/SettingController.cs",
            api_entry["codePaths"]["controller"],
        )
        self.assertIn(
            "Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/SettingServiceTests.cs",
            api_entry["codePaths"]["unitTest"],
        )
        self.assertIn(
            "Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/SettingControllerTests.cs",
            api_entry["codePaths"]["integrationTest"],
        )


if __name__ == "__main__":
    unittest.main()
