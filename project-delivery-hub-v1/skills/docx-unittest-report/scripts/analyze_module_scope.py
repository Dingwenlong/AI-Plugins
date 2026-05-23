from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from chain_workspace import resolve_chain_workspace, write_workspace_snapshot


OPERATION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("query", ("get", "query", "search", "list", "detail", "fetch")),
    ("create", ("create", "add", "insert", "register")),
    ("update", ("update", "edit", "set", "change", "modify")),
    ("delete", ("delete", "remove")),
    ("download", ("download", "export")),
    ("notify", ("notify", "message", "send", "push", "mail", "sms")),
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_context_root(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"context root not found: {path.as_posix()}")
    if not (path / "api-checklist.json").exists():
        raise SystemExit(f"api-checklist.json not found under context root: {path.as_posix()}")
    return path


def infer_repo_root(context_root: Path) -> Path:
    state_path = context_root / "execution-state.json"
    if state_path.exists():
        state = load_json(state_path)
        code_project_root = normalize_text(state.get("codeProjectRoot"))
        if code_project_root and code_project_root != ".":
            project_root = Path(code_project_root).expanduser()
            if project_root.is_absolute() and project_root.exists():
                return project_root.resolve()
    try:
        return context_root.parents[2]
    except IndexError as exc:
        raise SystemExit(f"unable to infer repo root from context root: {context_root.as_posix()}") from exc


def resolve_central_context_root(args: argparse.Namespace) -> Path:
    if args.context_root:
        return resolve_context_root(args.context_root)
    function_code = normalize_text(args.function_code)
    if not function_code:
        raise SystemExit("please provide context_root or --function-code")
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
    write_workspace_snapshot(workspace)
    return resolve_context_root(str(workspace.context_root / function_code))


def resolve_artifact_path(repo_root: Path, raw_path: str | None) -> str:
    if not normalize_text(raw_path or ""):
        return ""
    return (repo_root / str(raw_path)).resolve().as_posix()


def infer_operation_type(api_name: str) -> str:
    token = normalize_text(api_name).lower()
    for operation_type, keywords in OPERATION_RULES:
        if any(token.startswith(keyword) or keyword in token for keyword in keywords):
            return operation_type
    return "unknown"


def infer_business_traits(spec: dict[str, Any]) -> dict[str, bool]:
    request = spec.get("request") or []
    business_logic = spec.get("businessLogic") or {}
    sql_specs = business_logic.get("sqlSpecs") or []
    runtime_dependencies = business_logic.get("runtimeDependencies") or []
    backend_apis = spec.get("backendApis") or {}
    error_code_rules = business_logic.get("errorCodeRules") or []

    sql_text = "\n".join(normalize_text(item.get("queryText", "")) for item in sql_specs).upper()
    runtime_text = "\n".join(normalize_text(item.get("description", "")) for item in runtime_dependencies).upper()
    backend_text = json.dumps(backend_apis, ensure_ascii=False).upper()

    return {
        "hasRequestPayload": len(request) > 0,
        "hasValidationRules": len(error_code_rules) > 0 or any(field.get("required") for field in request),
        "usesRedis": "REDIS" in backend_text or "REDIS" in runtime_text,
        "usesSql": bool(sql_specs) or "SQL" in runtime_text,
        "hasDbRead": "SELECT" in sql_text,
        "hasDbWrite": any(keyword in sql_text for keyword in ("INSERT", "UPDATE", "DELETE")),
        "hasExternalDependency": any(dep.get("type") == "external" for dep in runtime_dependencies),
    }


