from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEV_GUIDELINE_CATALOG_RELATIVE_PATH = "rules/code-guidelines/catalog.json"
DEV_GUIDELINE_SOURCE_NAME = "project code guidelines"
DEV_GUIDELINE_VERSION = "external"
PROJECT_RULES_DEFAULT_CATALOG = DEV_GUIDELINE_CATALOG_RELATIVE_PATH


FRONTSTAGE_KEYWORDS = {
    "member": 3,
    "customer": 1,
    "cust": 1,
    "會員": 3,
    "会员": 3,
    "客戶": 1,
    "客户": 1,
    "app": 1,
    "bff": 2,
    "frontend": 2,
    "frontstage": 3,
    "前台": 3,
    "login": 1,
    "登入": 1,
    "jwt": 2,
    "access_token": 3,
    "auth_sn": 3,
    "session": 2,
    "redis": 1,
    "profile": 2,
    "個人": 2,
    "个人": 2,
}

MID_BACKOFFICE_KEYWORDS = {
    "admin": 3,
    "backoffice": 3,
    "management": 2,
    "manage": 1,
    "staff": 2,
    "employee": 2,
    "teller": 2,
    "role": 2,
    "permission": 2,
    "authorization": 2,
    "menu": 2,
    "audit": 2,
    "operationlog": 2,
    "行員": 3,
    "行员": 3,
    "內部": 2,
    "内部": 2,
    "中後台": 4,
    "中后台": 4,
    "後台": 3,
    "后台": 3,
    "管理": 2,
    "權限": 3,
    "权限": 3,
    "角色": 2,
    "菜單": 2,
    "菜单": 2,
    "審計": 2,
    "审计": 2,
    "操作日誌": 2,
    "操作日志": 2,
}

SHARED_KEYWORDS = {
    "common": 2,
    "commonfunc": 3,
    "commonutil": 3,
    "shared": 2,
    "infrastructure": 2,
    "utility": 2,
    "helper": 1,
    "framework": 1,
    "共用": 3,
    "公用": 3,
    "共享": 2,
    "基礎": 2,
    "基础": 2,
    "工具": 1,
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def _walk_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, item in value.items():
            strings.extend(_walk_strings(key))
            strings.extend(_walk_strings(item))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_walk_strings(item))
        return strings
    if isinstance(value, (bool, int, float)):
        return [str(value)]
    return []


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", clean_text(value)).casefold()


def _keyword_hits(text: str, keywords: dict[str, int], scope: str) -> tuple[int, list[dict[str, Any]]]:
    score = 0
    evidence: list[dict[str, Any]] = []
    for keyword, weight in keywords.items():
        if keyword.casefold() in text:
            score += weight
            evidence.append({"scope": scope, "keyword": keyword, "weight": weight})
    return score, evidence


def _collect_model_text(item: dict[str, Any], normalized_model: dict[str, Any], framework_plan: Any) -> str:
    strings: list[str] = []
    strings.extend(_walk_strings(item))
    strings.extend(_walk_strings(normalized_model.get("source") or {}))
    strings.extend(_walk_strings(normalized_model.get("apiCategory")))
    strings.extend(_walk_strings(normalized_model.get("apiName")))
    strings.extend(_walk_strings(normalized_model.get("businessSteps") or []))
    strings.extend(_walk_strings(normalized_model.get("runtimeDependencies") or []))
    strings.extend(_walk_strings(normalized_model.get("dependencyHints") or []))
    strings.extend(_walk_strings(normalized_model.get("backendApis") or []))
    strings.extend(_walk_strings(normalized_model.get("referenceHints") or []))
    strings.extend(_walk_strings(normalized_model.get("queryContracts") or []))
    strings.extend(_walk_strings(normalized_model.get("constraints") or []))
    strings.extend(
        [
            clean_text(getattr(framework_plan, "module_name", "")),
            clean_text(getattr(framework_plan, "controller_file", "")),
            clean_text(getattr(framework_plan, "target_file", "")),
        ]
    )
    return _normalize_text("\n".join(text for text in strings if clean_text(text)))


