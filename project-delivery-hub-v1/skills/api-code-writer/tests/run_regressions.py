#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
WRITE_API_CODE = SKILL_DIR / "scripts" / "write_api_code.py"
CONVERT_DEV_GUIDELINES = SKILL_DIR / "scripts" / "convert_dev_guidelines.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def minimal_csproj(root_namespace: str | None = None) -> str:
    lines = ["<Project Sdk=\"Microsoft.NET.Sdk\">", "  <PropertyGroup>"]
    if root_namespace:
        lines.append(f"    <RootNamespace>{root_namespace}</RootNamespace>")
    lines.extend(["    <TargetFramework>net10.0</TargetFramework>", "  </PropertyGroup>", "</Project>", ""])
    return "\n".join(lines)


def fake_dotnet_script() -> str:
    return "\n".join(
        [
            "@echo off",
            "if not \"%DOTNET_LOG%\"==\"\" echo %*>>\"%DOTNET_LOG%\"",
            "if not \"%DOTNET_STDERR%\"==\"\" echo %DOTNET_STDERR% 1>&2",
            "if \"%DOTNET_EXIT_CODE%\"==\"\" exit /b 0",
            "exit /b %DOTNET_EXIT_CODE%",
            "",
        ]
    )


def default_business_logic(api_id: str, response: list[dict]) -> dict:
    primary_response_field = response[0]["fieldName"] if response else "result"
    mapping_rule = {
        "target": primary_response_field,
        "source": f"legacyResult.{primary_response_field}",
        "rule": "map_direct",
        "fields": [
            {
                "field": primary_response_field,
                "source": f"legacyResult.{primary_response_field}",
                "rule": "map_direct",
            }
        ],
    }
    if api_id == "N.006.setting.queryuserloginlog":
        return {
            "steps": [
                {"step": "1", "title": "初始化與參數處理", "details": "從執行上下文取得 CustId 與 keyId。"},
                {"step": "2", "title": "查詢登入記錄", "details": "依 CustId 查詢 USER_LOGIN_LOG 並組裝登入方式。"},
                {"step": "3", "title": "參考舊代碼邏輯", "details": "var rows = QueryUserLoginLog(custId); loginWay = MapLoginWay(rows.LOGIN_WAY);"},
            ],
            "fieldMappings": [
                {
                    "target": "loginLogs",
                    "source": "loginRows",
                    "rule": "map_login_logs",
                    "fields": [
                        {"field": "loginTime", "source": "loginRows.LOGIN_TIME", "rule": "datetime_to_string"},
                        {"field": "loginStatus", "source": "loginRows.LOGIN_STATUS", "rule": "pass_through"},
                    ],
                }
            ],
            "lookupTables": [
                {
                    "id": "login_way_lookup",
                    "sourceField": "LOGIN_WAY",
                    "description": "轉換登入方式顯示名稱",
                    "entries": [
                        {"key": "1", "title": "網銀", "mappedValues": {"loginWay": "網銀"}, "rule": "lookup"},
                        {"key": "2", "title": "行銀", "mappedValues": {"loginWay": "行銀"}, "rule": "lookup"},
                    ],
                }
            ],
            "errorCodeRules": [{"code": "0000", "scenario": "success", "message": "成功"}],
            "runtimeDependencies": [
                {"id": "current_customer_context", "type": "service", "description": "取得當前客戶上下文"},
                {"id": "mma_sql_connection", "type": "service", "description": "查詢 MMA 登入記錄"},
            ],
            "dataSources": [{"name": "USER_LOGIN_LOG", "type": "sql_table", "authority": "backend_contract", "required": True}],
            "sqlSpecs": [
                {
                    "id": "query_login_logs",
                    "title": "查詢登入記錄 SQL",
                    "authority": "backend_contract",
                    "required": True,
                    "dataSources": ["USER_LOGIN_LOG", "J_COUNTRY"],
                    "mustContain": ["USER_LOGIN_LOG", "@CustId", "TOP 10", "ORDER BY"],
                    "queryText": "SELECT TOP 10 * FROM USER_LOGIN_LOG WHERE CUST_ID = @CustId ORDER BY LOGIN_TIME DESC",
                }
            ],
            "legacyReferences": [
                {
                    "id": "legacy_query_user_login_log",
                    "title": "參考舊代碼邏輯",
                    "kind": "legacyReference",
                    "origin": "Legacy ProfileService",
                    "authority": "legacy_reference",
                    "summary": "依 CustId 查詢登入記錄並轉換登入方式。",
                    "snippet": "var rows = QueryUserLoginLog(custId); loginWay = MapLoginWay(rows.LOGIN_WAY);",
                    "symbols": ["QueryUserLoginLog", "MapLoginWay"],
                    "nonAuthoritative": True,
                }
            ],
            "prohibitedShortcuts": ["mock_response_payload", "hardcoded_custid"],
            "referenceHints": [
                {
                    "id": "project-framework",
                    "category": "dev_guideline",
                    "matchSource": "framework_keyword",
                    "matchKey": "EnterpriseAPI",
                    "title": "新大戶框架説明 V2.0 20260203",
                    "relativePath": ".agent/Reference/raw/dev-guidelines/新大戶框架説明 V2.0 20260203.docx",
                    "locator": {"sectionTitle": "框架説明"},
                    "reason": "Use EnterpriseAPI slot rules first.",
                    "authority": "reference_imported",
                }
            ],
        }
    return {
        "steps": [{"step": "1", "title": "初始化與參數處理", "details": "整理輸入並呼叫模組服務。"}],
        "fieldMappings": [mapping_rule],
        "lookupTables": [],
        "errorCodeRules": [{"code": "0000", "scenario": "success", "message": "成功"}],
        "runtimeDependencies": [{"id": "current_customer_context", "description": "取得當前客戶上下文"}],
        "dataSources": [],
        "sqlSpecs": [],
        "legacyReferences": [],
        "prohibitedShortcuts": [],
        "referenceHints": [
            {
                "id": "project-framework",
                "category": "dev_guideline",
                "matchSource": "framework_keyword",
                "matchKey": "EnterpriseAPI",
                "title": "新大戶框架説明 V2.0 20260203",
                "relativePath": ".agent/Reference/raw/dev-guidelines/新大戶框架説明 V2.0 20260203.docx",
                "locator": {"sectionTitle": "框架説明"},
                "reason": "Use EnterpriseAPI slot rules first.",
                "authority": "reference_imported",
            }
        ],
    }


