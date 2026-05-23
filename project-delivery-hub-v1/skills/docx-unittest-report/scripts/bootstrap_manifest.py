from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docx_report_utils import (
    build_manifest_from_outline,
    default_manifest_path,
    load_report_outline,
    write_json,
)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Bootstrap a DOCX-driven UnitTest report manifest from a Word test report.",
    )
    parser.add_argument("docx_path", help="Path to the input DOCX test report.")
    parser.add_argument(
        "--output",
        help="Path to the JSON manifest to create. Defaults next to the DOCX file.",
    )
    parser.add_argument(
        "--output-docx",
        help="Path to the revised DOCX file that later apply_report_results.py should write.",
    )
    args = parser.parse_args()

    outline = load_report_outline(args.docx_path)
    manifest = build_manifest_from_outline(outline, output_docx=args.output_docx)
    output_path = args.output or default_manifest_path(args.docx_path)
    write_json(output_path, manifest)

    print(f"Manifest created: {Path(output_path).resolve().as_posix()}")
    print(f"Sections discovered: {len(manifest['sections'])}")
    print(
        "Fill metadata, UnitTest/IntegrationTest config, and explicit testBindings.testNames before running the job."
    )


if __name__ == "__main__":
    main()
