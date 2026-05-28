from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_delivery.py"
FUNCTION = "D.001.001_D.002.001"


class PackageDeliverySequenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "system-design"
        self.agent_root = self.root / ".agent"
        self.workspace.mkdir()
        (self.workspace / "v1.x").mkdir()
        (self.workspace / "v1.x Reference" / "共用svg").mkdir(parents=True)
        (self.workspace / "v1.x Reference" / "共用vsdx").mkdir(parents=True)
        self._write(self.workspace / "v1.x" / "TSD.D.001.001_D.002.001_臺(外)幣定存查詢_v1.3_20260528.docx", "x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_packager(self, summary: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--workspace",
                str(self.workspace),
                "--agent-root",
                str(self.agent_root),
                "--function",
                "D.001.001 D.002.001",
                "--summary",
                str(summary),
                "--date",
                "20260528",
                "--dry-run",
                "--json",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def write_summary(self, common_rows: str = "") -> Path:
        summary = self.workspace / "summary.md"
        summary.write_text(
            f"""## 总体判断
95% 可进入开发，接近冻版。

## 已确认交付物
| 类别 | 文件 | 说明 |
| --- | --- | --- |
| TSD | `v1.x/TSD.D.001.001_D.002.001_臺(外)幣定存查詢_v1.3_20260528.docx` | 已确认 |
| 本功能时序图 | 已确认 | 由正式时序图来源解析 |
{common_rows}
""",
            encoding="utf-8",
        )
        return summary

    def create_agent_sequence(self, ref_text: str = "循序圖請參考：04_CommonFunc.GenFntTranSeq 取得交易序號") -> Path:
        seq = self.agent_root / "functions" / FUNCTION / "analysis" / "sequence-diagrams"
        (seq / "vsdx").mkdir(parents=True)
        self._write(seq / "vsdx" / f"{FUNCTION}_01.svg", f"<svg><desc>{ref_text}</desc></svg>")
        self._write(seq / "vsdx" / f"{FUNCTION}_01.vsdx", "not a real vsdx")
        self._write(seq / f"{FUNCTION}_sequence.puml", ref_text)
        self._write(seq / f"{FUNCTION}_native_visio_spec.json", "{}")
        return seq

    def create_reference_sequence(self) -> Path:
        ref = self.workspace / "v1.x Reference"
        self._write(ref / f"{FUNCTION}_01.svg", "<svg></svg>")
        self._write(ref / f"{FUNCTION}_01.vsdx", "not a real vsdx")
        self._write(ref / "D.001_D.002_01.svg", "<svg>old</svg>")
        self._write(ref / "~$$D.001.001_D.002.001_01.~vsdx", "lock")
        self._write(ref / "D.001.001_D.002.001_01.vsdx.bak", "bak")
        return ref

    def create_legacy_sequence(self) -> None:
        legacy = self.workspace / "output" / "sequence_diagram" / FUNCTION / "vsdx"
        legacy.mkdir(parents=True)
        self._write(legacy / f"{FUNCTION}_01.svg", "<svg></svg>")
        self._write(legacy / f"{FUNCTION}_01.vsdx", "not a real vsdx")

    def create_common_pair(self, name: str = "04_CommonFunc.GenFntTranSeq") -> str:
        svg = self.workspace / "v1.x Reference" / "共用svg" / f"{name}.svg"
        vsdx = self.workspace / "v1.x Reference" / "共用vsdx" / f"{name}_01.vsdx"
        self._write(svg, "<svg></svg>")
        self._write(vsdx, "not a real vsdx")
        return f"| 共用/外部时序图 | `{svg.relative_to(self.workspace)}` `{vsdx.relative_to(self.workspace)}` | 已确认 |\n"

    def test_agent_sequence_wins_over_legacy_output(self) -> None:
        self.create_agent_sequence()
        self.create_legacy_sequence()
        summary = self.write_summary(self.create_common_pair())

        result = self.run_packager(summary)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        source_root = payload["sequenceValidation"][0]["sourceRoot"]
        self.assertIn(str(self.agent_root), source_root)
        self.assertNotIn("output\\sequence_diagram", json.dumps(payload, ensure_ascii=False))

    def test_reference_used_when_agent_sequence_missing(self) -> None:
        self.create_reference_sequence()
        summary = self.write_summary()

        result = self.run_packager(summary)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        files = [Path(item["source"]).name for item in payload["files"] if item["category"] == "function_diagram"]
        self.assertEqual(files, [f"{FUNCTION}_01.svg", f"{FUNCTION}_01.vsdx"])
        self.assertNotIn("D.001_D.002_01.svg", files)
        self.assertNotIn("~$$D.001.001_D.002.001_01.~vsdx", files)

    def test_only_legacy_output_blocks(self) -> None:
        self.create_legacy_sequence()
        summary = self.write_summary()

        result = self.run_packager(summary)

        self.assertEqual(result.returncode, 2)
        self.assertIn("output/sequence_diagram", result.stderr)
        self.assertIn("已禁止", result.stderr)

    def test_missing_common_diagram_blocks(self) -> None:
        self.create_agent_sequence()
        summary = self.write_summary()

        result = self.run_packager(summary)

        self.assertEqual(result.returncode, 2)
        self.assertIn("未完整列出", result.stderr)
        self.assertIn("04_CommonFunc.GenFntTranSeq", result.stderr)

    def test_ambiguous_common_diagram_blocks(self) -> None:
        self.create_agent_sequence()
        row = self.create_common_pair()
        duplicate = self.workspace / "v1.x Reference" / "共用svg" / "04_CommonFunc.GenFntTranSeq_01.svg"
        self._write(duplicate, "<svg></svg>")
        row = row.replace(
            "| 已确认 |",
            f"`{duplicate.relative_to(self.workspace)}` | 已确认 |",
        )
        summary = self.write_summary(row)

        result = self.run_packager(summary)

        self.assertEqual(result.returncode, 2)
        self.assertIn("多重匹配 svg", result.stderr)

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
