from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "send_wedoc_change_records.py"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_config(root: Path) -> Path:
    config_path = root / ".agent" / "config" / "wedoc-smartsheet-targets.json"
    webhook_url = (
        "https://qyapi.weixin.qq.com"
        + "/cgi-bin/wedoc/smartsheet/webhook?key=abcdefgh"
    )
    write_json(
        config_path,
        {
            "targets": {
                "common-change-list": {
                    "displayName": "Common change list",
                    "description": "CommonFunc/CommonUtil changes",
                    "keywords": ["Common", "異動清單"],
                    "webhookUrl": webhook_url,
                    "userId": "jimmy-user-id",
                    "requestFormat": {
                        "schema": {
                            "fld_note": "備註",
                            "fld_content": "調整內容",
                            "fld_date": "調整日期",
                            "fld_user": "調整人",
                            "fld_type": "所屬類型",
                            "fld_api": "調整接口",
                        },
                        "fieldMap": {
                            "note": "fld_note",
                            "content": "fld_content",
                            "date": "fld_date",
                            "user": "fld_user",
                            "type": "fld_type",
                            "api": "fld_api",
                        },
                    },
                }
            }
        },
    )
    return config_path


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_records_json_is_payload_source_and_excel_is_evidence_only() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config_path = make_config(root)
        excel_path = root / "Common異動清單.xlsx"
        records_path = root / "records.json"
        write_text(excel_path, "not parsed by this script")
        write_json(
            records_path,
            [
                {
                    "note": "變更公共方法",
                    "content": "1. 調整內容來自 records-json",
                    "type": "CommonUtil",
                    "api": "GetCommonCurrency",
                }
            ],
        )

        result = run_script(
            "--config",
            str(config_path),
            "--target-key",
            "common-change-list",
            "--excel",
            str(excel_path),
            "--records-json",
            str(records_path),
            "--date",
            "2026/5/23",
            "--dry-run",
        )

        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(result.stdout)
        values = payload["add_records"][0]["values"]
        assert values["fld_note"] == "變更公共方法"
        assert values["fld_content"] == "1. 調整內容來自 records-json"
        assert values["fld_type"] == "CommonUtil"
        assert values["fld_api"] == "GetCommonCurrency"
        assert values["fld_user"] == [{"user_id": "jimmy-user-id"}]


def test_excel_without_records_json_blocks_add_records() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config_path = make_config(root)
        excel_path = root / "Common異動清單.xlsx"
        write_text(excel_path, "evidence only")

        result = run_script(
            "--config",
            str(config_path),
            "--target-key",
            "common-change-list",
            "--excel",
            str(excel_path),
            "--dry-run",
        )

        assert result.returncode == 2
        assert "--records-json is required when adding records" in result.stderr


def main() -> int:
    test_records_json_is_payload_source_and_excel_is_evidence_only()
    print("[pass] test_records_json_is_payload_source_and_excel_is_evidence_only")
    test_excel_without_records_json_blocks_add_records()
    print("[pass] test_excel_without_records_json_blocks_add_records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