def default_code_handoff(api_id: str, request: list[dict], response: list[dict], business_logic: dict) -> dict:
    response_paths = []
    for field in response:
        field_name = field.get("fieldName")
        if field_name:
            response_paths.append(field_name)
        for child in field.get("properties") or []:
            if child.get("fieldName"):
                response_paths.append(child["fieldName"])
    if api_id == "N.006.setting.queryuserloginlog":
        return {
            "schemaVersion": "1.0.0",
            "logicSummary": {
                "stepCount": 3,
                "queryContractCount": 1,
                "mappingRuleCount": 3,
                "legacyEvidenceCount": 1,
                "dependencyHintCount": 2,
                "constraintCount": 3,
                "unresolvedCount": 0,
                "primarySource": "businessLogic",
            },
            "logicFlow": [
                {"stepId": "step_1", "title": "初始化與參數處理", "actionType": "process", "inputs": ["custId"], "outputs": ["custId"], "evidenceIds": []},
                {"stepId": "step_2", "title": "查詢登入記錄", "actionType": "query", "inputs": ["custId"], "outputs": response_paths, "evidenceIds": []},
                {"stepId": "step_3", "title": "參考舊代碼邏輯", "actionType": "legacy_reference", "inputs": ["custId"], "outputs": response_paths, "evidenceIds": ["legacy_query_user_login_log"]},
            ],
            "legacyEvidence": [
                {
                    "evidenceId": "legacy_query_user_login_log",
                    "kind": "legacyReference",
                    "origin": "Legacy ProfileService",
                    "authority": "legacy_reference",
                    "symbols": ["QueryUserLoginLog", "MapLoginWay"],
                    "summary": "依 CustId 查詢登入記錄並轉換登入方式。",
                    "snippet": "var rows = QueryUserLoginLog(custId); loginWay = MapLoginWay(rows.LOGIN_WAY);",
                }
            ],
            "queryContracts": [
                {
                    "contractId": "query_login_logs",
                    "purpose": "查詢登入記錄 SQL",
                    "dataSources": ["USER_LOGIN_LOG", "J_COUNTRY"],
                    "mustContain": ["USER_LOGIN_LOG", "@CustId", "TOP 10", "ORDER BY"],
                    "sqlText": "SELECT TOP 10 * FROM USER_LOGIN_LOG WHERE CUST_ID = @CustId ORDER BY LOGIN_TIME DESC",
                    "parameterHints": ["@CustId"],
                    "resultShape": response_paths,
                    "evidenceIds": ["legacy_query_user_login_log"],
                }
            ],
            "mappingRules": [
                {
                    "ruleId": "map_login_time",
                    "sourceField": "loginRows.LOGIN_TIME",
                    "targetField": "loginTime",
                    "mappingType": "field_mapping",
                    "mappingTable": None,
                    "defaultValue": "datetime_to_string",
                    "evidenceIds": [],
                },
                {
                    "ruleId": "map_login_status",
                    "sourceField": "loginRows.LOGIN_STATUS",
                    "targetField": "loginStatus",
                    "mappingType": "field_mapping",
                    "mappingTable": None,
                    "defaultValue": "pass_through",
                    "evidenceIds": [],
                },
                {
                    "ruleId": "lookup_login_way",
                    "sourceField": "LOGIN_WAY",
                    "targetField": "loginWay",
                    "mappingType": "lookup_table",
                    "mappingTable": {"1": "網銀", "2": "行銀"},
                    "defaultValue": None,
                    "evidenceIds": ["legacy_query_user_login_log"],
                },
            ],
            "dependencyHints": [
                {"dependencyType": "service", "preferredAbstractions": ["ICurrentRuntimeContextAccessor", "IRedisService"], "purpose": "取得當前客戶上下文", "evidenceIds": []},
                {"dependencyType": "service", "preferredAbstractions": ["ISqlQueryExecutor"], "purpose": "查詢 MMA 登入記錄", "evidenceIds": []},
            ],
            "constraints": [
                {"constraintType": "prohibited_shortcut", "rule": "mock_response_payload", "severity": "error", "evidenceIds": []},
                {"constraintType": "prohibited_shortcut", "rule": "hardcoded_custid", "severity": "error", "evidenceIds": []},
                {"constraintType": "error_code_rule", "rule": "0000 | success | 成功", "severity": "warning", "evidenceIds": []},
            ],
            "unresolved": [],
        }
    constraints = [{"constraintType": "error_code_rule", "rule": "0000 | success | 成功", "severity": "warning", "evidenceIds": []}]
    for field in request:
        field_name = field.get("fieldName")
        if not field_name or not field.get("required"):
            continue
        constraints.append(
            {
                "constraintType": "request_field_validation",
                "rule": f"{field_name} | required",
                "field": field_name,
                "validationLayer": "dto_attribute",
                "validationType": "required",
                "expectedCode": "9999",
                "expectedMessage": f"請輸入{field_name}",
                "customValidationAttributeNeeded": False,
                "severity": "error",
                "evidenceIds": [],
            }
        )
    return {
        "schemaVersion": "1.0.0",
        "logicSummary": {
            "stepCount": len(business_logic.get("steps") or []),
            "queryContractCount": 0,
            "mappingRuleCount": 1,
            "legacyEvidenceCount": 0,
            "dependencyHintCount": 1,
            "constraintCount": 1,
            "unresolvedCount": 0,
            "primarySource": "businessLogic",
        },
        "logicFlow": [{"stepId": "step_1", "title": "初始化與參數處理", "actionType": "process", "inputs": [], "outputs": response_paths, "evidenceIds": []}],
        "legacyEvidence": [],
        "queryContracts": [],
        "mappingRules": [
            {
                "ruleId": "map_primary_field",
                "sourceField": f"legacyResult.{response[0]['fieldName']}" if response else "legacyResult.value",
                "targetField": response[0]["fieldName"] if response else "result",
                "mappingType": "field_mapping",
                "mappingTable": None,
                "defaultValue": "map_direct",
                "evidenceIds": [],
            }
        ],
        "dependencyHints": [{"dependencyType": "service", "preferredAbstractions": ["ICurrentRuntimeContextAccessor"], "purpose": "取得當前客戶上下文", "evidenceIds": []}],
        "constraints": constraints,
        "unresolved": [],
    }


def build_api_spec(
    *,
    api_id: str,
    function_code: str,
    version: str,
    api_category: str,
    api_name: str,
    request: list[dict],
    response: list[dict],
    schema_version: str = "4.3.0",
    include_code_handoff: bool = True,
    business_logic_override: dict | None = None,
    code_handoff_override: dict | None = None,
    mock_examples: list[dict] | None = None,
) -> dict:
    business_logic = business_logic_override or default_business_logic(api_id, response)
    return {
        "schemaVersion": schema_version,
        "apiId": api_id,
        "newAuthor": "Regression",
        "functionCode": function_code,
        "version": version,
        "apiCategory": api_category,
        "apiName": api_name,
        "source": {
            "tsdFile": f".agent/TSD/TSD.{function_code}.docx",
            "workbookFile": ".agent/API Spec/NEWDA_API_DETAIL.xlsx",
            "sheetNames": [api_category],
        },
        "request": request,
        "response": response,
        "mockExamples": mock_examples if mock_examples is not None else [{"scenario": "happy-path"}],
        "backendApis": {},
        "businessLogic": business_logic,
        **({"codeHandoff": (code_handoff_override or default_code_handoff(api_id, request, response, business_logic))} if include_code_handoff else {}),
    }


def build_manifest(function_code: str, api_id: str, api_category: str, api_name: str, api_spec_rel: str) -> dict:
    return {
        "schemaVersion": "4.1.0",
        "manifestType": "api",
        "executionId": function_code,
        "apiId": api_id,
        "apiCategory": api_category,
        "apiName": api_name,
        "status": "pending",
        "phase": "pending",
        "updatedAt": "2026-04-09T12:00:00+08:00",
        "newAuthor": "Regression",
        "specStatus": "done",
        "specUpdatedAt": "2026-04-09T12:00:00+08:00",
        "specBlockReason": None,
        "specSourceFingerprint": f"sha256:{function_code.lower()}-fingerprint",
        "specSource": {
            "tsdFile": f".agent/TSD/TSD.{function_code}.docx",
            "workbookFile": ".agent/API Spec/NEWDA_API_DETAIL.xlsx",
            "sheetNames": [api_category],
        },
        "specArtifacts": {"apiSpec": api_spec_rel},
        "codeStatus": "pending",
        "codePhase": "pending",
        "codeUpdatedAt": None,
        "codeBlockReason": None,
        "codeProjectRoot": None,
        "codeSolutionPath": None,
        "inputHashes": {},
        "modifiedFiles": [],
        "validationChecks": [],
        "validationResults": [],
        "repoDriftFiles": [],
        "codeArtifacts": {
            "changePlan": None,
            "implementationReport": None,
            "diagnosisReport": None,
        },
        "lastMessage": None,
    }


def build_review_notes(api_id: str) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "apiId": api_id,
        "sourceDoc": ".agent/Reference/reviews/N.006-review.docx",
        "language": "zh-Hant",
        "items": [
            {
                "reviewId": "naming_external_api",
                "scope": "api_behavior",
                "fileRole": "shared",
                "ruleType": "naming",
                "instruction": "對外 API 名稱不得追加 Async；route、change-plan 顯示名與需求文件名稱必須一致。",
                "severity": "error",
                "blocking": True,
                "appliesTo": ["apiName"],
                "examples": ["QueryUserLoginLog"],
            },
            {
                "reviewId": "contract_type_match",
                "scope": "api_behavior",
                "fileRole": "entity",
                "ruleType": "contract_type",
                "instruction": "欄位類型必須與 spec 一致。",
                "severity": "error",
                "blocking": True,
                "appliesTo": ["response.loginLogs[].loginTime", "response.loginLogs[].loginStatus"],
                "examples": [],
            },
            {
                "reviewId": "response_dt_after_mapping",
                "scope": "service",
                "fileRole": "service",
                "ruleType": "response_lifecycle",
                "instruction": "responseDT 應在查詢與資料映射完成後再賦值，不得在 TransactionResult<T> 預設建構時提早記錄。",
                "severity": "error",
                "blocking": True,
                "appliesTo": ["TransactionResult.responseDT"],
                "examples": [],
            },
            {
                "reviewId": "failure_response_data_null",
                "scope": "service",
                "fileRole": "service",
                "ruleType": "failure_payload",
                "instruction": "失敗時 responseData 必須回傳 null，不是空的實體類。",
                "severity": "error",
                "blocking": True,
                "appliesTo": ["TransactionResult.responseData"],
                "examples": [],
            },
        ],
    }


