from __future__ import annotations

import hashlib
import json
from typing import Any


_READY_FIXTURE_DEFAULTS = {
    "fixtureStatus": "pending",
    "fixturePhase": "pending",
    "fixtureBlockReason": None,
    "fixtureSourceFingerprint": None,
}


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def _normalized_fixture_value(payload: dict[str, Any], key: str) -> object:
    value = payload.get(key)
    if _clean_text(value):
        return value
    if _clean_text(payload.get("specStatus")) == "done":
        return _READY_FIXTURE_DEFAULTS[key]
    return None


def stable_spec_manifest_hash(payload: dict[str, Any]) -> str:
    """Hash only upstream spec identity and normalized fixture readiness inputs."""

    subset = {
        "specStatus": payload.get("specStatus"),
        "specBlockReason": payload.get("specBlockReason"),
        "specSourceFingerprint": payload.get("specSourceFingerprint") or payload.get("sourceFingerprint"),
        "specSource": payload.get("specSource") or payload.get("source") or {},
        "fixtureStatus": _normalized_fixture_value(payload, "fixtureStatus"),
        "fixturePhase": _normalized_fixture_value(payload, "fixturePhase"),
        "fixtureBlockReason": _normalized_fixture_value(payload, "fixtureBlockReason"),
        "fixtureSourceFingerprint": _normalized_fixture_value(payload, "fixtureSourceFingerprint"),
    }
    rendered = json.dumps(subset, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(rendered.encode('utf-8')).hexdigest()}"
