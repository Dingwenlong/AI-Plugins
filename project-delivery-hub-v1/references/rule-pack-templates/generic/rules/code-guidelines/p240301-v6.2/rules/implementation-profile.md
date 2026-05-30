# Project Implementation Profile (TEMPLATE — customize per project)

Runtime use: loaded by `api-code-writer` (step 04) for your project's `frameworkProfile`, or when the API Spec / repository evidence points to your project's framework. This file is the **project-owned** source for framework-specific code-writer details; the plugin skill entry must not restate these rules.

> This is a GENERIC placeholder. Replace every `<...>` and the example bullets with your project's real framework slots, contracts, and conventions — or generate it via `project-rule-analyzer --category code-guidelines --approve` from your framework guideline document.

## Framework Slots

- Resolve framework slots before deciding whether to reuse or create files. Rule priority: project rule catalog framework guidance > example project files > local similar repository files.
- Define your project's default business slots, for example:
  - `<Controllers path>/<Module>Controller.cs`
  - `<Business interface path>/I<Module>Service.cs`
  - `<Business impl path>/<Module>/<Module>Service.cs`
  - `<Entity path>/<Module>/...Info.cs`
- Missing required slots must block with diagnostics; do not fall back to whole-repository guessing. Test target files are handoff metadata only; step 04 must not create or modify test source.

## Contracts

- State your service return contract (e.g. `Task<TransactionResult<TResponse>>`), controller attributes/versioning, dependency-injection style (primary constructors?), and failure-path conventions.

## Shared Abstractions

- Reuse existing helpers / factories / executors before adding new abstractions. Add shared `CommonStatic`-level helpers only when the repository already has the pattern or at least two modules will clearly reuse it. Keep business-specific constants/messages in module code.

## Identity, Session, And Cache

- Define the single auditable source of truth for runtime identity (verified JWT claim / session-scoped key / existing framework auth context). Block (`spec_handoff_gap` / `framework_gap`) when identity source, session model, or authoritative store is unclear. Treat Redis/memory as cache, not source of truth, unless handoff says otherwise.

## Request Validation

- Put single-field constraints (required, length, format, enum) on DTO/entity attributes; keep business / cross-field / runtime-context checks in the service. Map attribute validation failures to the spec code/message.

## C# Style And Comments

- Define your project's naming, comment, namespace, SQL-literal, and file-header conventions. The generic baseline is in `common-style.md`.

## Test Handoff And Validation

- Step 04 never writes UnitTest / IntegrationTest / Service runtime validation source; it only hands off targets, scenarios, fixture needs, and runtime-validation plans to step 05.
- Define your project's validation commands here, for example:
  - `dotnet build "<your-api.csproj>" -m:1`
  - `dotnet test "<your-unit.csproj>" -m:1`
  - `dotnet test "<your-integration.csproj>" -m:1`
- Use limited retries for recoverable file locks (`assembly_locked`, `GenerateDepsFile`, `ref/*.dll`); never hide compile errors, assertion failures, or handoff gaps behind retry or downgrade.
