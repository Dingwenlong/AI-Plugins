from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SENSITIVE_KEY_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "x-auth-token",
}
SENSITIVE_KEY_FRAGMENTS = (
    "access_token",
    "refresh_token",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "api_key",
    "apikey",
)
MASKED_VALUES = {
    "",
    "***",
    "****",
    "<masked>",
    "[masked]",
    "masked",
    "<redacted>",
    "[redacted]",
    "redacted",
    "***masked***",
    "***redacted***",
}


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def read_json_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON artifact must be an object.")
    return payload


def parse_status_code(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    text = normalize_text(value)
    match = re.search(r"\b([1-5][0-9]{2})\b", text)
    if match:
        return int(match.group(1))
    return None


def response_status_code(response_payload: dict[str, Any]) -> int | None:
    candidate_paths = [
        ("statusCode",),
        ("status_code",),
        ("httpStatusCode",),
        ("httpStatus",),
        ("status",),
        ("response", "statusCode"),
        ("response", "status_code"),
        ("response", "httpStatusCode"),
        ("response", "httpStatus"),
        ("response", "status"),
    ]
    for path in candidate_paths:
        current: Any = response_payload
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        status_code = parse_status_code(current)
        if status_code is not None:
            return status_code
    return None


def expected_status_codes(values: Any) -> list[int]:
    if values is None:
        return []
    raw_values = values if isinstance(values, list) else [values]
    codes: list[int] = []
    for raw_value in raw_values:
        code = parse_status_code(raw_value)
        if code is None or code in codes:
            continue
        codes.append(code)
    return codes


def is_masked_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple)):
        return all(is_masked_value(item) for item in value)
    if isinstance(value, dict):
        return False
    text = normalize_text(value)
    if not text:
        return True
    lowered = text.casefold()
    if lowered in MASKED_VALUES:
        return True
    return bool(re.fullmatch(r"[*xX]{3,}", text))


def sensitive_key_reason(key: str) -> str:
    lowered = normalize_text(key).casefold()
    if lowered in SENSITIVE_KEY_NAMES:
        return "sensitive header"
    if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
        return "sensitive field"
    return ""


def find_unmasked_sensitive_values(payload: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = normalize_text(key)
            child_path = f"{path}.{key_text}" if key_text else path
            reason = sensitive_key_reason(key_text)
            if reason and not is_masked_value(value):
                findings.append(f"{child_path} contains unmasked {reason}")
                continue
            findings.extend(find_unmasked_sensitive_values(value, child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            findings.extend(find_unmasked_sensitive_values(value, f"{path}[{index}]"))
    return findings


def extract_request_summary(request_payload: dict[str, Any]) -> tuple[str, str]:
    request_node = request_payload.get("request") if isinstance(request_payload.get("request"), dict) else {}
    method = normalize_text(request_payload.get("method") or request_node.get("method") or "HTTP")
    url = normalize_text(
        request_payload.get("url")
        or request_payload.get("endpoint")
        or request_node.get("url")
        or request_node.get("endpoint")
        or ""
    )
    return method.upper(), url


def render_status_screenshot(
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    output_path: Path,
    expected_codes: list[int],
) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:  # pragma: no cover - fallback only when Pillow is unavailable.
        raise RuntimeError("Pillow is required to render Postman MCP status screenshots.") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    method, url = extract_request_summary(request_payload)
    status_code = response_status_code(response_payload)
    matched = status_code in expected_codes if status_code is not None else False
    width, height = 960, 360
    background = (246, 248, 250)
    accent = (26, 127, 55) if matched else (207, 34, 46)
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    try:
        title_font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 24)
        body_font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)
        mono_font = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 18)
    except Exception:
        title_font = body_font = mono_font = font

    draw.rectangle((0, 0, width, 72), fill=(36, 41, 47))
    draw.text((28, 22), "Postman MCP / 真实接口调用状态", fill=(255, 255, 255), font=title_font)
    draw.rounded_rectangle((28, 104, width - 28, 304), radius=8, fill=(255, 255, 255), outline=(208, 215, 222))
    draw.ellipse((56, 134, 96, 174), fill=accent)
    draw.text((116, 138), "通過" if matched else "不通過", fill=accent, font=title_font)
    draw.text((56, 202), f"Method: {method}", fill=(36, 41, 47), font=mono_font)
    draw.text((56, 232), f"URL: {url or '<not captured>'}", fill=(36, 41, 47), font=mono_font)
    draw.text((56, 262), f"HTTP Status: {status_code or '<missing>'}", fill=(36, 41, 47), font=mono_font)
    draw.text((56, 292), f"Expected: {', '.join(str(code) for code in expected_codes) or '<missing>'}", fill=(87, 96, 106), font=body_font)
    image.save(output_path, format="PNG")