def create_project_rules_fixture(workspace_root: Path) -> None:
    rules_root = workspace_root / ".agent" / "project-rules" / "default"
    dump_json(
        rules_root / "catalog.json",
        {
            "schemaVersion": "1.0.0",
            "workspaceKey": "default",
            "defaults": {
                "codeGuidelineCatalog": "rules/code-guidelines/catalog.json",
            },
        },
    )
    dump_json(
        rules_root / "rules" / "code-guidelines" / "catalog.json",
        {
            "schemaVersion": "1.0.0",
            "sourceName": "Regression project code guidelines",
            "version": "fixture",
            "sourceStatus": "approved",
            "rules": [
                {
                    "ruleId": "common-style",
                    "title": "共同落碼風格",
                    "category": "common-style",
                    "direction": "production-code",
                    "ruleType": "style_only",
                    "audienceScopes": ["frontstage", "midBackoffice", "shared", "unknown"],
                    "featureTriggers": ["always"],
                    "loadPath": "rules/code-guidelines/common-style.md",
                    "action": "load_on_demand",
                },
                {
                    "ruleId": "data-access",
                    "title": "DB / SQL 規範",
                    "category": "data-access",
                    "direction": "production-code",
                    "ruleType": "blocking_gap",
                    "audienceScopes": ["frontstage", "midBackoffice", "shared", "unknown"],
                    "featureTriggers": ["hasSql"],
                    "loadPath": "rules/code-guidelines/data-access.md",
                    "action": "select_and_check_gaps",
                },
                {
                    "ruleId": "frontstage-session",
                    "title": "前台 Session 規範",
                    "category": "identity-session",
                    "direction": "production-code",
                    "ruleType": "blocking_gap",
                    "audienceScopes": ["frontstage"],
                    "featureTriggers": ["hasIdentity", "hasCache"],
                    "loadPath": "rules/code-guidelines/frontstage-session.md",
                    "action": "select_and_check_gaps",
                },
                {
                    "ruleId": "backoffice-authz",
                    "title": "中後台權限規範",
                    "category": "authorization-audit",
                    "direction": "production-code",
                    "ruleType": "blocking_gap",
                    "audienceScopes": ["midBackoffice"],
                    "featureTriggers": ["hasAuditOrAuthorization"],
                    "loadPath": "rules/code-guidelines/backoffice-authz.md",
                    "action": "select_and_check_gaps",
                },
                {
                    "ruleId": "test-handoff",
                    "title": "第 05 步測試交接規範",
                    "category": "test-handoff",
                    "direction": "handoff-only",
                    "ruleType": "handoff_only",
                    "audienceScopes": ["frontstage", "midBackoffice", "shared", "unknown"],
                    "featureTriggers": ["hasTestHandoff", "hasSql"],
                    "loadPath": "rules/code-guidelines/test-handoff.md",
                    "action": "handoff_only",
                },
            ],
        },
    )


def create_base_repo(repo_root: Path) -> None:
    write_text(repo_root / "Sinopac.DawhoEnterprise.sln", "Microsoft Visual Studio Solution File, Format Version 12.00\n")
    write_text(
        repo_root / "API" / "EnterpriseAPI" / "EnterpriseAPI" / "EnterpriseAPI.csproj",
        minimal_csproj("Sinopac.DawhoEnterprise.API.EnterpriseAPI.EnterpriseAPI"),
    )
    write_text(
        repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness.Interface" / "EnterpriseApiBusiness.Interface.csproj",
        minimal_csproj("Sinopac.DawhoEnterprise.BusinessLogicLayout.EnterpriseApi.EnterpriseApiBusiness.Interface"),
    )
    write_text(
        repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "EnterpriseApiBusiness.csproj",
        minimal_csproj("Sinopac.DawhoEnterprise.BusinessLogicLayout.EnterpriseApi.EnterpriseApiBusiness"),
    )
    write_text(
        repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiEntity" / "EnterpriseApiEntity.csproj",
        minimal_csproj("Sinopac.DawhoEnterprise.BusinessLogicLayout.EnterpriseApi.EnterpriseApiEntity"),
    )
    write_text(
        repo_root / "Test" / "UnitTesting" / "EnterpriseAPI" / "EnterpriseApiUnit" / "EnterpriseAPIUnit.csproj",
        minimal_csproj("Sinopac.DawhoEnterprise.Test.UnitTesting.EnterpriseAPI.EnterpriseApiUnit"),
    )
    write_text(
        repo_root / "Test" / "IntegrationTesting" / "EnterpriseAPI" / "EnterpriseApiIntegration" / "EnterpriseAPIIntegration.csproj",
        minimal_csproj("Sinopac.DawhoEnterprise.Test.IntegrationTesting.EnterpriseAPI.EnterpriseApiIntegration"),
    )
    write_text(
        repo_root / "Libray" / "Common" / "CommonStatic" / "ProgramExtensions.cs",
        "\n".join(
            [
                "namespace Sinopac.DawhoEnterprise.Libray.Common.CommonStatic;",
                "",
                "public static class ProgramExtensions",
                "{",
                "    public static void AddBusinessScoped(this object builder)",
                "    {",
                "    }",
                "}",
                "",
            ]
        ),
    )


def create_p240301git_repo(project_root: Path) -> None:
    enterprise_root = project_root / "Sinopac.EnterpriseAPI"
    write_text(
        enterprise_root / "Sinopac.EnterpriseAPI.slnx",
        "\n".join(
            [
                "<Solution>",
                "  <Project Path=\"EnterpriseApiBusiness.Interface\\EnterpriseApiBusiness.Interface.csproj\" />",
                "  <Project Path=\"EnterpriseApiBusiness\\EnterpriseApiBusiness.csproj\" />",
                "  <Project Path=\"EnterpriseApiEntity\\EnterpriseApiEntity.csproj\" />",
                "  <Project Path=\"..\\Libray\\Sinopac.CommonFunc\\Sinopac.CommonFunc.csproj\" />",
                "  <Project Path=\"Sinopac.EnterpriseAPI\\Sinopac.EnterpriseAPI.csproj\" />",
                "</Solution>",
                "",
            ]
        ),
    )
    write_text(
        enterprise_root / "Sinopac.EnterpriseAPI" / "Sinopac.EnterpriseAPI.csproj",
        minimal_csproj("Sinopac.EnterpriseAPI"),
    )
    write_text(
        enterprise_root / "Sinopac.EnterpriseAPI" / "ProgramExtensions.cs",
        "\n".join(
            [
                "namespace Sinopac.EnterpriseAPI;",
                "",
                "public static class ProgramExtensions",
                "{",
                "    public static void AddBusinessScoped(this object builder)",
                "    {",
                "    }",
                "}",
                "",
            ]
        ),
    )
    write_text(
        enterprise_root / "EnterpriseApiBusiness.Interface" / "EnterpriseApiBusiness.Interface.csproj",
        minimal_csproj("EnterpriseApiBusiness.Interface"),
    )
    write_text(
        enterprise_root / "EnterpriseApiBusiness" / "EnterpriseApiBusiness.csproj",
        minimal_csproj("EnterpriseApiBusiness"),
    )
    write_text(
        enterprise_root / "EnterpriseApiEntity" / "EnterpriseApiEntity.csproj",
        minimal_csproj("EnterpriseApiEntity"),
    )
    write_text(
        enterprise_root / "Test" / "EnterpriseApi.Unit" / "EnterpriseApi.Unit.csproj",
        minimal_csproj("EnterpriseApi.Unit"),
    )
    write_text(
        enterprise_root / "Test" / "EnterpriseApi.Integration" / "EnterpriseApi.Integration.csproj",
        minimal_csproj("EnterpriseApi.Integration"),
    )

    common_func_root = project_root / "Libray" / "Sinopac.CommonFunc"
    write_text(common_func_root / "Sinopac.CommonFunc.csproj", minimal_csproj("Sinopac.CommonFunc"))
    write_text(
        common_func_root / "IFuncService" / "ICommonFuncService.cs",
        "\n".join(
            [
                "namespace Sinopac.CommonFunc;",
                "",
                "public interface ICommonFuncService",
                "{",
                "}",
                "",
            ]
        ),
    )
    write_text(
        common_func_root / "FuncService" / "CommonFuncService.cs",
        "\n".join(
            [
                "namespace Sinopac.CommonFunc;",
                "",
                "public partial class CommonFuncService : ICommonFuncService",
                "{",
                "}",
                "",
            ]
        ),
    )
    write_text(common_func_root / "Dto" / ".gitkeep", "")
    write_text(common_func_root / "ResponseCodes" / "O_Common.resx", "<root />\n")
    write_text(common_func_root / "ResponseCodes" / "O_Common.Designer.cs", "namespace Sinopac.CommonFunc.ResponseCodes;\n")


def create_existing_deposit_module(repo_root: Path) -> None:
    controller_path = repo_root / "API" / "EnterpriseAPI" / "EnterpriseAPI" / "Controllers" / "DepositController.cs"
    interface_path = repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness.Interface" / "IDepositService.cs"
    service_path = repo_root / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "Deposit" / "DepositService.cs"
    write_text(
        controller_path,
        "\n".join(
            [
                "using Asp.Versioning;",
                "using Microsoft.AspNetCore.Mvc;",
                "using Microsoft.Extensions.Logging;",
                "using Sinopac.DawhoEnterprise.BusinessLogicLayout.EnterpriseApi.EnterpriseApiBusiness.Interface;",
                "",
                "namespace Sinopac.DawhoEnterprise.API.EnterpriseAPI.EnterpriseAPI.Controllers;",
                "",
                "[ApiVersion(\"1.0\")]",
                "[Route(\"api/v{version:apiVersion}/[controller]\")]",
                "public class DepositController(ILogger<DepositController> logger, IDepositService depositService) : ControllerBase",
                "{",
                "    private readonly ILogger<DepositController> _logger = logger ?? throw new ArgumentNullException(nameof(logger));",
                "    private readonly IDepositService _depositService = depositService ?? throw new ArgumentNullException(nameof(depositService));",
                "}",
                "",
            ]
        ),
    )
    write_text(
        interface_path,
        "\n".join(
            [
                "namespace Sinopac.DawhoEnterprise.BusinessLogicLayout.EnterpriseApi.EnterpriseApiBusiness.Interface;",
                "",
                "public interface IDepositService",
                "{",
                "}",
                "",
            ]
        ),
    )
    write_text(
        service_path,
        "\n".join(
            [
                "namespace Sinopac.DawhoEnterprise.BusinessLogicLayout.EnterpriseApi.EnterpriseApiBusiness.Deposit;",
                "",
                "public class DepositService : Sinopac.DawhoEnterprise.BusinessLogicLayout.EnterpriseApi.EnterpriseApiBusiness.Interface.IDepositService",
                "{",
                "}",
                "",
            ]
        ),
    )


