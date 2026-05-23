from __future__ import annotations

import subprocess
import sys
import unittest

from docx import Document

from test_support import build_temp_manifest, create_sample_docx, read_json, temp_dir, write_json, SKILL_ROOT


class ApplyReportResultsTests(unittest.TestCase):
    def test_apply_report_results_updates_status_actual_and_evidence_without_duplicates(self) -> None:
        workspace = temp_dir()
        docx_path = create_sample_docx(workspace / "sample.docx")
        output_docx = workspace / "sample.report.docx"
        manifest_path = build_temp_manifest(docx_path, output_docx)
        manifest = read_json(manifest_path)
        manifest["sections"][0]["items"][0]["enabled"] = True
        write_json(manifest_path, manifest)

        results_path = workspace / "sample.results.json"
        write_json(
            results_path,
            {
                "manifestPath": manifest_path.as_posix(),
                "trxPath": (workspace / "sample.trx").as_posix(),
                "summary": {"passed": 1, "failed": 0, "manual": 1, "pending": 0, "skipped": 0},
                "cases": [
                    {
                        "caseId": "ut-01-001",
                        "checkItem": "HTTP 狀態碼使用正確(依規格)",
                        "status": "passed",
                        "actualResult": "通過，詳見 UnitTest 結果",
                        "boundTests": ["Tests.Sample.Passes"],
                        "missingTests": [],
                        "failureDetails": [],
                        "attachmentPaths": [],
                        "trxPath": (workspace / "sample.trx").as_posix(),
                    },
                    {
                        "caseId": "ut-01-002",
                        "checkItem": "DB 資料已正確更新",
                        "status": "manual",
                        "actualResult": "已人工確認 DB 結果",
                        "boundTests": [],
                        "missingTests": [],
                        "failureDetails": [],
                        "attachmentPaths": ["docs/db-check.txt"],
                        "trxPath": "",
                    },
                    {
                        "caseId": "ut-10-001",
                        "checkItem": "回應結構符合規格",
                        "status": "pending",
                        "actualResult": "待補",
                        "boundTests": [],
                        "missingTests": [],
                        "failureDetails": [],
                        "attachmentPaths": [],
                        "trxPath": "",
                    },
                ],
            },
        )

        script = SKILL_ROOT / "scripts" / "apply_report_results.py"
        for _ in range(2):
            subprocess.run(
                [sys.executable, str(script), str(manifest_path), str(results_path)],
                cwd=str(SKILL_ROOT),
                check=True,
            )

        document = Document(str(output_docx))
        table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
        self.assertIn("通過", table_text)
        self.assertIn("已人工確認 DB 結果", table_text)
        self.assertNotIn("綁定測試：Tests.Sample.Passes", table_text)
        self.assertIn("共 2 項檢查，已執行 1 項，其中通過 1 項、失敗 0 項。", table_text)
        self.assertIn("共 1 項檢查，已執行 0 項，其中通過 0 項、失敗 0 項。", table_text)
        self.assertNotIn("自動化證據摘要", table_text)
        self.assertNotIn("綁定測試", table_text)
        self.assertNotIn("結論：", table_text)
        self.assertNotIn("待補項目：", table_text)


if __name__ == "__main__":
    unittest.main()
