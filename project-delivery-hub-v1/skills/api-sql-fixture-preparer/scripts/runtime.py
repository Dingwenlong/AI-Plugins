from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chain_workspace import resolve_chain_workspace, write_workspace_snapshot


STATE_SCHEMA_VERSION = "4.1.0"
BATCH_SCHEMA_VERSION = "1.0.0"
SKILL_NAME = "api-sql-fixture-preparer"
UPSTREAM_API_SPEC_SCHEMA_VERSION = "4.2.0"
COMPATIBLE_UPSTREAM_API_SPEC_SCHEMA_VERSIONS = {"4.1.0", "4.2.0"}


@dataclass(frozen=True)
class ExecutionPaths:
    root: Path

    @property
    def execution_state_path(self) -> Path:
        return self.root / "execution-state.json"

    @property
    def checklist_path(self) -> Path:
        return self.root / "api-checklist.json"

    @property
    def progress_path(self) -> Path:
        return self.root / "fixture-progress.md"

    def api_dir(self, api_id: str) -> Path:
        return self.root / "apis" / api_id

    def manifest_path(self, api_id: str) -> Path:
        return self.api_dir(api_id) / "manifest.json"

    def db_fixture_report_path(self, api_id: str) -> Path:
        return self.api_dir(api_id) / "db-fixture-report.json"

    def table_checks_path(self, api_id: str) -> Path:
        return self.api_dir(api_id) / "table-checks.json"

    def seed_plan_path(self, api_id: str) -> Path:
        return self.api_dir(api_id) / "seed-plan.sql"

    def seed_executed_path(self, api_id: str) -> Path:
        return self.api_dir(api_id) / "seed-executed.sql"

    def seed_manifest_path(self, api_id: str) -> Path:
        return self.api_dir(api_id) / "seed-manifest.json"


@dataclass(frozen=True)
class ExecutionContext:
    project_root: Path
    solution_path: Path | None
    agent_dir: Path
    context_root: Path
    batch_file: Path
    state_root: Path
    execution_id: str

    @property
    def paths(self) -> ExecutionPaths:
        return ExecutionPaths(self.state_root)


def configure_stdio() -> None:
    for stream in (getattr(__import__("sys"), "stdout"), getattr(__import__("sys"), "stderr")):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_persisted_path(path: Path | str | None, *, project_root: Path | str | None = None) -> str | None:
    if path is None:
        return None
    normalized = Path(path)
    if not normalized.is_absolute():
        return normalized.as_posix()
    resolved = normalized.resolve()
    if project_root is None:
        return resolved.name
    project_root_path = Path(project_root).resolve()
    try:
        relative = os.path.relpath(resolved, project_root_path)
        return Path(relative).as_posix()
    except ValueError:
        return resolved.as_posix()


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_schema(filename: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parent.parent / "schemas" / filename
    return json.loads(path.read_text(encoding="utf-8"))


def append_progress(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- [{now_iso()}] {message}\n")


def remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def sha256_file(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def resolve_project_root(project_root_arg: str) -> Path:
    project_root = Path(project_root_arg).expanduser()
    if not project_root.is_absolute():
        project_root = (Path.cwd() / project_root).resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise SystemExit(f"project-root does not exist: {project_root.as_posix()}")
    return project_root


def resolve_agent_dir(
    project_root: Path,
    agent_dir_arg: str,
    agent_root_arg: str | None = None,
    workspace_root_arg: str | None = None,
    workspace_key_arg: str | None = None,
    rules_root_arg: str | None = None,
) -> Path:
    workspace = resolve_chain_workspace(
        project_root=project_root,
        agent_dir_arg=agent_dir_arg,
        agent_root_arg=agent_root_arg,
        workspace_root_arg=workspace_root_arg,
        workspace_key_arg=workspace_key_arg,
        rules_root_arg=rules_root_arg,
        start_path=Path(__file__).resolve().parents[1],
    )
    write_workspace_snapshot(workspace)
    return workspace.agent_root


def resolve_context_root(project_root: Path, agent_dir: Path, context_root_arg: str | None) -> Path:
    context_root = Path(context_root_arg).expanduser() if context_root_arg else (agent_dir / "context")
    if not context_root.is_absolute():
        context_root = (project_root / context_root).resolve()
    return context_root.resolve()


def default_batch_file(context_root: Path) -> Path:
    return (context_root / "execution-batch.json").resolve()


def load_batch_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schemaVersion": BATCH_SCHEMA_VERSION,
            "activeFunctionCode": None,
            "items": [],
            "updatedAt": None,
            "updatedBy": None,
        }
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"execution-batch.json must be a JSON object: {path.as_posix()}")
    return payload


def save_batch_file(path: Path, payload: dict[str, Any], *, updated_by: str | None) -> None:
    dump_json(
        path,
        {
            "schemaVersion": BATCH_SCHEMA_VERSION,
            "activeFunctionCode": payload.get("activeFunctionCode"),
            "items": list(payload.get("items") or []),
            "updatedAt": now_iso(),
            "updatedBy": updated_by,
        },
    )


def resolve_solution_path(project_root: Path, solution_path_arg: str | None) -> Path | None:
    if not solution_path_arg:
        return None
    solution_path = Path(solution_path_arg).expanduser()
    if not solution_path.is_absolute():
        solution_path = (project_root / solution_path).resolve()
    if not solution_path.exists() or not solution_path.is_file() or solution_path.suffix.lower() != ".sln":
        raise SystemExit(f"solution-path does not exist or is not a .sln: {solution_path.as_posix()}")
    return solution_path