def create_execution(
    workspace_root: Path,
    *,
    function_code: str,
    api_id: str,
    api_category: str,
    api_name: str,
    version: str,
    request: list[dict],
    response: list[dict],
    review_notes: dict | None = None,
    mock_examples: list[dict] | None = None,
    code_handoff_override: dict | None = None,
) -> dict[str, Path]:
    context_root = workspace_root / ".agent" / "context"
    execution_root = context_root / function_code
    api_root = execution_root / "apis" / api_id
    api_spec_name = f"{function_code}_API_Spec.json"
    api_spec_path = api_root / api_spec_name
    api_spec_rel = f".agent/context/{function_code}/apis/{api_id}/{api_spec_name}"

    dump_json(
        api_spec_path,
        build_api_spec(
            api_id=api_id,
            function_code=function_code,
            version=version,
            api_category=api_category,
            api_name=api_name,
            request=request,
            response=response,
            mock_examples=mock_examples,
            code_handoff_override=code_handoff_override,
        ),
    )
    dump_json(api_root / "manifest.json", build_manifest(function_code, api_id, api_category, api_name, api_spec_rel))
    dump_json(
        execution_root / "api-checklist.json",
        {
            "schemaVersion": "4.1.0",
            "executionId": function_code,
            "updatedAt": "2026-04-09T12:00:00+08:00",
            "items": [
                {
                    "apiId": api_id,
                    "apiCategory": api_category,
                    "apiName": api_name,
                    "specStatus": "done",
                    "specBlockReason": None,
                    "specSourceFingerprint": f"sha256:{function_code.lower()}-fingerprint",
                    "codeStatus": "pending",
                    "codePhase": "pending",
                    "codeBlockReason": None,
                }
            ],
        },
    )
    dump_json(
        execution_root / "execution-state.json",
        {
            "schemaVersion": "4.1.0",
            "executionId": function_code,
            "functionCode": function_code,
            "status": "waiting_code",
            "phase": "pending",
            "updatedAt": "2026-04-09T12:00:00+08:00",
            "specStatus": "done",
            "specUpdatedAt": "2026-04-09T12:00:00+08:00",
            "specSummary": {"total": 1, "done": 1, "pending": 0, "blocked": 0, "error": 0},
            "specDocxPath": f".agent/TSD/TSD.{function_code}.docx",
            "specLastMessage": "Fixture spec completed.",
            "codeStatus": "pending",
            "codePhase": "pending",
            "codeUpdatedAt": None,
            "codeCurrentApiId": None,
            "codeSummary": {
                "total": 1,
                "pending": 1,
                "in_progress": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "blocked": 0,
                "error": 0,
                "upstream_not_ready": 0,
            },
            "codeProjectRoot": None,
            "codeSolutionPath": None,
            "codeLastMessage": None,
            "artifacts": {
                "batchFile": ".agent/context/execution-batch.json",
                "checklist": f".agent/context/{function_code}/api-checklist.json",
                "specProgress": f".agent/context/{function_code}/spec-progress.md",
                "codeProgress": f".agent/context/{function_code}/code-progress.md",
                "repoSnapshot": f".agent/context/{function_code}/repo-snapshot.json",
            },
        },
    )
    dump_json(
        context_root / "execution-batch.json",
        {
            "schemaVersion": "1.0.0",
            "activeFunctionCode": function_code,
            "items": [{"functionCode": function_code, "docxRef": f".agent/TSD/TSD.{function_code}.docx", "order": 1}],
            "updatedAt": "2026-04-09T12:00:00+08:00",
            "updatedBy": "Regression",
        },
    )
    if review_notes is not None:
        dump_json(api_root / "review-notes.json", review_notes)
    write_text(execution_root / "spec-progress.md", "- spec done\n")
    return {
        "context_root": context_root,
        "execution_root": execution_root,
        "api_root": api_root,
        "api_spec_path": api_spec_path,
        "manifest_path": api_root / "manifest.json",
        "execution_state_path": execution_root / "execution-state.json",
        "checklist_path": execution_root / "api-checklist.json",
        "change_plan_path": api_root / "change-plan.json",
        "implementation_report_path": api_root / "implementation-report.md",
        "diagnosis_path": api_root / "diagnosis-report.json",
        "test_evidence_path": api_root / "test-evidence.json",
        "review_notes_path": api_root / "review-notes.json",
    }


def setup_workspace(
    temp_dir: Path,
    *,
    function_code: str,
    api_id: str,
    api_category: str,
    api_name: str,
    version: str,
    request: list[dict],
    response: list[dict],
    existing_deposit: bool = False,
    missing_slots: tuple[str, ...] = (),
    review_notes: dict | None = None,
    mock_examples: list[dict] | None = None,
    code_handoff_override: dict | None = None,
) -> dict[str, Path]:
    workspace_root = temp_dir / "FixtureWorkspace"
    repo_root = workspace_root / "Sinopac.DawhoEnterprise"
    create_project_rules_fixture(workspace_root)
    create_base_repo(repo_root)
    if existing_deposit:
        create_existing_deposit_module(repo_root)
    for missing in missing_slots:
        path = repo_root / missing
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    paths = create_execution(
        workspace_root,
        function_code=function_code,
        api_id=api_id,
        api_category=api_category,
        api_name=api_name,
        version=version,
        request=request,
        response=response,
        review_notes=review_notes,
        mock_examples=mock_examples,
        code_handoff_override=code_handoff_override,
    )
    fake_bin = temp_dir / "fake-bin"
    write_text(fake_bin / "dotnet.cmd", fake_dotnet_script())
    paths.update(
        {
            "workspace_root": workspace_root,
            "repo_root": repo_root,
            "solution_path": repo_root / "Sinopac.DawhoEnterprise.sln",
            "batch_file": workspace_root / ".agent" / "context" / "execution-batch.json",
            "fake_bin": fake_bin,
            "dotnet_log": temp_dir / "dotnet.log",
        }
    )
    return paths


def setup_p240301git_commonfunc_workspace(temp_dir: Path) -> dict[str, Path]:
    workspace_root = temp_dir / "FixtureWorkspace"
    create_project_rules_fixture(workspace_root)
    create_p240301git_repo(workspace_root)
    paths = create_execution(
        workspace_root,
        function_code="Common",
        api_id="Common.CommonFunc.GetCENCurr",
        api_category="CommonFunc",
        api_name="GetCENCurr",
        version="v1.0",
        request=[{"fieldName": "currCode", "dataType": "string", "required": True, "description": "幣別"}],
        response=[{"fieldName": "currName", "dataType": "string", "required": False, "description": "幣別名稱"}],
    )
    fake_bin = temp_dir / "fake-bin"
    write_text(fake_bin / "dotnet.cmd", fake_dotnet_script())
    paths.update(
        {
            "workspace_root": workspace_root,
            "repo_root": workspace_root,
            "solution_path": workspace_root / "Sinopac.EnterpriseAPI" / "Sinopac.EnterpriseAPI.slnx",
            "batch_file": workspace_root / ".agent" / "context" / "execution-batch.json",
            "fake_bin": fake_bin,
            "dotnet_log": temp_dir / "dotnet.log",
        }
    )
    return paths


def base_command(paths: dict[str, Path], *, function_code: str) -> list[str]:
    return [
        sys.executable,
        str(WRITE_API_CODE),
        "--project-root",
        str(paths["workspace_root"]),
        "--solution-path",
        str(paths["solution_path"]),
        "--function-code",
        function_code,
    ]


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False, env=merged_env)


def fake_dotnet_env(paths: dict[str, Path], *, exit_code: int = 0, stderr_text: str = "") -> dict[str, str]:
    return {
        "PATH": str(paths["fake_bin"]) + os.pathsep + os.environ.get("PATH", ""),
        "DOTNET_LOG": str(paths["dotnet_log"]),
        "DOTNET_EXIT_CODE": str(exit_code),
        "DOTNET_STDERR": stderr_text,
    }


def read_dotnet_commands(paths: dict[str, Path]) -> list[str]:
    if not paths["dotnet_log"].exists():
        return []
    return [line.strip() for line in paths["dotnet_log"].read_text(encoding="utf-8").splitlines() if line.strip()]


