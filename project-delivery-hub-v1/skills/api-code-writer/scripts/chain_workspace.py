from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_FILENAME = "local-workspaces.json"
CHAIN_STATUS_SCHEMA_VERSION = "1.0.0"
AGENT_ROOT_ENV_KEYS = ("PROJECT_AGENT_ROOT",)
WORKSPACE_ROOT_ENV_KEYS = ("PROJECT_WORKSPACE_ROOT",)
WORKSPACE_KEY_ENV_KEYS = ("PROJECT_WORKSPACE_KEY",)
RULES_ROOT_ENV_KEYS = ("PROJECT_RULES_ROOT",)


@dataclass(frozen=True)
class ChainWorkspace:
    project_root: Path
    agent_root: Path
    workspace_root: Path | None
    rules_root: Path | None
    workspace_key: str | None
    config_source: Path | None
    resolution_source: str

    @property
    def context_root(self) -> Path:
        return self.agent_root / "context"

    @property
    def status_path(self) -> Path:
        return self.agent_root / "status" / "chain-status.json"

    @property
    def project_rules_root(self) -> Path:
        if self.rules_root is not None:
            return self.rules_root
        if self.workspace_key:
            return self.agent_root / "project-rules" / self.workspace_key
        return self.agent_root / "project-rules" / "default"

    @property
    def project_rules_catalog_path(self) -> Path:
        return self.project_rules_root / "catalog.json"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_env(keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = clean_text(os.environ.get(key))
        if value:
            return value
    return None


def resolve_path(value: str | None, *, base: Path | None = None) -> Path | None:
    text = clean_text(value)
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    return path.resolve()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def find_plugin_root(start: Path | None = None) -> Path | None:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".codex-plugin" / "plugin.json").exists():
            return candidate
    return None


