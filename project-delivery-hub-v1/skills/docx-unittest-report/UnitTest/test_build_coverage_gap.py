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

from build_coverage_gap import build_gap_payload


class BuildCoverageGapTests(unittest.TestCase):
    def test_build_gap_payload_detects_missing_bindings_and_non_applicable_items(self) -> None:
        classification = {
            "moduleContext": {"moduleCode": "N.001.001"},
            "sections": [
                {
                    "sectionId": "UT-01",
                    "items": [
                        {
                            "caseId": "ut-01-001",
                            "checkItem": "Endpoint 一致",
                            "applicability": "applicable",
                            "recommendedMode": "integration_test",
                            "traceability": {"apis": ["A"]},
                        },
                        {
                            "caseId": "ut-01-002",
                            "checkItem": "Swagger 文件",
                            "applicability": "applicable",
                            "recommendedMode": "manual",
                            "traceability": {"apis": ["A"]},
                        },
                        {
                            "caseId": "ut-08-001",
                            "checkItem": "下載檔案",
                            "applicability": "not_applicable",
                            "recommendedMode": "skip",
                            "traceability": {"apis": []},
                        },
                    ],
                }
            ],
        }
        manifest = {
            "sections": [
                {
                    "items": [
                        {
                            "caseId": "ut-01-001",
                            "mode": "integration_test",
                            "enabled": False,
                            "testBindings": {"testNames": ["Test.A"], "allowMissing": False},
                        },
                        {
                            "caseId": "ut-01-002",
                            "mode": "manual",
                            "enabled": False,
                            "actualResult": "",
                            "testBindings": {"testNames": [], "allowMissing": False},
                        },
                    ]
                }
            ]
        }
        results = {"cases": []}

        payload = build_gap_payload(classification, manifest, results)
        self.assertEqual(payload["summary"]["applicableItems"], 2)
        self.assertEqual(payload["summary"]["notApplicableItems"], 1)
        self.assertEqual(payload["summary"]["gapCount"], 2)
        gap_types = {gap["gapType"] for gap in payload["gaps"]}
        self.assertIn("binding_disabled", gap_types)
        self.assertIn("manual_evidence_missing", gap_types)

    def test_build_gap_payload_detects_missing_manifest_and_failed_automation(self) -> None:
        classification = {
            "moduleContext": {"moduleCode": "N.002.001"},
            "sections": [
                {
                    "sectionId": "UT-06",
                    "items": [
                        {
                            "caseId": "ut-06-001",
                            "checkItem": "DB 更新正確",
                            "applicability": "applicable",
                            "recommendedMode": "unit_test",
                            "traceability": {"apis": ["B"]},
                        },
                        {
                            "caseId": "ut-06-002",
                            "checkItem": "商業邏輯正確",
                            "applicability": "applicable",
                            "recommendedMode": "unit_test",
                            "traceability": {"apis": ["B"]},
                        },
                    ],
                }
            ],
        }
        manifest = {
            "sections": [
                {
                    "items": [
                        {
                            "caseId": "ut-06-001",
                            "mode": "unit_test",
                            "enabled": True,
                            "testBindings": {"testNames": ["Test.B"], "allowMissing": False},
                        }
                    ]
                }
            ]
        }
        results = {
            "cases": [
                {
                    "caseId": "ut-06-001",
                    "status": "failed",
                }
            ]
        }

        payload = build_gap_payload(classification, manifest, results)
        self.assertEqual(payload["summary"]["gapCount"], 2)
        gap_types = {gap["gapType"] for gap in payload["gaps"]}
        self.assertIn("automation_not_passing", gap_types)
        self.assertIn("manifest_missing", gap_types)

    def test_build_gap_payload_detects_code_inspection_gap(self) -> None:
        classification = {
            "moduleContext": {"moduleCode": "N.005.001", "repoRoot": "D:/Repo"},
            "sections": [
                {
                    "sectionId": "UT-01",
                    "items": [
                        {
                            "caseId": "ut-01-001",
                            "checkItem": "Endpoint 路由 / HTTP Method / 版本 與介面設計文件一致",
                            "applicability": "applicable",
                            "recommendedMode": "code_inspection",
                            "traceability": {"apis": ["C"], "pathGroups": {"controller": ["D:/Repo/Controllers/C.cs"]}},
                        }
                    ],
                }
            ],
        }
        manifest = {
            "sections": [
                {
                    "items": [
                        {
                            "caseId": "ut-01-001",
                            "mode": "manual",
                            "enabled": False,
                            "codeInspection": {"evidencePaths": []},
                            "testBindings": {"testNames": [], "allowMissing": False},
                        }
                    ]
                }
            ]
        }

        payload = build_gap_payload(classification, manifest, {"cases": []})
        self.assertEqual(payload["summary"]["gapCount"], 1)
        self.assertEqual(payload["gaps"][0]["gapType"], "code_inspection_mode_mismatch")

    def test_build_coverage_gap_cli_writes_json_and_plan(self) -> None:
        root = temp_dir()
        classification_path = root / "classification.json"
        manifest_path = root / "manifest.json"
        results_path = root / "results.json"
        output_path = root / "coverage-gap.json"
        plan_path = root / "test-improvement-plan.md"

        write_json(
            classification_path,
            {
                "moduleContext": {"moduleCode": "N.003.001"},
                "sections": [
                    {
                        "sectionId": "UT-02",
                        "items": [
                            {
                                "caseId": "ut-02-001",
                                "checkItem": "必填驗證",
                                "applicability": "applicable",
                                "recommendedMode": "integration_test",
                                "traceability": {"apis": ["C"]},
                            }
                        ],
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
                                "testBindings": {"testNames": [], "allowMissing": False},
                            }
                        ]
                    }
                ]
            },
        )
        write_json(results_path, {"cases": []})

        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "build_coverage_gap.py"),
                str(classification_path),
                "--manifest",
                str(manifest_path),
                "--results",
                str(results_path),
                "--output",
                str(output_path),
                "--plan-md",
                str(plan_path),
            ],
            check=True,
        )

        payload = read_json(output_path)
        self.assertEqual(payload["moduleContext"]["moduleCode"], "N.003.001")
        self.assertEqual(payload["summary"]["gapCount"], 1)
        self.assertTrue(plan_path.exists())


if __name__ == "__main__":
    unittest.main()