def mark_fixture_status(paths: dict[str, Path], *, status: str, phase: str | None = None) -> None:
    manifest = load_json(paths["manifest_path"])
    manifest["fixtureStatus"] = status
    manifest["fixturePhase"] = phase or status
    manifest["fixtureBlockReason"] = None
    manifest["fixtureSourceFingerprint"] = None
    dump_json(paths["manifest_path"], manifest)

    checklist = load_json(paths["checklist_path"])
    for item in checklist.get("items") or []:
        item["fixtureStatus"] = status
        item["fixturePhase"] = phase or status
        item["fixtureBlockReason"] = None
        item["fixtureSourceFingerprint"] = None
    dump_json(paths["checklist_path"], checklist)


def extract_planned_files(change_plan: dict) -> list[str]:
    analysis = change_plan.get("analysis") or {}
    files = []
    for key in ("controllerFile", "interfaceFile", "targetFile"):
        candidate = analysis.get(key)
        if isinstance(candidate, str) and candidate and candidate not in files:
            files.append(candidate)
    for key in ("codeTargetFiles", "serviceFiles", "entityFiles"):
        for candidate in analysis.get(key) or []:
            if isinstance(candidate, str) and candidate and candidate not in files:
                files.append(candidate)
    return files


def simulate_ai_authored_changes(paths: dict[str, Path], *, marker: str) -> list[str]:
    change_plan = load_json(paths["change_plan_path"])
    modified_files: list[str] = []
    for relative_path in extract_planned_files(change_plan):
        target_path = paths["workspace_root"] / relative_path
        if target_path.exists():
            target_path.write_text(target_path.read_text(encoding="utf-8").rstrip() + f"\n// {marker}\n", encoding="utf-8")
        else:
            write_text(target_path, f"// {marker}: {relative_path}\n")
        modified_files.append(relative_path)
    return modified_files


def assert_n006_prepare_output(paths: dict[str, Path]) -> None:
    change_plan = load_json(paths["change_plan_path"])
    manifest = load_json(paths["manifest_path"])
    state = load_json(paths["execution_state_path"])
    controller_path = paths["repo_root"] / "API" / "EnterpriseAPI" / "EnterpriseAPI" / "Controllers" / "SettingController.cs"
    interface_path = paths["repo_root"] / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness.Interface" / "ISettingService.cs"
    service_root_path = paths["repo_root"] / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "Setting" / "SettingService.cs"
    service_method_path = paths["repo_root"] / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "Setting" / "SettingService.QueryUserLoginLog.cs"
    entity_path = paths["repo_root"] / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiEntity" / "Setting" / "QueryUserLoginLogInfo.cs"
    unit_controller_path = paths["repo_root"] / "Test" / "UnitTesting" / "EnterpriseAPI" / "EnterpriseApiUnit" / "SettingControllerTest.cs"
    unit_service_path = paths["repo_root"] / "Test" / "UnitTesting" / "EnterpriseAPI" / "EnterpriseApiUnit" / "SettingServiceTests.cs"
    integration_path = paths["repo_root"] / "Test" / "IntegrationTesting" / "EnterpriseAPI" / "EnterpriseApiIntegration" / "SettingControllerTests.cs"

    assert_true(change_plan["analysis"]["frameworkProfile"] == "enterpriseapi", "N.006 should resolve EnterpriseAPI framework profile")
    assert_true(change_plan["analysis"]["moduleName"] == "Setting", "N.006 should map category to Setting module")
    assert_true(change_plan["analysis"]["creationMode"] == "create_module", "N.006 should create a new module chain")
    assert_true(change_plan["analysis"]["handoffSource"] == "codeHandoff", "N.006 should prefer explicit codeHandoff")
    assert_true(change_plan["analysis"]["queryContractsSelected"][0]["contractId"] == "query_login_logs", "N.006 change-plan should record the selected query contract")
    assert_true(any(rule["mappingType"] == "lookup_table" for rule in change_plan["analysis"]["mappingRulesSelected"]), "N.006 change-plan should record lookup mapping rules")
    assert_true(change_plan["analysis"]["legacyEvidenceUsed"][0]["evidenceId"] == "legacy_query_user_login_log", "N.006 change-plan should record selected legacy evidence")
    assert_true(change_plan["analysis"]["testScenarioCoverageRequired"] is True, "Prepare should require test coverage for spec mockExamples")
    selected_rule_ids = {entry["ruleId"] for entry in change_plan["analysis"]["devGuidelineRulesSelected"]}
    assert_true(change_plan["analysis"]["audienceProfile"]["scope"] == "frontstage", "Prepare should classify customer-context APIs as frontstage")
    assert_true("data-access" in selected_rule_ids, "SQL APIs should select data-access dev guidelines")
    assert_true("frontstage-session" in selected_rule_ids, "Frontstage identity APIs should select session guidelines")
    assert_true("backoffice-authz" not in selected_rule_ids, "Frontstage APIs should not load backoffice authorization guidelines")
    assert_true(
        not any(gap.get("blocking") for gap in change_plan["analysis"]["devGuidelineGaps"]),
        "Clear frontstage evidence should not create blocking guideline gaps",
    )
    assert_true("unitTestFiles" not in change_plan["analysis"], "Prepare should not expose step-04 test files as writable targets")
    assert_true("integrationTestFiles" not in change_plan["analysis"], "Prepare should not expose step-04 integration test files as writable targets")
    assert_true(change_plan["analysis"]["unitTestTargetFiles"], "Prepare should provide unit test handoff target hints")
    assert_true(change_plan["analysis"]["integrationTestTargetFiles"], "Prepare should provide integration test handoff target hints")
    assert_true(
        change_plan["analysis"]["testCodeHandoff"]["ownerStep"] == "05 docx-unittest-report",
        "Prepare should mark test-code ownership as step 05",
    )
    write_code_step = next(step for step in change_plan["steps"] if step["id"] == "write_code")
    assert_true("handoff-only" in write_code_step["note"], "write_code note should state test targets are handoff-only")
    assert_true("/test files" not in write_code_step["note"], "write_code note must not ask AI to modify test files")
    scenario_names = [entry["scenario"] for entry in change_plan["analysis"]["testScenarioPlan"]]
    assert_true(scenario_names == ["正常結果返回", "查無登入紀錄"], "Prepare should preserve every mockExample scenario in order")
    assert_true(
        [entry["expectedResponseCode"] for entry in change_plan["analysis"]["testScenarioPlan"]] == ["0000", "0000"],
        "Prepare must not collapse mockExamples just because responseCode repeats",
    )
    assert_true(
        change_plan["analysis"]["testScenarioPlan"][1]["expectedResponseMessage"] == "查無資料",
        "Prepare should carry expected response payload details into the test scenario plan",
    )
    assert_true("CustomerLogin/Common/ProfileService.cs" not in json.dumps(change_plan, ensure_ascii=False), "N.006 change-plan must not target CustomerLogin")
    assert_true(not controller_path.exists(), "Prepare must not create SettingController.cs")
    assert_true(not interface_path.exists(), "Prepare must not create ISettingService.cs")
    assert_true(not service_root_path.exists(), "Prepare must not create SettingService.cs")
    assert_true(not service_method_path.exists(), "Prepare must not create SettingService.QueryUserLoginLog.cs")
    assert_true(not entity_path.exists(), "Prepare must not create QueryUserLoginLogInfo.cs")
    assert_true(not unit_controller_path.exists(), "Prepare must not create SettingControllerTest.cs")
    assert_true(not unit_service_path.exists(), "Prepare must not create SettingServiceTests.cs")
    assert_true(not integration_path.exists(), "Prepare must not create SettingControllerTests.cs")
    assert_true(manifest["codeStatus"] == "pending", "Prepare should leave manifest pending")
    assert_true(manifest["codePhase"] == "planned", "Prepare should leave manifest in planned phase")
    assert_true(state["codeStatus"] == "waiting_resume", "Prepare should leave execution waiting for resumed apply")
    assert_true(state["codePhase"] == "planned", "Prepare should leave execution phase at planned")
    assert_true(paths["implementation_report_path"].exists() is False, "Prepare should not emit implementation report yet")


def test_n006_prepare_only_generates_change_plan_and_defers_code_writing() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[
                {"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"},
                {
                    "fieldName": "loginLogs",
                    "dataType": "list",
                    "required": False,
                    "description": "登入記錄列表",
                    "properties": [
                        {"fieldName": "loginTime", "dataType": "string", "required": False, "description": "登入時間"},
                        {"fieldName": "loginStatus", "dataType": "string", "required": False, "description": "登入狀態"},
                    ],
                },
            ],
            mock_examples=[
                {
                    "scenario": "正常結果返回",
                    "requestPayload": {"keyId": "jwt-key"},
                    "responsePayload": {
                        "isSuccess": True,
                        "responseCode": "0000",
                        "responseMessage": "執行成功",
                        "responseData": {"loginLogs": [{"loginTime": "2026/04/01 09:00:00", "loginStatus": "成功"}]},
                    },
                },
                {
                    "scenario": "查無登入紀錄",
                    "requestPayload": {"keyId": "jwt-key"},
                    "responsePayload": {
                        "isSuccess": True,
                        "responseCode": "0000",
                        "responseMessage": "查無資料",
                        "responseData": {"loginLogs": []},
                    },
                },
            ],
        )
        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"], env=fake_dotnet_env(paths))
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        assert_n006_prepare_output(paths)
        assert_true(read_dotnet_commands(paths) == [], "Prepare must not run validation commands")