def load_workspace_config(start: Path | None = None) -> tuple[dict[str, Any], Path | None]:
    candidates: list[Path] = []
    plugin_root = find_plugin_root(start)
    if plugin_root is not None:
        candidates.append(plugin_root / "references" / CONFIG_FILENAME)
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for parent in [current, *current.parents]:
        candidates.append(parent / "references" / CONFIG_FILENAME)

    seen: set[Path] = set()
    for candidate in candidates:
        normalized = candidate.resolve()
        if normalized in seen:
            continue
        seen.add(normalized)
        if not normalized.exists():
            continue
        payload = json.loads(normalized.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            return payload, normalized
    return {}, None


def workspace_items(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = config.get("workspaces")
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def select_config_workspace(
    config: dict[str, Any],
    *,
    project_root: Path,
    workspace_root_arg: str | None,
    workspace_key_arg: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    items = workspace_items(config)
    requested_key = clean_text(workspace_key_arg) or first_env(WORKSPACE_KEY_ENV_KEYS)
    if requested_key and requested_key in items:
        return requested_key, items[requested_key]

    requested_root = resolve_path(workspace_root_arg or first_env(WORKSPACE_ROOT_ENV_KEYS))
    if requested_root is not None:
        for key, value in items.items():
            configured_root = resolve_path(clean_text(value.get("workspaceRoot")))
            if configured_root is not None and configured_root == requested_root:
                return key, value

    for key, value in items.items():
        configured_root = resolve_path(clean_text(value.get("workspaceRoot")))
        if configured_root is not None and is_relative_to(project_root, configured_root):
            return key, value
    return None, None


def resolve_chain_workspace(
    *,
    project_root: Path,
    agent_dir_arg: str = ".agent",
    agent_root_arg: str | None = None,
    rules_root_arg: str | None = None,
    workspace_root_arg: str | None = None,
    workspace_key_arg: str | None = None,
    start_path: Path | None = None,
) -> ChainWorkspace:
    project_root = project_root.resolve()
    explicit_agent_root = resolve_path(agent_root_arg)
    if explicit_agent_root is not None:
        workspace_root = resolve_path(workspace_root_arg) or explicit_agent_root.parent
        rules_root = resolve_path(rules_root_arg or first_env(RULES_ROOT_ENV_KEYS))
        if rules_root is None:
            rules_root = explicit_agent_root / "project-rules" / (workspace_key_arg or "default")
        return ChainWorkspace(project_root, explicit_agent_root, workspace_root, rules_root, workspace_key_arg, None, "arg")

    env_agent_root = resolve_path(first_env(AGENT_ROOT_ENV_KEYS))
    if env_agent_root is not None:
        workspace_root = resolve_path(workspace_root_arg or first_env(WORKSPACE_ROOT_ENV_KEYS)) or env_agent_root.parent
        workspace_key = workspace_key_arg or first_env(WORKSPACE_KEY_ENV_KEYS)
        rules_root = resolve_path(rules_root_arg or first_env(RULES_ROOT_ENV_KEYS))
        if rules_root is None:
            rules_root = env_agent_root / "project-rules" / (workspace_key or "default")
        return ChainWorkspace(project_root, env_agent_root, workspace_root, rules_root, workspace_key, None, "env")

    config, config_source = load_workspace_config(start_path)
    selected_key, selected_workspace = select_config_workspace(
        config,
        project_root=project_root,
        workspace_root_arg=workspace_root_arg,
        workspace_key_arg=workspace_key_arg,
    )
    if selected_workspace is not None:
        workspace_root = resolve_path(workspace_root_arg or clean_text(selected_workspace.get("workspaceRoot")))
        agent_root = resolve_path(clean_text(selected_workspace.get("agentRoot")), base=workspace_root)
        if agent_root is not None:
            rules_root = resolve_path(
                rules_root_arg or first_env(RULES_ROOT_ENV_KEYS) or clean_text(selected_workspace.get("rulesRoot")),
                base=workspace_root,
            )
            if rules_root is None:
                rules_root = agent_root / "project-rules" / (selected_key or "default")
            return ChainWorkspace(project_root, agent_root, workspace_root, rules_root, selected_key, config_source, "config")

    legacy_agent = Path(agent_dir_arg).expanduser()
    if not legacy_agent.is_absolute():
        legacy_agent = project_root / legacy_agent
    legacy_agent = legacy_agent.resolve()
    rules_root = resolve_path(rules_root_arg or first_env(RULES_ROOT_ENV_KEYS))
    if rules_root is None:
        rules_root = legacy_agent / "project-rules" / "default"
    return ChainWorkspace(project_root, legacy_agent, project_root, rules_root, None, config_source, "legacy")


def normalize_persisted_path(path: Path | str | None, *, base: Path | str | None = None) -> str | None:
    if path is None:
        return None
    raw = Path(path)
    if not raw.is_absolute():
        return raw.as_posix()
    resolved = raw.resolve()
    if base is None:
        return resolved.as_posix()
    agent_path = Path(base).resolve()
    try:
        return Path(os.path.relpath(resolved, agent_path)).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def load_project_rules_catalog(rules_root: Path) -> dict[str, Any]:
    return load_json_object(rules_root / "catalog.json")


def project_rule_catalog_gap(rules_root: Path) -> dict[str, Any] | None:
    catalog_path = rules_root / "catalog.json"
    if catalog_path.exists():
        return None
    return {
        "gapType": "project_rules_missing",
        "severity": "warning",
        "blocking": False,
        "message": f"缺少专案规则库 catalog：{catalog_path.as_posix()}；将只执行通用流程，不加载项目专属规则。",
    }


def resolve_project_asset_path(rules_root: Path, asset_key: str) -> Path | None:
    catalog = load_project_rules_catalog(rules_root)
    assets = catalog.get("assets")
    if not isinstance(assets, dict):
        return None
    raw_path = clean_text(assets.get(asset_key))
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = rules_root / path
    return path.resolve() if path.exists() else None


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_workspace_snapshot(workspace: ChainWorkspace) -> None:
    payload = {
        "schemaVersion": "1.0.0",
        "workspaceKey": workspace.workspace_key,
        "workspaceRoot": workspace.workspace_root.as_posix() if workspace.workspace_root else None,
        "agentRoot": workspace.agent_root.as_posix(),
        "rulesRoot": workspace.project_rules_root.as_posix(),
        "rulesCatalog": workspace.project_rules_catalog_path.as_posix(),
        "lastProjectRoot": workspace.project_root.as_posix(),
        "resolutionSource": workspace.resolution_source,
        "configSource": workspace.config_source.as_posix() if workspace.config_source else None,
        "updatedAt": now_iso(),
    }
    dump_json(workspace.agent_root / "config" / "chain-workspace.json", payload)


def update_chain_status(
    *,
    agent_root: Path,
    function_code: str | None,
    stage: str,
    status: str | None,
    phase: str | None = None,
    message: str | None = None,
    project_root: Path | None = None,
    workspace_key: str | None = None,
    artifacts: dict[str, Any] | None = None,
    blockers: list[Any] | None = None,
) -> None:
    if not function_code:
        return
    status_path = agent_root / "status" / "chain-status.json"
    payload = load_json_object(status_path)
    functions = payload.get("functions")
    if not isinstance(functions, dict):
        functions = {}
    record = functions.get(function_code)
    if not isinstance(record, dict):
        record = {}

    stage_key = f"{stage}Status" if not stage.endswith("Status") else stage
    if status:
        record[stage_key] = status
    if phase:
        record[f"{stage}Phase"] = phase
    if message:
        record["lastMessage"] = message
    if project_root is not None:
        record["projectRoot"] = project_root.as_posix()
    if workspace_key:
        record["workspaceKey"] = workspace_key
    if artifacts:
        existing_artifacts = record.get("artifacts")
        if not isinstance(existing_artifacts, dict):
            existing_artifacts = {}
        existing_artifacts.update(artifacts)
        record["artifacts"] = existing_artifacts
    if blockers is not None:
        record["blockers"] = blockers
    record["updatedAt"] = now_iso()
    functions[function_code] = record

    payload.update(
        {
            "schemaVersion": CHAIN_STATUS_SCHEMA_VERSION,
            "agentRoot": agent_root.as_posix(),
            "updatedAt": now_iso(),
            "functions": functions,
        }
    )
    dump_json(status_path, payload)