def validate_api_runtime_call_artifacts(
    *,
    request_path: Path,
    response_path: Path,
    screenshot_path: Path,
    expected_codes: list[int],
) -> tuple[dict[str, Any], list[str]]:
    blocking_issues: list[str] = []
    call_record: dict[str, Any] = {
        "requestPath": request_path.as_posix(),
        "responsePath": response_path.as_posix(),
        "screenshotPath": screenshot_path.as_posix(),
        "expectedStatusCodes": expected_codes,
        "statusCode": None,
        "method": "",
        "url": "",
        "status": "pending",
        "failureDetails": [],
    }

    if not request_path.exists():
        blocking_issues.append(f"Postman MCP request JSON not found: {request_path.as_posix()}")
    if not response_path.exists():
        blocking_issues.append(f"Postman MCP response JSON not found: {response_path.as_posix()}")
    if not screenshot_path.exists():
        blocking_issues.append(f"Postman MCP status screenshot not found: {screenshot_path.as_posix()}")
    elif screenshot_path.stat().st_size <= 0:
        blocking_issues.append(f"Postman MCP status screenshot is empty: {screenshot_path.as_posix()}")
    if not expected_codes:
        blocking_issues.append("apiRuntimeCall.expectedStatusCodes must contain at least one HTTP status code.")
    if blocking_issues:
        return call_record, blocking_issues

    try:
        request_payload = read_json_payload(request_path)
    except Exception as exc:
        blocking_issues.append(f"Postman MCP request JSON is invalid: {request_path.as_posix()} ({exc})")
        return call_record, blocking_issues

    try:
        response_payload = read_json_payload(response_path)
    except Exception as exc:
        blocking_issues.append(f"Postman MCP response JSON is invalid: {response_path.as_posix()} ({exc})")
        return call_record, blocking_issues

    sensitive_findings = (
        find_unmasked_sensitive_values(request_payload, "$.request")
        + find_unmasked_sensitive_values(response_payload, "$.response")
    )
    if sensitive_findings:
        blocking_issues.extend(sensitive_findings)
        return call_record, blocking_issues

    method, url = extract_request_summary(request_payload)
    status_code = response_status_code(response_payload)
    call_record.update(
        {
            "statusCode": status_code,
            "method": method,
            "url": url,
        }
    )

    if status_code is None:
        blocking_issues.append(f"Postman MCP response JSON does not include a parseable HTTP status: {response_path.as_posix()}")
        return call_record, blocking_issues

    if status_code in expected_codes:
        call_record["status"] = "passed"
    else:
        call_record["status"] = "failed"
        call_record["failureDetails"] = [
            {
                "message": f"HTTP status {status_code} is not in expected statuses: {', '.join(str(code) for code in expected_codes)}",
                "attachments": [response_path.as_posix(), screenshot_path.as_posix()],
            }
        ]
    return call_record, blocking_issues


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Validate or render Postman MCP actual API call evidence artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render-status", help="Render a deterministic status PNG.")
    render_parser.add_argument("--request", required=True, help="Path to request.json.")
    render_parser.add_argument("--response", required=True, help="Path to response.json.")
    render_parser.add_argument("--output", required=True, help="Path to status.png.")
    render_parser.add_argument("--expected-status", action="append", default=[], help="Expected HTTP status code. Can be repeated.")

    args = parser.parse_args()
    if args.command == "render-status":
        request_path = Path(args.request).expanduser().resolve()
        response_path = Path(args.response).expanduser().resolve()
        output_path = Path(args.output).expanduser().resolve()
        request_payload = read_json_payload(request_path)
        response_payload = read_json_payload(response_path)
        render_status_screenshot(
            request_payload,
            response_payload,
            output_path,
            expected_status_codes(args.expected_status),
        )
        print(f"Postman MCP status screenshot written: {output_path.as_posix()}")


if __name__ == "__main__":
    main()
