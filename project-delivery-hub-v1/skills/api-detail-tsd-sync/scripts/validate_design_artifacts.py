#!/usr/bin/env python3
"""Validate design-stage orchestration artifacts against their JSON schemas.

READ-ONLY. Checks `.agent/functions/<functionCode>/orchestration/*.json` against the
schemas in `skills/api-detail-tsd-sync/schemas/`. Never writes any file.

Resolution of the central `.agent` root mirrors the other delivery-hub scripts:
`--agent-root` > `PROJECT_AGENT_ROOT` env > selected workspace `agentRoot` in
`references/local-workspaces.json` (`--workspace-key` / `defaultWorkspace`).

Exit codes: 0 = all present artifacts valid (missing ones are skipped),
1 = at least one artifact failed validation, 2 = usage / resolution error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - dependency preflight
    raise SystemExit(
        "validate_design_artifacts 缺少 Python 依赖：jsonschema。"
        "请在当前解释器安装后重试，例如：python -m pip install jsonschema"
    ) from exc

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SCHEMA_DIR = SKILL_DIR / "schemas"
PLUGIN_ROOT = SKILL_DIR.parent.parent
CONFIG_PATH = PLUGIN_ROOT / "references" / "local-workspaces.json"

# artifact filename -> schema filename (design-stage orchestration plane)
ARTIFACT_SCHEMAS = {
    "design-change-plan.json": "design-change-plan.schema.json",
    "office-edit-plan.json": "office-edit-plan.schema.json",
    "file-claims.json": "file-claims.schema.json",
    "worker-results.json": "worker-results.schema.json",
    "final-design-fix-report.json": "final-design-fix-report.schema.json",
    "office-edit-results.json": "office-edit-results.schema.json",
}


def clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def load_workspace_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_agent_root(agent_root_arg: str | None, workspace_key: str | None) -> Path | None:
    explicit = clean_text(agent_root_arg) or clean_text(os.environ.get("PROJECT_AGENT_ROOT"))
    if explicit:
        return Path(explicit).expanduser().resolve()
    config = load_workspace_config()
    workspaces = config.get("workspaces") if isinstance(config.get("workspaces"), dict) else {}
    selected_key = (
        clean_text(workspace_key)
        or clean_text(os.environ.get("PROJECT_WORKSPACE_KEY"))
        or clean_text(config.get("defaultWorkspace"))
    )
    selected = workspaces.get(selected_key) if selected_key else None
    if isinstance(selected, dict):
        raw = clean_text(selected.get("agentRoot"))
        if raw:
            return Path(raw).expanduser().resolve()
    return None


def load_schema(schema_file: str) -> dict:
    return json.loads((SCHEMA_DIR / schema_file).read_text(encoding="utf-8"))


def validate_dir(orchestration_dir: Path) -> tuple[int, int, int, list[str]]:
    passed = failed = skipped = 0
    lines: list[str] = []
    for artifact, schema_file in ARTIFACT_SCHEMAS.items():
        target = orchestration_dir / artifact
        if not target.exists():
            skipped += 1
            lines.append(f"  - {artifact}: (缺，跳过)")
            continue
        try:
            data = json.loads(target.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError) as exc:
            failed += 1
            lines.append(f"  x {artifact}: 无法解析 JSON：{exc}")
            continue
        schema = load_schema(schema_file)
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        if errors:
            failed += 1
            lines.append(f"  x {artifact}: {len(errors)} 处不符 schema")
            for err in errors[:5]:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                lines.append(f"      @ {loc}: {err.message}")
        else:
            passed += 1
            lines.append(f"  ok {artifact}")
    return passed, failed, skipped, lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate design-stage orchestration artifacts against their JSON schemas (read-only)."
    )
    parser.add_argument(
        "--function-code", action="append", default=[],
        help="Function code, e.g. D.006 (repeatable)",
    )
    parser.add_argument("--agent-root", help="Central .agent root; overrides workspace config")
    parser.add_argument("--workspace-key", help="Workspace key from references/local-workspaces.json")
    parser.add_argument(
        "--orchestration-dir",
        help="Validate this orchestration dir directly (skips function-code / agent-root resolution)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dirs: list[Path] = []
    if args.orchestration_dir:
        dirs.append(Path(args.orchestration_dir).expanduser().resolve())
    else:
        if not args.function_code:
            print("ERROR: 需要 --function-code 或 --orchestration-dir", file=sys.stderr)
            return 2
        agent_root = resolve_agent_root(args.agent_root, args.workspace_key)
        if agent_root is None:
            print(
                "ERROR: 无法解析 agent-root（传 --agent-root，或在 references/local-workspaces.json "
                "配置 agentRoot 并指定 --workspace-key）",
                file=sys.stderr,
            )
            return 2
        for fc in args.function_code:
            dirs.append(agent_root / "functions" / fc / "orchestration")

    total_pass = total_fail = total_skip = 0
    for d in dirs:
        print(f"# {d}")
        if not d.exists():
            print("  (orchestration 目录不存在，跳过)")
            continue
        p, f, s, lines = validate_dir(d)
        print("\n".join(lines))
        total_pass += p
        total_fail += f
        total_skip += s

    print(f"\n=== 通过 {total_pass} / 失败 {total_fail} / 跳过 {total_skip} ===")
    return 1 if total_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
