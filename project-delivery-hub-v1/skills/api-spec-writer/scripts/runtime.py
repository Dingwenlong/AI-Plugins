from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chain_workspace import resolve_chain_workspace, write_workspace_snapshot


STATE_SCHEMA_VERSION = "4.1.0"
API_SPEC_SCHEMA_VERSION = "4.2.0"
BATCH_SCHEMA_VERSION = "1.0.0"
SKILL_NAME = "api-spec-writer"
ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT_DIR / "schemas"
VERSION_TOKEN_PATTERN = re.compile(r"(?i)(?:^|[_-])(?P<version>v\d+(?:\.\d+)+)(?:[_-]|\.docx$)")


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
        return self.root / "spec-progress.md"

    def api_dir(self, api_id: str) -> Path:
        return self.root / "apis" / api_id

    def manifest_path(self, api_id: str) -> Path:
        return self.api_dir(api_id) / "manifest.json"

    def api_spec_path(self, api_id: str, *, function_code: str | None, tsd_path: Path | str | None) -> Path:
        return self.api_dir(api_id) / build_api_spec_filename(function_code, tsd_path)


@dataclass(frozen=True)
class ExecutionContext:
    project_root: Path
    agent_dir: Path
    context_root: Path
    batch_file: Path
    state_root: Path
    docx_path: Path
    execution_id: str
    function_code: str | None
    new_author: str | None

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


def normalize_author_name(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:1].upper() + text[1:]


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMA_DIR / name)


def append_progress(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- [{now_iso()}] {message}\n")


def sha256_file(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def sanitize_slug(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered)
    return lowered.strip("-") or "unnamed"


def extract_function_code(name: str) -> str | None:
    match = re.search(r"TSD\.([A-Za-z](?:\.\d+)+)", name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def extract_version_token_from_tsd_path(tsd_path: Path | str | None) -> str | None:
    if not tsd_path:
        return None
    match = VERSION_TOKEN_PATTERN.search(Path(tsd_path).name)
    if not match:
        return None
    version = match.group("version")
    return "v" + version[1:] if version and version[0].lower() == "v" else version


def build_api_spec_filename(function_code: str | None, tsd_path: Path | str | None) -> str:
    resolved_function_code = function_code or extract_function_code(Path(tsd_path).name if tsd_path else "")
    if not resolved_function_code:
        raise ValueError("functionCode is required to build the API_Spec file name.")
    return f"{resolved_function_code}_API_Spec.json"


def build_api_id(function_code: str | None, api_category: str, api_name: str) -> str:
    parts = []
    if function_code:
        parts.append(function_code.upper())
    parts.append(sanitize_slug(api_category))
    parts.append(sanitize_slug(api_name))
    return ".".join(parts)


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
        start_path=ROOT_DIR,
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
    items = payload.get("items")
    if not isinstance(items, list):
        raise SystemExit(f"execution-batch.json.items must be an array: {path.as_posix()}")
    normalized_items: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SystemExit(f"execution-batch.json.items[{index}] must be an object: {path.as_posix()}")
        function_code = str(item.get("functionCode") or "").strip()
        docx_ref = str(item.get("docxRef") or "").strip()
        if not function_code or not docx_ref:
            raise SystemExit(f"execution-batch.json.items[{index}] is missing functionCode/docxRef: {path.as_posix()}")
        order = item.get("order")
        normalized_items.append(
            {
                "functionCode": function_code,
                "docxRef": docx_ref,
                "order": int(order) if isinstance(order, int) else len(normalized_items) + 1,
            }
        )
    return {
        "schemaVersion": str(payload.get("schemaVersion") or BATCH_SCHEMA_VERSION),
        "activeFunctionCode": payload.get("activeFunctionCode"),
        "items": normalized_items,
        "updatedAt": payload.get("updatedAt"),
        "updatedBy": payload.get("updatedBy"),
    }


def save_batch_file(path: Path, payload: dict[str, Any], *, updated_by: str | None) -> None:
    items = sorted(
        [
            {
                "functionCode": str(item["functionCode"]).strip(),
                "docxRef": str(item["docxRef"]).strip(),
                "order": int(item["order"]),
            }
            for item in list(payload.get("items") or [])
        ],
        key=lambda item: (item["order"], item["functionCode"]),
    )
    dump_json(
        path,
        {
            "schemaVersion": BATCH_SCHEMA_VERSION,
            "activeFunctionCode": payload.get("activeFunctionCode"),
            "items": items,
            "updatedAt": now_iso(),
            "updatedBy": updated_by,
        },
    )


def upsert_batch_item(
    payload: dict[str, Any],
    *,
    function_code: str,
    docx_ref: str,
    make_active: bool,
) -> dict[str, Any]:
    items = [dict(item) for item in list(payload.get("items") or [])]
    target: dict[str, Any] | None = None
    for item in items:
        if str(item.get("functionCode")).strip() == function_code:
            target = item
            break
    if target is None:
        target = {
            "functionCode": function_code,
            "docxRef": docx_ref,
            "order": len(items) + 1,
        }
        items.append(target)
    else:
        target["docxRef"] = docx_ref
        if not isinstance(target.get("order"), int):
            target["order"] = len(items)
    payload = dict(payload)
    payload["items"] = items
    if make_active:
        payload["activeFunctionCode"] = function_code
    return payload


def resolve_docx_path(project_root: Path, agent_dir: Path, docx_ref: str) -> Path:
    tsd_dir = agent_dir / "TSD"
    if docx_ref:
        direct_path = Path(docx_ref).expanduser()
        if not direct_path.is_absolute():
            candidates = [Path.cwd().resolve(), project_root, agent_dir, tsd_dir]
            for agent_path in candidates:
                candidate = (agent_path / direct_path).resolve()
                if candidate.exists():
                    direct_path = candidate
                    break
            else:
                direct_path = (Path.cwd().resolve() / direct_path).resolve()
        if direct_path.exists():
            if direct_path.suffix.lower() != ".docx":
                raise SystemExit(f"指定文件不是 .docx：{direct_path.as_posix()}")
            return direct_path.resolve()

    docx_files = sorted(path for path in tsd_dir.glob("*.docx") if path.is_file())
    if not docx_files:
        raise SystemExit("请导入TSD文件")

    if docx_ref:
        needle = docx_ref.casefold()
        exact_matches = [path for path in docx_files if path.name.casefold() == needle]
        if len(exact_matches) == 1:
            return exact_matches[0]
        partial_matches = [path for path in docx_files if needle in path.name.casefold() or needle in path.stem.casefold()]
        if len(partial_matches) == 1:
            return partial_matches[0]
        if len(partial_matches) > 1:
            rendered = "\n".join(f"- {path.name}" for path in partial_matches)
            raise SystemExit(f"找到多个匹配文档，请提供更完整的文件名：\n{rendered}")
        raise SystemExit("请导入TSD文件")

    if len(docx_files) == 1:
        return docx_files[0]

    rendered = "\n".join(f"- {path.name}" for path in docx_files)
    raise SystemExit(f"请提供 TSD 文档文件名；当前找到多个候选文件：\n{rendered}")
