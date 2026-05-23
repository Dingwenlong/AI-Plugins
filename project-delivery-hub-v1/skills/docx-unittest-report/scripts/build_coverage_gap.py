from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"path not found: {path.as_posix()}")
    return path


def normalize_text(text: str | None) -> str:
    return " ".join(str(text or "").split()).strip()


def default_output_path(classification_path: Path) -> Path:
    return classification_path.with_name(f"{classification_path.stem}.coverage-gap.json")


def default_plan_path(output_path: Path) -> Path:
    return output_path.with_suffix(".md")


def build_manifest_item_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for section in manifest.get("sections") or []:
        for item in section.get("items") or []:
            case_id = normalize_text(item.get("caseId", ""))
            if case_id:
                lookup[case_id] = item
    return lookup


def build_case_result_lookup(results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in results.get("cases") or []:
        case_id = normalize_text(item.get("caseId", ""))
        if case_id:
            lookup[case_id] = item
    return lookup


def infer_gap(
    classified_item: dict[str, Any],
    manifest_item: dict[str, Any] | None,
    result_item: dict[str, Any] | None,
) -> dict[str, Any] | None:
    applicability = classified_item.get("applicability", "")
    if applicability != "applicable":
        return None

    case_id = classified_item.get("caseId", "")
    recommended_mode = classified_item.get("recommendedMode", "manual")
    traceability = classified_item.get("traceability") or {}

    if manifest_item is None:
        return {
            "caseId": case_id,
            "checkItem": classified_item.get("checkItem", ""),
            "gapType": "manifest_missing",
            "severity": "medium",
            "recommendedMode": recommended_mode,
            "currentMode": "",
            "reason": "分類結果顯示此項適用，但 manifest 尚未建立對應條目。",
            "suggestedAction": "先把此模板項加入 manifest，再決定要綁 UnitTest、IntegrationTest、代碼定位或人工驗證。",
            "traceability": traceability,
        }

    current_mode = manifest_item.get("mode", "")
    enabled = bool(manifest_item.get("enabled", False))
    bindings = ((manifest_item.get("testBindings") or {}).get("testNames") or [])
    binding_count = len([name for name in bindings if normalize_text(name)])

    if recommended_mode == "code_inspection":
        code_inspection = manifest_item.get("codeInspection") or {}
        evidence_paths = [
            normalize_text(path)
            for path in code_inspection.get("evidencePaths", [])
            if normalize_text(path)
        ]

        if current_mode != "code_inspection":
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "code_inspection_mode_mismatch",
                "severity": "medium",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": f"分類建議此項改走 {recommended_mode}，但 manifest 目前是 {current_mode or '未設定'}。",
                "suggestedAction": "將 manifest mode 改成 code_inspection，並補齊 codeInspection 規則與證據路徑。",
                "traceability": traceability,
            }

        if not evidence_paths:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "code_inspection_config_missing",
                "severity": "high",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": "此項建議改走代碼定位，但 manifest 尚未配置 codeInspection.evidencePaths。",
                "suggestedAction": "補齊 codeInspection.evidencePaths 與必要 token 規則。",
                "traceability": traceability,
            }

        if not enabled:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "code_inspection_disabled",
                "severity": "medium",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": "此項已具備代碼定位配置，但 manifest 仍未啟用。",
                "suggestedAction": "確認 codeInspection 配置正確後，將 enabled 改成 true。",
                "traceability": traceability,
            }

        if result_item is None:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "result_missing",
                "severity": "high",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": "此項已啟用代碼定位，但結果檔中沒有對應 case 結果。",
                "suggestedAction": "重新執行 run_report_job.py，確認 collect/results 產物與 manifest 對齊。",
                "traceability": traceability,
            }

        status = result_item.get("status", "")
        if status in {"pending", "failed"}:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "code_inspection_not_passing",
                "severity": "high" if status == "failed" else "medium",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": f"此項已走代碼定位，但目前狀態為 {status}。",
                "suggestedAction": "依 results.json 檢查證據路徑、token 規則或補強程式碼定位。",
                "traceability": traceability,
            }

        return None

    if recommended_mode in {"unit_test", "integration_test"}:
        if current_mode not in {"unit_test", "integration_test"}:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "mode_mismatch",
                "severity": "medium",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": f"分類建議此項使用 {recommended_mode}，但 manifest 目前是 {current_mode or '未設定'}。",
                "suggestedAction": f"將 manifest mode 調整為 {recommended_mode}，再補齊 testBindings。",
                "traceability": traceability,
            }

        if binding_count == 0:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "missing_test_binding",
                "severity": "high",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": "此項適用且應自動化，但 manifest 尚未綁定任何顯式測試名稱。",
                "suggestedAction": f"補齊 {recommended_mode} 的 testBindings.testNames。",
                "traceability": traceability,
            }

        if not enabled:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "binding_disabled",
                "severity": "medium",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": "此項已具備測試綁定，但 manifest 仍未啟用。",
                "suggestedAction": "確認綁定測試正確後，將 enabled 改成 true。",
                "traceability": traceability,
            }

        if result_item is None:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "result_missing",
                "severity": "high",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": "此項已啟用自動化，但結果檔中沒有對應 case 結果。",
                "suggestedAction": "重新執行 run_report_job.py，確認 collect/results 產物與 manifest 對齊。",
                "traceability": traceability,
            }

        status = result_item.get("status", "")
        if status in {"pending", "failed"}:
            return {
                "caseId": case_id,
                "checkItem": classified_item.get("checkItem", ""),
                "gapType": "automation_not_passing",
                "severity": "high" if status == "failed" else "medium",
                "recommendedMode": recommended_mode,
                "currentMode": current_mode,
                "reason": f"此項已自動化，但目前狀態為 {status}。",
                "suggestedAction": "依 results.json 檢查缺失測試、失敗訊息或待補證據。",
                "traceability": traceability,
            }

        return None

    if current_mode not in {"manual", "skip"}:
        return {
            "caseId": case_id,
            "checkItem": classified_item.get("checkItem", ""),
            "gapType": "manual_mode_mismatch",
            "severity": "low",
            "recommendedMode": recommended_mode,
            "currentMode": current_mode,
            "reason": f"分類建議此項先走 {recommended_mode}，但 manifest 目前是 {current_mode or '未設定'}。",
            "suggestedAction": f"若暫不自動化，將 mode 改成 {recommended_mode} 並補人工證據說明。",
            "traceability": traceability,
        }

    if current_mode == "manual" and not normalize_text(manifest_item.get("actualResult", "")):
        return {
            "caseId": case_id,
            "checkItem": classified_item.get("checkItem", ""),
            "gapType": "manual_evidence_missing",
            "severity": "low",
            "recommendedMode": recommended_mode,
            "currentMode": current_mode,
            "reason": "此項目前走人工驗證，但尚未填寫實際結果或人工證據。",
            "suggestedAction": "補上 actualResult 與必要的 manualEvidencePaths。",
            "traceability": traceability,
        }

    return None


