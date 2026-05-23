# Manifest Format

Use `scripts/bootstrap_manifest.py` to generate the initial JSON, then fill the missing fields before execution.

## Workflow

1. Generate the manifest from the report template.
2. Fill `metadata`.
3. Fill `unitTest` and optionally `integrationTest`.
4. For each case:
   - Use `mode: "unit_test"` for UnitTest-backed items.
   - Use `mode: "integration_test"` for IntegrationTest-backed items.
   - Use `mode: "api_runtime_call"` for Postman MCP actual API invocation evidence.
   - Use `mode: "code_inspection"` for items that can be verified by direct code inspection.
   - Use `mode: "manual"` for items that require human verification.
   - Use `mode: "skip"` for out-of-scope items.
   - Set `enabled: true` only after `testBindings.testNames`, `apiRuntimeCall` evidence paths, or `codeInspection.evidencePaths` is complete.
5. Run `scripts/run_report_job.py`.
6. Review the output DOCX and re-run if any case needs adjustment.

## Top-Level Fields

### `document`

- `inputPath`: source `.docx` report.
- `outputPath`: revised `.docx` output.
- `reportTitle`: optional human-readable title.

### `metadata`

- `apiDisplayName`: report header API name.
- `tester`: test owner written into the first table.
- `testDate`: `YYYY/MM/DD`.
- `actualSummary`: optional override for the summary row.
- `overallStatus`: optional override, otherwise computed from results.

### `analysisContext`

- `repoRoot`: optional repo root used to resolve relative `codeInspection.evidencePaths`.
- `contextRoot`: optional `.agent/context/<functionCode>` root for module-scoped jobs.

### `unitTest`

- `trxPath`: direct `.trx` path. Optional when `resultsDir` can resolve a `.trx`.
- `resultsDir`: directory used to search for the latest `.trx`.
- `command`: optional command executed before parsing `.trx`.
- `workingDirectory`: working directory for `command`.
- `timeoutSeconds`: command timeout in seconds.
- `failIfTrxMissing`: block when no `.trx` can be resolved.

### `integrationTest`

- Same base fields as `unitTest`: `trxPath`, `resultsDir`, `command`, `workingDirectory`, `timeoutSeconds`, `failIfTrxMissing`.
- Optional `cleanWorkspace`:
  - `enabled`: whether to stage a clean repo copy before execution.
  - `sourceRoot`: original repo root.
  - `targetRoot`: clean-copy destination root.
  - `excludeDirNames`: directories to skip while copying, typically `bin`, `obj`, `.vs`, `TestResults`.
- `command`, `workingDirectory`, `trxPath`, and `resultsDir` may use:
  - `{workspaceRoot}`: resolved execution workspace root
  - `{manifestDir}`: directory that contains the manifest

### `apiRuntimeCall`

`api_runtime_call` is configured per section item, not as a top-level command. The agent must call Postman MCP before running the report job and save the evidence artifacts.

- Default artifact folder: `.agent/context/<functionCode>/ut-report/postman-mcp/<apiId>/<scenarioId>/`.
- Required artifacts:
  - `request.json`: masked request method, URL, headers, and body.
  - `response.json`: masked response metadata/body with a parseable HTTP status.
  - `status.png`: screenshot evidence of the call status.
- Sensitive values such as `Authorization`, `Cookie`, API keys, tokens, passwords, and secrets must be masked before saving.

## Section Items

Each section contains `items[]`. Important fields:

- `caseId`: stable ID used to join manifest rows and result rows.
- `rowIndex`: Word table row index.
- `checkItem`: the original text from the document.
- `mode`: `unit_test`, `integration_test`, `api_runtime_call`, `code_inspection`, `manual`, or `skip`.
- `enabled`: when `false`, the runner marks the row as pending instead of executing it.
- `actualResult`: optional custom sentence written back to the document.
- `notes`: optional operator note.
- `manualEvidencePaths`: text evidence paths used when `mode` is `manual`.
- `codeInspection`:
  - `ruleId`: optional rule identifier.
  - `evidencePaths`: explicit code paths to inspect. Supports absolute paths plus `{repoRoot}`, `{workspaceRoot}`, and `{manifestDir}` tokens.
  - `mustContainAny`: pass when any token is found.
  - `mustContainAll`: pass only when every token is found.
  - `mustNotContainAny`: fail when any forbidden token is found.
  - `passActualResult`, `pendingActualResult`, `failActualResult`: optional status-specific sentences.
- `apiRuntimeCall`:
  - `requestPath`: path to the masked Postman MCP request JSON. Supports absolute paths plus `{repoRoot}`, `{workspaceRoot}`, `{contextRoot}`, and `{manifestDir}` tokens.
  - `responsePath`: path to the masked Postman MCP response JSON.
  - `screenshotPath`: path to the status screenshot PNG.
  - `expectedStatusCodes`: one or more expected HTTP status codes.
  - `passActualResult`, `failActualResult`: optional status-specific sentences.
- `testBindings`:
  - `testNames`: explicit UnitTest or IntegrationTest names.
  - `matchMode`: currently only `all_pass`.
  - `allowMissing`: whether missing test results are tolerated.

## Matching Rules

- `unit_test` and `integration_test` items must bind explicit `testNames`.
- `api_runtime_call` items must bind explicit `apiRuntimeCall` evidence paths and `expectedStatusCodes`; they do not require `.trx` or `testBindings.testNames`.
- `code_inspection` items must bind explicit `evidencePaths` and token rules.
- The runner does not infer or fuzzy-match test names from checklist text.
- `matchMode: "all_pass"` means:
  - all bound tests passed => case passed
  - any bound test failed => case failed
  - missing or skipped tests => case pending unless `allowMissing: true`

## Document Write-Back Rules

- Two-column UT tables: the first column becomes the result status.
- Three-column requirement tables: the middle column is filled with `actualResult`.
- Append or reuse one summary row during write-back, but keep only the single-line execution summary and do not render the `自動化證據摘要` label.

## Known Limits

- The DOCX parser assumes the first table is the report header and later tables are section tables.
- The document alone is not enough to infer test names.
- Code inspection is structural evidence. It can confirm routes, validation rules, query structure, response contracts, downloads, and notification flow, but it is not a replacement for runtime assertions when behavior must be executed.
- Postman MCP actual API calls are runtime evidence for HTTP invocation and status/response capture, but they must be labeled as `Postman MCP / 真实接口调用`, not UnitTest.
- Clean-copy execution is intended for unstable workspaces with external `bin/obj/ref/*.dll` locking; it is not a replacement for a valid test command.
- The skill validates Postman MCP status screenshots saved as artifacts; it does not call Postman MCP itself.
