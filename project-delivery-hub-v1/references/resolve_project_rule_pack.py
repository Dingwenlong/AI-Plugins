from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


CONFIG_FILENAME = "local-workspaces.json"
DEFAULT_ACTIVE_STATUSES = ("approved", "active")


def clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def find_plugin_root(start: Path | None = None) -> Path | None:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".codex-plugin" / "plugin.json").exists():
            return candidate
    return None


def env_value(*keys: str) -> str:
    for key in keys:
        value = clean_text(os.environ.get(key))
        if value:
            return value
    return ""


def workspace_env_key(workspace_key: str | None, suffix: str) -> str:
    key = clean_text(workspace_key).upper()
    safe_key = "".join(ch if ch.isalnum() else "_" for ch in key)
    return f"{safe_key}_{suffix}" if safe_key else ""


def candidate_from_cwd(workspace_key: str | None) -> Path | None:
    key = clean_text(workspace_key)
    if not key:
        return None
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        rules_root = candidate / ".agent" / "project-rules" / key
        if (rules_root / "catalog.json").exists():
            return rules_root.resolve()
    return None


def resolve_rules_root(
    rules_root_arg: str | None,
    *,
    workspace_key: str | None,
    start_path: Path | None = None,
) -> tuple[Path | None, str, str]:
    key = clean_text(workspace_key) or env_value("PROJECT_WORKSPACE_KEY")
    workspace_rules_env = workspace_env_key(key, "RULES_ROOT")
    explicit = clean_text(rules_root_arg) or env_value(workspace_rules_env, "PROJECT_RULES_ROOT")
    if explicit:
        return Path(explicit).expanduser().resolve(), "explicit-or-env", key

    plugin_root = find_plugin_root(start_path)
    config_path = plugin_root / "references" / CONFIG_FILENAME if plugin_root is not None else None
    config = read_json(config_path) if config_path is not None else {}
    workspaces = config.get("workspaces") if isinstance(config.get("workspaces"), dict) else {}
    selected_key = key or clean_text(config.get("defaultWorkspace"))
    selected = workspaces.get(selected_key) if selected_key else None
    if isinstance(selected, dict):
        raw_rules_root = clean_text(selected.get("rulesRoot"))
        if raw_rules_root:
            return Path(raw_rules_root).expanduser().resolve(), "workspace-config.rulesRoot", selected_key
        raw_agent_root = clean_text(selected.get("agentRoot"))
        if raw_agent_root and selected_key:
            return (Path(raw_agent_root).expanduser().resolve() / "project-rules" / selected_key).resolve(), (
                "workspace-config.agentRoot"
            ), selected_key

    agent_env = env_value(workspace_env_key(selected_key, "AGENT_ROOT"), "PROJECT_AGENT_ROOT")
    if agent_env and selected_key:
        return (Path(agent_env).expanduser().resolve() / "project-rules" / selected_key).resolve(), (
            "agent-root-env"
        ), selected_key

    workspace_env = env_value(workspace_env_key(selected_key, "WORKSPACE_ROOT"), "PROJECT_WORKSPACE_ROOT")
    if workspace_env and selected_key:
        return (Path(workspace_env).expanduser().resolve() / ".agent" / "project-rules" / selected_key).resolve(), (
            "workspace-root-env"
        ), selected_key

    cwd_candidate = candidate_from_cwd(selected_key)
    if cwd_candidate is not None:
        return cwd_candidate, "cwd-ancestor", selected_key

    return None, "unresolved", selected_key


def path_field(entry: object) -> str:
    if isinstance(entry, str):
        return clean_text(entry)
    if isinstance(entry, dict):
        return clean_text(entry.get("path")) or clean_text(entry.get("loadPath"))
    return ""


def resolve_relative(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def as_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_text(item) for item in value if clean_text(item)]


