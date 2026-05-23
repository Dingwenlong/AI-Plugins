#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


def clean_text(value: object) -> str:
    return "" if value is None else str(value).strip()


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_function_contexts(agent_dir: Path) -> list[str]:
    context_root = agent_dir / "context"
    if not context_root.exists():
        return []
    return sorted(path.name for path in context_root.iterdir() if path.is_dir())


def list_function_inputs(agent_dir: Path) -> list[str]:
    function_root = agent_dir / "functions"
    if not function_root.exists():
        return []
    return sorted(path.name for path in function_root.iterdir() if path.is_dir())


def scan_legacy_agents(workspace_root: Path, agent_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for child in sorted(workspace_root.iterdir(), key=lambda item: item.name.casefold()):
        if not child.is_dir():
            continue
        legacy_agent = (child / ".agent").resolve()
        if not legacy_agent.exists() or legacy_agent == agent_root.resolve():
            continue
        context_functions = list_function_contexts(legacy_agent)
        input_functions = list_function_inputs(legacy_agent)
        conflicts = [
            function_code
            for function_code in context_functions
            if (agent_root / "context" / function_code).exists()
        ]
        results.append(
            {
                "workspace": child.name,
                "sourceAgent": legacy_agent.as_posix(),
                "copyTarget": (agent_root / "legacy-imports" / child.name / ".agent").as_posix(),
                "contextFunctions": context_functions,
                "inputFunctions": input_functions,
                "conflicts": conflicts,
                "missing": {
                    "context": not (legacy_agent / "context").exists(),
                    "reference": not ((legacy_agent / "Reference").exists() or (legacy_agent / "reference").exists()),
                },
            }
        )
    return results


def copy_legacy_agents(entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        source = Path(entry["sourceAgent"])
        target = Path(entry["copyTarget"])
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run/apply migration from branch-local .agent folders into a centralized .agent legacy area.")
    parser.add_argument("--workspace-root", default=r"D:\Repo\Project")
    parser.add_argument("--agent-root", default=None)
    parser.add_argument("--apply", action="store_true", help="Copy legacy .agent trees into <agent-root>/legacy-imports; never delete sources.")
    parser.add_argument("--output", default=None, help="Optional JSON report path. Defaults to <agent-root>/status/migration-plan.json when --apply is used.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    if not workspace_root.exists() or not workspace_root.is_dir():
        raise SystemExit(f"workspace-root not found: {workspace_root.as_posix()}")
    agent_root = Path(clean_text(args.agent_root) or workspace_root / ".agent").expanduser().resolve()
    entries = scan_legacy_agents(workspace_root, agent_root)
    payload = {
        "schemaVersion": "1.0.0",
        "workspaceRoot": workspace_root.as_posix(),
        "agentRoot": agent_root.as_posix(),
        "mode": "apply" if args.apply else "dry-run",
        "entries": entries,
    }
    if args.apply:
        copy_legacy_agents(entries)
        output_path = Path(args.output).expanduser().resolve() if args.output else agent_root / "status" / "migration-plan.json"
        dump_json(output_path, payload)
    elif args.output:
        dump_json(Path(args.output).expanduser().resolve(), payload)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
