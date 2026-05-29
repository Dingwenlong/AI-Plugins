from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from project_rules import resolve_asset_path


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def feature_tester_map_path(agent_root: Path | None = None) -> Path | None:
    if agent_root is not None:
        path = (agent_root / "config" / "feature-tester-map.json").resolve()
        return path if path.exists() else None
    return resolve_asset_path("featureTesterMap")


def load_feature_tester_map(agent_root: Path | None = None) -> dict[str, str]:
    path = feature_tester_map_path(agent_root)
    if path is None or not path.exists():
        raise SystemExit(
            "feature-tester-map.json is required at <workspaceRoot>/.agent/config/feature-tester-map.json; "
            "configure the workspace .agent tester map before generating the UT report."
        )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    mapping = payload.get("mapping")
    if not isinstance(mapping, dict):
        raise SystemExit(f"feature-tester-map.json mapping must be an object: {path}")
    return {
        normalize_text(feature_id).casefold(): normalize_text(tester_name)
        for feature_id, tester_name in mapping.items()
        if normalize_text(feature_id) and normalize_text(tester_name)
    }


def resolve_feature_tester_name(function_code: str, agent_root: Path | None = None) -> str:
    normalized_function_code = normalize_text(function_code)
    tester_name = load_feature_tester_map(agent_root).get(normalized_function_code.casefold())
    if not tester_name:
        raise SystemExit(
            f"feature-tester-map.json missing tester for Feature ID '{normalized_function_code}'; "
            "add it under <workspaceRoot>/.agent/config/feature-tester-map.json."
        )
    return tester_name
