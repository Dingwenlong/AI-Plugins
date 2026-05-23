from __future__ import annotations

import subprocess
import sys
import unittest

from test_support import SKILL_ROOT, read_json, temp_dir, write_json


class CompactReportOutputsTests(unittest.TestCase):
    def test_compact_report_outputs_promotes_final_files_and_removes_sidecars(self) -> None:
        workspace = temp_dir()
        final_manifest = workspace / "module.autofixed.job.json"
        final_results = workspace / "module.autofixed.results.json"
        coverage_gap = workspace / "module.coverage-gap.json"
        plan = workspace / "module.test-improvement-plan.md"
        autofix_report = workspace / "module.autofix-report.json"
        autofixed_gap = workspace / "module.autofixed.coverage-gap.json"

        write_json(final_manifest, {"document": {"outputPath": "report.docx"}})
        write_json(final_results, {"summary": {"passed": 1}})
        write_json(coverage_gap, {"summary": {"gapCount": 3}})
        plan.write_text("# Plan\n", encoding="utf-8")
        write_json(autofix_report, {"appliedChangeCount": 2})
        write_json(autofixed_gap, {"summary": {"gapCount": 1}})

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "compact_report_outputs.py"),
                str(final_manifest),
                str(final_results),
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        promoted_manifest = workspace / "module.job.json"
        promoted_results = workspace / "module.results.json"
        self.assertTrue(promoted_manifest.exists())
        self.assertTrue(promoted_results.exists())
        self.assertEqual(read_json(promoted_results)["summary"]["passed"], 1)
        self.assertFalse(final_manifest.exists())
        self.assertFalse(final_results.exists())
        self.assertFalse(coverage_gap.exists())
        self.assertFalse(plan.exists())
        self.assertFalse(autofix_report.exists())
        self.assertFalse(autofixed_gap.exists())

    def test_compact_report_outputs_can_keep_debug_sidecars(self) -> None:
        workspace = temp_dir()
        final_manifest = workspace / "module.autofixed.job.json"
        final_results = workspace / "module.autofixed.results.json"
        coverage_gap = workspace / "module.coverage-gap.json"

        write_json(final_manifest, {"document": {"outputPath": "report.docx"}})
        write_json(final_results, {"summary": {"passed": 1}})
        write_json(coverage_gap, {"summary": {"gapCount": 3}})

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "compact_report_outputs.py"),
                str(final_manifest),
                str(final_results),
                "--keep-debug",
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        self.assertTrue((workspace / "module.job.json").exists())
        self.assertTrue((workspace / "module.results.json").exists())
        self.assertTrue(coverage_gap.exists())

    def test_compact_report_outputs_removes_module_level_sidecars_for_report_job_names(self) -> None:
        workspace = temp_dir()
        final_manifest = workspace / "report-job.json"
        final_results = workspace / "report-job.results.json"
        coverage_gap = workspace / "coverage-gap.json"
        module_scope = workspace / "module-scope.json"
        template_classification = workspace / "template-classification.json"
        autofix_report = workspace / "report-job.autofix-report.json"

        write_json(final_manifest, {"document": {"outputPath": "report.docx"}})
        write_json(final_results, {"summary": {"passed": 1}})
        write_json(coverage_gap, {"summary": {"gapCount": 3}})
        write_json(module_scope, {"moduleCode": "N.006"})
        write_json(template_classification, {"summary": {"applicable": 1}})
        write_json(autofix_report, {"appliedChangeCount": 2})

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "compact_report_outputs.py"),
                str(final_manifest),
                str(final_results),
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        self.assertTrue(final_manifest.exists())
        self.assertTrue(final_results.exists())
        self.assertFalse(coverage_gap.exists())
        self.assertFalse(module_scope.exists())
        self.assertFalse(template_classification.exists())
        self.assertFalse(autofix_report.exists())

    def test_compact_report_outputs_preserves_postman_mcp_evidence_artifacts(self) -> None:
        workspace = temp_dir()
        final_manifest = workspace / "module.autofixed.job.json"
        final_results = workspace / "module.autofixed.results.json"
        evidence_root = workspace / "postman-mcp" / "Setting.Query" / "success"
        evidence_root.mkdir(parents=True, exist_ok=True)
        request_json = evidence_root / "request.json"
        response_json = evidence_root / "response.json"
        status_png = evidence_root / "status.png"

        write_json(final_manifest, {"document": {"outputPath": "report.docx"}})
        write_json(final_results, {"summary": {"passed": 1}})
        write_json(request_json, {"method": "GET"})
        write_json(response_json, {"statusCode": 200})
        status_png.write_bytes(b"png")

        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "compact_report_outputs.py"),
                str(final_manifest),
                str(final_results),
            ],
            cwd=str(SKILL_ROOT),
            check=True,
        )

        self.assertTrue(request_json.exists())
        self.assertTrue(response_json.exists())
        self.assertTrue(status_png.exists())


if __name__ == "__main__":
    unittest.main()
