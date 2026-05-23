from __future__ import annotations

import getpass
import json
import re
from typing import Any


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def flatten_contract_fields(fields: Any, *, prefix: str = "") -> list[dict[str, Any]]:
    if not isinstance(fields, list):
        return []
    flattened: list[dict[str, Any]] = []
    for item in fields:
        if not isinstance(item, dict):
            continue
        field_name = clean_text(item.get("fieldName"))
        if not field_name:
            continue
        data_type = clean_text(item.get("dataType")) or "unknown"
        is_collection = data_type.casefold() in {"list", "array"}
        path = f"{prefix}.{field_name}" if prefix else field_name
        flattened.append(
            {
                "path": path,
                "dataType": data_type,
                "required": bool(item.get("required")),
                "description": clean_text(item.get("description")),
                "notes": clean_text(item.get("notes")),
            }
        )
        child_prefix = f"{path}[]" if is_collection else path
        flattened.extend(flatten_contract_fields(item.get("properties"), prefix=child_prefix))
    return flattened


def normalize_backend_api_lines(raw_backend_apis: Any) -> list[str]:
    if not isinstance(raw_backend_apis, dict):
        return []
    lines: list[str] = []
    for system, targets in sorted(raw_backend_apis.items()):
        system_name = clean_text(system)
        if not system_name:
            continue
        if isinstance(targets, list):
            for target in targets:
                target_text = clean_text(target)
                if target_text:
                    lines.append(f"{system_name} -> {target_text}")
        elif clean_text(targets):
            lines.append(f"{system_name} -> {clean_text(targets)}")
    return lines


def build_handoff_identifier(prefix: str, raw_value: object, *, fallback: str = "item") -> str:
    normalized = clean_text(raw_value)
    slug = re.sub(r"[^a-z0-9]+", "_", normalized.casefold()).strip("_")
    return f"{prefix}_{slug or fallback}"


def summarize_snippet(value: object, *, fallback: str) -> str:
    text = clean_text(value)
    if not text:
        return fallback
    first_line = clean_text(text.split("\n", 1)[0])
    return first_line or fallback


def extract_symbol_candidates(value: object) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    symbols: list[str] = []
    for match in re.findall(r"[A-Za-z_][A-Za-z0-9_.]{2,}", text):
        if match not in symbols:
            symbols.append(match)
        if len(symbols) >= 8:
            break
    return symbols


def extract_parameter_hints(query_text: object) -> list[str]:
    text = clean_text(query_text)
    if not text:
        return []
    hints: list[str] = []
    for match in re.findall(r"@[A-Za-z0-9_]+", text):
        if match not in hints:
            hints.append(match)
    return hints


