#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from chain_workspace import resolve_chain_workspace, update_chain_status, write_workspace_snapshot


FUNCTION_CODE_RE = re.compile(r"(?<![A-Za-z0-9])(?P<code>[A-Za-z](?:\.\d+)+)(?![A-Za-z0-9])")
FILE_SUFFIX_RE = re.compile(r"\.(?:docx|xlsx|xls|pdf|pptx|vsdx|md|json|sql)\b", re.IGNORECASE)
ABSOLUTE_FILE_RE = re.compile(r"(?P<path>[A-Za-z]:[^\r\n<>|\"*?]+?\.(?:docx|xlsx|xls|pdf|pptx|vsdx|md|json|sql))", re.IGNORECASE)
QUOTED_FILE_RE = re.compile(r"[`\"'《「“（(](?P<path>[^`\"'》」”）)]+?\.(?:docx|xlsx|xls|pdf|pptx|vsdx|md|json|sql))[`\"'》」”）)]", re.IGNORECASE)


def clean_text(value: object) -> str:
    return "" if value is None else str(value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_rel(path: Path, agent_root: Path) -> str:
    try:
        return path.resolve().relative_to(agent_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def infer_function_code(*values: object) -> str | None:
    for value in values:
        match = FUNCTION_CODE_RE.search(clean_text(value))
        if match:
            return match.group("code").upper()
    return None


def summary_sort_key(path: Path) -> tuple[float, str]:
    return (path.stat().st_mtime, path.name.casefold())


def resolve_summary_path(agent_root: Path, design_root: Path | None, function_code: str | None, explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if not candidate.exists() or not candidate.is_file():
            raise SystemExit(f"summary file not found: {candidate.as_posix()}")
        return candidate.resolve()

    if not function_code:
        raise SystemExit("please provide --function-code when --summary is omitted")

    candidates: list[Path] = []
    analysis_root = agent_root / "functions" / function_code / "analysis"
    if analysis_root.exists():
        candidates.extend(path for path in analysis_root.glob("*.md") if path.is_file())

    if design_root is not None and design_root.exists():
        compact_code = function_code.replace(".", "")
        output_root = design_root / "output"
        if output_root.exists():
            candidates.extend(path for path in output_root.rglob("*.md") if path.is_file() and compact_code.casefold() in path.as_posix().casefold())

    if not candidates:
        raise SystemExit(f"no design summary found for {function_code}; pass --summary explicitly")
    return sorted(candidates, key=summary_sort_key, reverse=True)[0].resolve()


def resolve_candidate_path(raw_path: str, *, summary_dir: Path, design_root: Path | None, workspace_root: Path | None) -> Path | None:
    text = clean_text(raw_path).strip("`'\"，,；;。)）]】")
    if not text:
        return None
    path = Path(text).expanduser()
    candidates = [path] if path.is_absolute() else []
    if not path.is_absolute():
        candidates.extend(
            base / path
            for base in [summary_dir, design_root, workspace_root, Path.cwd().resolve()]
            if base is not None
        )
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def iter_markdown_file_refs(markdown_text: str) -> list[str]:
    refs: list[str] = []
    for line in markdown_text.splitlines():
        if not FILE_SUFFIX_RE.search(line):
            continue
        refs.extend(match.group("path") for match in ABSOLUTE_FILE_RE.finditer(line))
        refs.extend(match.group("path") for match in QUOTED_FILE_RE.finditer(line))
    ordered: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        key = ref.casefold()
        if key not in seen:
            ordered.append(ref)
            seen.add(key)
    return ordered


def classify_input(path: Path) -> str:
    name = path.name.casefold()
    if path.suffix.lower() == ".docx" and "tsd" in name:
        return "tsd"
    if "newda_api_detail" in name or "api_detail" in name:
        return "api-spec"
    if "commonfunc" in name or "commonutil" in name or "method_detail" in name or "common" in name:
        return "common"
    if "response" in name or "returncode" in name or "response_code" in name:
        return "response-codes"
    return "reference"


def unique_target_path(root: Path, source: Path) -> Path:
    target = root / source.name
    if not target.exists():
        return target
    digest = sha256_file(source).split(":", 1)[1][:10]
    return root / f"{source.stem}_{digest}{source.suffix}"


def assess_readiness(markdown_text: str) -> tuple[bool, str, str]:
    text = markdown_text.replace(" ", "").casefold()
    negative_markers = ("不可进入开发", "不可進入開發", "需补齐后再开发", "需補齊後再開發", "blocked")
    positive_markers = ("可进入开发", "可進入開發", "开发就绪", "開發就緒", "近冻版", "近凍版", "冻版", "凍版")
    if any(marker.casefold() in text for marker in negative_markers):
        return False, "blocked", "功能设计梳理稿标记尚不可进入开发"
    if any(marker.casefold() in text for marker in positive_markers):
        return True, "ready", ""
    return False, "blocked", "功能设计梳理稿未明确达到可进入开发或近冻版"


def materialize_handoff(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).expanduser()
    if not project_root.is_absolute():
        project_root = (Path.cwd() / project_root).resolve()
    workspace = resolve_chain_workspace(
        project_root=project_root,
        agent_dir_arg=args.agent_dir,
        agent_root_arg=args.agent_root,
        rules_root_arg=args.rules_root,
        workspace_root_arg=args.workspace_root,
        workspace_key_arg=args.workspace_key,
        start_path=Path(__file__).resolve().parents[2],
    )
    design_root = Path(args.design_root).expanduser().resolve() if args.design_root else None
    function_code = clean_text(args.function_code).upper() or None
    summary_path = resolve_summary_path(workspace.agent_root, design_root, function_code, args.summary)
    markdown_text = summary_path.read_text(encoding="utf-8-sig")
    function_code = function_code or infer_function_code(summary_path.name, markdown_text)
    if not function_code:
        raise SystemExit("cannot infer function code from summary; pass --function-code")

    function_root = workspace.agent_root / "functions" / function_code
    analysis_root = function_root / "analysis"
    inputs_root = function_root / "inputs"
    handoff_path = function_root / "handoff" / "development-handoff.json"
    analysis_target = analysis_root / summary_path.name

    ready, readiness_status, block_reason = assess_readiness(markdown_text)
    source_records: list[dict[str, Any]] = []
    resolved_files: list[Path] = []
    seen_files: set[Path] = set()
    for raw_ref in iter_markdown_file_refs(markdown_text):
        resolved = resolve_candidate_path(
            raw_ref,
            summary_dir=summary_path.parent,
            design_root=design_root,
            workspace_root=workspace.workspace_root,
        )
        if resolved is None or resolved == summary_path:
            continue
        if resolved in seen_files:
            continue
        resolved_files.append(resolved)
        seen_files.add(resolved)

    copy_plan: list[tuple[Path, Path, str]] = []
    for source in resolved_files:
        kind = classify_input(source)
        target_dir = inputs_root / kind
        target = unique_target_path(target_dir, source)
        copy_plan.append((source, target, kind))

    if not args.dry_run:
        write_workspace_snapshot(workspace)
        analysis_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(summary_path, analysis_target)
        for source, target, kind in copy_plan:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            source_records.append(
                {
                    "kind": kind,
                    "sourcePath": source.as_posix(),
                    "copiedRelativePath": normalize_rel(target, workspace.agent_root),
                    "hash": sha256_file(target),
                }
            )
    else:
        for source, target, kind in copy_plan:
            source_records.append(
                {
                    "kind": kind,
                    "sourcePath": source.as_posix(),
                    "copiedRelativePath": normalize_rel(target, workspace.agent_root),
                    "hash": sha256_file(source),
                }
            )

    payload = {
        "schemaVersion": "1.0.0",
        "functionCode": function_code,
        "status": readiness_status,
        "readiness": {
            "developmentReady": ready,
            "status": readiness_status,
            "blockReason": block_reason or None,
        },
        "analysis": {
            "sourcePath": summary_path.as_posix(),
            "copiedRelativePath": normalize_rel(analysis_target, workspace.agent_root),
            "hash": sha256_file(summary_path),
        },
        "inputsRoot": normalize_rel(inputs_root, workspace.agent_root),
        "sourceFiles": sorted(source_records, key=lambda item: (item["kind"], item["copiedRelativePath"].casefold())),
    }

    if not args.dry_run:
        dump_json(handoff_path, payload)
        update_chain_status(
            agent_root=workspace.agent_root,
            function_code=function_code,
            stage="design",
            status=readiness_status,
            phase="handoff_ready" if ready else "blocked",
            message=block_reason or "development handoff generated",
            project_root=project_root,
            workspace_key=workspace.workspace_key,
            artifacts={
                "analysis": normalize_rel(analysis_target, workspace.agent_root),
                "developmentHandoff": normalize_rel(handoff_path, workspace.agent_root),
                "inputsRoot": normalize_rel(inputs_root, workspace.agent_root),
            },
            blockers=[block_reason] if block_reason else [],
        )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize project design summary handoff into centralized .agent/functions/<functionCode>.")
    parser.add_argument("--project-root", default=str(Path.cwd()), help="Current code branch/project root; used only for .agent resolution.")
    parser.add_argument("--agent-dir", default=".agent")
    parser.add_argument("--agent-root")
    parser.add_argument("--workspace-root")
    parser.add_argument("--workspace-key")
    parser.add_argument("--rules-root")
    parser.add_argument("--design-root")
    parser.add_argument("--function-code")
    parser.add_argument("--summary", help="Explicit 功能设计梳理 markdown path.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def main() -> int:
    configure_stdio()
    payload = materialize_handoff(parse_args())
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