def test_commonfunc_prepare_uses_library_folders_without_controller() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_p240301git_commonfunc_workspace(Path(temp_dir))
        completed = run_command(base_command(paths, function_code="Common") + ["--execution-mode", "prepare"], env=fake_dotnet_env(paths))
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        change_plan = load_json(paths["change_plan_path"])
        analysis = change_plan["analysis"]
        serialized = json.dumps(change_plan, ensure_ascii=False)

        assert_true(analysis["moduleName"] == "CommonFunc", "CommonFunc prepare should pin the shared module name")
        assert_true(analysis["controllerFile"] is None, "CommonFunc prepare must not plan a controller")
        assert_true(
            analysis["interfaceFile"] == "Libray/Sinopac.CommonFunc/IFuncService/ICommonFuncService.cs",
            "CommonFunc interface should land in IFuncService",
        )
        assert_true(
            analysis["targetFile"] == "Libray/Sinopac.CommonFunc/FuncService/CommonFuncService.GetCENCurr.cs",
            "CommonFunc method partial should land in FuncService",
        )
        assert_true(
            analysis["serviceFiles"]
            == [
                "Libray/Sinopac.CommonFunc/FuncService/CommonFuncService.cs",
                "Libray/Sinopac.CommonFunc/FuncService/CommonFuncService.GetCENCurr.cs",
            ],
            "CommonFunc service files should stay under FuncService",
        )
        assert_true(
            analysis["entityFiles"] == ["Libray/Sinopac.CommonFunc/Dto/GetCENCurrInfo.cs"],
            "CommonFunc DTO should stay under Dto",
        )
        assert_true(
            "Libray/Sinopac.CommonFunc/IFuncService/ICommonFuncService.cs" in analysis["codeTargetFiles"],
            "CommonFunc code targets should include IFuncService interface",
        )
        assert_true(
            "Libray/Sinopac.CommonFunc/FuncService/CommonFuncService.GetCENCurr.cs" in analysis["codeTargetFiles"],
            "CommonFunc code targets should include FuncService method partial",
        )
        assert_true("EnterpriseApiBusiness/CommonFunc" not in serialized, "CommonFunc prepare must not use old EnterpriseApiBusiness path")
        assert_true("CommonFuncController" not in serialized, "CommonFunc prepare must not plan CommonFuncController")
        assert_true(read_dotnet_commands(paths) == [], "Prepare must not run validation commands")


def test_n006_apply_uses_real_ai_authored_changes_and_default_validation() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[
                {"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"},
                {
                    "fieldName": "loginLogs",
                    "dataType": "list",
                    "required": False,
                    "description": "登入記錄列表",
                    "properties": [
                        {"fieldName": "loginTime", "dataType": "string", "required": False, "description": "登入時間"},
                        {"fieldName": "loginStatus", "dataType": "string", "required": False, "description": "登入狀態"},
                    ],
                },
            ],
        )
        mark_fixture_status(paths, status="skipped")
        prepare = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(prepare.returncode == 0, prepare.stdout + prepare.stderr)

        modified_files = simulate_ai_authored_changes(paths, marker="REAL AI IMPLEMENTATION")
        service_method_path = paths["workspace_root"] / "Sinopac.DawhoEnterprise/BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/Setting/SettingService.QueryUserLoginLog.cs"
        assert_true("REAL AI IMPLEMENTATION" in service_method_path.read_text(encoding="utf-8"), "Fixture should contain the AI-authored marker before apply")

        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "apply"], env=fake_dotnet_env(paths))
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)

        manifest = load_json(paths["manifest_path"])
        state = load_json(paths["execution_state_path"])
        report = paths["implementation_report_path"].read_text(encoding="utf-8")
        test_evidence = load_json(paths["test_evidence_path"])
        commands = read_dotnet_commands(paths)
        validation_commands = [command for command in commands if "build-server shutdown" not in command]

        assert_true("REAL AI IMPLEMENTATION" in service_method_path.read_text(encoding="utf-8"), "Apply must not overwrite AI-authored service code")
        assert_true("Generated stub" not in service_method_path.read_text(encoding="utf-8"), "Apply must not reintroduce generator stubs")
        assert_true(all("/Test/" not in path and "\\Test\\" not in path for path in modified_files), "Step 04 simulated AI changes should not target test source files")
        assert_true(sorted(manifest["modifiedFiles"]) == sorted(modified_files), "Apply should record the real AI-authored modified files")
        assert_true(manifest["codeStatus"] == "tests_passed", "Successful apply should finish as tests_passed")
        assert_true(state["codeStatus"] == "done", "Execution should end in done after successful apply")
        assert_true("AI writes repository code directly" in report, "Implementation report should describe the new orchestration boundary")
        assert_true(len(validation_commands) == 3, "Apply should invoke build + unit test + integration test by default")
        assert_true(test_evidence["apiDisplayName"] == "Setting/QueryUserLoginLog", "Apply should emit report display metadata")
        assert_true(test_evidence["unitTestProject"].endswith("EnterpriseAPIUnit.csproj"), "Apply should record the unit-test project path")
        assert_true(test_evidence["integrationTestProject"].endswith("EnterpriseAPIIntegration.csproj"), "Apply should record the integration-test project path")
        assert_true(test_evidence["trxHints"]["unit"].endswith("/.agent/report-results/N.006/N.006.setting.queryuserloginlog/unit"), "Apply should emit the dedicated unit TRX hint directory")
        assert_true(test_evidence["trxHints"]["integration"].endswith("/.agent/report-results/N.006/N.006.setting.queryuserloginlog/integration"), "Apply should emit the dedicated integration TRX hint directory")
        assert_true(test_evidence["testTargetFiles"]["writerPolicy"] == "handoff_only", "Apply should mark test target files as handoff-only")
        assert_true(isinstance(test_evidence["testNames"]["unit"], list), "Apply should always emit a unit test-name list")
        assert_true(isinstance(test_evidence["testNames"]["integration"], list), "Apply should always emit an integration test-name list")


def test_apply_pending_fixture_reuses_prepare_plan_without_cleanup() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[{"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"}],
        )
        prepare = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(prepare.returncode == 0, prepare.stdout + prepare.stderr)
        simulate_ai_authored_changes(paths, marker="PENDING FIXTURE")

        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "apply"], env=fake_dotnet_env(paths))
        assert_true(completed.returncode == 1, "Apply should wait for pending fixture instead of deleting the prepare plan")
        assert_true(paths["change_plan_path"].exists(), "Pending fixture apply must preserve change-plan.json")
        manifest = load_json(paths["manifest_path"])
        assert_true(manifest["codeStatus"] == "waiting_fixture", "Apply should report waiting_fixture in the shared manifest")
        assert_true("change-plan" not in (completed.stdout + completed.stderr).lower(), "Apply should not misdiagnose the prepared change-plan as missing")