def detect_audience_profile(item: dict[str, Any], normalized_model: dict[str, Any], framework_plan: Any) -> dict[str, Any]:
    text = _collect_model_text(item, normalized_model, framework_plan)
    front_score, front_evidence = _keyword_hits(text, FRONTSTAGE_KEYWORDS, "frontstage")
    back_score, back_evidence = _keyword_hits(text, MID_BACKOFFICE_KEYWORDS, "midBackoffice")
    shared_score, shared_evidence = _keyword_hits(text, SHARED_KEYWORDS, "shared")
    unresolved: list[dict[str, Any]] = []

    scope = "unknown"
    confidence = "low"
    if front_score >= 4 and front_score >= back_score + 2:
        scope = "frontstage"
        confidence = "high" if front_score >= 5 else "medium"
    elif back_score >= 3 and back_score >= front_score + 2:
        scope = "midBackoffice"
        confidence = "high" if back_score >= 5 else "medium"
    elif shared_score >= 3 and front_score < 3 and back_score < 3:
        scope = "shared"
        confidence = "high" if shared_score >= 5 else "medium"
    elif front_score > 0 and back_score > 0:
        unresolved.append(
            {
                "gapType": "audience_profile_ambiguous",
                "severity": "error",
                "blocking": True,
                "message": "API 同時命中前台與中後台線索，需由 spec/handoff 補明確調用者或使用場景。",
            }
        )

    evidence = [*front_evidence, *back_evidence, *shared_evidence]
    return {
        "scope": scope,
        "confidence": confidence,
        "scores": {
            "frontstage": front_score,
            "midBackoffice": back_score,
            "shared": shared_score,
        },
        "evidence": evidence[:16],
        "unresolved": unresolved,
    }


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def load_dev_guideline_catalog(skill_root: Path, rules_root: Path | None = None) -> dict[str, Any]:
    def missing_catalog(source_status: str, catalog_path: str = "") -> dict[str, Any]:
        return {
            "schemaVersion": "1.0.0",
            "sourceName": DEV_GUIDELINE_SOURCE_NAME,
            "version": DEV_GUIDELINE_VERSION,
            "catalogPath": catalog_path,
            "rulesRoot": rules_root.as_posix() if rules_root is not None else "",
            "sourceStatus": source_status,
            "rules": [],
        }

    if rules_root is not None:
        project_catalog = load_json_object(rules_root / "catalog.json")
        defaults = project_catalog.get("defaults") if isinstance(project_catalog.get("defaults"), dict) else {}
        catalog_rel = clean_text(defaults.get("codeGuidelineCatalog")) or PROJECT_RULES_DEFAULT_CATALOG
        catalog_path = rules_root / catalog_rel
        if catalog_path.exists():
            payload = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                payload["catalogPath"] = catalog_rel.replace("\\", "/")
                payload["rulesRoot"] = rules_root.as_posix()
                return payload
        return missing_catalog("project_rules_missing", catalog_rel.replace("\\", "/"))
    return missing_catalog("rules_root_not_resolved", DEV_GUIDELINE_CATALOG_RELATIVE_PATH)


def _feature_flags(normalized_model: dict[str, Any], model_text: str) -> dict[str, bool]:
    query_contracts = [entry for entry in list(normalized_model.get("queryContracts") or []) if isinstance(entry, dict)]
    request_fields = [entry for entry in list(normalized_model.get("requestFields") or []) if isinstance(entry, dict)]
    constraints = [entry for entry in list(normalized_model.get("constraints") or []) if isinstance(entry, dict)]
    mock_examples = [entry for entry in list(normalized_model.get("mockExamples") or []) if isinstance(entry, dict)]
    return {
        "always": True,
        "hasSql": bool(query_contracts) or any(keyword in model_text for keyword in ("sql", "db", "database", "table", "sp_", "select ", "insert ", "update ")),
        "hasCache": any(keyword in model_text for keyword in ("redis", "cache", "session", "ttl", "缓存", "快取")),
        "hasIdentity": any(keyword in model_text for keyword in ("jwt", "access_token", "auth_sn", "member", "會員", "会员", "身份", "身分")),
        "hasValidation": bool(request_fields) or any(clean_text(entry.get("constraintType")) == "request_field_validation" for entry in constraints),
        "hasConfig": any(keyword in model_text for keyword in ("appsettings", "config", "configuration", "第三方", "external", "endpoint", "url")),
        "hasAuditOrAuthorization": any(keyword in model_text for keyword in ("role", "permission", "authorization", "audit", "menu", "權限", "权限", "角色", "審計", "审计", "操作日誌", "操作日志")),
        "hasTestHandoff": bool(mock_examples),
        "hasLoggingOrException": any(keyword in model_text for keyword in ("exception", "error", "log", "logging", "例外", "異常", "异常", "錯誤", "错误")),
    }


