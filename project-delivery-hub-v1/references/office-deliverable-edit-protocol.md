# Office Deliverable Edit Protocol

This protocol is the shared contract for writing project delivery Office files. It covers physical edits to Word and Excel deliverables only; it does not decide business semantics or delivery-format rules.

## Scope

Use this protocol when a caller needs to save changes to:

- TSD `.docx`
- API Detail `.xlsx`
- CommonFunc / CommonUtil `.xlsx`
- Response Code or other project-owned Office workbooks

Non-Office files such as Markdown analysis, JSON handoff, source code, VSDX, and shared `.agent` status are outside this protocol.

## Caller Responsibilities

The caller owns the decision and the acceptance criteria:

- `api-detail-tsd-sync` decides API contract, field naming, BackendAPI source, Common reuse, Response Code, readiness, and handoff effects.
- `delivery-format-checker` decides format findings, severity, visual-risk status, and pass/fail.
- `design-feedback-fix-coordinator` parses feedback and routes issues back to the Design Leader.

The Office editor executes only the claimed file operations supplied by the caller.

## Plan Shape

When a design-stage leader or format checker persists a plan, use:

```text
.agent/functions/<functionCode>/orchestration/office-edit-plan.json
```

Minimal shape:

```json
{
  "schemaVersion": "1.0.0",
  "functionCode": "D.001.001",
  "owner": "api-detail-tsd-sync",
  "claimId": "office-d001001-api-detail",
  "mode": "semantic-content|format-fix|content-and-format",
  "targetFiles": [
    {
      "path": "D:/path/NEWDA_API_DETAIL_Deposit.xlsx",
      "kind": "api-detail-xlsx",
      "claimScope": "whole-file",
      "sourceOfTruth": "design-source-registry or explicit user path"
    }
  ],
  "allowedOperations": [
    {
      "file": "D:/path/NEWDA_API_DETAIL_Deposit.xlsx",
      "location": "sheet=Api_List,row=12,column=J",
      "operation": "replace-cell-text|apply-style|autofit-row|update-hyperlink|replace-docx-text",
      "before": "optional current value",
      "after": "required target value",
      "reason": "caller-owned reason"
    }
  ],
  "forbiddenOperations": [
    "write shared .agent state",
    "modify unclaimed files",
    "expand workbook-wide formatting without explicit approval"
  ],
  "validation": [
    "reopen target file",
    "run caller-specified check command",
    "report visual QA blocker if render is unavailable"
  ]
}
```

## Result Shape

When under a leader, the Office editor returns this result to the leader; the leader records it in `worker-results.json`. Standalone runs may report the same shape directly to the user.

```json
{
  "schemaVersion": "1.0.0",
  "claimId": "office-d001001-api-detail",
  "modifiedFiles": [
    "D:/path/NEWDA_API_DETAIL_Deposit.xlsx"
  ],
  "changeSummary": [
    "Updated Api_List backend source for Deposit/GetFixedDepositDetail."
  ],
  "validationCommands": [
    {
      "command": "python skills/delivery-format-checker/scripts/check_api_xlsx_format.py ...",
      "result": "passed|failed|blocked",
      "summary": "Must fix = 0; Visual risk = 0"
    }
  ],
  "blockers": [],
  "risks": []
}
```

## Write Rules

- Treat each `.docx` or `.xlsx` as a whole-file claim. Do not split one workbook by sheet across parallel workers.
- Do not write `.agent/functions/<functionCode>/handoff/*`, `.agent/functions/<functionCode>/orchestration/*`, `.agent/context/*`, `.agent/status/*`, final reports, package metadata, or chain status.
- Do not create `.bak`, `.before_*`, timestamp backup, or delivery-directory backup copies unless the user explicitly asks or the active workspace rule requires it.
- If safety requires a temporary copy, use a tool temp directory or another non-delivery area and remove it before reporting completion.
- Prefer Excel COM for saving `.xlsx` files that may contain OLE, EMF, media, controls, comments, external links, or mixed rich text. `openpyxl` may be used for read-only checks, and only for saving when the plan and file contents make that safe.
- Use `python-docx` for precise `.docx` edits when it preserves the target structure; render or reopen the document when layout fidelity matters.
- Preserve unrelated content, unrelated styles, hidden workbook assets, hyperlinks, formulas, media, OLE objects, comments, and sheet order.
- Reopen every modified Office file before reporting success.

## Validation

The Office editor must run caller-specified validation when available:

- TSD: `skills/delivery-format-checker/scripts/check_tsd_docx.py`
- API workbook: `skills/delivery-format-checker/scripts/check_api_xlsx_format.py`
- Excel format repair scripts under `skills/delivery-format-checker/scripts/` only when the plan explicitly calls for them.
- Visual/render QA when the caller requires it; otherwise report it as a remaining risk.

Completion requires: all `modifiedFiles` are claimed, files reopen, validation results are reported, and no temporary files or secrets remain in delivery/package scope.
