# EnterpriseAPI Runtime Validation Rules

Runtime use: load for `unitTestReport` work when the API belongs to the NEWDAWHO `EnterpriseAPI` framework profile. This file owns EnterpriseAPI configured-connection runtime validation wording and evidence requirements; the UT report skill entry must not restate these project-specific details.

## Configured-Connection Evidence

- For every DB / SQL API, create or update EnterpriseAPI configured-connection runtime validation.
- The validation loads EnterpriseAPI `appsettings.json` connection strings, uses the formal `SqlDbFactory` / `SqlExecutor` path, and executes Service SQL against the configured database.
- LocalDB or SQL fixture tests may be added for controlled seed, mapping, join, and ordering checks, but they do not replace configured-connection runtime validation.
- Do not put configured-connection validation into a narrow UnitTest project, and do not silently substitute LocalDB evidence for it.
- If configured database login, permission, schema, or network access is unavailable, keep the evidence gap visible and do not mark configured-connection validation as passed.

## Target Test Files

- Unit test targets may include `Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/*ControllerTest.cs`, `Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/*ServiceTests.cs`, and related support fixtures.
- Integration/runtime validation targets may include `Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/*ControllerTests.cs` and Service runtime validation support.
- Step 05 owns these test source files. Step 04 only writes target paths and handoff plans.

## Report And Checklist Rules

- For DB-backed APIs, keep at least two evidence lanes visible:
  - mock-based UnitTests for spec examples, response contract, and mapping logic
  - IntegrationTest / Service runtime validation using configured connection or approved test DB evidence
- Mock SQL and LocalDB fixture evidence must not imply that configured database SQL execution has been verified.
- Do not add broad environment assumptions such as "EnterpriseAPI configured connection string can open" to a single feature checklist. That belongs to configured-connection IntegrationTest / Service runtime validation evidence.
- When DB-backed API lacks configured-connection runtime evidence, affected checklist rows must remain failed or blocked with a concise reason, such as missing Service SQL execution, schema/table/column check, or DB permission check.
- Runtime SQL execution, schema/table/column consistency, and least-privilege DB permission checks apply only to DB-backed APIs.
- Production pre-go-live environment confirmation is a release condition and should be marked not applicable in UT reports unless the report explicitly covers that release verification.

## Wording Rules

- Describe mock-based UnitTests as validating spec examples and Service mapping logic.
- Describe LocalDB/fixture tests as validating Service query, sorting, join, and field conversion against controlled test data.
- Describe EnterpriseAPI configured-connection tests as validating formal SQL executability with EnterpriseAPI configured connection.
- If EnterpriseAPI configured-connection evidence is missing or failed, use restrained wording such as: "本次已完成规格范例与 Service 映射逻辑验证；EnterpriseAPI 设定连线 SQL 执行因测试资料库连线、权限或环境资料未就绪，需补齐后确认。"
- Do not describe a DB-backed API as fully production-runtime validated until configured-connection evidence or an approved equivalent is present.