def synthesize_code_handoff(
    business_logic: dict[str, Any],
    *,
    request_fields: list[dict[str, Any]],
    response_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    response_paths = [field["path"] for field in response_fields if clean_text(field.get("path"))]
    request_paths = [field["path"] for field in request_fields if clean_text(field.get("path"))]
    business_steps = [step for step in list(business_logic.get("steps") or []) if isinstance(step, dict)]
    field_mappings = [mapping for mapping in list(business_logic.get("fieldMappings") or []) if isinstance(mapping, dict)]
    lookup_tables = [table for table in list(business_logic.get("lookupTables") or []) if isinstance(table, dict)]
    runtime_dependencies = [dependency for dependency in list(business_logic.get("runtimeDependencies") or []) if isinstance(dependency, dict)]
    data_sources = [source for source in list(business_logic.get("dataSources") or []) if isinstance(source, dict)]
    sql_specs = [spec for spec in list(business_logic.get("sqlSpecs") or []) if isinstance(spec, dict)]
    legacy_references = [reference for reference in list(business_logic.get("legacyReferences") or []) if isinstance(reference, dict)]
    prohibited_shortcuts = list(business_logic.get("prohibitedShortcuts") or [])
    error_code_rules = [rule for rule in list(business_logic.get("errorCodeRules") or []) if isinstance(rule, dict)]

    legacy_evidence: list[dict[str, Any]] = []
    seen_evidence_ids: set[str] = set()
    for reference in legacy_references:
        snippet = clean_text(reference.get("snippet"))
        if not snippet:
            continue
        evidence_id = clean_text(reference.get("id")) or build_handoff_identifier("legacy", reference.get("title"), fallback="reference")
        if evidence_id in seen_evidence_ids:
            continue
        legacy_evidence.append(
            {
                "evidenceId": evidence_id,
                "kind": clean_text(reference.get("kind")) or "legacyReference",
                "origin": clean_text(reference.get("origin") or reference.get("title")) or "legacy_reference",
                "authority": clean_text(reference.get("authority")) or "legacy_reference",
                "symbols": [symbol for symbol in list(reference.get("symbols") or []) if clean_text(symbol)],
                "summary": clean_text(reference.get("summary")) or summarize_snippet(snippet, fallback="legacy reference"),
                "snippet": snippet,
            }
        )
        seen_evidence_ids.add(evidence_id)
    for step in business_steps:
        title = clean_text(step.get("title"))
        details = clean_text(step.get("details"))
        if not details:
            continue
        if "舊代碼" not in title and "legacy" not in title.casefold() and "舊代碼" not in details:
            continue
        evidence_id = build_handoff_identifier("legacy", title or step.get("step"), fallback="step")
        if evidence_id in seen_evidence_ids:
            continue
        legacy_evidence.append(
            {
                "evidenceId": evidence_id,
                "kind": "legacyStep",
                "origin": title or f"step-{clean_text(step.get('step'))}",
                "authority": "legacy_step_detail",
                "symbols": extract_symbol_candidates(details),
                "summary": summarize_snippet(details, fallback=title or "legacy step"),
                "snippet": details,
            }
        )
        seen_evidence_ids.add(evidence_id)

    query_contracts: list[dict[str, Any]] = []
    for sql_spec in sql_specs:
        contract_id = clean_text(sql_spec.get("id")) or build_handoff_identifier("query", sql_spec.get("title"), fallback="contract")
        sql_text = clean_text(sql_spec.get("sqlText") or sql_spec.get("queryText"))
        if not contract_id or not sql_text:
            continue
        query_contracts.append(
            {
                "contractId": contract_id,
                "purpose": clean_text(sql_spec.get("title")) or contract_id,
                "dataSources": [clean_text(value) for value in list(sql_spec.get("dataSources") or []) if clean_text(value)],
                "mustContain": [clean_text(value) for value in list(sql_spec.get("mustContain") or []) if clean_text(value)],
                "sqlText": sql_text,
                "parameterHints": extract_parameter_hints(sql_text),
                "resultShape": response_paths,
                "evidenceIds": [],
            }
        )

    mapping_rules: list[dict[str, Any]] = []
    for mapping in field_mappings:
        fields = [field for field in list(mapping.get("fields") or []) if isinstance(field, dict)]
        if fields:
            for field in fields:
                target_field = clean_text(field.get("field"))
                source_field = clean_text(field.get("source") or mapping.get("source"))
                if not target_field or not source_field:
                    continue
                mapping_rules.append(
                    {
                        "ruleId": build_handoff_identifier("map", f"{source_field}_{target_field}", fallback="field"),
                        "sourceField": source_field,
                        "targetField": target_field,
                        "mappingType": "field_mapping",
                        "mappingTable": None,
                        "defaultValue": clean_text(field.get("rule") or mapping.get("rule")) or None,
                        "evidenceIds": [],
                    }
                )
        else:
            target_field = clean_text(mapping.get("target"))
            source_field = clean_text(mapping.get("source"))
            if not target_field or not source_field:
                continue
            mapping_rules.append(
                {
                    "ruleId": build_handoff_identifier("map", f"{source_field}_{target_field}", fallback="field"),
                    "sourceField": source_field,
                    "targetField": target_field,
                    "mappingType": "field_mapping",
                    "mappingTable": None,
                    "defaultValue": clean_text(mapping.get("rule")) or None,
                    "evidenceIds": [],
                }
            )
    for lookup_table in lookup_tables:
        source_field = clean_text(lookup_table.get("sourceField"))
        entries = [entry for entry in list(lookup_table.get("entries") or []) if isinstance(entry, dict)]
        target_fields = sorted(
            {
                clean_text(target_field)
                for entry in entries
                for target_field in (entry.get("mappedValues") or {}).keys()
                if clean_text(target_field)
            }
        )
        for target_field in target_fields:
            table_payload = {
                clean_text(entry.get("key")): clean_text((entry.get("mappedValues") or {}).get(target_field)) or None
                for entry in entries
                if clean_text(entry.get("key")) and clean_text((entry.get("mappedValues") or {}).get(target_field))
            }
            if not source_field or not target_field or not table_payload:
                continue
            mapping_rules.append(
                {
                    "ruleId": build_handoff_identifier("lookup", f"{lookup_table.get('id')}_{target_field}", fallback="table"),
                    "sourceField": source_field,
                    "targetField": target_field,
                    "mappingType": "lookup_table",
                    "mappingTable": table_payload,
                    "defaultValue": None,
                    "evidenceIds": [],
                }
            )

    dependency_hints: list[dict[str, Any]] = []
    for dependency in runtime_dependencies:
        dependency_id = clean_text(dependency.get("id"))
        preferred: list[str] = []
        lowered = dependency_id.casefold()
        if "sql" in lowered:
            preferred.append("ISqlQueryExecutor")
        if "runtime" in lowered or "context" in lowered or "cust" in lowered:
            preferred.append("ICurrentRuntimeContextAccessor")
            preferred.append("IRedisService")
        if "api" in lowered:
            preferred.append("IApiRequestService")
        if not preferred:
            preferred.append("FrameworkProvidedDependency")
        dependency_hints.append(
            {
                "dependencyType": clean_text(dependency.get("type")) or dependency_id or "dependency",
                "preferredAbstractions": preferred,
                "purpose": clean_text(dependency.get("description")) or dependency_id or "dependency",
                "evidenceIds": [],
            }
        )
    for source in data_sources:
        source_name = clean_text(source.get("name"))
        source_type = clean_text(source.get("type")) or "data_source"
        if not source_name:
            continue
        dependency_hints.append(
            {
                "dependencyType": source_type,
                "preferredAbstractions": ["ISqlQueryExecutor"] if "sql" in source_type.casefold() else ["FrameworkProvidedDependency"],
                "purpose": f"Read from {source_name}",
                "evidenceIds": [],
            }
        )

    constraints: list[dict[str, Any]] = []
    for shortcut in prohibited_shortcuts:
        rule = clean_text(shortcut if isinstance(shortcut, str) else json.dumps(shortcut, ensure_ascii=False, sort_keys=True))
        if not rule:
            continue
        constraints.append(
            {
                "constraintType": "prohibited_shortcut",
                "rule": rule,
                "severity": "error",
                "evidenceIds": [],
            }
        )
    for error_rule in error_code_rules:
        code = clean_text(error_rule.get("code"))
        scenario = clean_text(error_rule.get("scenario"))
        message = clean_text(error_rule.get("message"))
        if not code:
            continue
        constraints.append(
            {
                "constraintType": "error_code_rule",
                "rule": f"{code} | {scenario or 'n/a'} | {message or 'n/a'}",
                "severity": "warning",
                "evidenceIds": [],
            }
        )

    unresolved: list[dict[str, Any]] = []
    if any(("舊代碼" in clean_text(step.get("title")) or "legacy" in clean_text(step.get("title")).casefold()) for step in business_steps) and not legacy_evidence:
        unresolved.append(
            {
                "topic": "legacy_logic",
                "reason": "Detected legacy-reference prose, but no structured legacy evidence snippet could be synthesized.",
                "blocking": True,
            }
        )

    logic_flow: list[dict[str, Any]] = []
    for index, step in enumerate(business_steps, start=1):
        title = clean_text(step.get("title")) or f"step-{index}"
        details = clean_text(step.get("details"))
        lowered = f"{title} {details}".casefold()
        if "sql" in lowered or "查詢" in lowered or "query" in lowered:
            action_type = "query"
        elif "mapping" in lowered or "轉" in lowered or "對應" in lowered:
            action_type = "mapping"
        elif "回傳" in lowered or "return" in lowered or "response" in lowered:
            action_type = "return"
        elif "驗證" in lowered or "validate" in lowered:
            action_type = "validation"
        elif "舊代碼" in lowered or "legacy" in lowered:
            action_type = "legacy_reference"
        else:
            action_type = "process"
        logic_flow.append(
            {
                "stepId": f"step_{clean_text(step.get('step')) or index}",
                "title": title,
                "actionType": action_type,
                "inputs": request_paths[:4],
                "outputs": response_paths[:4],
                "evidenceIds": [entry["evidenceId"] for entry in legacy_evidence] if action_type == "legacy_reference" else [],
            }
        )

    return {
        "schemaVersion": "1.0.0",
        "logicSummary": {
            "stepCount": len(logic_flow),
            "queryContractCount": len(query_contracts),
            "mappingRuleCount": len(mapping_rules),
            "legacyEvidenceCount": len(legacy_evidence),
            "dependencyHintCount": len(dependency_hints),
            "constraintCount": len(constraints),
            "unresolvedCount": len(unresolved),
            "primarySource": "businessLogic_compat",
        },
        "logicFlow": logic_flow,
        "legacyEvidence": legacy_evidence,
        "queryContracts": query_contracts,
        "mappingRules": mapping_rules,
        "dependencyHints": dependency_hints,
        "constraints": constraints,
        "unresolved": unresolved,
    }


def normalize_or_synthesize_code_handoff(
    api_spec: dict[str, Any],
    business_logic: dict[str, Any],
    *,
    request_fields: list[dict[str, Any]],
    response_fields: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    raw_handoff = api_spec.get("codeHandoff")
    if isinstance(raw_handoff, dict):
        handoff = {
            "schemaVersion": clean_text(raw_handoff.get("schemaVersion")) or "1.0.0",
            "logicSummary": raw_handoff.get("logicSummary") if isinstance(raw_handoff.get("logicSummary"), dict) else {},
            "logicFlow": [item for item in list(raw_handoff.get("logicFlow") or []) if isinstance(item, dict)],
            "legacyEvidence": [item for item in list(raw_handoff.get("legacyEvidence") or []) if isinstance(item, dict)],
            "queryContracts": [item for item in list(raw_handoff.get("queryContracts") or []) if isinstance(item, dict)],
            "mappingRules": [item for item in list(raw_handoff.get("mappingRules") or []) if isinstance(item, dict)],
            "dependencyHints": [item for item in list(raw_handoff.get("dependencyHints") or []) if isinstance(item, dict)],
            "constraints": [item for item in list(raw_handoff.get("constraints") or []) if isinstance(item, dict)],
            "unresolved": [item for item in list(raw_handoff.get("unresolved") or []) if isinstance(item, dict)],
        }
        return handoff, "codeHandoff"
    return synthesize_code_handoff(business_logic, request_fields=request_fields, response_fields=response_fields), "businessLogic_compat"


def normalize_upstream_model(upstream_api: Any) -> dict[str, Any]:
    api_spec = upstream_api.api_spec_payload or {}
    business_logic = api_spec.get("businessLogic")
    if not isinstance(business_logic, dict):
        business_logic = {}
    request_fields = flatten_contract_fields(api_spec.get("request"))
    response_fields = flatten_contract_fields(api_spec.get("response"))
    code_handoff, handoff_source = normalize_or_synthesize_code_handoff(
        api_spec,
        business_logic,
        request_fields=request_fields,
        response_fields=response_fields,
    )
    steps = list(business_logic.get("steps") or [])
    field_mappings = list(business_logic.get("fieldMappings") or [])
    error_codes = list(business_logic.get("errorCodeRules") or [])
    runtime_dependencies = list(business_logic.get("runtimeDependencies") or [])
    reference_hints = list(business_logic.get("referenceHints") or [])
    backend_api_lines = normalize_backend_api_lines(api_spec.get("backendApis"))
    mock_examples = [entry for entry in list(api_spec.get("mockExamples") or []) if isinstance(entry, dict)]
    return {
        "apiId": upstream_api.api_id,
        "apiCategory": upstream_api.api_category,
        "apiName": upstream_api.api_name,
        "newAuthor": clean_text(api_spec.get("newAuthor")) or getpass.getuser(),
        "source": api_spec.get("source") or upstream_api.manifest_payload.get("specSource") or upstream_api.manifest_payload.get("source") or {},
        "requestFields": request_fields,
        "responseFields": response_fields,
        "businessSteps": [step for step in steps if isinstance(step, dict)],
        "fieldMappings": [mapping for mapping in field_mappings if isinstance(mapping, dict)],
        "errorCodes": [rule for rule in error_codes if isinstance(rule, dict)],
        "runtimeDependencies": [dependency for dependency in runtime_dependencies if isinstance(dependency, dict)],
        "referenceHints": [hint for hint in reference_hints if isinstance(hint, dict)],
        "backendApis": backend_api_lines,
        "mockExamples": mock_examples,
        "codeHandoff": code_handoff,
        "handoffSource": handoff_source,
        "logicSummary": code_handoff.get("logicSummary") if isinstance(code_handoff.get("logicSummary"), dict) else {},
        "logicFlow": [entry for entry in list(code_handoff.get("logicFlow") or []) if isinstance(entry, dict)],
        "legacyEvidence": [entry for entry in list(code_handoff.get("legacyEvidence") or []) if isinstance(entry, dict)],
        "queryContracts": [entry for entry in list(code_handoff.get("queryContracts") or []) if isinstance(entry, dict)],
        "mappingRules": [entry for entry in list(code_handoff.get("mappingRules") or []) if isinstance(entry, dict)],
        "dependencyHints": [entry for entry in list(code_handoff.get("dependencyHints") or []) if isinstance(entry, dict)],
        "constraints": [entry for entry in list(code_handoff.get("constraints") or []) if isinstance(entry, dict)],
        "unresolvedLogic": [entry for entry in list(code_handoff.get("unresolved") or []) if isinstance(entry, dict)],
    }
