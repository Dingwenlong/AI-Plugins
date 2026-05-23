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

from apply_manifest_gap_fixes import apply_gap_fixes


class ApplyManifestGapFixesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.binding_rules = {
            "strongRules": [
                {
                    "id": "required-validation",
                    "whenCheckItemContainsAny": ["必填"],
                    "recommendedModes": ["integration_test"],
                    "matchTestNameContainsAny": ["missing", "specvalidation"],
                }
            ],
            "codeInspectionRules": [
                {
                    "id": "http-contract",
                    "whenCheckItemContainsAny": ["Endpoint", "HTTP Method"],
                    "pathBuckets": ["controller"],
                    "mustContainAny": ["[Http", "Route("],
                    "passActualResult": "通過，已由代碼定位檢查確認 HTTP 介面契約。",
                    "pendingActualResult": "待補，尚未定位到充分的 HTTP 介面契約證據。",
                }
            ],
            "weakRules": [
                {
                    "id": "response-contract",
                    "whenCheckItemContainsAny": ["Content-Type"],
                    "recommendedModes": ["integration_test"],
                    "matchTestNameContainsAny": ["returnsuccesspayload"],
                }
            ],
        }

    def test_apply_gap_fixes_updates_manual_mode_and_high_confidence_binding(self) -> None:
        manifest = {
            "sections": [
                {
                    "items": [
                        {
                            "caseId": "ut-01-003",
                            "mode": "integration_test",
                            "enabled": False,
                            "notes": "",
                            "testBindings": {"testNames": [], "matchMode": "all_pass", "allowMissing": False},
                        },
                        {
                            "caseId": "ut-02-001",
                            "mode": "integration_test",
                            "enabled": False,
                            "notes": "",
                            "testBindings": {"testNames": [], "matchMode": "all_pass", "allowMissing": False},
                        },
                    ]
                }
            ]
        }
        coverage_gap = {
            "moduleContext": {"moduleCode": "N.001.001"},
            "gaps": [
                {
                    "caseId": "ut-01-003",
                    "gapType": "manual_mode_mismatch",
                    "recommendedMode": "manual",
                    "checkItem": "OpenAPI/Swagger 文件",
                    "traceability": {"apis": ["N.001.001.setting.updateuseralias"]},
                },
                {
                    "caseId": "ut-02-001",
                    "gapType": "missing_test_binding",
                    "recommendedMode": "integration_test",
                    "checkItem": "必填參數有做必填驗證",
                    "traceability": {"apis": ["N.001.001.setting.updateuseralias"]},
                },
            ],
        }
        results = {
            "sourceResults": {
                "integrationTest": {
                    "tests": [
                        {
                            "testName": "Sinopac.DawhoEnterprise.Test.IntegrationTesting.EnterpriseAPI.EnterpriseApiIntegration.SettingControllerTests.UpdateUserAlias_ShouldReturnSpecValidationMessage_WhenAliasMissing"
                        },
                        {
                            "testName": "Sinopac.DawhoEnterprise.Test.IntegrationTesting.EnterpriseAPI.EnterpriseApiIntegration.SettingControllerTests.UpdateUserAlias_ShouldReturnSuccessPayload"
                        },
                    ]
                },
                "unitTest": {"tests": []},
            }
        }

        report = apply_gap_fixes(manifest, coverage_gap, results, self.binding_rules)
        self.assertEqual(report["appliedChangeCount"], 2)

        manual_item = manifest["sections"][0]["items"][0]
        self.assertEqual(manual_item["mode"], "manual")
        self.assertFalse(manual_item["enabled"])
        self.assertEqual(manual_item["testBindings"]["testNames"], [])

        binding_item = manifest["sections"][0]["items"][1]
        self.assertEqual(binding_item["mode"], "integration_test")
        self.assertTrue(binding_item["enabled"])
        self.assertEqual(
            binding_item["testBindings"]["testNames"],
            [
                "Sinopac.DawhoEnterprise.Test.IntegrationTesting.EnterpriseAPI.EnterpriseApiIntegration.SettingControllerTests.UpdateUserAlias_ShouldReturnSpecValidationMessage_WhenAliasMissing"
            ],
        )

    def test_apply_gap_fixes_aligns_mode_but_leaves_unmatched_binding_gap(self) -> None:
        manifest = {
            "sections": [
                {
                    "items": [
                        {
                            "caseId": "ut-06-001",
                            "mode": "integration_test",
                            "enabled": False,
                            "notes": "",
                            "testBindings": {"testNames": [], "matchMode": "all_pass", "allowMissing": False},
                        },
                        {
                            "caseId": "ut-01-002",
                            "mode": "integration_test",
                            "enabled": False,
                            "notes": "",
                            "testBindings": {"testNames": [], "matchMode": "all_pass", "allowMissing": False},
                        },
                    ]
                }
            ]
        }
        coverage_gap = {
            "moduleContext": {"moduleCode": "N.002.001"},
            "gaps": [
                {
                    "caseId": "ut-06-001",
                    "gapType": "mode_mismatch",
                    "recommendedMode": "unit_test",
                    "checkItem": "DB 資料正確更新",
                    "traceability": {"apis": ["N.002.001.setting.updateuseralias"]},
                },
                {
                    "caseId": "ut-01-002",
                    "gapType": "missing_test_binding",
                    "recommendedMode": "integration_test",
                    "checkItem": "Content-Type 正確",
                    "traceability": {"apis": ["N.002.001.setting.updateuseralias"]},
                },
            ],
        }
        results = {
            "sourceResults": {
                "integrationTest": {
                    "tests": [
                        {
                            "testName": "Sinopac.DawhoEnterprise.Test.IntegrationTesting.EnterpriseAPI.EnterpriseApiIntegration.SettingControllerTests.UpdateUserAlias_ShouldReturnSuccessPayload"
                        }
                    ]
                },
                "unitTest": {"tests": []},
            }
        }

        report = apply_gap_fixes(manifest, coverage_gap, results, self.binding_rules)
        self.assertEqual(report["appliedChangeCount"], 1)
        self.assertEqual(manifest["sections"][0]["items"][0]["mode"], "unit_test")
        self.assertEqual(manifest["sections"][0]["items"][1]["testBindings"]["testNames"], [])
        self.assertEqual(len(report["suggestions"]), 1)
        self.assertEqual(report["suggestions"][0]["action"], "weak_suggestion_only")

    def test_apply_gap_fixes_preserves_weak_suggestions_without_autobinding(self) -> None:
        manifest = {
            "sections": [
                {
                    "items": [
                        {
                            "caseId": "ut-01-002",
                            "mode": "integration_test",
                            "enabled": False,
                            "notes": "",
                            "testBindings": {"testNames": [], "matchMode": "all_pass", "allowMissing": False},
                        }
                    ]
                }
            ]
        }
        coverage_gap = {
            "moduleContext": {"moduleCode": "N.004.001"},
            "gaps": [
                {
                    "caseId": "ut-01-002",
                    "gapType": "missing_test_binding",
                    "recommendedMode": "integration_test",
                    "checkItem": "Request/Response Content-Type 正確",
                    "traceability": {"apis": ["N.004.001.setting.getuseralias"]},
                }
            ],
        }
        results = {
            "sourceResults": {
                "integrationTest": {
                    "tests": [
                        {
                            "testName": "Sinopac.DawhoEnterprise.Test.IntegrationTesting.EnterpriseAPI.EnterpriseApiIntegration.SettingControllerTests.GetUserAlias_ShouldReturnSuccessPayload"
                        }
                    ]
                },
                "unitTest": {"tests": []},
            }
        }

        report = apply_gap_fixes(manifest, coverage_gap, results, self.binding_rules)
        self.assertEqual(report["appliedChangeCount"], 0)
        self.assertFalse(manifest["sections"][0]["items"][0]["enabled"])
        self.assertEqual(report["suggestions"][0]["action"], "weak_suggestion_only")

    def test_apply_gap_fixes_populates_code_inspection(self) -> None:
        manifest = {
            "sections": [
                {
                    "items": [
                        {
                            "caseId": "ut-01-001",
                            "mode": "manual",
                            "enabled": False,
                            "notes": "",
                            "codeInspection": {"evidencePaths": []},
                            "testBindings": {"testNames": [], "matchMode": "all_pass", "allowMissing": False},
                        }
                    ]
                }
            ]
        }
        coverage_gap = {
            "moduleContext": {"moduleCode": "N.010.001", "repoRoot": "D:/Repo"},
            "gaps": [
                {
                    "caseId": "ut-01-001",
                    "gapType": "code_inspection_mode_mismatch",
                    "recommendedMode": "code_inspection",
                    "checkItem": "Endpoint 路由 / HTTP Method / 版本 與介面設計文件一致",
                    "traceability": {
                        "apis": ["N.010.001.setting.sample"],
                        "pathGroups": {"controller": ["Controllers/SettingController.cs"]},
                    },
                }
            ],
        }

        report = apply_gap_fixes(manifest, coverage_gap, {"sourceResults": {}}, self.binding_rules)
        self.assertEqual(report["appliedChangeCount"], 1)
        item = manifest["sections"][0]["items"][0]
        self.assertEqual(item["mode"], "code_inspection")
        self.assertTrue(item["enabled"])
        self.assertEqual(item["testBindings"]["testNames"], [])
        self.assertEqual(item["codeInspection"]["ruleId"], "http-contract")
        self.assertEqual(
            item["codeInspection"]["evidencePaths"],
            ["D:/Repo/Controllers/SettingController.cs"],
        )

    def test_apply_manifest_gap_fixes_cli_writes_outputs(self) -> None:
        root = temp_dir()
        coverage_gap_path = root / "coverage-gap.json"
        manifest_path = root / "manifest.json"
        results_path = root / "results.json"
        output_manifest = root / "manifest.autofixed.json"
        output_report = root / "manifest.autofix-report.json"

        write_json(
            coverage_gap_path,
            {
                "moduleContext": {"moduleCode": "N.003.001"},
                "gaps": [
                    {
                        "caseId": "ut-02-001",
                        "gapType": "missing_test_binding",
                        "recommendedMode": "integration_test",
                        "checkItem": "必填參數有做必填驗證",
                        "traceability": {"apis": ["N.003.001.setting.updateuseralias"]},
                    }
                ],
            },
        )
        write_json(
            manifest_path,
            {
                "sections": [
                    {
                        "items": [
                            {
                                "caseId": "ut-02-001",
                                "mode": "integration_test",
                                "enabled": False,
                                "notes": "",
                                "testBindings": {"testNames": [], "matchMode": "all_pass", "allowMissing": False},
                            }
                        ]
                    }
                ]
            },
        )
        write_json(
            results_path,
            {
                "sourceResults": {
                    "integrationTest": {
                        "tests": [
                            {
                                "testName": "Sinopac.DawhoEnterprise.Test.IntegrationTesting.EnterpriseAPI.EnterpriseApiIntegration.SettingControllerTests.UpdateUserAlias_ShouldReturnSpecValidationMessage_WhenAliasMissing"
                            }
                        ]
                    },
                    "unitTest": {"tests": []},
                }
            },
        )
        rules_path = root / "binding-rules.json"
        write_json(rules_path, self.binding_rules)

        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "apply_manifest_gap_fixes.py"),
                str(coverage_gap_path),
                str(manifest_path),
                str(results_path),
                "--binding-rules",
                str(rules_path),
                "--output-manifest",
                str(output_manifest),
                "--output-report",
                str(output_report),
            ],
            check=True,
        )

        updated_manifest = read_json(output_manifest)
        report = read_json(output_report)
        self.assertEqual(report["appliedChangeCount"], 1)
        item = updated_manifest["sections"][0]["items"][0]
        self.assertTrue(item["enabled"])
        self.assertEqual(len(item["testBindings"]["testNames"]), 1)


if __name__ == "__main__":
    unittest.main()