def build_rule_report(
    *,
    rule_id: str,
    rule: dict[str, Any] | None,
    rules_root: Path,
    active_statuses: set[str],
    required: bool,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    if rule is None:
        return None, {"type": "rule", "id": rule_id, "required": str(required).lower(), "reason": "catalog entry missing"}

    status = clean_text(rule.get("reviewStatus"))
    if status not in active_statuses:
        return None, {
            "type": "rule",
            "id": rule_id,
            "required": str(required).lower(),
            "reason": f"reviewStatus is not active: {status or 'blank'}",
        }

    raw_path = path_field(rule)
    if not raw_path:
        return None, {"type": "rule", "id": rule_id, "required": str(required).lower(), "reason": "path/loadPath missing"}

    resolved = resolve_relative(rules_root, raw_path)
    exists = resolved.exists()
    issue = None
    if not exists:
        issue = {
            "type": "rule",
            "id": rule_id,
            "required": str(required).lower(),
            "reason": f"file missing: {resolved}",
        }

    report = {
        "ruleId": rule_id,
        "category": clean_text(rule.get("category")),
        "title": clean_text(rule.get("title")),
        "path": raw_path.replace("\\", "/"),
        "resolvedPath": str(resolved),
        "reviewStatus": status,
        "required": required,
        "exists": exists,
    }
    return report, issue


def build_asset_report(
    *,
    asset_key: str,
    asset_entry: object,
    rules_root: Path,
    required: bool,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    raw_path = path_field(asset_entry)
    if not raw_path:
        return None, {
            "type": "asset",
            "id": asset_key,
            "required": str(required).lower(),
            "reason": "catalog asset missing",
        }

    resolved = resolve_relative(rules_root, raw_path)
    exists = resolved.exists()
    issue = None
    if not exists:
        issue = {
            "type": "asset",
            "id": asset_key,
            "required": str(required).lower(),
            "reason": f"file missing: {resolved}",
        }
    return {
        "assetKey": asset_key,
        "path": raw_path.replace("\\", "/"),
        "resolvedPath": str(resolved),
        "required": required,
        "exists": exists,
    }, issue


def build_pack_report(rules_root: Path | None, catalog: dict[str, Any], pack_name: str, source: str, workspace_key: str) -> dict[str, Any]:
    if rules_root is None:
        return {
            "status": "blocked",
            "workspaceKey": workspace_key,
            "packName": pack_name,
            "rulesRoot": "",
            "rulesRootSource": source,
            "catalogPath": "",
            "missing": [{"type": "rulesRoot", "id": pack_name, "required": "true", "reason": "rules root unresolved"}],
            "rules": [],
            "assets": [],
        }

    packs = catalog.get("rulePacks") if isinstance(catalog.get("rulePacks"), dict) else {}
    pack = packs.get(pack_name) if isinstance(packs.get(pack_name), dict) else None
    if pack is None:
        return {
            "status": "blocked",
            "workspaceKey": workspace_key,
            "packName": pack_name,
            "rulesRoot": str(rules_root),
            "rulesRootSource": source,
            "catalogPath": str(rules_root / "catalog.json"),
            "missing": [{"type": "rulePack", "id": pack_name, "required": "true", "reason": "catalog.rulePacks entry missing"}],
            "rules": [],
            "assets": [],
        }

    active_statuses = {
        clean_text(value)
        for value in list(catalog.get("activeReviewStatuses") or DEFAULT_ACTIVE_STATUSES)
        if clean_text(value)
    } or set(DEFAULT_ACTIVE_STATUSES)

    rules = catalog.get("rules") if isinstance(catalog.get("rules"), list) else []
    rules_by_id = {clean_text(rule.get("ruleId")): rule for rule in rules if isinstance(rule, dict)}
    assets = catalog.get("assets") if isinstance(catalog.get("assets"), dict) else {}

    required_rule_ids = as_text_list(pack.get("requiredRuleIds"))
    optional_rule_ids = as_text_list(pack.get("optionalRuleIds"))
    required_assets = as_text_list(pack.get("requiredAssets"))
    optional_assets = as_text_list(pack.get("optionalAssets"))
    strict = bool(pack.get("strict", True))

    missing: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    resolved_rules: list[dict[str, Any]] = []
    resolved_assets: list[dict[str, Any]] = []

    for rule_id in required_rule_ids:
        report, issue = build_rule_report(
            rule_id=rule_id,
            rule=rules_by_id.get(rule_id),
            rules_root=rules_root,
            active_statuses=active_statuses,
            required=True,
        )
        if report is not None:
            resolved_rules.append(report)
        if issue is not None:
            missing.append(issue)

    for rule_id in optional_rule_ids:
        report, issue = build_rule_report(
            rule_id=rule_id,
            rule=rules_by_id.get(rule_id),
            rules_root=rules_root,
            active_statuses=active_statuses,
            required=False,
        )
        if report is not None:
            resolved_rules.append(report)
        if issue is not None:
            warnings.append(issue)

    for asset_key in required_assets:
        report, issue = build_asset_report(asset_key=asset_key, asset_entry=assets.get(asset_key), rules_root=rules_root, required=True)
        if report is not None:
            resolved_assets.append(report)
        if issue is not None:
            missing.append(issue)

    for asset_key in optional_assets:
        report, issue = build_asset_report(asset_key=asset_key, asset_entry=assets.get(asset_key), rules_root=rules_root, required=False)
        if report is not None:
            resolved_assets.append(report)
        if issue is not None:
            warnings.append(issue)

    blocked = bool(missing and strict)
    return {
        "status": "blocked" if blocked else "ready",
        "strict": strict,
        "workspaceKey": workspace_key,
        "packName": pack_name,
        "purpose": clean_text(pack.get("purpose")),
        "rulesRoot": str(rules_root),
        "rulesRootSource": source,
        "catalogPath": str(rules_root / "catalog.json"),
        "requiredRuleIds": required_rule_ids,
        "optionalRuleIds": optional_rule_ids,
        "requiredAssets": required_assets,
        "optionalAssets": optional_assets,
        "rules": resolved_rules,
        "assets": resolved_assets,
        "missing": missing,
        "warnings": warnings,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Resolve a project rule pack from project-rules catalog.")
    parser.add_argument("--pack", required=False, help="catalog.rulePacks key, for example apiSpecWriter")
    parser.add_argument("--rules-root", help="Project rules root containing catalog.json")
    parser.add_argument("--workspace-key", help="Workspace key used with references/local-workspaces.json")
    parser.add_argument("--list-packs", action="store_true", help="List catalog rule pack names and return success")
    parser.add_argument("--allow-missing", action="store_true", help="Print missing items but return success")
    args = parser.parse_args()

    rules_root, source, workspace_key = resolve_rules_root(
        args.rules_root,
        workspace_key=args.workspace_key,
        start_path=Path(__file__).resolve(),
    )
    catalog = read_json(rules_root / "catalog.json") if rules_root is not None else {}

    if args.list_packs:
        packs = catalog.get("rulePacks") if isinstance(catalog.get("rulePacks"), dict) else {}
        print(json.dumps({"rulesRoot": str(rules_root or ""), "packs": sorted(packs.keys())}, ensure_ascii=False, indent=2))
        return 0

    if not clean_text(args.pack):
        parser.error("--pack is required unless --list-packs is used")

    report = build_pack_report(rules_root, catalog, clean_text(args.pack), source, workspace_key)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report.get("status") == "blocked" and not args.allow_missing:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