def classify_code_path(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    if "/Test/UnitTesting/" in normalized:
        return "unitTest"
    if "/Test/IntegrationTesting/" in normalized:
        return "integrationTest"
    if "/Controllers/" in normalized:
        return "controller"
    if "/Business/" in normalized or "/BusinessLogicLayout/" in normalized:
        return "service"
    if "/Entity/" in normalized or "/EnterpriseApiEntity/" in normalized:
        return "entity"
    if "/Libray/Common/" in normalized:
        return "common"
    return "other"


def build_code_path_groups(paths: list[str]) -> dict[str, list[str]]:
    groups = {
        "controller": [],
        "service": [],
        "entity": [],
        "common": [],
        "unitTest": [],
        "integrationTest": [],
        "other": [],
    }
    for relative_path in paths:
        groups[classify_code_path(relative_path)].append(relative_path)
    for key in groups:
        groups[key] = sorted(dict.fromkeys(groups[key]))
    return groups


def find_candidate_test_files(repo_root: Path, api_name: str, api_category: str) -> dict[str, list[str]]:
    test_root = repo_root / "Sinopac.DawhoEnterprise" / "Test"
    if not test_root.exists():
        return {"unitTest": [], "integrationTest": []}

    api_name_token = normalize_text(api_name)
    category_token = normalize_text(api_category)
    controller_token = f"{category_token}Controller"

    discovered = {"unitTest": [], "integrationTest": []}
    for file_path in test_root.rglob("*.cs"):
        relative_path = file_path.relative_to(repo_root).as_posix()
        file_name = file_path.name.lower()
        if category_token.lower() in file_name or api_name_token.lower() in file_name:
            bucket = "integrationTest" if "/IntegrationTesting/" in relative_path else "unitTest"
            discovered[bucket].append(relative_path)
            continue

        content = ""
        for encoding in ("utf-8", "utf-8-sig", "cp950", "gb18030", "latin-1"):
            try:
                content = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if any(token and token in content for token in (api_name_token, category_token, controller_token)):
            bucket = "integrationTest" if "/IntegrationTesting/" in relative_path else "unitTest"
            discovered[bucket].append(relative_path)

    discovered["unitTest"] = sorted(dict.fromkeys(discovered["unitTest"]))
    discovered["integrationTest"] = sorted(dict.fromkeys(discovered["integrationTest"]))
    return discovered


def collect_api_entry(repo_root: Path, context_root: Path, item: dict[str, Any]) -> dict[str, Any]:
    api_id = item["apiId"]
    api_name = item["apiName"]
    api_category = item["apiCategory"]
    api_root = context_root / "apis" / api_id
    manifest_path = api_root / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}

    spec_relative = ((manifest.get("specArtifacts") or {}).get("apiSpec")) or ""
    spec_path = (repo_root / spec_relative).resolve() if spec_relative else None
    spec = load_json(spec_path) if spec_path and spec_path.exists() else {}

    modified_files = list(manifest.get("modifiedFiles") or [])
    grouped_paths = build_code_path_groups(modified_files)
    candidate_tests = find_candidate_test_files(repo_root, api_name, api_category)
    grouped_paths["unitTest"] = sorted(dict.fromkeys(grouped_paths["unitTest"] + candidate_tests["unitTest"]))
    grouped_paths["integrationTest"] = sorted(dict.fromkeys(grouped_paths["integrationTest"] + candidate_tests["integrationTest"]))

    request_fields = [field.get("fieldName", "") for field in spec.get("request") or []]
    response_fields = [field.get("fieldName", "") for field in spec.get("response") or []]
    business_logic = spec.get("businessLogic") or {}
    traits = infer_business_traits(spec)

    return {
        "apiId": api_id,
        "apiName": api_name,
        "apiCategory": api_category,
        "operationType": infer_operation_type(api_name),
        "specStatus": item.get("specStatus", ""),
        "codeStatus": item.get("codeStatus", ""),
        "codePhase": item.get("codePhase", ""),
        "source": spec.get("source") or manifest.get("specSource") or {},
        "artifacts": {
            "apiRoot": api_root.as_posix(),
            "manifestPath": manifest_path.as_posix() if manifest_path.exists() else "",
            "apiSpecPath": spec_path.as_posix() if spec_path else "",
            "changePlanPath": resolve_artifact_path(repo_root, ((manifest.get("codeArtifacts") or {}).get("changePlan"))),
            "implementationReportPath": resolve_artifact_path(repo_root, ((manifest.get("codeArtifacts") or {}).get("implementationReport"))),
        },
        "request": {
            "fieldCount": len(request_fields),
            "requiredFieldCount": sum(1 for field in (spec.get("request") or []) if field.get("required")),
            "fields": request_fields,
        },
        "response": {
            "fieldCount": len(response_fields),
            "fields": response_fields,
        },
        "businessTraits": traits,
        "businessSteps": [
            {
                "step": step.get("step"),
                "title": step.get("title", ""),
            }
            for step in (business_logic.get("steps") or [])
        ],
        "runtimeDependencies": [
            dependency.get("id", "")
            for dependency in (business_logic.get("runtimeDependencies") or [])
            if normalize_text(dependency.get("id", ""))
        ],
        "codePaths": grouped_paths,
        "validationChecks": list(manifest.get("validationChecks") or []),
    }


