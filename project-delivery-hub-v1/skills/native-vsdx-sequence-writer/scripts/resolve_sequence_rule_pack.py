from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from project_rules import load_catalog, resolve_rules_root


DEFAULT_REQUIRED_RULE_IDS = [
    "system-design-v2.5-sequence-rules",
    "native-vsdx-deep-rules",
    "sequence-diagram-handoff-rules",
    "e001-native-reference-summary",
]

DEFAULT_REQUIRED_ASSETS = [
    "nativeVsdxTemplate",
    "nativeShapeLibrary",
    "sequencePlantUmlStyle",
]

DEFAULT_OPTIONAL_ASSETS = [
    "nativeVsdxPreview",
]


def clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def resolve_relative(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def rule_path(rule: dict[str, Any]) -> str:
    return clean_text(rule.get("path")) or clean_text(rule.get("loadPath"))


def selected_pack(catalog: dict[str, Any]) -> dict[str, Any]:
    packs = catalog.get("rulePacks") if isinstance(catalog.get("rulePacks"), dict) else {}
    pack = packs.get("sequenceDiagram") if isinstance(packs.get("sequenceDiagram"), dict) else {}
    return {
        "requiredRuleIds": [clean_text(item) for item in list(pack.get("requiredRuleIds") or []) if clean_text(item)]
        or DEFAULT_REQUIRED_RULE_IDS,
        "requiredAssets": [clean_text(item) for item in list(pack.get("requiredAssets") or []) if clean_text(item)]
        or DEFAULT_REQUIRED_ASSETS,
        "optionalAssets": [clean_text(item) for item in list(pack.get("optionalAssets") or []) if clean_text(item)]
        or DEFAULT_OPTIONAL_ASSETS,
        "strict": bool(pack.get("strict", True)),
        "source": "catalog.rulePacks.sequenceDiagram" if pack else "default-sequence-pack",
    }


def build_report(rules_root: Path | None, catalog: dict[str, Any]) -> dict[str, Any]:
    pack = selected_pack(catalog)
    rules = catalog.get("rules") if isinstance(catalog.get("rules"), list) else []
    by_id = {clean_text(rule.get("ruleId")): rule for rule in rules if isinstance(rule, dict)}
    assets = catalog.get("assets") if isinstance(catalog.get("assets"), dict) else {}
    active_statuses = {
        clean_text(value)
        for value in list(catalog.get("activeReviewStatuses") or ["approved", "active"])
        if clean_text(value)
    }
    if not active_statuses:
        active_statuses = {"approved", "active"}

    missing: list[dict[str, str]] = []
    resolved_rules: list[dict[str, Any]] = []
    resolved_assets: list[dict[str, Any]] = []

    for rule_id in pack["requiredRuleIds"]:
        rule = by_id.get(rule_id)
        if not rule:
            missing.append({"type": "rule", "id": rule_id, "reason": "catalog entry missing"})
            continue
        status = clean_text(rule.get("reviewStatus"))
        if status not in active_statuses:
            missing.append({"type": "rule", "id": rule_id, "reason": f"reviewStatus is not active: {status or 'blank'}"})
            continue
        raw_path = rule_path(rule)
        if not raw_path:
            missing.append({"type": "rule", "id": rule_id, "reason": "path/loadPath missing"})
            continue
        resolved = resolve_relative(rules_root, raw_path) if rules_root is not None else Path(raw_path)
        exists = resolved.exists()
        if not exists:
            missing.append({"type": "rule", "id": rule_id, "reason": f"file missing: {resolved}"})
        resolved_rules.append(
            {
                "ruleId": rule_id,
                "title": clean_text(rule.get("title")),
                "path": raw_path.replace("\\", "/"),
                "resolvedPath": str(resolved),
                "reviewStatus": status,
                "exists": exists,
            }
        )

    for asset_key in [*pack["requiredAssets"], *pack["optionalAssets"]]:
        required = asset_key in pack["requiredAssets"]
        raw_path = clean_text(assets.get(asset_key))
        if not raw_path:
            if required:
                missing.append({"type": "asset", "id": asset_key, "reason": "catalog asset missing"})
            continue
        resolved = resolve_relative(rules_root, raw_path) if rules_root is not None else Path(raw_path)
        exists = resolved.exists()
        if required and not exists:
            missing.append({"type": "asset", "id": asset_key, "reason": f"file missing: {resolved}"})
        resolved_assets.append(
            {
                "assetKey": asset_key,
                "path": raw_path.replace("\\", "/"),
                "resolvedPath": str(resolved),
                "required": required,
                "exists": exists,
            }
        )

    return {
        "status": "blocked" if missing and pack["strict"] else "ready",
        "strict": pack["strict"],
        "packSource": pack["source"],
        "rulesRoot": str(rules_root) if rules_root is not None else "",
        "catalogPath": str(rules_root / "catalog.json") if rules_root is not None else "",
        "requiredRuleIds": pack["requiredRuleIds"],
        "requiredAssets": pack["requiredAssets"],
        "optionalAssets": pack["optionalAssets"],
        "rules": resolved_rules,
        "assets": resolved_assets,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve the mandatory sequence-diagram rule pack from project-rules catalog.")
    parser.add_argument("--rules-root", help="Project rules root, for example D:\\Devs\\<PROJECT>\\.agent\\project-rules\\NEWDAWHO")
    parser.add_argument("--workspace-key", help="Workspace key used with references/local-workspaces.json")
    parser.add_argument("--allow-missing", action="store_true", help="Print missing items but return success.")
    args = parser.parse_args()

    rules_root = resolve_rules_root(args.rules_root, workspace_key=args.workspace_key, start_path=Path(__file__).resolve())
    catalog = load_catalog(rules_root)
    report = build_report(rules_root, catalog)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["status"] == "blocked" and not args.allow_missing:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
