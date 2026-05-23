# Artifact Naming Standard

This standard defines the next naming shape for artifacts created under the shared `.agent` workspace. It is a standard-only document for now: existing `.agent` files are not renamed by this round.

## Naming Rules

- Machine-consumed artifacts use lowercase kebab-case.
- Stage-owned artifacts use a stage prefix: `01-`, `02-`, `03-`, `04-`, or `05-`.
- Design analysis and design-to-development handoff artifacts use `00-`.
- Artifacts maintained across multiple skills use the `chain-` prefix.
- `functionCode` keeps its dots, for example `D.003` and `N.001.001`.
- Files copied into `.agent/functions/<functionCode>/inputs/` keep their original source filenames.
- Customer formal delivery names keep project delivery standards first, even when they do not match internal `.agent` naming.

## First-Round Mapping

| Current name | Proposed name | Owner | Action |
| --- | --- | --- | --- |
| `development-handoff.json` | `00-design-handoff.json` | Design sync | Rename later |
| `<functionCode>_功能设计梳理_yyyyMMdd.md` | `00-功能设计梳理_<functionCode>_<yyyyMMdd>.md` | Design sync | Rename later |
| `reference/global/catalog.json` | `01-reference-catalog.json` | 01 Reference index | Rename later |
| `execution-batch.json` | `chain-execution-batch.json` | Shared chain | Rename later |
| `execution-state.json` | `chain-execution-state.json` | Shared chain | Rename later |
| `api-checklist.json` | `chain-api-checklist.json` | Shared chain | Rename later |
| `apis/<apiId>/manifest.json` | `chain-api-manifest.json` | Shared chain | Rename later |
| `<functionCode>_API_Spec.json` | `02-api-spec_<functionCode>.json` | 02 API spec | Rename later |
| `spec-progress.md` | `02-spec-progress.md` | 02 API spec | Rename later |
| `fixture-progress.md` | `03-fixture-progress.md` | 03 SQL fixture | Rename later |
| `db-fixture-report.json` | `03-db-fixture-report.json` | 03 SQL fixture | Rename later |
| `table-checks.json` | `03-table-checks.json` | 03 SQL fixture | Rename later |
| `seed-plan.sql` | `03-seed-plan.sql` | 03 SQL fixture | Rename later |
| `seed-executed.sql` | `03-seed-executed.sql` | 03 SQL fixture | Rename later |
| `seed-manifest.json` | `03-seed-manifest.json` | 03 SQL fixture | Rename later |
| `repo-snapshot.json` | `04-repo-snapshot.json` | 04 Code writer | Rename later |
| `code-progress.md` | `04-code-progress.md` | 04 Code writer | Rename later |
| `change-plan.json` | `04-change-plan.json` | 04 Code writer | Rename later |
| `implementation-report.md` | `04-implementation-report.md` | 04 Code writer | Rename later |
| `diagnosis-report.json` | `04-diagnosis-report.json` | 04 Code writer | Rename later |
| `test-evidence.json` | `04-validation-evidence.json` | 04 Code writer | Rename later |
| `code-contract-review.json` | `04-code-contract-review.json` | 04 Code writer | Rename later |
| `review-notes.json` | `04-review-notes.json` | 04 Code writer | Rename later |
| `module-scope.json` | `05-module-scope.json` | 05 UT report | Rename later |
| `coverage-gap.json` | `05-coverage-gap.json` | 05 UT report | Rename later |
| `<functionCode>_native_visio_spec.json` | `sequence-native-vsdx-spec_<functionCode>.json` | Native VSDX | Rename later |
| `<functionCode>_sequence.puml` | `sequence-diagram_<functionCode>.puml` | Native VSDX | Rename later |
| `<functionCode>_plantuml_落版說明.md` | `sequence-layout-notes_<functionCode>.md` | Native VSDX | Rename later |
| `vsdx/<functionCode>_01.vsdx` | `vsdx/<functionCode>_01.vsdx` | Native VSDX | External delivery exception |
| `专案交付中枢_主流程图.svg` | `专案交付中枢_主流程图.svg` | Plugin packager | Keep |
| `专案交付中枢_技能与agent架构图.svg` | `专案交付中枢_技能与agent架构图.svg` | Plugin packager | Keep |
| `专案交付中枢_工作区与agent结构树.svg` | `专案交付中枢_工作区与agent结构树.svg` | Plugin packager | Keep |
| `project-rules/<workspaceKey>/catalog.json` | `project-rules/<workspaceKey>/catalog.json` | Project rules | Keep |

## Check Script

Run the read-only checker before a naming migration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\<username>\plugins\project-delivery-hub-v1\skills\plugin-packager\scripts\check_artifact_names.ps1 -AgentRoot D:\Devs\<PROJECT>\.agent
```

The script reports old names that still match `rename_later` mappings. It does not rename, delete, or move any file.

## Migration Boundary

The next migration round must update readers and writers first, then copy or rename artifacts with backups where needed. Until that round is approved, new files may begin using the proposed names, but existing `.agent` files remain untouched.
