#!/usr/bin/env python3
"""Send change records to a WeCom WeDoc smartsheet webhook."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


CONFIG_FILE_NAME = "wedoc-smartsheet-targets.json"
CONFIG_ENV = "WEDOC_SMARTSHEET_CONFIG"
WEBHOOK_PREFIX = "https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/webhook"
RECEIPT_DIR_NAME = "wedoc-smartsheet-receipts"
REQUIRED_FIELD_KEYS = ("note", "content", "date", "user", "type", "api")
PLACEHOLDER_PATTERNS = (
    "REPLACE",
    "YOUR_",
    "<",
    ">",
    "TODO",
    "填入",
    "示例",
    "EXAMPLE",
)


class ConfigError(ValueError):
    """Raised when target configuration is missing or invalid."""


class ReceiptLogError(RuntimeError):
    """Raised when a sent add_records response cannot be recorded."""


def now_beijing() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def now_iso() -> str:
    return now_beijing().isoformat(timespec="seconds")


def date_to_ms(value: str | None) -> str:
    if not value:
        dt = now_beijing()
    else:
        normalized = value.replace("-", "/")
        parts = [int(x) for x in normalized.split("/")]
        if len(parts) != 3:
            raise ValueError(f"Unsupported date: {value}")
        dt = datetime(parts[0], parts[1], parts[2], tzinfo=timezone(timedelta(hours=8)))
    start = datetime(dt.year, dt.month, dt.day, tzinfo=timezone(timedelta(hours=8)))
    return str(int(start.timestamp() * 1000))


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def example_config_path() -> Path:
    return plugin_root() / "references" / "wedoc-smartsheet-targets.example.json"


def is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    upper = text.upper()
    return any(marker in upper for marker in PLACEHOLDER_PATTERNS)


def find_config(explicit_path: str | None) -> Path:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env_path = os.environ.get(CONFIG_ENV)
    if env_path:
        candidates.append(Path(env_path))
    cwd = Path.cwd().resolve()
    candidates.extend(parent / ".agent" / "config" / CONFIG_FILE_NAME for parent in (cwd, *cwd.parents))

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise ConfigError(
        "Missing WeDoc smartsheet config. Copy the template to "
        f"<workspaceRoot>\\.agent\\config\\{CONFIG_FILE_NAME}: {example_config_path()}"
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_records(path: Path) -> list[dict[str, Any]]:
    records = load_json(path)
    if not isinstance(records, list):
        raise ConfigError("--records-json must contain a JSON array")
    if any(not isinstance(item, dict) for item in records):
        raise ConfigError("--records-json items must be objects")
    return records


def safe_file_stem(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return stem.strip("._") or "target"


def default_receipt_log_path(config_path: Path, target_key: str) -> Path:
    config_path = config_path.resolve()
    if config_path.parent.name.lower() == "config" and config_path.parent.parent.name.lower() == ".agent":
        agent_root = config_path.parent.parent
    else:
        agent_root = config_path.parent
    return agent_root / RECEIPT_DIR_NAME / f"{safe_file_stem(target_key)}.jsonl"


def resolve_receipt_log_path(config_path: Path, target_key: str, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).resolve()
    return default_receipt_log_path(config_path, target_key)


def target_summary(key: str, target: dict[str, Any]) -> str:
    display = str(target.get("displayName") or "").strip()
    desc = str(target.get("description") or "").strip()
    if desc:
        return f"{key}: {display} - {desc}".strip()
    return f"{key}: {display}".strip()


def list_targets(config: dict[str, Any]) -> list[str]:
    targets = config.get("targets")
    if not isinstance(targets, dict) or not targets:
        raise ConfigError("Config must define targets")
    return [target_summary(key, target if isinstance(target, dict) else {}) for key, target in targets.items()]


def target_search_blob(key: str, target: dict[str, Any]) -> str:
    parts = [
        key,
        str(target.get("displayName") or ""),
        str(target.get("description") or ""),
    ]
    keywords = target.get("keywords")
    if isinstance(keywords, list):
        parts.extend(str(item) for item in keywords)
    return "\n".join(parts).lower()


def hint_matches(hint: str, key: str, target: dict[str, Any]) -> bool:
    blob = target_search_blob(key, target)
    normalized = hint.strip().lower()
    if not normalized:
        return False
    if normalized in blob:
        return True
    tokens = [token for token in re.split(r"[\s,;，；/\\|]+", normalized) if token]
    return bool(tokens) and all(token in blob for token in tokens)


def select_target(config: dict[str, Any], target_key: str | None, target_hint: str | None) -> tuple[str, dict[str, Any]]:
    targets = config.get("targets")
    if not isinstance(targets, dict) or not targets:
        raise ConfigError("Config must define targets")

    if target_key:
        target = targets.get(target_key)
        if not isinstance(target, dict):
            available = "\n".join(list_targets(config))
            raise ConfigError(f"Target key not found: {target_key}\nAvailable targets:\n{available}")
        return target_key, target

    if target_hint:
        matches = [
            (key, target)
            for key, target in targets.items()
            if isinstance(target, dict) and hint_matches(target_hint, key, target)
        ]
        if len(matches) == 1:
            return matches[0]
        available = "\n".join(list_targets(config))
        if not matches:
            raise ConfigError(f"No target matched hint: {target_hint}\nAvailable targets:\n{available}")
        matched = "\n".join(target_summary(key, target) for key, target in matches)
        raise ConfigError(f"Target hint is ambiguous: {target_hint}\nMatched targets:\n{matched}")

    if len(targets) == 1:
        key, target = next(iter(targets.items()))
        if isinstance(target, dict):
            return key, target

    available = "\n".join(list_targets(config))
    raise ConfigError(f"Multiple targets are configured. Choose one with --target-key.\nAvailable targets:\n{available}")


def validate_webhook(webhook: Any) -> str:
    if is_placeholder(webhook):
        raise ConfigError("target.webhookUrl is required and must not be a placeholder")
    url = str(webhook).strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "qyapi.weixin.qq.com":
        raise ConfigError("target.webhookUrl must be a qyapi.weixin.qq.com HTTPS URL")
    if parsed.path != "/cgi-bin/wedoc/smartsheet/webhook":
        raise ConfigError("target.webhookUrl must point to /cgi-bin/wedoc/smartsheet/webhook")
    key_values = urllib.parse.parse_qs(parsed.query).get("key", [])
    if not key_values or is_placeholder(key_values[0]):
        raise ConfigError("target.webhookUrl must include a real key query parameter")
    return url


def validate_request_format(target: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    request_format = target.get("requestFormat")
    if not isinstance(request_format, dict):
        raise ConfigError("target.requestFormat is required")
    schema = request_format.get("schema")
    field_map = request_format.get("fieldMap")
    if not isinstance(schema, dict) or not schema:
        raise ConfigError("target.requestFormat.schema is required")
    if not isinstance(field_map, dict):
        raise ConfigError("target.requestFormat.fieldMap is required")

    normalized_schema = {str(key): str(value) for key, value in schema.items()}
    normalized_map: dict[str, str] = {}
    for logical_key in REQUIRED_FIELD_KEYS:
        field_id = field_map.get(logical_key)
        if is_placeholder(field_id):
            raise ConfigError(f"target.requestFormat.fieldMap.{logical_key} is required")
        field_id = str(field_id)
        if field_id not in normalized_schema:
            raise ConfigError(f"fieldMap.{logical_key} references unknown schema field id: {field_id}")
        normalized_map[logical_key] = field_id
    return normalized_schema, normalized_map


def validate_target(target_key: str, target: dict[str, Any]) -> dict[str, Any]:
    display_name = str(target.get("displayName") or target_key)
    webhook = validate_webhook(target.get("webhookUrl"))
    user_id = target.get("userId")
    user_text = target.get("userText")
    if not is_placeholder(user_id):
        person_mode = "userId"
        person_identity = str(user_id).strip()
    elif not is_placeholder(user_text):
        person_mode = "userText"
        person_identity = str(user_text).strip()
    else:
        raise ConfigError(f"target '{target_key}' must define a real userId or userText")
    schema, field_map = validate_request_format(target)
    return {
        "key": target_key,
        "displayName": display_name,
        "webhookUrl": webhook,
        "userId": str(user_id).strip() if not is_placeholder(user_id) else "",
        "userText": str(user_text).strip() if not is_placeholder(user_text) else "",
        "personMode": person_mode,
        "personIdentity": person_identity,
        "schema": schema,
        "fieldMap": field_map,
    }


def normalize_record(raw: dict[str, Any]) -> dict[str, str]:
    return {
        "note": str(raw.get("note") or raw.get("備註") or ""),
        "content": str(raw.get("content") or raw.get("調整內容") or ""),
        "type": str(raw.get("type") or raw.get("所屬類型") or ""),
        "api": str(raw.get("api") or raw.get("調整接口") or ""),
    }


def person_value(target: dict[str, Any]) -> list[dict[str, str]] | list[str]:
    if target["personMode"] == "userId":
        return [{"user_id": target["personIdentity"]}]
    return [target["personIdentity"]]


def build_add_payload(records: list[dict[str, Any]], date_ms: str, target: dict[str, Any]) -> dict[str, Any]:
    field_map = target["fieldMap"]
    return {
        "schema": target["schema"],
        "add_records": [
            {
                "values": {
                    field_map["note"]: record["note"],
                    field_map["content"]: record["content"],
                    field_map["date"]: date_ms,
                    field_map["user"]: person_value(target),
                    field_map["type"]: record["type"],
                    field_map["api"]: record["api"],
                }
            }
            for record in (normalize_record(item) for item in records)
        ],
    }


def build_update_user_payload(record_ids: list[str], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": target["schema"],
        "update_records": [
            {
                "record_id": record_id,
                "values": {target["fieldMap"]["user"]: person_value(target)},
            }
            for record_id in record_ids
            if record_id
        ],
    }


def post_json(webhook: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        data = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {data}") from exc
    return json.loads(data)


def build_receipt_entry(
    *,
    target: dict[str, Any],
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    request_records = request_payload.get("add_records")
    if not isinstance(request_records, list):
        request_records = []

    response_records = extract_response_records(response_payload)

    records = []
    for index, request_record in enumerate(request_records):
        response_record = response_records[index] if index < len(response_records) else {}
        if not isinstance(request_record, dict):
            request_record = {}
        if not isinstance(response_record, dict):
            response_record = {}
        record_id = str(
            response_record.get("record_id")
            or response_record.get("recordId")
            or response_record.get("result_id")
            or ""
        )
        records.append(
            {
                "inputIndex": index,
                "recordId": record_id,
                "resultIdAlias": record_id,
                "requestValues": request_record.get("values", {}),
                "responseValues": response_record.get("values", {}),
            }
        )

    return {
        "receiptId": str(uuid.uuid4()),
        "operation": "add_records",
        "targetKey": target["key"],
        "targetDisplayName": target["displayName"],
        "createdAt": now_iso(),
        "requestPayload": request_payload,
        "responsePayload": response_payload,
        "records": records,
    }


def extract_response_records(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[Any] = [
        response_payload.get("add_records"),
        response_payload.get("records"),
    ]
    data = response_payload.get("data")
    if isinstance(data, dict):
        candidates.extend([data.get("add_records"), data.get("records")])
    result = response_payload.get("result")
    if isinstance(result, dict):
        candidates.extend([result.get("add_records"), result.get("records")])

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item if isinstance(item, dict) else {} for item in candidate]
    return []


def append_receipt_log(receipt_log_path: Path, receipt: dict[str, Any]) -> None:
    try:
        receipt_log_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
    except OSError as exc:
        raise ReceiptLogError(f"已发送但回执未记录: {receipt_log_path}: {exc}") from exc


def iter_receipts(receipt_log_path: Path) -> list[dict[str, Any]]:
    if not receipt_log_path.exists():
        return []
    receipts: list[dict[str, Any]] = []
    with receipt_log_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ConfigError(f"Invalid receipt log JSON at {receipt_log_path}:{line_number}: {exc}") from exc
            if isinstance(item, dict):
                receipts.append(item)
    return receipts


def list_receipts(receipt_log_path: Path) -> None:
    receipts = iter_receipts(receipt_log_path)
    if not receipts:
        print(f"No receipt records found: {receipt_log_path}")
        return
    print("createdAt\ttargetKey\trecordId\tresultIdAlias\ttype\tapi\treceiptId")
    for receipt in receipts:
        created_at = str(receipt.get("createdAt") or "")
        target_key = str(receipt.get("targetKey") or "")
        receipt_id = str(receipt.get("receiptId") or "")
        for record in receipt.get("records") or []:
            if not isinstance(record, dict):
                continue
            values = record.get("requestValues") if isinstance(record.get("requestValues"), dict) else {}
            record_id = str(record.get("recordId") or "")
            result_id_alias = str(record.get("resultIdAlias") or "")
            row_type = ""
            api = ""
            if isinstance(receipt.get("requestPayload"), dict):
                schema = receipt["requestPayload"].get("schema") or {}
                if isinstance(schema, dict):
                    for field_id, title in schema.items():
                        if title == "所屬類型":
                            row_type = str(values.get(field_id) or "")
                        if title == "調整接口":
                            api = str(values.get(field_id) or "")
            print(f"{created_at}\t{target_key}\t{record_id}\t{result_id_alias}\t{row_type}\t{api}\t{receipt_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help=f"Path to .agent/config/{CONFIG_FILE_NAME}.")
    parser.add_argument("--target-key", help="Exact target key in the smartsheet config.")
    parser.add_argument("--target-hint", help="Natural-language hint used to match target key/displayName/keywords.")
    parser.add_argument("--list-targets", action="store_true", help="List configured targets and exit.")
    parser.add_argument("--excel", help="Optional workbook evidence for header/list style. Rows are not parsed.")
    parser.add_argument("--records-json", help="JSON array with note/content/type/api records; required for add_records.")
    parser.add_argument("--date")
    parser.add_argument("--update-user-record-ids", help="Comma-separated record ids to update user field only.")
    parser.add_argument("--receipt-log", help="Override receipt JSONL path. Defaults to .agent/wedoc-smartsheet-receipts/<targetKey>.jsonl.")
    parser.add_argument("--list-receipts", action="store_true", help="List add_records receipts for the selected target and exit.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config_path = find_config(args.config)
    config = load_json(config_path)
    if args.list_targets:
        print("\n".join(list_targets(config)))
        return 0

    target_key, raw_target = select_target(config, args.target_key, args.target_hint)
    target = validate_target(target_key, raw_target)
    receipt_log_path = resolve_receipt_log_path(config_path, target["key"], args.receipt_log)

    if args.list_receipts:
        list_receipts(receipt_log_path)
        return 0

    if args.excel and not Path(args.excel).exists():
        raise FileNotFoundError(args.excel)

    is_add_records = not bool(args.update_user_record_ids)
    if args.update_user_record_ids:
        record_ids = [item.strip() for item in args.update_user_record_ids.split(",")]
        payload = build_update_user_payload(record_ids, target)
    else:
        if not args.records_json:
            raise ConfigError("--records-json is required when adding records")
        payload = build_add_payload(load_records(Path(args.records_json)), date_to_ms(args.date), target)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0

    response = post_json(target["webhookUrl"], payload)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    if response.get("errcode") != 0:
        return 2
    if is_add_records:
        receipt = build_receipt_entry(target=target, request_payload=payload, response_payload=response)
        append_receipt_log(receipt_log_path, receipt)
        print(f"receiptLog: {receipt_log_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except ReceiptLogError as exc:
        print(f"Receipt log error: {exc}", file=sys.stderr)
        raise SystemExit(3)