def test_dev_guidelines_select_mid_backoffice_without_frontstage_rules() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="M.001",
            api_id="M.001.admin.queryrolepermission",
            api_category="admin",
            api_name="QueryRolePermission",
            version="v1.0",
            request=[],
            response=[{"fieldName": "roleName", "dataType": "string", "required": False, "description": "角色名稱"}],
        )
        completed = run_command(base_command(paths, function_code="M.001") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        change_plan = load_json(paths["change_plan_path"])
        selected_rule_ids = {entry["ruleId"] for entry in change_plan["analysis"]["devGuidelineRulesSelected"]}
        assert_true(change_plan["analysis"]["audienceProfile"]["scope"] == "midBackoffice", "Admin role APIs should classify as midBackoffice")
        assert_true("backoffice-authz" in selected_rule_ids, "Mid/backoffice role APIs should select backoffice authz guidelines")
        assert_true("frontstage-session" not in selected_rule_ids, "Mid/backoffice APIs should not load frontstage session guidelines")


def test_dev_guidelines_pure_db_query_keeps_front_back_rules_out() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        handoff = {
            "schemaVersion": "1.0.0",
            "logicSummary": {"stepCount": 1, "queryContractCount": 1, "mappingRuleCount": 1, "legacyEvidenceCount": 0, "dependencyHintCount": 1, "constraintCount": 0, "unresolvedCount": 0, "primarySource": "businessLogic"},
            "logicFlow": [{"stepId": "step_1", "title": "查詢利率資料", "actionType": "query", "inputs": [], "outputs": ["rate"], "evidenceIds": []}],
            "legacyEvidence": [],
            "queryContracts": [
                {
                    "contractId": "query_rates",
                    "purpose": "查詢利率資料",
                    "dataSources": ["RATE_TABLE"],
                    "mustContain": ["RATE_TABLE", "ORDER BY"],
                    "sqlText": "SELECT Rate FROM RATE_TABLE ORDER BY EffectiveDate DESC",
                    "parameterHints": [],
                    "resultShape": ["rate"],
                    "evidenceIds": [],
                }
            ],
            "mappingRules": [{"ruleId": "map_rate", "sourceField": "RATE_TABLE.Rate", "targetField": "rate", "mappingType": "field_mapping", "mappingTable": None, "defaultValue": None, "evidenceIds": []}],
            "dependencyHints": [{"dependencyType": "database", "preferredAbstractions": ["ISqlQueryExecutor"], "purpose": "查詢利率資料", "evidenceIds": []}],
            "constraints": [],
            "unresolved": [],
        }
        paths = setup_workspace(
            Path(temp_dir),
            function_code="R.001",
            api_id="R.001.report.queryrate",
            api_category="report",
            api_name="QueryRate",
            version="v1.0",
            request=[],
            response=[{"fieldName": "rate", "dataType": "decimal", "required": False, "description": "利率"}],
            code_handoff_override=handoff,
        )
        completed = run_command(base_command(paths, function_code="R.001") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        change_plan = load_json(paths["change_plan_path"])
        selected_rule_ids = {entry["ruleId"] for entry in change_plan["analysis"]["devGuidelineRulesSelected"]}
        assert_true(change_plan["analysis"]["audienceProfile"]["scope"] == "unknown", "Pure DB APIs without caller evidence should stay unknown")
        assert_true("data-access" in selected_rule_ids, "Pure DB APIs should select data-access guidelines")
        assert_true("frontstage-session" not in selected_rule_ids, "Pure DB APIs should not load frontstage rules")
        assert_true("backoffice-authz" not in selected_rule_ids, "Pure DB APIs should not load backoffice rules")
        assert_true(not change_plan["analysis"]["devGuidelineGaps"], "Pure DB selection should not block on audience")


def test_dev_guidelines_ambiguous_front_back_scope_blocks_prepare() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="X.001",
            api_id="X.001.memberadmin.querymemberrolepermission",
            api_category="memberAdmin",
            api_name="QueryMemberRolePermission",
            version="v1.0",
            request=[],
            response=[{"fieldName": "permissionName", "dataType": "string", "required": False, "description": "權限名稱"}],
        )
        completed = run_command(base_command(paths, function_code="X.001") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 1, "Ambiguous frontstage/backoffice audience should block prepare")
        change_plan = load_json(paths["change_plan_path"])
        manifest = load_json(paths["manifest_path"])
        assert_true(manifest["codeStatus"] == "blocked", "Ambiguous audience should leave the manifest blocked")
        assert_true(change_plan["analysis"]["audienceProfile"]["scope"] == "unknown", "Ambiguous evidence should keep audience unknown")
        assert_true(any(gap.get("blocking") for gap in change_plan["analysis"]["devGuidelineGaps"]), "Ambiguous audience should emit blocking guideline gaps")


def test_convert_dev_guidelines_rejects_ole_source_without_empty_rules() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "encrypted.docx"
        source.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"legacy-office-container")
        out_dir = Path(temp_dir) / "out"
        completed = run_command([sys.executable, str(CONVERT_DEV_GUIDELINES), "--source", str(source), "--out-dir", str(out_dir)])
        assert_true(completed.returncode == 2, "OLE/DRM sources should be rejected as source_unreadable")
        assert_true("source_unreadable" in completed.stderr, "Converter should report source_unreadable")
        assert_true(not (out_dir / "catalog.json").exists(), "Converter must not generate empty rule catalogs for unreadable sources")


def test_d006_prepare_reuses_existing_deposit_module() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="D.006",
            api_id="D.006.deposit.addexchangedepositinit",
            api_category="deposit",
            api_name="AddExchangeDepositInit",
            version="v1.0",
            request=[{"fieldName": "currency", "dataType": "string", "required": True, "description": "幣別"}],
            response=[{"fieldName": "applyId", "dataType": "string", "required": False, "description": "申請序號"}],
            existing_deposit=True,
        )
        completed = run_command(
            base_command(paths, function_code="D.006") + ["--execution-mode", "prepare", "--validation-check", "cmd /c exit 0"]
        )
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        change_plan = load_json(paths["change_plan_path"])
        manifest = load_json(paths["manifest_path"])
        service_path = paths["repo_root"] / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "Deposit" / "DepositService.cs"
        controller_path = paths["repo_root"] / "API" / "EnterpriseAPI" / "EnterpriseAPI" / "Controllers" / "DepositController.cs"
        interface_path = paths["repo_root"] / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness.Interface" / "IDepositService.cs"

        assert_true(change_plan["analysis"]["creationMode"] == "reuse", "D.006 should reuse the existing Deposit module")
        assert_true(change_plan["analysis"]["targetFile"].endswith("DepositService.cs"), "D.006 should target DepositService.cs")
        assert_true((paths["repo_root"] / "BusinessLogicLayout" / "EnterpriseApi" / "EnterpriseApiBusiness" / "Deposit" / "DepositService.AddExchangeDepositInit.cs").exists() is False, "D.006 should not create a parallel DepositService partial file during prepare")
        assert_true("AddExchangeDepositInitAsync" not in service_path.read_text(encoding="utf-8"), "Prepare must not append methods into DepositService.cs")
        assert_true("AddExchangeDepositInitAsync" not in controller_path.read_text(encoding="utf-8"), "Prepare must not append methods into DepositController.cs")
        assert_true("AddExchangeDepositInitAsync" not in interface_path.read_text(encoding="utf-8"), "Prepare must not append methods into IDepositService.cs")
        assert_true(manifest["codeStatus"] == "pending", "Prepare should keep D.006 manifest pending")


def test_apply_without_real_changes_blocks() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[{"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"}],
        )
        mark_fixture_status(paths, status="skipped")
        prepare = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(prepare.returncode == 0, prepare.stdout + prepare.stderr)

        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "apply"], env=fake_dotnet_env(paths))
        assert_true(completed.returncode == 1, "Apply without AI-authored code changes should block")
        manifest = load_json(paths["manifest_path"])
        diagnosis = load_json(paths["diagnosis_path"])
        assert_true(manifest["codeStatus"] == "blocked", "Apply without changes should leave manifest blocked")
        assert_true("No AI-authored code changes detected" in (diagnosis.get("detail") or ""), "Diagnosis should explain that apply needs real code changes")
        assert_true(read_dotnet_commands(paths) == [], "Apply without changes should not start validation")


def test_missing_enterprise_slots_block_precheck() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[{"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"}],
            missing_slots=("BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness.Interface/EnterpriseApiBusiness.Interface.csproj",),
        )
        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 1, "Missing EnterpriseAPI slots should block the writer")
        assert_true("EnterpriseAPI framework slots are missing" in (completed.stdout + completed.stderr), "Failure message should explain which framework slots are missing")
        manifest = load_json(paths["manifest_path"])
        diagnosis = load_json(paths["diagnosis_path"])
        report = paths["implementation_report_path"].read_text(encoding="utf-8")
        assert_true(manifest["codeStatus"] == "blocked", "Manifest should record blocked when framework slots are missing")
        assert_true(diagnosis["diagnosisType"] == "framework_gap", "Diagnosis should classify missing slots as framework gap")
        assert_true("EnterpriseAPI framework slots are missing" in report, "Implementation report should capture the missing-slot reason")


def test_environment_validation_failure_is_classified() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[{"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"}],
        )
        mark_fixture_status(paths, status="skipped")
        prepare = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(prepare.returncode == 0, prepare.stdout + prepare.stderr)
        simulate_ai_authored_changes(paths, marker="ENV FAILURE CASE")

        completed = run_command(
            base_command(paths, function_code="N.006") + ["--execution-mode", "apply"],
            env=fake_dotnet_env(
                paths,
                exit_code=1,
                stderr_text="MSB3248: Could not copy the file because it is being used by another process.",
            ),
        )
        assert_true(completed.returncode == 1, "Environment validation failure should fail the run")
        diagnosis = load_json(paths["diagnosis_path"])
        manifest = load_json(paths["manifest_path"])
        assert_true(diagnosis["failureKind"] == "environment", "Diagnosis should classify MSB3248 as environment failure")
        assert_true(diagnosis["failureClassifications"][0]["reason"] == "assembly_locked", "Diagnosis should capture the assembly lock reason")
        assert_true(diagnosis["diagnosisType"] == "environment_issue", "Diagnosis should label environment failures consistently")
        assert_true(manifest["codeStatus"] == "tests_failed", "Validation failure should leave manifest in tests_failed")


def test_old_spec_without_code_handoff_uses_business_logic_compat() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[
                {"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"},
                {"fieldName": "loginWay", "dataType": "string", "required": False, "description": "登入方式"},
            ],
        )
        api_spec = load_json(paths["api_spec_path"])
        api_spec["schemaVersion"] = "4.1.0"
        api_spec.pop("codeHandoff", None)
        dump_json(paths["api_spec_path"], api_spec)

        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"], env=fake_dotnet_env(paths))
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        change_plan = load_json(paths["change_plan_path"])
        assert_true(change_plan["analysis"]["handoffSource"] == "businessLogic_compat", "Old spec should synthesize handoff from businessLogic")
        assert_true(change_plan["analysis"]["queryContractsSelected"][0]["contractId"] == "query_login_logs", "Compat path should still recover SQL contracts")


