# NEWDAWHO Implementation Profile

Runtime use: load for `frameworkProfile=newdawho.enterpriseapi` or when the API Spec / repository evidence points to the NEWDAWHO `EnterpriseAPI` workspace profile. This file is the project-owned source for EnterpriseAPI code writer details; the plugin skill entry must not restate these rules.

## Framework Slots

- Resolve framework slots before deciding whether to reuse or create files.
- Rule priority: project rule catalog framework guidance > example project files > local similar repository files.
- Do not write `EnterpriseAPI` specifications into `CustomerLogin`, `Common`, or other API projects.
- Missing `Controller / Business.Interface / Business / Entity` slots must block with diagnostics; do not fall back to whole-repository guessing.
- If the module does not exist, create the full `Controller -> Interface -> Service -> Entity` business skeleton. Test skeletons are only handed off to step 05 and must not be written by step 04.
- Default business slots:
  - `API/EnterpriseAPI/EnterpriseAPI/Controllers/<Module>Controller.cs`
  - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness.Interface/I<Module>Service.cs`
  - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/<Module>/<Module>Service.cs`
  - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/<Module>/<Module>Service.<ApiName>.cs`
  - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiEntity/<Module>/...Info.cs`
- Test target files are handoff metadata only, such as `Test/UnitTesting/...` and `Test/IntegrationTesting/...`; step 04 must not create or modify test source.

## EnterpriseAPI Contracts

- Controllers keep `[ApiVersion]` and versioned routes; do not add `[ApiController]` unless current repository framework evidence requires it.
- New `Controller` / `Service` types default to C# primary constructors unless target framework, partial type layout, or established module style blocks them.
- Service implementation files use module folders, for example `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/Setting/SettingService.cs`.
- Service return contracts keep `Task<TransactionResult<TResponse>>`.
- Failure paths may return `ResponseData = null` unless spec, legacy contract, or front-end consumer evidence requires an empty response object.
- Prefer shared `TransactionResults.Success/Failure` or equivalent repository factory. Do not add local `BuildSuccess` / `BuildFailure` methods per service unless they carry module-specific business semantics.
- When `AddBusinessScoped()` already wires services, changing `Program.cs` or `ProgramExtensions.cs` is not a routine step.

## Shared Abstractions

- Reuse existing `CommonStatic`, helper, response factory, header parser, response-code wrapper, or SQL executor patterns before adding module code.
- Do not create shared abstractions only for one API. Add `CommonStatic`-level helpers or infrastructure wrappers only when the repository already has the pattern, or at least two APIs/modules will clearly reuse it.
- Shared code must remain low-business-semantics. Candidate header lists, field priority, error messages, length limits, and business-specific constants stay in module code or handoff evidence.
- `CommonStatic.cs` should only contain cross-domain, stable, low-business-semantics utilities. One-off string trimming, null-to-empty conversion, and lightweight format conversion stay local unless reuse is proven.
- `CurrentRuntimeContextAccessor`, `RequestContextAccessor`, `UserContextAccessor`, and similar current-request identity infrastructure are high risk. Do not create or extend them unless handoff proves identity source, session key, upstream login state, and source of truth.

## Identity, Session, And Cache

- Source of truth for runtime identity must be single and auditable: verified JWT claim, session-scoped Redis key, or existing framework authentication context.
- Do not combine arbitrary header candidates, global Redis keys, and local fallback rules to invent a current user.
- If `CustId`, `KeyId`, `auth_sn`, `sub`, or equivalent identity fields lack authenticated source and session scope evidence, block with `spec_handoff_gap` or `framework_gap`.
- Treat Redis / memory / local cache as cache by default, not as business source of truth. Handoff must state authoritative store before cache values can decide business state.
- New business cache behavior must define TTL, invalidation or refresh strategy, null handling, and concurrent update policy. Missing evidence blocks or keeps the API uncached.
- For user profile, nickname, address, member data, and other externally mutable data, describe stale-read risk and acceptance conditions before using cache.
- DB plus cache write paths must state how DB success, cache failure, stale cache, empty-result cache, delete, and invalidation are handled.

## System Design V2.5 Implementation Rules

- External resource interactions use async/await by default, including HTTP, database, webservice, file IO, FTP, upload/download, and email. Async methods end with `Async`, return `Task` / `Task<T>`, and must not block with `.Result`.
- Data retrieval must follow System Design v2.5 retrieval order and handoff `dataRetrievalOrder` or equivalent. If DB/cache/API priority, cache miss behavior, inconsistency handling, or authoritative source is missing, block or mark handoff gap.
- Redis key implementation must first confirm simple shared Hash/Member lifecycle or advanced custom-key mode. Custom keys can use `[A-Za-z0-9]`, `_`, and `:` only, and must not contain spaces, new lines, percent signs, IDs, full card numbers, passwords, or secrets.
- Appsetting changes use existing `appsettings.{Environment}.json` environment-file rules. Section/key names use PascalCase and hierarchical JSON. Third-party service settings over 50 items should follow handoff or repository pattern for separate config files; do not invent arbitrary config files.
- DB object naming follows System Design v2.5: table and column names use PascalCase, stored procedures use `sp_`, and views use `vw_`. Legacy DB names are preserved only when legacy evidence is authoritative for the current API.

