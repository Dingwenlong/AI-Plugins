#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError as exc:
    if exc.name == "jsonschema":
        print(
            "Missing Python dependency: jsonschema. Install it in the Python runtime used for api-code-writer, "
            "for example `python -m pip install jsonschema`, then rerun.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    raise

from runtime import (
    SKILL_NAME,
    configure_stdio,
    dump_json,
    load_json,
    load_schema,
    normalize_persisted_path,
    resolve_agent_dir,
    resolve_context_root,
    resolve_project_root,
)


REVIEW_NOTE_SCOPES = {"global_skill", "api_behavior", "controller", "service", "entity", "test", "reporting"}
REVIEW_NOTE_FILE_ROLES = {"controller", "service", "entity", "unit_test", "integration_test", "shared"}
PROJECT_HARD_CONSTRAINTS_FILENAME = "project-hard-constraints.json"


class SkillError(RuntimeError):
    pass


class ZhArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)
        self._positionals.title = "位置参数"
        self._optionals.title = "可选参数"

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        text = super().format_help()
        return (
            text.replace("usage:", "用法：", 1)
            .replace("positional arguments:", "位置参数：")
            .replace("optional arguments:", "可选参数：")
            .replace("options:", "可选参数：")
            .replace("show this help message and exit", "显示此帮助并退出")
        )

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 错误：{message}\n")


