from __future__ import annotations

import unittest
from pathlib import Path

from test_support import ASSETS_DIR, temp_dir
from trx_result_utils import build_test_lookup, parse_trx


class TrxResultUtilsTests(unittest.TestCase):
    def test_parse_trx_extracts_status_error_and_attachments(self) -> None:
        payload = parse_trx(ASSETS_DIR / "sample-results.trx")
        self.assertEqual(payload["summary"]["total"], 3)
        self.assertEqual(payload["summary"]["passed"], 1)
        self.assertEqual(payload["summary"]["failed"], 1)
        self.assertEqual(payload["summary"]["skipped"], 1)

        failed = next(test for test in payload["tests"] if test["testName"] == "Tests.Sample.Fails")
        self.assertEqual(failed["status"], "failed")
        self.assertIn("Expected success", failed["errorMessage"])
        self.assertTrue(any(path.endswith("sample-attachments/fail-log.txt") for path in failed["attachments"]))

    def test_parse_trx_raises_when_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            parse_trx(Path("Z:/missing/sample-results.trx"))

    def test_parse_trx_raises_when_invalid_xml(self) -> None:
        workspace = temp_dir()
        broken = workspace / "broken.trx"
        broken.write_text("<broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            parse_trx(broken)

    def test_build_test_lookup_supports_unique_class_method_aliases(self) -> None:
        lookup = build_test_lookup(
            [
                {
                    "testName": (
                        "Sinopac.DawhoEnterprise.Test.UnitTesting.EnterpriseAPI."
                        "EnterpriseApiUnit.SettingServiceTests.QueryUserLoginLogAsync_ShouldReturnNotFound_WhenSqlReturnsNoRows"
                    )
                }
            ]
        )

        self.assertIn(
            "SettingServiceTests.QueryUserLoginLogAsync_ShouldReturnNotFound_WhenSqlReturnsNoRows",
            lookup,
        )

    def test_build_test_lookup_drops_ambiguous_class_method_aliases(self) -> None:
        lookup = build_test_lookup(
            [
                {"testName": "NamespaceA.SettingServiceTests.QueryUserLoginLogAsync_ShouldReturnNotFound_WhenSqlReturnsNoRows"},
                {"testName": "NamespaceB.SettingServiceTests.QueryUserLoginLogAsync_ShouldReturnNotFound_WhenSqlReturnsNoRows"},
            ]
        )

        self.assertNotIn(
            "SettingServiceTests.QueryUserLoginLogAsync_ShouldReturnNotFound_WhenSqlReturnsNoRows",
            lookup,
        )


if __name__ == "__main__":
    unittest.main()