def test_sequence_diagram_43_spec_is_accepted_by_code_writer_prepare() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="D.006",
            api_id="D.006.deposit.apply",
            api_category="Deposit",
            api_name="ApplyDeposit",
            version="v1.0",
            request=[{"fieldName": "custId", "dataType": "string", "required": True, "description": "客戶代號"}],
            response=[{"fieldName": "responseCode", "dataType": "string", "required": False, "description": "回應代碼"}],
            existing_deposit=True,
        )
        sequence_source = {
            "path": ".agent/functions/D.006/analysis/sequence-diagrams/D.006_ApplyDeposit_native_visio_spec.json",
            "kind": "native_visio_spec",
            "sha256": "sha256:sequence-fixture",
            "matchedBy": "functionCode+apiName",
            "authority": "supporting",
        }
        evidence_id = "sequence_1_d006_applydeposit"
        api_spec = load_json(paths["api_spec_path"])
        api_spec["source"]["sequenceDiagrams"] = [sequence_source]
        api_spec["rawAppendix"] = {
            "sequenceDiagramExtracts": [
                {
                    "evidenceId": evidence_id,
                    "path": sequence_source["path"],
                    "kind": sequence_source["kind"],
                    "appliedToApi": True,
                    "messages": ["Controller -> Service: ApplyDeposit(custId)", "Service -> IRIS: verify deposit state"],
                }
            ]
        }
        code_handoff = api_spec["codeHandoff"]
        code_handoff["legacyEvidence"].append(
            {
                "evidenceId": evidence_id,
                "kind": "sequenceDiagram",
                "origin": sequence_source["path"],
                "authority": "supporting",
                "symbols": ["ApplyDeposit", "IRIS"],
                "summary": "ApplyDeposit 時序圖補強 IRIS 驗證流程。",
                "snippet": "Service -> IRIS: verify deposit state",
            }
        )
        code_handoff["logicFlow"].append(
            {
                "stepId": "sequence-1-1",
                "title": "時序圖：IRIS 驗證存款狀態",
                "actionType": "sequence",
                "inputs": ["custId"],
                "outputs": ["responseCode"],
                "evidenceIds": [evidence_id],
            }
        )
        code_handoff["dependencyHints"].append(
            {
                "dependencyType": "IRIS",
                "preferredAbstractions": ["IIrisDepositClient"],
                "purpose": "依時序圖驗證存款狀態。",
                "evidenceIds": [evidence_id],
            }
        )
        code_handoff["logicSummary"]["legacyEvidenceCount"] = len(code_handoff["legacyEvidence"])
        code_handoff["logicSummary"]["dependencyHintCount"] = len(code_handoff["dependencyHints"])
        code_handoff["logicSummary"]["primarySource"] = "businessLogic+sequenceDiagram"
        dump_json(paths["api_spec_path"], api_spec)

        manifest = load_json(paths["manifest_path"])
        manifest["schemaVersion"] = "4.2.0"
        manifest["specSource"]["sequenceDiagrams"] = [sequence_source]
        dump_json(paths["manifest_path"], manifest)

        completed = run_command(base_command(paths, function_code="D.006") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        analysis = load_json(paths["change_plan_path"])["analysis"]
        assert_true(any(entry["kind"] == "sequenceDiagram" for entry in analysis["legacyEvidenceUsed"]), "Prepare should keep sequence evidence from API_Spec 4.3.0")
        assert_true(any(entry["dependencyType"] == "IRIS" for entry in analysis["dependencyHintsSelected"]), "Prepare should keep sequence dependency hints")


def test_old_spec_with_prose_only_logic_blocks() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[{"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"}],
        )
        api_spec = load_json(paths["api_spec_path"])
        api_spec["schemaVersion"] = "4.1.0"
        api_spec.pop("codeHandoff", None)
        api_spec["businessLogic"] = {
            "steps": [{"step": "1", "title": "說明", "details": "請依既有流程處理，不提供具體查詢或映射。"}],
            "fieldMappings": [],
            "lookupTables": [],
            "errorCodeRules": [{"code": "0000", "scenario": "success", "message": "成功"}],
            "runtimeDependencies": [],
            "dataSources": [],
            "sqlSpecs": [],
            "legacyReferences": [],
            "prohibitedShortcuts": [],
            "referenceHints": [],
        }
        dump_json(paths["api_spec_path"], api_spec)

        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 1, "Prose-only old spec should block the writer")
        manifest = load_json(paths["manifest_path"])
        diagnosis = load_json(paths["diagnosis_path"])
        assert_true(manifest["codeStatus"] == "blocked", "Prose-only old spec should leave manifest blocked")
        assert_true(diagnosis["diagnosisType"] == "spec_handoff_gap", "Diagnosis should identify missing structured handoff")
        assert_true("missing structured query, mapping, or legacy evidence" in (diagnosis.get("detail") or "").lower(), "Diagnosis detail should explain the handoff gap")


def test_n006_prepare_consumes_review_notes_and_splits_role_requirements() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[
                {
                    "fieldName": "loginLogs",
                    "dataType": "list",
                    "required": False,
                    "description": "登入記錄列表",
                    "properties": [
                        {"fieldName": "loginTime", "dataType": "string", "required": False, "description": "登入時間"},
                        {"fieldName": "loginStatus", "dataType": "string", "required": False, "description": "登入狀態"},
                    ],
                }
            ],
            review_notes=build_review_notes("N.006.setting.queryuserloginlog"),
        )
        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 0, completed.stdout + completed.stderr)
        change_plan = load_json(paths["change_plan_path"])
        analysis = change_plan["analysis"]
        assert_true(analysis["reviewSources"][0]["reviewNotes"] == ".agent/context/N.006/apis/N.006.setting.queryuserloginlog/review-notes.json", "Prepare should record the review-notes source")
        assert_true(any(item["ruleType"] == "response_lifecycle" for item in analysis["reviewConstraintsSelected"]), "Prepare should select response lifecycle review constraints")
        assert_true(any(item["ruleType"] == "failure_payload" for item in analysis["reviewConstraintsSelected"]), "Prepare should select failure payload review constraints")
        assert_true(any(item["ruleType"] == "contract_type" for item in analysis["fileRequirements"]["entity"]), "Entity requirements should carry contract type constraints")
        assert_true(any(item["ruleType"] == "response_lifecycle" for item in analysis["fileRequirements"]["service"]), "Service requirements should carry response lifecycle constraints")
        assert_true(analysis["externalApiName"] == "QueryUserLoginLog", "External API name should stay aligned with the spec name")
        assert_true(not analysis["externalApiName"].endswith("Async"), "External API name must not append Async")


def test_review_notes_with_unknown_field_blocks_prepare() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        review_notes = build_review_notes("N.006.setting.queryuserloginlog")
        review_notes["items"][1]["appliesTo"] = ["response.nonexistentField"]
        paths = setup_workspace(
            Path(temp_dir),
            function_code="N.006",
            api_id="N.006.setting.queryuserloginlog",
            api_category="setting",
            api_name="QueryUserLoginLog",
            version="v1.2",
            request=[],
            response=[{"fieldName": "keyId", "dataType": "string", "required": False, "description": "JWT key"}],
            review_notes=review_notes,
        )
        completed = run_command(base_command(paths, function_code="N.006") + ["--execution-mode", "prepare"])
        assert_true(completed.returncode == 1, "Prepare should block when blocking review notes reference unknown spec fields")
        diagnosis = load_json(paths["diagnosis_path"])
        manifest = load_json(paths["manifest_path"])
        assert_true(manifest["codeStatus"] == "blocked", "Invalid blocking review notes should leave manifest blocked")
        assert_true(diagnosis["diagnosisType"] == "review_constraint_gap", "Diagnosis should classify review-note conflicts separately")


def main() -> int:
    tests = [
        test_n006_prepare_only_generates_change_plan_and_defers_code_writing,
        test_commonfunc_prepare_uses_library_folders_without_controller,
        test_n006_apply_uses_real_ai_authored_changes_and_default_validation,
        test_apply_pending_fixture_reuses_prepare_plan_without_cleanup,
        test_d006_prepare_reuses_existing_deposit_module,
        test_apply_without_real_changes_blocks,
        test_missing_enterprise_slots_block_precheck,
        test_environment_validation_failure_is_classified,
        test_old_spec_without_code_handoff_uses_business_logic_compat,
        test_sequence_diagram_43_spec_is_accepted_by_code_writer_prepare,
        test_old_spec_with_prose_only_logic_blocks,
        test_n006_prepare_consumes_review_notes_and_splits_role_requirements,
        test_review_notes_with_unknown_field_blocks_prepare,
        test_dev_guidelines_select_mid_backoffice_without_frontstage_rules,
        test_dev_guidelines_pure_db_query_keeps_front_back_rules_out,
        test_dev_guidelines_ambiguous_front_back_scope_blocks_prepare,
        test_convert_dev_guidelines_rejects_ole_source_without_empty_rules,
    ]
    for test in tests:
        test()
        print(f"[pass] {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