## Request Validation

- Put basic single-field request constraints on DTO/entity attributes when repository support exists. Examples include required, length, format, enum range, and single-field constraints.
- Service validation keeps business semantics, runtime context, DB/cache state, and cross-field rules. Do not duplicate DTO attribute validation in service code.
- Text-element length rules should use a reusable custom `ValidationAttribute`; do not degrade to UTF-16 `StringLength` / `MaxLength`.
- If spec defines exact validation failure code/message, attribute validation must map to the spec contract. If repository infrastructure cannot map attribute errors to spec code/message, mark a shared validation infrastructure gap instead of hand-writing duplicate service checks.

## C# Style And Comments

- Dependency-injection fields use `_camelCase`. Do not generate PascalCase fields such as `CtxAccessor` or `Logger`.
- Primary constructor XML comments must describe the type and every constructor parameter.
- Use concise but clear member names. Prefer `_service`, `_sqlExecutor`, and `ctx` when unambiguous; keep longer names only when needed to avoid ambiguity.
- Anonymous object initialization uses inferred names when natural, for example `new { ctx.CustId, ctx.Ip }`; use explicit property names only for rename or ambiguity.
- SQL strings default to C# raw string literals with readable SQL clause layout.
- Partial service/controller files must include their own required `using` directives. Do not rely on another partial file for extension methods such as `ILogger.LogError`.
- File-local types are allowed only when the type does not appear in non-file-local signatures.
- Null-coalescing collection operands must keep compatible types; do not combine `List<T>` with `T[]` in a way that causes `CS0019`.
- Arrays use `Length` for count checks unless the actual type is `ICollection<T>`, `List<T>`, or a LINQ result.
- New source files keep the repository file header. The header must describe file responsibility, author/date placeholders, and modification placeholders without fabricating history.
- Generated business code comments use Traditional Chinese, explain the business reason or responsibility, and avoid line-by-line narration.
- `Service` implementations may use numbered comments only when directly mapping `API_Spec.json` business steps. Supplemental explanation uses normal prose comments.
- Public methods, interface implementations, and controller actions should have responsibility-matched XML comments. Use `inheritdoc` only when the upstream interface comment is already complete and semantically exact.
- Leave one blank line before `return` in main paths, `if`, and `catch` blocks when it improves readability.

## Test Handoff And Validation

- Step 04 never writes UnitTest, IntegrationTest, or Service runtime validation source. It only records `unitTestTargetFiles`, `integrationTestTargetFiles`, SQL fixture needs, mock examples, and Service runtime validation plans for step 05.
- Preserve every `mockExamples` scenario in `testScenarioPlan`, including request payload, full response payload, expected code/message/success flag, source order, and responseData field assertions.
- For DB/SQL APIs, separate mock-based scenario/mapping UnitTests from real Service SQL runtime validation. Mock SQL tests do not prove SQL correctness.
- Real Service runtime validation should keep the real business Service and SQL executor or equivalent test DB executor, replacing only uncontrollable boundaries such as authentication context, clock, or external network calls.
- Explicit `validation-check` commands take priority. When absent, run the EnterpriseAPI API build and existing unit/integration test projects as regression validation.
- Default validation commands use `-m:1` to reduce MSBuild parallelism. Do not use `--no-build` as the default normal path.
- Stable validation command examples:
  - `dotnet build "Sinopac.DawhoEnterprise/API/EnterpriseAPI/EnterpriseAPI/EnterpriseAPI.csproj" -m:1`
  - `dotnet test "Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/EnterpriseAPIUnit.csproj" -m:1`
  - `dotnet test "Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/EnterpriseAPIIntegration.csproj" -m:1`
- Before validation, clear recoverable file-lock state when needed. For `assembly_locked`, `GenerateDepsFile`, `obj/refint/*.dll`, `ref/*.dll`, `bin/*.dll`, or `MSB3248`, use limited retries with `dotnet build-server shutdown` and cleanup of `dotnet`, `VBCSCompiler`, or `testhost` processes when explicitly allowed.
- If `dotnet build` finally fails only because of recoverable file locks, and the same round's `EnterpriseAPIUnit` and `EnterpriseAPIIntegration` `--no-build` validation pass, `apply` may downgrade to passed with a clear note in `implementation-report.md` and execution output. Code compile errors, test assertion failures, handoff gaps, and non-lock problems must not be hidden by retry or downgrade.