def _rule_feature_matches(rule: dict[str, Any], features: dict[str, bool]) -> bool:
    triggers = rule.get("featureTriggers")
    if not isinstance(triggers, list) or not triggers:
        return bool(features.get("always"))
    return any(bool(features.get(clean_text(trigger))) for trigger in triggers)


def _rule_audience_matches(rule: dict[str, Any], audience_scope: str) -> bool:
    scopes = [clean_text(scope) for scope in list(rule.get("audienceScopes") or []) if clean_text(scope)]
    if not scopes:
        return True
    return "all" in scopes or audience_scope in scopes


def _is_exclusive_audience_rule(rule: dict[str, Any]) -> bool:
    scopes = {clean_text(scope) for scope in list(rule.get("audienceScopes") or []) if clean_text(scope)}
    return bool(scopes & {"frontstage", "midBackoffice"}) and "all" not in scopes


def select_dev_guidelines(
    *,
    skill_root: Path,
    rules_root: Path | None = None,
    item: dict[str, Any],
    normalized_model: dict[str, Any],
    framework_plan: Any,
) -> dict[str, Any]:
    catalog = load_dev_guideline_catalog(skill_root, rules_root)
    model_text = _collect_model_text(item, normalized_model, framework_plan)
    audience_profile = detect_audience_profile(item, normalized_model, framework_plan)
    features = _feature_flags(normalized_model, model_text)
    selected_rules: list[dict[str, Any]] = []
    load_hints: list[dict[str, str]] = []
    gaps: list[dict[str, Any]] = list(audience_profile.get("unresolved") or [])
    load_paths_seen: set[str] = set()

    for rule in list(catalog.get("rules") or []):
        if not isinstance(rule, dict):
            continue
        if not _rule_feature_matches(rule, features):
            continue
        if not _rule_audience_matches(rule, clean_text(audience_profile.get("scope"))):
            if clean_text(audience_profile.get("scope")) == "unknown" and _is_exclusive_audience_rule(rule):
                gaps.append(
                    {
                        "gapType": "audience_profile_required",
                        "ruleId": clean_text(rule.get("ruleId")),
                        "severity": "error",
                        "blocking": True,
                        "message": "命中特定前台/中後台規範，但 API 使用者或入口方向證據不足。",
                        "missingEvidence": ["caller channel", "frontstage/backoffice scope", "route or TSD audience"],
                    }
                )
            continue
        load_path = clean_text(rule.get("loadPath"))
        selected = {
            "ruleId": clean_text(rule.get("ruleId")),
            "title": clean_text(rule.get("title")),
            "category": clean_text(rule.get("category")),
            "direction": clean_text(rule.get("direction")),
            "ruleType": clean_text(rule.get("ruleType")),
            "audienceScopes": [clean_text(scope) for scope in list(rule.get("audienceScopes") or []) if clean_text(scope)],
            "loadPath": load_path,
            "action": clean_text(rule.get("action")) or "load_on_demand",
        }
        selected_rules.append(selected)
        if load_path and load_path not in load_paths_seen:
            load_hints.append(
                {
                    "ruleId": selected["ruleId"],
                    "loadPath": load_path,
                    "reason": clean_text(rule.get("loadReason")) or selected["title"],
                }
            )
            load_paths_seen.add(load_path)

    return {
        "audienceProfile": audience_profile,
        "devGuidelineProfile": {
            "sourceName": clean_text(catalog.get("sourceName")) or DEV_GUIDELINE_SOURCE_NAME,
            "version": clean_text(catalog.get("version")) or DEV_GUIDELINE_VERSION,
            "catalogPath": clean_text(catalog.get("catalogPath")) or DEV_GUIDELINE_CATALOG_RELATIVE_PATH,
            "rulesRoot": clean_text(catalog.get("rulesRoot")),
            "sourceStatus": clean_text(catalog.get("sourceStatus")) or "converted_reference_required",
        },
        "devGuidelineRulesSelected": selected_rules,
        "devGuidelineLoadHints": load_hints,
        "devGuidelineGaps": gaps,
    }


def blocking_dev_guideline_gaps(dev_guideline_resolution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        gap
        for gap in list(dev_guideline_resolution.get("devGuidelineGaps") or [])
        if isinstance(gap, dict) and bool(gap.get("blocking"))
    ]
