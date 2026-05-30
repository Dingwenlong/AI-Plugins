# Design Leader Protocol

This protocol is shared by design-stage skills that need to coordinate multiple delivery files before stage 02. It applies to PRD/TSD/API Detail/Common/Response Code design work and customer feedback fixes.

## State Location

Design-stage orchestration state lives under:

```text
.agent/functions/<functionCode>/orchestration/
```

Do not write design orchestration state into `.agent/context/<functionCode>/`; `.agent/context` is reserved for the 02-05 execution chain.

## Artifacts

| Artifact | Purpose | Writer |
| --- | --- | --- |
| `design-change-plan.json` | Customer/new-demand issues, affected files, planned edits, validation scope | leader only |
| `file-claims.json` | File ownership for workers, including binary Word/Excel locks | leader only |
| `office-edit-plan.json` | Precise Word/Excel write plan for the Office editor when `.docx` or `.xlsx` files are claimed | leader or format checker |
| `office-edit-results.json` | Optional persisted Office editor results when the leader wants a separate Office write log | leader only after Office editor return |
| `worker-results.json` | Collected worker reports: modified files, validation, blockers, risks | leader only after worker return |
| `final-design-fix-report.json` | Final design-stage verdict, validation summary, handoff readiness | leader only |

JSON Schemas for these artifacts live in `skills/api-detail-tsd-sync/schemas/` (`design-change-plan`, `office-edit-plan`, `file-claims`, `worker-results`, `final-design-fix-report`, `office-edit-results`); validate against them before and after writing. The design-stage `file-claims.json` schema differs from the dev-execution one at `skills/multi-api-leader/schemas/file-claims.schema.json` — design-stage `targetFiles` entries are `{path, kind, claimScope}` objects, the dev-execution one uses plain file-path strings.

The leader may also update `.agent/functions/<functionCode>/handoff/development-handoff.json`, source/copy hashes, and high-level chain status after all worker changes are verified.

## Leader Responsibilities

- Resolve `functionCode`, workspace, project rules, registry entries, and authoritative source files before assigning work.
- Decide business semantics: API contract, field naming, BackendAPI source, CommonFunc/CommonUtil reuse, Response Code, readiness, and sequence-diagram impact.
- Create `design-change-plan.json` before edits when multiple files or workers are involved.
- Create `file-claims.json` and group overlapping write targets into the same serial work group.
- Treat `.docx`, `.xlsx`, `.vsdx`, and other compound/binary delivery files as file-level locks. Do not split one workbook by sheet across parallel workers.
- For Word/Excel write claims, create or hand off `office-edit-plan.json` and use the `专案 Office 交付文件编辑器` boundary for physical saves.
- Spawn workers only for disjoint write sets; keep immediate blocking judgment work local.
- Validate every worker `modifiedFiles` entry against `file-claims.json` before accepting changes.
- Run focused validation and update shared state, hashes, handoff, and final reports serially.

## Worker Contract

Each worker prompt must include:

- `functionCode`
- `workGroupId` or `claimId`
- exact writable file paths
- read-only context paths
- forbidden paths, including shared `.agent` status/handoff/final report files
- expected return fields: `modifiedFiles`, summary, validation commands/results, blockers, risks

Workers must not write:

- `.agent/functions/<functionCode>/handoff/*`
- `.agent/functions/<functionCode>/orchestration/*`
- `.agent/status/*`
- `.agent/context/*`
- final reports, chain status, or package metadata

Workers may read shared `.agent` artifacts and project rules, but they only edit claimed source/delivery files.

Word/Excel workers must follow `references/office-deliverable-edit-protocol.md` and return an Office edit result to the leader. They must not write shared orchestration artifacts themselves.

## Feedback Fix Flow

For customer feedback, SA issue lists, or email-based fixes:

1. Parse feedback into discrete issues with source evidence.
2. Map each issue to affected files: TSD, API Detail, CommonFunc, CommonUtil, Response Code, analysis, handoff, sequence-diagram impact.
3. Ask the design sync rules to decide semantics; do not duplicate API contract rules in feedback-specific instructions.
4. Build `design-change-plan.json` and `file-claims.json`.
5. Build `office-edit-plan.json` for claimed `.docx` / `.xlsx` writes, then dispatch the Office editor or other disjoint workers.
6. Leader validates modified files, updates analysis and handoff hashes, and writes `final-design-fix-report.json`.

## Validation Checklist

- Target TSD/API Detail/Common files match the authoritative source registry or explicit user path.
- No worker modified unclaimed files.
- Word/Excel files were saved through the Office editor boundary or an equivalent explicit plan, and are readable after save.
- TSD/API Detail semantic checks cover the changed API rows, sheets, and examples.
- Format checker has run for changed Word/Excel files, or any remaining format risk is reported.
- `development-handoff.json` hashes match changed analysis/input files.
- Sequence-diagram changes are either completed by the VSDX skill or explicitly listed as pending.
- No `.bak`, `.before_*`, timestamp backup, private config, webhook URL, debug log, or worker scratch file remains in delivery/package scope.
