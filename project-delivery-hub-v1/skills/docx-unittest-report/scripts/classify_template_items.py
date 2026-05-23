from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from code_inspection_utils import aggregate_path_groups, build_code_inspection_plan, load_code_inspection_rules


SECTION_RULES: dict[str, dict[str, Any]] = {
    "UT-01": {
        "title": "API 介面規格與一致性",
        "trait": "hasHttpApi",
        "reason": "模組含對外 HTTP API，需驗證介面契約與一致性。",
        "apiOperationTypes": None,
        "defaultMode": "integration_test",
    },
    "UT-02": {
        "title": "請求參數驗證",
        "trait": "hasValidationSurface",
        "reason": "模組存在輸入參數或欄位驗證，需驗證請求參數規則。",
        "apiOperationTypes": None,
        "defaultMode": "unit_test",
    },
    "UT-03": {
        "title": "回應格式與錯誤處理",
        "trait": "hasHttpApi",
        "reason": "模組有對外回應契約，需驗證回應格式與錯誤處理。",
        "apiOperationTypes": None,
        "defaultMode": "integration_test",
    },
    "UT-04": {
        "title": "查詢/列表類 API",
        "trait": "hasQueryApi",
        "reason": "模組包含查詢/列表 API，需驗證查詢行為。",
        "apiOperationTypes": {"query"},
        "defaultMode": "unit_test",
    },
    "UT-05": {
        "title": "新增/建立類 API",
        "trait": "hasCreateApi",
        "reason": "模組包含新增/建立 API，需驗證建立流程。",
        "apiOperationTypes": {"create"},
        "defaultMode": "unit_test",
    },
    "UT-06": {
        "title": "修改/更新類 API",
        "trait": "hasUpdateApi",
        "reason": "模組包含修改/更新 API，需驗證更新流程。",
        "apiOperationTypes": {"update"},
        "defaultMode": "unit_test",
    },
    "UT-07": {
        "title": "刪除類 API",
        "trait": "hasDeleteApi",
        "reason": "模組包含刪除 API，需驗證刪除流程。",
        "apiOperationTypes": {"delete"},
        "defaultMode": "unit_test",
    },
    "UT-08": {
        "title": "匯出/下載類 API",
        "trait": "hasDownloadApi",
        "reason": "模組包含匯出/下載 API，需驗證下載與檔案回應。",
        "apiOperationTypes": {"download"},
        "defaultMode": "integration_test",
    },
    "UT-09": {
        "title": "通知/訊息發送類 API",
        "trait": "hasNotifyApi",
        "reason": "模組包含通知/訊息發送 API，需驗證通知流程。",
        "apiOperationTypes": {"notify"},
        "defaultMode": "integration_test",
    },
    "UT-10": {
        "title": "需求/規格對照",
        "trait": "hasHttpApi",
        "reason": "模組需保留需求、規格、API 與測試的追溯矩陣。",
        "apiOperationTypes": None,
        "defaultMode": "manual",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(text: str | None) -> str:
    return " ".join(str(text or "").split()).strip()


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"path not found: {path.as_posix()}")
    return path


def has_validation_surface(module_scope: dict[str, Any]) -> bool:
    for api in module_scope.get("apis") or []:
        traits = api.get("businessTraits") or {}
        if traits.get("hasRequestPayload") or traits.get("hasValidationRules"):
            return True
    return False


def has_attachment_surface(module_scope: dict[str, Any]) -> bool:
    attachment_tokens = ("file", "upload", "attachment", "附件", "檔案", "mime")
    for api in module_scope.get("apis") or []:
        if api.get("operationType") == "download":
            return True
        for field in ((api.get("request") or {}).get("fields") or []):
            text = normalize_text(field).casefold()
            if any(token.casefold() in text for token in attachment_tokens):
                return True
        for field in ((api.get("response") or {}).get("fields") or []):
            text = normalize_text(field).casefold()
            if any(token.casefold() in text for token in attachment_tokens):
                return True
    return False


def get_module_traits(module_scope: dict[str, Any]) -> dict[str, bool]:
    summary_traits = ((module_scope.get("summary") or {}).get("moduleTraits") or {}).copy()
    summary_traits["hasValidationSurface"] = has_validation_surface(module_scope)
    summary_traits["hasAttachmentSurface"] = has_attachment_surface(module_scope)
    return summary_traits


def filter_relevant_apis(module_scope: dict[str, Any], section_rule: dict[str, Any]) -> list[dict[str, Any]]:
    operation_types = section_rule.get("apiOperationTypes")
    apis = module_scope.get("apis") or []
    if not operation_types:
        return apis
    return [api for api in apis if api.get("operationType") in operation_types]


def aggregate_traceability(
    apis: list[dict[str, Any]],
    repo_root: str,
) -> dict[str, Any]:
    path_groups = aggregate_path_groups(apis, repo_root)
    return {
        "apis": [api.get("apiId", "") for api in apis if normalize_text(api.get("apiId", ""))],
        "codePaths": sorted(
            {
                path
                for bucket in ("controller", "service", "entity", "common", "other")
                for path in path_groups.get(bucket, [])
            }
        ),
        "pathGroups": path_groups,
        "unitTests": sorted(path_groups.get("unitTest", [])),
        "integrationTests": sorted(path_groups.get("integrationTest", [])),
    }


def infer_item_mode(section_id: str, check_item: str, default_mode: str) -> str:
    text = normalize_text(check_item)

    if "Swagger" in text or "OpenAPI" in text or "命名與描述" in text or "版本控管" in text:
        return "code_inspection"
    if "Response Header" in text or "Content-Type" in text or "HTTP Method" in text or "Endpoint" in text:
        return "code_inspection"
    if "HTTP 狀態碼" in text or "回應結構" in text or "Header 規範" in text:
        return "code_inspection"
    if "schema" in text.lower() or "欄位命名" in text or "型別符合規格" in text:
        return "code_inspection"
    if "必填" in text or "參數驗證" in text or "模型驗證" in text:
        return "code_inspection"
    if "查詢" in text or "列表" in text or "分頁" in text or "排序" in text:
        return "code_inspection"
    if "下載" in text or "匯出" in text or "檔案" in text:
        return "code_inspection"
    if "通知" in text or "訊息" in text or "發送" in text:
        return "code_inspection"
    if "DB" in text or "資料" in text or "快取" in text or "商業邏輯" in text:
        return "unit_test"
    if section_id in {"UT-01", "UT-02", "UT-03", "UT-08", "UT-09"}:
        return "code_inspection"
    if section_id == "UT-10":
        return "manual"
    if section_id == "UT-04":
        return "code_inspection"
    if section_id in {"UT-05", "UT-06", "UT-07"}:
        return default_mode
    return default_mode


def infer_item_applicability(
    item: dict[str, Any],
    section_id: str,
    section_applicability: str,
    module_traits: dict[str, bool],
) -> tuple[str, str]:
    if section_applicability != "applicable":
        return "not_applicable", "所屬區塊對此模組不適用。"

    text = normalize_text(item.get("checkItem", ""))
    if "DB" in text and not module_traits.get("usesSql", False):
        return "not_applicable", "模組未使用 SQL/資料庫，不適用 DB 驗證項。"
    if "快取" in text and not module_traits.get("usesRedis", False):
        return "not_applicable", "模組未使用 Redis/快取，不適用快取驗證項。"
    if any(token in text for token in ("檔案", "附件", "MIME", "副檔名")) and not module_traits.get("hasAttachmentSurface", False):
        return "not_applicable", "接口未涉及檔案/附件處理，不適用附件驗證項。"
    if section_id == "UT-02" and not module_traits.get("hasValidationSurface", False):
        return "not_applicable", "模組沒有可驗證的請求欄位或欄位規則。"
    if section_id == "UT-10":
        return "applicable", "模組級報告需保留需求與測試追溯。"
    return "applicable", "區塊適用，後續再依顯式測試綁定補足自動化證據。"


def classify_section(
    section: dict[str, Any],
    module_scope: dict[str, Any],
    code_inspection_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    module_traits = get_module_traits(module_scope)
    section_id = section.get("sectionId", "")
    section_rule = SECTION_RULES.get(
        section_id,
        {
            "trait": "hasHttpApi",
            "reason": "未命名規則的區塊，先保守視為需人工判定。",
            "apiOperationTypes": None,
            "defaultMode": "manual",
        },
    )

    trait_name = section_rule["trait"]
    section_applicable = bool(module_traits.get(trait_name, False))
    relevant_apis = filter_relevant_apis(module_scope, section_rule)
    repo_root = normalize_text(module_scope.get("repoRoot", ""))
    section_traceability = aggregate_traceability(relevant_apis, repo_root)

    section_applicability = "applicable" if section_applicable else "not_applicable"
    section_reason = section_rule["reason"] if section_applicable else f"模組不具備 {section_rule['title']} 所需能力。"

    items = []
    for item in section.get("items") or []:
        item_applicability, item_reason = infer_item_applicability(
            item,
            section_id,
            section_applicability,
            module_traits,
        )
        recommended_mode = infer_item_mode(
            section_id,
            item.get("checkItem", ""),
            section_rule["defaultMode"],
        )
        if item_applicability == "not_applicable":
            recommended_mode = "skip"

        payload = {
            "caseId": item.get("caseId", ""),
            "checkItem": item.get("checkItem", ""),
            "applicability": item_applicability,
            "applicabilityReason": item_reason,
            "recommendedMode": recommended_mode,
            "traceability": section_traceability,
        }
        if recommended_mode == "code_inspection":
            inspection_plan = build_code_inspection_plan(
                item.get("checkItem", ""),
                section_traceability,
                repo_root=repo_root,
                rules=code_inspection_rules,
            )
            if inspection_plan:
                payload["codeInspection"] = inspection_plan

        items.append(payload)

    return {
        "sectionId": section_id,
        "title": section.get("title", ""),
        "applicability": section_applicability,
        "applicabilityReason": section_reason,
        "recommendedMode": section_rule["defaultMode"] if section_applicable else "skip",
        "traceability": section_traceability,
        "items": items,
    }


def summarize_sections(sections: list[dict[str, Any]]) -> dict[str, Any]:
    section_counter = Counter(section["applicability"] for section in sections)
    item_counter = Counter(
        item["applicability"]
        for section in sections
        for item in section.get("items") or []
    )
    recommended_mode_counter = Counter(
        item["recommendedMode"]
        for section in sections
        for item in section.get("items") or []
    )
    return {
        "sectionCounts": dict(section_counter),
        "itemCounts": dict(item_counter),
        "recommendedModes": dict(recommended_mode_counter),
    }


def build_classification(module_scope: dict[str, Any], template_outline: dict[str, Any]) -> dict[str, Any]:
    code_inspection_rules = load_code_inspection_rules()
    sections = [
        classify_section(section, module_scope, code_inspection_rules)
        for section in template_outline.get("sections") or []
    ]
    return {
        "moduleContext": {
            "moduleCode": module_scope.get("moduleCode", ""),
            "repoRoot": module_scope.get("repoRoot", ""),
            "contextRoot": module_scope.get("contextRoot", ""),
            "solutionPath": module_scope.get("solutionPath", ""),
            "apiCount": ((module_scope.get("summary") or {}).get("apiCount") or 0),
        },
        "summary": summarize_sections(sections),
        "sections": sections,
    }


def default_output_path(module_scope_path: Path) -> Path:
    return module_scope_path.with_name(f"{module_scope_path.stem}.classification.json")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Classify DOCX test-report template items against a module-scope analysis result.",
    )
    parser.add_argument("module_scope_path", help="Path to module-scope.json")
    parser.add_argument("template_outline_path", help="Path to template-outline.json")
    parser.add_argument(
        "--output",
        help="Path to the classification JSON. Defaults next to module-scope.json.",
    )
    args = parser.parse_args()

    module_scope_path = resolve_path(args.module_scope_path)
    template_outline_path = resolve_path(args.template_outline_path)
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(module_scope_path)

    module_scope = load_json(module_scope_path)
    template_outline = load_json(template_outline_path)
    classification = build_classification(module_scope, template_outline)
    write_json(output_path, classification)

    print(f"Classification created: {output_path.as_posix()}")
    print(f"Sections classified: {len(classification['sections'])}")
    print(json.dumps(classification["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