def parse_args() -> argparse.Namespace:
    parser = ZhArgumentParser(description="把项目级 project-hard-constraints.json 展开成 API 级 review-notes.json。")
    parser.add_argument("-h", "--help", action="help", help="显示此帮助并退出")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--agent-dir", default=".agent")
    parser.add_argument("--agent-root", help="集中 .agent 根目录；优先级高于环境变量与插件本地配置。")
    parser.add_argument("--workspace-root", help="共享工作区根目录，例如 D:\\Repo\\Project。")
    parser.add_argument("--workspace-key", help="插件 local-workspaces.json 中的工作区 key，例如 PROJECT。")
    parser.add_argument("--rules-root", help="专案规则库根目录；优先级高于环境变量与 workspace 配置。")
    parser.add_argument("--context-root", default=None)
    parser.add_argument("--function-code", default=None)
    parser.add_argument("--api-id", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def normalize_token(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    return "".join(text.split()).casefold()


def format_validation_path(path_items: Iterable[object]) -> str:
    rendered = "".join(
        f"[{item}]" if isinstance(item, int) else (f".{item}" if index else str(item))
        for index, item in enumerate(path_items)
    )
    return rendered or "$"


def require_json_object(label: str, path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise SkillError(f"{label} must be a JSON object: {path.as_posix()}")
    return payload


def validate_payload_against_schema(payload: dict[str, Any], schema_name: str, label: str) -> None:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        raise SkillError(f"{label} schema 校验失败：{format_validation_path(first.absolute_path)} - {first.message}")


def project_constraints_path(agent_dir: Path) -> Path:
    return (agent_dir / "Common" / PROJECT_HARD_CONSTRAINTS_FILENAME).resolve()


def load_project_constraints(agent_dir: Path) -> tuple[dict[str, Any], Path]:
    path = project_constraints_path(agent_dir)
    if not path.exists():
        raise SkillError(f"缺少项目级约束文件：{path.as_posix()}")
    payload = require_json_object(PROJECT_HARD_CONSTRAINTS_FILENAME, path)
    validate_payload_against_schema(payload, "project-hard-constraints.schema.json", PROJECT_HARD_CONSTRAINTS_FILENAME)
    applies_to_skills = [clean_text(value) for value in list(payload.get("appliesToSkills") or []) if clean_text(value)]
    if applies_to_skills and SKILL_NAME not in applies_to_skills:
        raise SkillError(f"{PROJECT_HARD_CONSTRAINTS_FILENAME} 未声明适用于 {SKILL_NAME}。")
    return payload, path


def normalized_keyword_list(values: object) -> list[str]:
    if isinstance(values, str):
        candidates = [values]
    elif isinstance(values, list):
        candidates = [clean_text(value) for value in values]
    else:
        return []

    normalized_values: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = normalize_token(clean_text(candidate))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)
    return normalized_values


def walk_field_nodes(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    stack = list(reversed([field for field in fields if isinstance(field, dict)]))
    while stack:
        node = stack.pop()
        nodes.append(node)
        children = [child for child in list(node.get("children") or []) if isinstance(child, dict)]
        stack.extend(reversed(children))
    return nodes


def build_reference_text(
    *,
    function_code: str,
    api_category: str,
    api_name: str,
    api_spec: dict[str, Any] | None,
) -> str:
    parts: list[str] = [function_code, api_category, api_name]
    if api_spec:
        for field in walk_field_nodes([field for field in list(api_spec.get("request") or []) if isinstance(field, dict)]):
            parts.extend([clean_text(field.get("fieldName")), clean_text(field.get("description")), clean_text(field.get("notes"))])
        for field in walk_field_nodes([field for field in list(api_spec.get("response") or []) if isinstance(field, dict)]):
            parts.extend([clean_text(field.get("fieldName")), clean_text(field.get("description")), clean_text(field.get("notes"))])
        business_logic = api_spec.get("businessLogic") or {}
        if isinstance(business_logic, dict):
            for step in list(business_logic.get("steps") or []):
                if isinstance(step, dict):
                    parts.extend([clean_text(step.get("title")), clean_text(step.get("details"))])
            for dependency in list(business_logic.get("runtimeDependencies") or []):
                if isinstance(dependency, dict):
                    parts.extend([clean_text(dependency.get("id")), clean_text(dependency.get("description"))])
            for source in list(business_logic.get("dataSources") or []):
                if isinstance(source, dict):
                    parts.extend([clean_text(source.get("name")), clean_text(source.get("type"))])
            for sql_spec in list(business_logic.get("sqlSpecs") or []):
                if isinstance(sql_spec, dict):
                    parts.extend(
                        [
                            clean_text(sql_spec.get("title")),
                            clean_text(sql_spec.get("sqlText")),
                            clean_text(sql_spec.get("queryText")),
                        ]
                    )
            for shortcut in list(business_logic.get("prohibitedShortcuts") or []):
                parts.append(clean_text(shortcut))
    return normalize_token("\n".join(part for part in parts if part))


def rule_matches(
    rule: dict[str, Any],
    *,
    function_code: str,
    api_category: str,
    api_name: str,
    normalized_reference_text: str,
) -> bool:
    conditions = rule.get("conditions")
    if not isinstance(conditions, dict):
        return True

    function_codes = normalized_keyword_list(conditions.get("functionCodes"))
    if function_codes and normalize_token(function_code) not in function_codes:
        return False

    api_categories = normalized_keyword_list(conditions.get("apiCategories"))
    if api_categories and normalize_token(api_category) not in api_categories:
        return False

    api_names = normalized_keyword_list(conditions.get("apiNames"))
    if api_names and normalize_token(api_name) not in api_names:
        return False

    business_keywords = normalized_keyword_list(conditions.get("businessKeywordsAny"))
    if business_keywords and not any(keyword in normalized_reference_text for keyword in business_keywords):
        return False

    return True


def resolve_api_spec_path(project_root: Path, api_dir: Path, manifest: dict[str, Any]) -> Path | None:
    spec_artifacts = manifest.get("specArtifacts") or {}
    if isinstance(spec_artifacts, dict):
        persisted = clean_text(spec_artifacts.get("apiSpec"))
        if persisted:
            candidate = (project_root / persisted).resolve()
            if candidate.exists():
                return candidate
    candidates = sorted(path.resolve() for path in api_dir.glob("*_API_Spec.json") if path.is_file())
    if len(candidates) == 1:
        return candidates[0]
    return None


def iter_api_dirs(context_root: Path, *, function_code: str | None, api_id: str | None) -> list[Path]:
    targets: list[Path] = []
    function_dirs = []
    if function_code:
        candidate = (context_root / function_code).resolve()
        if not candidate.exists():
            raise SkillError(f"找不到 functionCode 目录：{candidate.as_posix()}")
        function_dirs.append(candidate)
    else:
        function_dirs.extend(
            sorted(
                path.resolve()
                for path in context_root.iterdir()
                if path.is_dir() and (path / "apis").exists()
            )
        )

    for function_dir in function_dirs:
        apis_dir = function_dir / "apis"
        for candidate in sorted(path.resolve() for path in apis_dir.iterdir() if path.is_dir()):
            if api_id and candidate.name != api_id:
                continue
            targets.append(candidate)

    if api_id and not targets:
        raise SkillError(f"找不到 apiId 目录：{api_id}")
    return targets


def build_review_notes_payload(
    *,
    api_id: str,
    language: str,
    source_doc: str,
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for index, rule in enumerate(rules):
        scope = clean_text(rule.get("scope"))
        file_role = clean_text(rule.get("fileRole"))
        if scope not in REVIEW_NOTE_SCOPES:
            raise SkillError(f"project-hard-constraints.rules[{index}].scope is invalid: {scope or 'null'}")
        if file_role not in REVIEW_NOTE_FILE_ROLES:
            raise SkillError(f"project-hard-constraints.rules[{index}].fileRole is invalid: {file_role or 'null'}")
        items.append(
            {
                "reviewId": clean_text(rule.get("ruleId")) or f"review_{index + 1}",
                "scope": scope,
                "fileRole": file_role,
                "ruleType": clean_text(rule.get("ruleType")) or "review_note",
                "instruction": clean_text(rule.get("instruction")),
                "severity": clean_text(rule.get("severity")) or "warning",
                "blocking": bool(rule.get("blocking")),
                "appliesTo": [clean_text(value) for value in list(rule.get("appliesTo") or []) if clean_text(value)],
                "examples": [clean_text(value) for value in list(rule.get("examples") or []) if clean_text(value)],
            }
        )
    payload = {
        "schemaVersion": "1.0.0",
        "apiId": api_id,
        "sourceDoc": source_doc,
        "language": language,
        "items": items,
    }
    validate_payload_against_schema(payload, "review-notes.schema.json", f"generated review-notes {api_id}")
    return payload


def main() -> int:
    configure_stdio()
    args = parse_args()
    try:
        project_root = resolve_project_root(args.project_root)
        agent_dir = resolve_agent_dir(project_root, args.agent_dir, args.agent_root, args.workspace_root, args.workspace_key, args.rules_root)
        context_root = resolve_context_root(project_root, agent_dir, args.context_root)
        project_constraints, project_constraints_path = load_project_constraints(agent_dir)
        source_doc = normalize_persisted_path(project_constraints_path, project_root=project_root) or project_constraints_path.name
        language = clean_text(project_constraints.get("language")) or "zh-TW"

        created = 0
        skipped = 0
        total_items = 0
        for api_dir in iter_api_dirs(context_root, function_code=args.function_code, api_id=args.api_id):
            manifest_path = api_dir / "manifest.json"
            if not manifest_path.exists():
                raise SkillError(f"缺少 manifest.json：{manifest_path.as_posix()}")
            manifest = require_json_object("manifest.json", manifest_path)
            api_id = clean_text(manifest.get("apiId")) or api_dir.name
            function_code = clean_text(manifest.get("executionId")) or api_dir.parent.parent.name
            api_category = clean_text(manifest.get("apiCategory")) or "Unknown"
            api_name = clean_text(manifest.get("apiName")) or api_id

            api_spec_path = resolve_api_spec_path(project_root, api_dir, manifest)
            api_spec = require_json_object("API_Spec.json", api_spec_path) if api_spec_path else None
            normalized_reference_text = build_reference_text(
                function_code=function_code,
                api_category=api_category,
                api_name=api_name,
                api_spec=api_spec,
            )
            selected_rules = [
                rule
                for rule in list(project_constraints.get("rules") or [])
                if isinstance(rule, dict)
                and rule_matches(
                    rule,
                    function_code=function_code,
                    api_category=api_category,
                    api_name=api_name,
                    normalized_reference_text=normalized_reference_text,
                )
            ]
            payload = build_review_notes_payload(
                api_id=api_id,
                language=language,
                source_doc=source_doc,
                rules=selected_rules,
            )
            output_path = api_dir / "review-notes.json"
            if output_path.exists() and not args.overwrite:
                skipped += 1
                print(f"SKIP {api_id} (existing)")
                continue
            total_items += len(payload["items"])
            if not args.dry_run:
                dump_json(output_path, payload)
            created += 1
            print(f"{'DRYRUN' if args.dry_run else 'WRITE'} {api_id} -> {normalize_persisted_path(output_path, project_root=project_root)} ({len(payload['items'])} rules)")

        print(f"SUMMARY created={created} skipped={skipped} rules={total_items}")
        return 0
    except SkillError as exc:
        print(f"[materialize_review_notes] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
