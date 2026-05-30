# Rule-pack templates

Starting points for a project's `<rulesRoot>` (`<workspaceRoot>/.agent/project-rules/<workspaceKey>/`). The `workspace-onboarding` skill (`scripts/init_workspace_config.py --rule-pack ...`) copies one of these into your workspace; it never overwrites an existing rule pack.

## `generic/` — project-agnostic baseline (default)

`--rule-pack generic` copies this. It contains:

- `catalog.json` — a generic rules-root catalog wiring the **`apiCodeWriter`** rule pack to the code-guidelines below (so step 04 has dev guidelines out of the box).
- `rules/code-guidelines/p240301-v6.2/` — the generic .NET / C# guideline rules (`common-style`, `validation`, `cache`, `data-access`, `frontstage-session`, `backoffice-authz`, `logging-exception`, `config`, `test-handoff`) — usable as-is. `implementation-profile.md` is a **placeholder**: fill it with your framework slots / contracts / validation commands, or generate via `project-rule-analyzer`.

**You must add per project (not shipped in `generic/`):** the project/customer-specific categories and their rule packs — populate with `project-rule-analyzer --category <cat> --approve` and wire into the relevant pack:

- `api-contract`, `api-detail-workbook`, `field-kb` → `apiDetailSync` / `apiSpecWriter`
- `delivery-format` → `deliveryFormat`
- `sequence-diagram` + native VSDX assets → `sequenceDiagram`
- `sql-fixture` → `sqlFixture`
- `ut-report` + UT templates → `unitTestReport`

## Bundled real rule pack (same-team)

If the package shipped an `.agent` snapshot (agentBundle), it includes the source project's **fully-populated** rule pack at `.agent/project-rules/<workspaceKey>/`. Same-team installers can copy that instead of the generic baseline:

```
init_workspace_config.py --workspace-root <ws> --rule-pack <workspaceKey>
```

This is the "both" model: `generic` for fresh/other projects, the bundled real pack for same-team continuity.
