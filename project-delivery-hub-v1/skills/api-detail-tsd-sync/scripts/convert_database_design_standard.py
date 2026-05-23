from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def looks_like_ole(path: Path) -> bool:
    return path.read_bytes()[:8] == OLE_MAGIC


def inspect_ole(path: Path) -> dict[str, Any]:
    try:
        import olefile
    except Exception as exc:
        return {"available": False, "error": str(exc), "streams": []}

    try:
        ole = olefile.OleFileIO(str(path))
        streams = ["/".join(item) for item in ole.listdir()]
    except Exception as exc:
        return {"available": True, "error": str(exc), "streams": []}

    protections = []
    if any("DRMEncryptedDataSpace" in stream for stream in streams):
        protections.append("DRMEncryptedDataSpace")
    if any(stream == "EncryptedPackage" for stream in streams):
        protections.append("EncryptedPackage")
    return {"available": True, "streams": streams, "detectedProtection": protections}


def try_libreoffice(source: Path) -> dict[str, Any]:
    candidates = [
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files\LibreOffice\program\soffice.com",
    ]
    soffice = next((Path(item) for item in candidates if item and Path(item).exists()), None)
    if soffice is None:
        return {"tool": "LibreOffice headless", "result": "skipped", "message": "soffice not found"}

    with tempfile.TemporaryDirectory() as temp_dir:
        completed = subprocess.run(
            [str(soffice), "--headless", "--convert-to", "txt:Text", "--outdir", temp_dir, str(source)],
            text=True,
            capture_output=True,
            timeout=90,
        )
        converted = list(Path(temp_dir).glob("*.txt"))
        if completed.returncode == 0 and converted and converted[0].read_text(encoding="utf-8", errors="ignore").strip():
            return {
                "tool": "LibreOffice headless",
                "result": "success",
                "text": converted[0].read_text(encoding="utf-8", errors="ignore"),
            }
        message = (completed.stdout + completed.stderr).strip() or "no readable text was produced"
        return {"tool": "LibreOffice headless", "result": "failed", "message": message}


def try_word_com(source: Path) -> dict[str, Any]:
    if not sys.platform.startswith("win"):
        return {"tool": "Microsoft Word COM", "result": "skipped", "message": "not running on Windows"}

    script = f"""
$ErrorActionPreference = 'Stop'
$src = @'
{source}
'@
$outDir = Join-Path $env:TEMP ('dbstd_word_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $outDir | Out-Null
$outTxt = Join-Path $outDir 'database-design-standard-v3.txt'
$word = $null
$doc = $null
try {{
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $doc = $word.Documents.Open($src, $false, $true, $false)
  $doc.SaveAs([ref]$outTxt, [ref]2)
  $doc.Close([ref]$false)
  $word.Quit()
  Get-Content -LiteralPath $outTxt -Raw -Encoding Default
}} finally {{
  if ($doc -ne $null) {{ try {{ $doc.Close([ref]$false) }} catch {{}} }}
  if ($word -ne $null) {{ try {{ $word.Quit() }} catch {{}} }}
}}
"""
    powershell = shutil.which("powershell") or shutil.which("powershell.exe") or "powershell.exe"
    try:
        completed = subprocess.run([powershell, "-NoProfile", "-Command", script], text=True, capture_output=True, timeout=120)
    except Exception as exc:
        return {"tool": "Microsoft Word COM", "result": "failed", "message": str(exc)}
    text = completed.stdout.strip()
    if completed.returncode == 0 and text:
        return {"tool": "Microsoft Word COM", "result": "success", "text": text}
    message = (completed.stderr or completed.stdout).strip() or "COM open failed"
    return {"tool": "Microsoft Word COM", "result": "failed", "message": message}


def write_status(out_dir: Path, source: Path, attempts: list[dict[str, Any]], ole_info: dict[str, Any]) -> Path:
    source_dir = out_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    status = {
        "schemaVersion": "1.0.0",
        "sourceName": "數據庫設計規範",
        "version": "v3 20220908",
        "originalFileName": source.name,
        "sourceSha256": sha256(source),
        "detectedContainer": "ole_compound_file" if looks_like_ole(source) else "unknown",
        "detectedProtection": ole_info.get("detectedProtection", []),
        "status": "source_unreadable",
        "conversionAttempts": [
            {key: value for key, value in attempt.items() if key != "text"}
            for attempt in attempts
        ],
        "ruleGeneration": {
            "generatedDatabaseDesignRules": False,
            "reason": "Do not generate empty or inferred database design rules without readable source text.",
        },
    }
    status_path = source_dir / "source-status.json"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return status_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert database design standard v3 into a readable source artifact.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    source = args.source
    if not source.exists():
        print(json.dumps({"status": "source_missing", "source": str(source)}, ensure_ascii=False), file=sys.stderr)
        return 2

    ole_info = inspect_ole(source) if looks_like_ole(source) else {"detectedProtection": []}
    attempts = [try_libreoffice(source), try_word_com(source)]
    success = next((attempt for attempt in attempts if attempt.get("result") == "success" and attempt.get("text")), None)
    source_dir = args.out_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    if success:
        text_path = source_dir / "database-design-standard-v3.txt"
        text_path.write_text(str(success["text"]).strip() + "\n", encoding="utf-8")
        status = {
            "schemaVersion": "1.0.0",
            "sourceName": "數據庫設計規範",
            "version": "v3 20220908",
            "originalFileName": source.name,
            "sourceSha256": sha256(source),
            "status": "source_converted",
            "convertedTextPath": "source/database-design-standard-v3.txt",
            "conversionAttempts": [{key: value for key, value in attempt.items() if key != "text"} for attempt in attempts],
        }
        (source_dir / "source-status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "source_converted", "textPath": str(text_path)}, ensure_ascii=False))
        return 0

    status_path = write_status(args.out_dir, source, [*attempts, {"tool": "OLE stream inspection", "result": "blocked", "detectedProtection": ole_info.get("detectedProtection", [])}], ole_info)
    print(json.dumps({"status": "source_unreadable", "statusPath": str(status_path)}, ensure_ascii=False), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