def build_gap_payload(
    classification: dict[str, Any],
    manifest: dict[str, Any] | None,
    results: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest_lookup = build_manifest_item_lookup(manifest or {})
    result_lookup = build_case_result_lookup(results or {})

    gaps: list[dict[str, Any]] = []
    applicable_items = 0
    not_applicable_items = 0

    for section in classification.get("sections") or []:
        for item in section.get("items") or []:
            if item.get("applicability") == "applicable":
                applicable_items += 1
            else:
                not_applicable_items += 1

            gap = infer_gap(
                item,
                manifest_lookup.get(normalize_text(item.get("caseId", ""))),
                result_lookup.get(normalize_text(item.get("caseId", ""))),
            )
            if gap:
                gaps.append(gap)

    gap_type_counts = Counter(gap["gapType"] for gap in gaps)
    severity_counts = Counter(gap["severity"] for gap in gaps)
    recommended_mode_counts = Counter(gap["recommendedMode"] for gap in gaps)

    return {
        "moduleContext": classification.get("moduleContext") or {},
        "summary": {
            "applicableItems": applicable_items,
            "notApplicableItems": not_applicable_items,
            "gapCount": len(gaps),
            "gapTypeCounts": dict(gap_type_counts),
            "severityCounts": dict(severity_counts),
            "recommendedModes": dict(recommended_mode_counts),
        },
        "gaps": gaps,
    }


def render_plan_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Test Improvement Plan",
        "",
        f"- Applicable items: {summary.get('applicableItems', 0)}",
        f"- Not applicable items: {summary.get('notApplicableItems', 0)}",
        f"- Gaps: {summary.get('gapCount', 0)}",
        "",
        "## Gap Summary",
        "",
    ]

    for gap_type, count in sorted((summary.get("gapTypeCounts") or {}).items()):
        lines.append(f"- {gap_type}: {count}")

    lines.extend(["", "## Actions", ""])

    gaps = payload.get("gaps") or []
    if not gaps:
        lines.append("- No actionable gaps. Applicable items are either covered or intentionally manual.")
        return "\n".join(lines) + "\n"

    severity_order = {"high": 0, "medium": 1, "low": 2}
    for gap in sorted(gaps, key=lambda item: (severity_order.get(item["severity"], 9), item["caseId"])):
        lines.append(
            f"- [{gap['severity']}] {gap['caseId']} ({gap['recommendedMode']}): {gap['checkItem']} | {gap['suggestedAction']}"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Build a coverage-gap report from template classification plus optional manifest/results.",
    )
    parser.add_argument("classification_path", help="Path to template-classification.json")
    parser.add_argument("--manifest", help="Optional path to the report job manifest.")
    parser.add_argument("--results", help="Optional path to results.json from run_report_job.")
    parser.add_argument("--output", help="Output path for coverage-gap.json")
    parser.add_argument("--plan-md", help="Optional markdown output path for a human-readable improvement plan.")
    args = parser.parse_args()

    classification_path = resolve_path(args.classification_path)
    classification = load_json(classification_path)
    manifest = load_json(resolve_path(args.manifest)) if args.manifest else None
    results = load_json(resolve_path(args.results)) if args.results else None

    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(classification_path)
    plan_path = Path(args.plan_md).expanduser().resolve() if args.plan_md else default_plan_path(output_path)

    payload = build_gap_payload(classification, manifest, results)
    write_json(output_path, payload)
    write_text(plan_path, render_plan_markdown(payload))

    print(f"Coverage gap written: {output_path.as_posix()}")
    print(f"Improvement plan written: {plan_path.as_posix()}")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
