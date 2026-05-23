from __future__ import annotations

import unittest

from test_support import build_temp_manifest, create_sample_docx, read_json, temp_dir


class BootstrapManifestTests(unittest.TestCase):
    def test_bootstrap_manifest_emits_unittest_contract(self) -> None:
        workspace = temp_dir()
        docx_path = create_sample_docx(workspace / "sample.docx")
        manifest_path = build_temp_manifest(docx_path, workspace / "sample.report.docx")

        manifest = read_json(manifest_path)
        self.assertIn("unitTest", manifest)
        self.assertIn("integrationTest", manifest)
        self.assertNotIn("playwright", manifest)
        self.assertEqual(manifest["sections"][0]["items"][0]["mode"], "integration_test")
        self.assertEqual(manifest["sections"][0]["items"][1]["mode"], "manual")

        auto_item = manifest["sections"][0]["items"][0]
        for forbidden in ("driver", "request", "steps", "assertions", "capture"):
            self.assertNotIn(forbidden, auto_item)

        self.assertEqual(auto_item["testBindings"]["testNames"], [])
        self.assertEqual(auto_item["testBindings"]["matchMode"], "all_pass")
        self.assertFalse(auto_item["testBindings"]["allowMissing"])


if __name__ == "__main__":
    unittest.main()
