from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from code_inspection_utils import build_code_inspection_plan
from project_rules import resolve_asset_path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"path not found: {path.as_posix()}")
    return path


def normalize_text(text: str | None) -> str:
    return " ".join(str(text or "").split()).strip()


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_manifest_output(manifest_path: Path) -> Path:
    return manifest_path.with_name(f"{manifest_path.stem}.autofixed{manifest_path.suffix}")


def default_report_output(manifest_path: Path) -> Path:
    return manifest_path.with_name(f"{manifest_path.stem}.autofix-report.json")


def load_binding_rules(binding_rules_path: Path | None = None) -> dict[str, Any]:
    path = binding_rules_path or resolve_asset_path("utBindingRules", fallback=skill_root() / "assets" / "binding-rules.json")
    if path is None:
        raise SystemExit("binding-rules.json not found; pass --binding-rules or configure project-rules asset utBindingRules.")
    return load_json(path)


def build_manifest_item_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for section in manifest.get("sections") or []:
        for item in section.get("items") or []:
            case_id = normalize_text(item.get("caseId", ""))
            if case_id:
                lookup[case_id] = item
    return lookup


def append_note(item: dict[str, Any], note: str) -> None:
    current = normalize_text(item.get("notes", ""))
    if note in current:
        return
    item["notes"] = f"{current} {note}".strip()


