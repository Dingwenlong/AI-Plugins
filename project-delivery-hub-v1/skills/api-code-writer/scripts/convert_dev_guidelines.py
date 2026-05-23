#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path


OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate that a V6.2 guideline source is readable before indexing it.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args()


def source_kind(path: Path) -> str:
    header = path.read_bytes()[:8]
    if header == OLE_MAGIC:
        return "ole_or_drm_container"
    if zipfile.is_zipfile(path):
        return "openxml_zip"
    suffix = path.suffix.casefold()
    if suffix in {".md", ".markdown", ".json", ".txt"}:
        return "plain_text"
    return "unknown"


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    if not source.exists():
        print(json.dumps({"status": "source_unreadable", "reason": "missing_source", "source": source.as_posix()}, ensure_ascii=False), file=sys.stderr)
        return 2

    kind = source_kind(source)
    if kind == "ole_or_drm_container":
        print(
            json.dumps(
                {
                    "status": "source_unreadable",
                    "reason": "ole_or_drm_container",
                    "source": source.as_posix(),
                    "message": "Convert the guideline to readable Markdown/JSON first; do not index the encrypted/legacy Word container.",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    if kind == "unknown":
        print(json.dumps({"status": "source_unreadable", "reason": "unknown_format", "source": source.as_posix()}, ensure_ascii=False), file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": "1.0.0",
        "status": "readable_source_detected",
        "source": source.as_posix(),
        "sourceKind": kind,
        "nextStep": "Manually split the readable guideline into catalog.json and rules/*.md before runtime use.",
    }
    (out_dir / "source-status.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
