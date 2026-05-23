from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from test_support import read_json, temp_dir, write_json

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from classify_template_items import build_classification


class ClassifyTemplateItemsTests(unittest.TestCase):
    def test_classify_template_items_marks_non_applicable_sections(self) -> None:
        module_scope = {
            "moduleCode": "N.001.001",
            "repoRoot": "D:/Repo",
            "contextRoot": "D:/Repo/.agent/context/N.001.001",
            "solutionPath": "D:/Repo/App.sln",
            "summary": {
                "apiCount": 2,
                "moduleTraits": {
                    "hasHttpApi": True,
                    "hasQueryApi": True,
                    "hasCreateApi": False,
                    "hasUpdateApi": True,
                    "hasDeleteApi": False,
                    "hasDownloadApi": False,
                    "hasNotifyApi": False,
                    "usesRedis": True,
                    "usesSql": True,
                    "hasDbRead": True,
                    "hasDbWrite": True,
                    "hasUnitTests": True,
                    "hasIntegrationTests": True,
                },
            },
            "apis": [
                {
                    "apiId": "N.001.001.setting.getuseralias",
                    "operationType": "query",
                    "businessTraits": {
                        "hasRequestPayload": False,
                        "hasValidationRules": False,
                        "usesRedis": True,
                        "usesSql": True,
                        "hasDbRead": True,
                        "hasDbWrite": False,
                    },
                    "codePaths": {
                        "controller": ["Controllers/SettingController.cs"],
                        "service": ["Business/Setting/SettingService.GetUserAlias.cs"],
                        "entity": [],
                        "common": [],
                        "unitTest": ["Test/UnitTesting/SettingServiceTests.cs"],
                        "integrationTest": ["Test/IntegrationTesting/SettingControllerTests.cs"],
                    },
                },
                {
                    "apiId": "N.001.001.setting.updateuseralias",
                    "operationType": "update",
                    "businessTraits": {
                        "hasRequestPayload": True,
                        "hasValidationRules": True,
                        "usesRedis": True,
                        "usesSql": True,
                        "hasDbRead": True,
                        "hasDbWrite": True,
                    },
                    "codePaths": {
                        "controller": ["Controllers/SettingController.cs"],
                        "service": ["Business/Setting/SettingService.UpdateUserAlias.cs"],
                        "entity": [],
                        "common": ["Common/ValidateModelStateFilter.cs"],
                        "unitTest": ["Test/UnitTesting/SettingServiceTests.cs"],
                        "integrationTest": ["Test/IntegrationTesting/SettingControllerTests.cs"],
                    },
                },
            ],
        }
        template_outline = {
            "sections": [
                {
                    "sectionId": "UT-01",
                    "title": "UT-01 API 介面規格與一致性",
                    "items": [
                        {"caseId": "ut-01-001", "checkItem": "Endpoint 路由 / HTTP Method / 版本 與介面設計文件一致"},
                        {"caseId": "ut-01-003", "checkItem": "OpenAPI/Swagger 文件已更新且可正常呼叫(含範例與說明)"},
                    ],
                },
                {
                    "sectionId": "UT-06",
                    "title": "UT-06 修改/更新類 API",
                    "items": [
                        {"caseId": "ut-06-001", "checkItem": "DB 資料已正確更新"},
                    ],
                },
                {
                    "sectionId": "UT-07",
                    "title": "UT-07 刪除類 API",
                    "items": [
                        {"caseId": "ut-07-001", "checkItem": "刪除後資料不可再查得"},
                    ],
                },
                {
                    "sectionId": "UT-08",
                    "title": "UT-08 匯出/下載類 API",
                    "items": [
                        {"caseId": "ut-08-001", "checkItem": "下載檔案內容正確"},
                    ],
                },
            ],
        }

        classification = build_classification(module_scope, template_outline)

        summary = classification["summary"]
        self.assertEqual(summary["sectionCounts"]["applicable"], 2)
        self.assertEqual(summary["sectionCounts"]["not_applicable"], 2)

        ut01 = classification["sections"][0]
        self.assertEqual(ut01["applicability"], "applicable")
        self.assertEqual(ut01["items"][0]["recommendedMode"], "code_inspection")
        self.assertEqual(ut01["items"][1]["recommendedMode"], "code_inspection")
        self.assertTrue(ut01["items"][0]["codeInspection"]["evidencePaths"])

        ut06 = classification["sections"][1]
        self.assertEqual(ut06["applicability"], "applicable")
        self.assertEqual(ut06["items"][0]["recommendedMode"], "unit_test")
        self.assertIn("N.001.001.setting.updateuseralias", ut06["traceability"]["apis"])
        self.assertTrue(ut06["traceability"]["pathGroups"]["controller"])

        ut07 = classification["sections"][2]
        self.assertEqual(ut07["applicability"], "not_applicable")
        self.assertEqual(ut07["items"][0]["recommendedMode"], "skip")

        ut08 = classification["sections"][3]
        self.assertEqual(ut08["applicability"], "not_applicable")
        self.assertEqual(ut08["items"][0]["recommendedMode"], "skip")

    def test_classify_template_items_cli_writes_json(self) -> None:
        root = temp_dir()
        module_scope_path = root / "module-scope.json"
        template_outline_path = root / "template-outline.json"
        output_path = root / "classification.json"

        write_json(
            module_scope_path,
            {
                "moduleCode": "N.009.001",
                "repoRoot": "D:/Repo",
                "contextRoot": "D:/Repo/.agent/context/N.009.001",
                "solutionPath": "D:/Repo/App.sln",
                "summary": {
                    "apiCount": 1,
                    "moduleTraits": {
                        "hasHttpApi": True,
                        "hasQueryApi": True,
                        "hasCreateApi": False,
                        "hasUpdateApi": False,
                        "hasDeleteApi": False,
                        "hasDownloadApi": False,
                        "hasNotifyApi": False,
                        "usesRedis": False,
                        "usesSql": False,
                        "hasDbRead": False,
                        "hasDbWrite": False,
                        "hasUnitTests": False,
                        "hasIntegrationTests": False,
                    },
                },
                "apis": [
                    {
                        "apiId": "N.009.001.query.sample",
                        "operationType": "query",
                        "businessTraits": {
                            "hasRequestPayload": False,
                            "hasValidationRules": False,
                            "usesRedis": False,
                            "usesSql": False,
                            "hasDbRead": False,
                            "hasDbWrite": False,
                        },
                        "codePaths": {
                            "controller": [],
                            "service": [],
                            "entity": [],
                            "common": [],
                            "unitTest": [],
                            "integrationTest": [],
                        },
                    }
                ],
            },
        )
        write_json(
            template_outline_path,
            {
                "sections": [
                    {
                        "sectionId": "UT-04",
                        "title": "UT-04 查詢/列表類 API",
                        "items": [{"caseId": "ut-04-001", "checkItem": "查詢結果正確"}],
                    }
                ]
            },
        )

        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "classify_template_items.py"),
                str(module_scope_path),
                str(template_outline_path),
                "--output",
                str(output_path),
            ],
            check=True,
        )

        payload = read_json(output_path)
        self.assertEqual(payload["moduleContext"]["moduleCode"], "N.009.001")
        self.assertEqual(payload["sections"][0]["sectionId"], "UT-04")
        self.assertEqual(payload["sections"][0]["applicability"], "applicable")

    def test_classify_template_items_marks_attachment_checks_not_applicable_when_api_has_no_attachment_surface(self) -> None:
        module_scope = {
            "moduleCode": "B.003",
            "repoRoot": "D:/Repo",
            "contextRoot": "D:/Repo/.agent/context/B.003",
            "solutionPath": "D:/Repo/App.sln",
            "summary": {
                "apiCount": 1,
                "moduleTraits": {
                    "hasHttpApi": True,
                    "hasQueryApi": False,
                    "hasCreateApi": False,
                    "hasUpdateApi": False,
                    "hasDeleteApi": False,
                    "hasDownloadApi": False,
                    "hasNotifyApi": False,
                    "usesRedis": False,
                    "usesSql": True,
                    "hasDbRead": True,
                    "hasDbWrite": False,
                    "hasUnitTests": True,
                    "hasIntegrationTests": False,
                },
            },
            "apis": [
                {
                    "apiId": "B.003.commonutil.checkprelogindevicestatus",
                    "operationType": "unknown",
                    "businessTraits": {
                        "hasRequestPayload": True,
                        "hasValidationRules": True,
                        "usesRedis": False,
                        "usesSql": True,
                        "hasDbRead": True,
                        "hasDbWrite": False,
                    },
                    "request": {
                        "fields": ["deviceId", "custId"],
                    },
                    "response": {
                        "fields": ["verifyType", "returnCode"],
                    },
                    "codePaths": {
                        "controller": ["Controllers/CommonUtilController.cs"],
                        "service": ["Business/CommonUtilService.CheckPreLoginDeviceStatus.cs"],
                        "entity": [],
                        "common": [],
                        "unitTest": ["Test/UnitTesting/CommonUtilServiceTests.cs"],
                        "integrationTest": [],
                    },
                }
            ],
        }
        template_outline = {
            "sections": [
                {
                    "sectionId": "UT-02",
                    "title": "UT-02 請求參數驗證",
                    "items": [
                        {
                            "caseId": "ut-02-007",
                            "checkItem": "檔案/附件(如有):大小/類型/MIME/副檔名驗證;超限回傳是否正確(依規格)",
                        }
                    ],
                }
            ]
        }

        classification = build_classification(module_scope, template_outline)
        item = classification["sections"][0]["items"][0]
        self.assertEqual(item["applicability"], "not_applicable")
        self.assertEqual(item["recommendedMode"], "skip")
        self.assertIn("接口未涉及檔案/附件處理", item["applicabilityReason"])


if __name__ == "__main__":
    unittest.main()
