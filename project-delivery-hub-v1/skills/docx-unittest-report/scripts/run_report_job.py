from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from docx_report_utils import default_results_path, ensure_absolute_posix, load_json


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Run the manifest-driven UnitTest/IntegrationTest/Postman MCP evidence pipeline and write results back into the DOCX report.",
    )
    parser.add_argument("manifest_path", help="Path to the manifest JSON.")
    parser.add_argument("--results-json", help="Override path for the results JSON.")
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Do not collect UnitTest results; only apply an existing results JSON.",
    )
    parser.add_argument(
        "--skip-apply",
        action="store_true",
        help="Do not write results back into the DOCX.",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    manifest_path = Path(args.manifest_path).expanduser().resolve()
    manifest = load_json(manifest_path)
    results_path = (
        Path(args.results_json).expanduser().resolve()
        if args.results_json
        else Path(default_results_path(manifest_path))
    )

    if not args.skip_collect:
        subprocess.run(
            [
                sys.executable,
                str(skill_root / "scripts" / "collect_unittest_results.py"),
                str(manifest_path),
                "--output",
                str(results_path),
            ],
            cwd=str(skill_root),
            check=True,
        )

    if not args.skip_apply:
        subprocess.run(
            [
                sys.executable,
                str(skill_root / "scripts" / "apply_report_results.py"),
                str(manifest_path),
                str(results_path),
            ],
            cwd=str(skill_root),
            check=True,
        )

    print(f"Manifest: {ensure_absolute_posix(manifest_path)}")
    print(f"Results: {ensure_absolute_posix(results_path)}")
    print(f"Output DOCX: {ensure_absolute_posix(manifest['document']['outputPath'])}")


if __name__ == "__main__":
    main()
