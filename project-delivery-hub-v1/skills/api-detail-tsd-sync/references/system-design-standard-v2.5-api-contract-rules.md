# System Design Standard v2.5 - API Contract Rules

Source: `P240301_永豐商銀新大戶_系統設計規範 v2.5 20260514.docx`.

Use this reference only when a 既有专案 task touches API contract reconciliation, TSD `API清單`, API Detail workbook content, naming, Redis/Appsetting/DB design evidence, or development-readiness decisions. Do not load it for simple path lookup or pure format checking.

## Authority And Scope

- Treat system-design standard v2.5 as the current project rule set unless a newer project design standard is supplied.
- PRD/TSD/API Detail still decide the actual business contract. The standard supplies naming, completeness, traceability, and handoff rules.
- This reference belongs to design analysis. Do not extend its Redis/Appsetting/DB rules into `api-spec-writer`, `api-code-writer`, SQL fixture, or UT report skills unless the user explicitly asks.
- If a project-specific design rule conflicts with the general standard, prefer the project-specific rule; if the project-specific rule is silent, apply this standard.

## API Naming

- Query-style API names must use `Get`, not `Query`, to avoid URL parameter leakage and align DAWHO naming.
- API Name, DB table name, and DB table fields use PascalCase.
- API payload field names and variables use camelCase.
- Transaction page-flow APIs use the stage suffixes below:
  - fill/input page: `{FunctionName}Init`
  - confirm page: `{FunctionName}Confirm`
  - result/submit page: `{FunctionName}Result`
- Old DAWHO names are evidence only. Do not copy old field names, Redis keys, config names, API labels, or switch names directly into the new-system contract.
- Prefer clear business English over legacy abbreviations when the contract is not already frozen.

## API List And Workbook Completeness

- TSD `API清單` is the development entry point and should align with API Detail `Api_List` and API worksheets.
- New APIs must be added to the API list workbook `NEWDA_API_LIST_yyyyMMdd.xlsx` when that deliverable is in scope.
- Module-specific API detail workbooks follow `NEWDA_API_DETAIL_{ModuleEnglishName}_yyyyMMdd.xlsx`.
- Every API detail workbook must have a list sheet that shows all APIs. `Api_List` API names should hyperlink to the corresponding API worksheet, and each API worksheet should provide a return link to `Api_List`.
- Request and Response definitions must both be present in Excel. Do not leave request/response only in free text.
- API examples are required. Examples must match the declared request/response fields and should include success and failure response code/message cases when applicable.

## Field And Payload Rules

- Header fields do not need to appear as a visible `Header` section in every API worksheet, but API logic must state which values are obtained from Header when the API depends on them.
- Required flags must be explicit for request and response fields. Use the standard meaning:
  - `Y`: the field must be returned or supplied.
  - `N`: the field may be absent when no data exists.
- Data types must reflect real payload behavior. Do not use generic string/json types when the PRD, TSD, API behavior, or backend source proves a more precise type.
- `responseData` with no data should be `{}`, not `NULL`, unless a confirmed downstream contract requires otherwise.
- API-facing contracts must not use `password`. If the concept is unavoidable, use `passwd`.
- Avoid exposing unclear or security-sensitive words such as `ID`, `Key`, `PWD`, `Password`, `Dept`, `No.` as canonical field names when a clearer business name exists.
- Masking/hidden display is a frontend concern. API request/response payloads should carry clear business values, not display-mask strings, unless a source system contract explicitly requires masked data.
- Response fields need mapping relationships and explanations when values are derived, merged, filtered, converted, or sourced from backend data.

## Business Logic Requirements

API internal business logic should explain enough for development, not just list field names.

For backend/API/DB involvement, record:

- which BackendAPI, DB table, SP, view, or external endpoint is used;
- query conditions, selected fields, sort/group conditions, and any filtering/merge/conversion;
- insert/update/delete conditions and target fields when the operation modifies data;
- where each response field comes from and what it means;
- failure and exception handling, including response code/message mapping;
- performance concerns when the operation touches large data, high concurrency, external IO, or cache.

If DB/SP, source API, Header value, Response Code, or external endpoint is not confirmed, mark `todo` / `待確認` / `unresolved` instead of inventing a final answer.

## Redis, Appsetting, And DB Evidence

Use these rules as design-review evidence when a feature contract mentions Redis, configuration, or DB. They are not a code-generation mandate in this skill.

- Redis keys use readable English, PascalCase field segments, controlled length, and only safe characters such as letters, digits, `_`, and `:`.
- Do not place sensitive values such as identity number, full card number, or password directly in Redis keys.
- Login-wide shared user data belongs to the shared member/customer-login container pattern; module-specific temporary flow data should use its own lifecycle and must not be hidden in the shared member object.
- Appsetting files follow `appsettings.{Environment}.json`, and sections/keys use PascalCase and hierarchical semantic names.
- Large third-party service configuration should be split into a dedicated appsetting file when the interface/config volume is large.
- DB table and field names use recognizable PascalCase; stored procedures use `sp_`; views use `vw_`.

## Development Readiness Checklist

Before declaring a function development-ready, confirm:

- TSD `API清單`, API Detail `Api_List`, and API worksheets agree on API category, name, and function description.
- Request/Response fields have clear names, required flags, types, descriptions, examples, and source/meaning.
- Header dependencies, BackendAPI/DB/SP/external sources, Redis usage, and response code cases are traceable.
- Examples include representative success/failure conditions and match the actual field contract.
- Old-system names are either replaced by new-system canonical names or explicitly retained for a confirmed compatibility reason.
- Remaining unknowns are visible as `todo` / `待確認` / `unresolved`, with impact on development called out.