def pascal_tokens(text: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[A-Z][a-z0-9]+", text)]


def api_keywords(traceability: dict[str, Any]) -> set[str]:
    keywords: set[str] = set()
    for api_id in traceability.get("apis") or []:
        for segment in str(api_id).split("."):
            normalized = normalize_text(segment).replace("_", "").replace("-", "").casefold()
            if len(normalized) >= 3:
                keywords.add(normalized)
        for token in pascal_tokens(str(api_id)):
            if len(token) >= 3:
                keywords.add(token)
    return keywords


def filter_relevant_tests(tests: list[dict[str, Any]], traceability: dict[str, Any]) -> list[dict[str, Any]]:
    keywords = api_keywords(traceability)
    if not keywords:
        return tests

    matched = []
    for test in tests:
        test_name = normalize_text(test.get("testName", "")).replace("_", "").replace("-", "").casefold()
        if any(keyword in test_name for keyword in keywords):
            matched.append(test)
    return matched or tests


def configured_rules(
    rules: list[dict[str, Any]],
    check_item: str,
    recommended_mode: str,
) -> list[tuple[str, list[str]]]:
    text = normalize_text(check_item).casefold()
    matched_rules: list[tuple[str, list[str]]] = []
    for rule in rules:
        modes = [normalize_text(mode) for mode in rule.get("recommendedModes", [])]
        if modes and recommended_mode not in modes:
            continue
        triggers = [normalize_text(token).casefold() for token in rule.get("whenCheckItemContainsAny", []) if normalize_text(token)]
        if triggers and not any(trigger in text for trigger in triggers):
            continue
        keywords = [
            normalize_text(token).replace("_", "").replace("-", "").casefold()
            for token in rule.get("matchTestNameContainsAny", [])
            if normalize_text(token)
        ]
        if keywords:
            matched_rules.append((normalize_text(rule.get("id", "rule")), keywords))
    return matched_rules


def match_tests_by_rules(
    gap: dict[str, Any],
    results: dict[str, Any],
    rules: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    source_key = "integrationTest" if gap.get("recommendedMode") == "integration_test" else "unitTest"
    tests = ((results.get("sourceResults") or {}).get(source_key) or {}).get("tests") or []
    relevant_tests = filter_relevant_tests(tests, gap.get("traceability") or {})
    if not relevant_tests:
        return [], []

    suggestions: list[dict[str, Any]] = []
    for rule_id, rule_group in configured_rules(rules, gap.get("checkItem", ""), gap.get("recommendedMode", "")):
        matched = [
            test.get("testName", "")
            for test in relevant_tests
            if any(keyword in normalize_text(test.get("testName", "")).replace("_", "").replace("-", "").casefold() for keyword in rule_group)
        ]
        unique = sorted(dict.fromkeys(name for name in matched if normalize_text(name)))
        if unique:
            suggestions.append(
                {
                    "ruleId": rule_id,
                    "testNames": unique,
                }
            )
    if not suggestions:
        return [], []
    return suggestions[0]["testNames"], suggestions


def apply_fix(
    item: dict[str, Any],
    gap: dict[str, Any],
    results: dict[str, Any],
    binding_rules: dict[str, Any],
    repo_root: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    gap_type = gap.get("gapType", "")
    case_id = gap.get("caseId", "")
    recommended_mode = gap.get("recommendedMode", "")

    if gap_type in {
        "code_inspection_mode_mismatch",
        "code_inspection_config_missing",
        "code_inspection_disabled",
    }:
        inspection_plan = build_code_inspection_plan(
            gap.get("checkItem", ""),
            gap.get("traceability") or {},
            repo_root=repo_root,
            rules=list(binding_rules.get("codeInspectionRules") or []),
        )
        item["mode"] = "code_inspection"
        item["enabled"] = bool(inspection_plan)
        item.setdefault("testBindings", {})
        item["testBindings"]["testNames"] = []
        item["codeInspection"] = inspection_plan
        append_note(item, "已依 coverage-gap 調整為 code_inspection。")
        return (
            {
                "caseId": case_id,
                "action": "configure_code_inspection",
                "details": f"mode=code_inspection, enabled={bool(inspection_plan)}, evidencePaths={len(inspection_plan.get('evidencePaths', []))}",
            },
            None if inspection_plan else {
                "caseId": case_id,
                "action": "code_inspection_rule_missing",
                "details": "no code inspection rule matched this check item",
            },
        )

    if gap_type == "manual_mode_mismatch":
        item["mode"] = "manual"
        item["enabled"] = False
        item.setdefault("testBindings", {})
        item["testBindings"]["testNames"] = []
        append_note(item, "已依 coverage-gap 自動調整為 manual。")
        return (
            {
                "caseId": case_id,
                "action": "set_manual_mode",
                "details": "mode=manual, enabled=false, cleared test bindings",
            },
            None,
        )

    if gap_type == "mode_mismatch":
        item["mode"] = recommended_mode
        item["enabled"] = False
        append_note(item, f"已依 coverage-gap 調整為 {recommended_mode}，待補測試綁定。")
        return (
            {
                "caseId": case_id,
                "action": "align_mode",
                "details": f"mode={recommended_mode}, enabled=false",
            },
            None,
        )

    if gap_type == "missing_test_binding":
        suggested_tests, strong_suggestions = match_tests_by_rules(
            gap,
            results,
            list(binding_rules.get("strongRules") or []),
        )
        _, weak_suggestions = match_tests_by_rules(
            gap,
            results,
            list(binding_rules.get("weakRules") or []),
        )
        if not suggested_tests:
            if weak_suggestions:
                return None, {
                    "caseId": case_id,
                    "action": "weak_suggestion_only",
                    "details": "no strong-rule binding applied",
                    "suggestions": weak_suggestions,
                }
            return None, None
        item["mode"] = recommended_mode
        item["enabled"] = True
        item.setdefault("testBindings", {})
        item["testBindings"]["testNames"] = suggested_tests
        item["testBindings"]["matchMode"] = item["testBindings"].get("matchMode") or "all_pass"
        item["testBindings"]["allowMissing"] = False
        append_note(item, "已依 coverage-gap 高置信規則自動補齊 testBindings。")
        return (
            {
                "caseId": case_id,
                "action": "bind_tests",
                "details": f"bound {len(suggested_tests)} tests",
                "testNames": suggested_tests,
                "ruleSuggestions": strong_suggestions,
            },
            {
                "caseId": case_id,
                "action": "weak_suggestions_available" if weak_suggestions else "strong_binding_applied",
                "details": "weak suggestions retained for review" if weak_suggestions else "binding applied from strong rules",
                "suggestions": weak_suggestions,
            } if weak_suggestions else None,
        )

    return None, None


def apply_gap_fixes(
    manifest: dict[str, Any],
    coverage_gap: dict[str, Any],
    results: dict[str, Any],
    binding_rules: dict[str, Any],
) -> dict[str, Any]:
    manifest_lookup = build_manifest_item_lookup(manifest)
    changes: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    repo_root = normalize_text(((coverage_gap.get("moduleContext") or {}).get("repoRoot") or ""))

    for gap in coverage_gap.get("gaps") or []:
        case_id = normalize_text(gap.get("caseId", ""))
        item = manifest_lookup.get(case_id)
        if item is None:
            continue
        change, suggestion = apply_fix(item, gap, results, binding_rules, repo_root)
        if change:
            changes.append(change)
        if suggestion:
            suggestions.append(suggestion)

    return {
        "moduleCode": ((coverage_gap.get("moduleContext") or {}).get("moduleCode") or ""),
        "appliedChangeCount": len(changes),
        "changes": changes,
        "suggestions": suggestions,
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Apply safe manifest fixes from coverage-gap analysis.",
    )
    parser.add_argument("coverage_gap_path", help="Path to coverage-gap.json")
    parser.add_argument("manifest_path", help="Path to the report job manifest.")
    parser.add_argument("results_path", help="Path to results.json used for binding suggestions.")
    parser.add_argument("--output-manifest", help="Output path for the updated manifest.")
    parser.add_argument("--output-report", help="Output path for the autofix report.")
    parser.add_argument("--binding-rules", help="Optional path to binding-rules.json")
    args = parser.parse_args()

    coverage_gap_path = resolve_path(args.coverage_gap_path)
    manifest_path = resolve_path(args.manifest_path)
    results_path = resolve_path(args.results_path)

    output_manifest = (
        Path(args.output_manifest).expanduser().resolve()
        if args.output_manifest
        else default_manifest_output(manifest_path)
    )
    output_report = (
        Path(args.output_report).expanduser().resolve()
        if args.output_report
        else default_report_output(output_manifest)
    )

    coverage_gap = load_json(coverage_gap_path)
    manifest = load_json(manifest_path)
    results = load_json(results_path)
    binding_rules = load_binding_rules(
        resolve_path(args.binding_rules) if args.binding_rules else None
    )

    report = apply_gap_fixes(manifest, coverage_gap, results, binding_rules)
    write_json(output_manifest, manifest)
    write_json(output_report, report)

    print(f"Updated manifest written: {output_manifest.as_posix()}")
    print(f"Autofix report written: {output_report.as_posix()}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
