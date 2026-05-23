from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


CONFIG_FILENAME = "local-workspaces.json"
RULES_ROOT_ENV_KEYS = ("PROJECT_RULES_ROOT",)
WORKSPACE_KEY_ENV_KEYS = ("PROJECT_WORKSPACE_KEY",)


def clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def find_plugin_root(start: Path | None = None) -> Path | None:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".codex-plugin" / "plugin.json").exists():
            return candidate
    return None


def first_env(keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = clean_text(os.environ.get(key))
        if value:
            return value
    return None


def load_workspace_config(start: Path | None = None) -> tuple[dict[str, Any], Path | None]:
    plugin_root = find_plugin_root(start)
    if plugin_root is None:
        return {}, None
    path = plugin_root / "references" / CONFIG_FILENAME
    if not path.exists():
        return {}, path
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}, path


def resolve_rules_root(
    rules_root_arg: str | None = None,
    *,
    workspace_key: str | None = None,
    start_path: Path | None = None,
) -> Path | None:
    explicit = clean_text(rules_root_arg) or first_env(RULES_ROOT_ENV_KEYS)
    if explicit:
        return Path(explicit).expanduser().resolve()

    config, _ = load_workspace_config(start_path)
    workspaces = config.get("workspaces") if isinstance(config.get("workspaces"), dict) else {}
    selected_key = clean_text(workspace_key) or first_env(WORKSPACE_KEY_ENV_KEYS) or clean_text(config.get("defaultWorkspace"))
    selected = workspaces.get(selected_key) if selected_key else None
    if not isinstance(selected, dict):
        return None

    raw_rules_root = clean_text(selected.get("rulesRoot"))
    if raw_rules_root:
        return Path(raw_rules_root).expanduser().resolve()

    raw_agent_root = clean_text(selected.get("agentRoot"))
    if raw_agent_root and selected_key:
        return (Path(raw_agent_root).expanduser().resolve() / "project-rules" / selected_key).resolve()
    return None


def load_catalog(rules_root: Path | None) -> dict[str, Any]:
    if rules_root is None:
        return {}
    path = rules_root / "catalog.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def resolve_asset_path(asset_key: str, *, rules_root_arg: str | None = None, fallback: Path | None = None) -> Path | None:
    rules_root = resolve_rules_root(rules_root_arg, start_path=Path(__file__).resolve())
    catalog = load_catalog(rules_root)
    assets = catalog.get("assets") if isinstance(catalog.get("assets"), dict) else {}
    raw_path = clean_text(assets.get(asset_key))
    if raw_path and rules_root is not None:
        path = Path(raw_path)
        if not path.is_absolute():
            path = rules_root / path
        if path.exists():
            return path.resolve()
    return fallback.resolve() if fallback is not None and fallback.exists() else None