def summarize_module(apis: list[dict[str, Any]]) -> dict[str, Any]:
    operation_counter = Counter(api["operationType"] for api in apis)
    category_counter = Counter(api["apiCategory"] for api in apis)
    module_traits = {
        "hasHttpApi": bool(apis),
        "hasQueryApi": operation_counter.get("query", 0) > 0,
        "hasCreateApi": operation_counter.get("create", 0) > 0,
        "hasUpdateApi": operation_counter.get("update", 0) > 0,
        "hasDeleteApi": operation_counter.get("delete", 0) > 0,
        "hasDownloadApi": operation_counter.get("download", 0) > 0,
        "hasNotifyApi": operation_counter.get("notify", 0) > 0,
        "usesRedis": any(api["businessTraits"]["usesRedis"] for api in apis),
        "usesSql": any(api["businessTraits"]["usesSql"] for api in apis),
        "hasDbRead": any(api["businessTraits"]["hasDbRead"] for api in apis),
        "hasDbWrite": any(api["businessTraits"]["hasDbWrite"] for api in apis),
        "hasUnitTests": any(api["codePaths"]["unitTest"] for api in apis),
        "hasIntegrationTests": any(api["codePaths"]["integrationTest"] for api in apis),
    }
    return {
        "apiCount": len(apis),
        "categories": dict(category_counter),
        "operationTypes": dict(operation_counter),
        "moduleTraits": module_traits,
    }


def build_module_scope(context_root: Path) -> dict[str, Any]:
    repo_root = infer_repo_root(context_root)
    checklist = load_json(context_root / "api-checklist.json")
    execution_state = load_json(context_root / "execution-state.json")
    module_code = execution_state.get("functionCode") or context_root.name

    apis = [collect_api_entry(repo_root, context_root, item) for item in checklist.get("items") or []]
    discovered_paths = {
        "controllers": sorted(dict.fromkeys(path for api in apis for path in api["codePaths"]["controller"])),
        "services": sorted(dict.fromkeys(path for api in apis for path in api["codePaths"]["service"])),
        "entities": sorted(dict.fromkeys(path for api in apis for path in api["codePaths"]["entity"])),
        "common": sorted(dict.fromkeys(path for api in apis for path in api["codePaths"]["common"])),
        "unitTests": sorted(dict.fromkeys(path for api in apis for path in api["codePaths"]["unitTest"])),
        "integrationTests": sorted(dict.fromkeys(path for api in apis for path in api["codePaths"]["integrationTest"])),
    }

    return {
        "schemaVersion": "1.0.0",
        "moduleCode": module_code,
        "contextRoot": context_root.as_posix(),
        "repoRoot": repo_root.as_posix(),
        "solutionPath": resolve_artifact_path(repo_root, execution_state.get("codeSolutionPath")),
        "requirementSource": {
            "specDocxPath": resolve_artifact_path(repo_root, execution_state.get("specDocxPath")),
        },
        "summary": summarize_module(apis),
        "apis": apis,
        "discoveredPaths": discovered_paths,
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Analyze a module-level .agent/context execution surface and emit module-scope.json.",
    )
    parser.add_argument("context_root", nargs="?", help="Path to .agent/context/<moduleCode>.")
    parser.add_argument("--function-code", help="Function code used to resolve centralized .agent/context/<moduleCode>.")
    parser.add_argument("--project-root", default=str(Path.cwd()), help="Current code branch/project root; used for centralized .agent resolution.")
    parser.add_argument("--agent-dir", default=".agent")
    parser.add_argument("--agent-root")
    parser.add_argument("--workspace-root")
    parser.add_argument("--workspace-key")
    parser.add_argument("--rules-root")
    parser.add_argument("--output", help="Path to the output module-scope JSON.")
    args = parser.parse_args()

    context_root = resolve_central_context_root(args)
    payload = build_module_scope(context_root)
    output_path = Path(args.output).expanduser().resolve() if args.output else context_root / "module-scope.json"
    write_json(output_path, payload)
    print(f"Module scope written: {output_path.as_posix()}")
    print(f"APIs analyzed: {payload['summary']['apiCount']}")


if __name__ == "__main__":
    main()
