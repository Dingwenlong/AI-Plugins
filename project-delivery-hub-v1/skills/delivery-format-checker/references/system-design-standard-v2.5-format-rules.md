# System Design Standard v2.5 - Format Rules

Source: `P240301_永豐商銀新大戶_系統設計規範 v2.5 20260514.docx`.

Use this reference only for project delivery-format and structure checking. It does not decide API business correctness, field semantics, backend-source validity, or cross-file API contract reconciliation.

## TSD DOCX Rules

- Chinese text uses `微軟正黑體`.
- English letters, numbers, and half-width symbols use `Times New Roman`.
- A paragraph should not mix unintended font sizes within the same visible sentence/block.
- Ordered and unordered lists should be correctly structured, not hand-typed in a way that breaks numbering.
- Version labels in TSD filenames and document text use lowercase `v`.
- The cover version must match the latest version in the revision table.
- The table of contents must be updated after content changes and should match actual headings.
- For first delivery, keep only the initial revision record unless the project explicitly requires more history.

## TSD Table Rules

- Table headers should be horizontally and vertically centered.
- Table body cells should be vertically centered.
- Body text is generally left-aligned when content is long; dates, version numbers, names, and short labels are centered.
- All TSD table cells should be vertically centered.
- Sequence diagram title rows should be centered.
- `API清單` rows should be grouped by API category, keeping the same category together.
- `API清單` is a Word table in TSD format checking. Its presence, headers, alignment, font, Traditional Chinese text, and page layout are format concerns; API semantic correctness belongs to the design-sync skill.
- The `API清單` heading and table should not be split awkwardly across pages. If a long table spans pages, repeat headers and avoid splitting a single row.

## Required TSD Structure

For standard TSD documents, check the expected visible sections:

- `功能目的(Functional Description)`
- `功能結構圖(Functional Structure Diagram)`
- `循序圖(Sequence Diagram)`
- `參考訊息來源(Reference)`
- `API清單`

The functional structure diagram should use the PRD process/flow diagram when available; if PRD has no flow diagram, the TSD should provide a self-drawn structure diagram.

## Sequence Diagram Table In TSD

- The TSD sequence diagram section should list diagram file names and descriptions in a table.
- Sequence diagram titles and table contents should use the same font/alignment rules as the rest of TSD.
- Formal diagram business correctness is checked by the sequence-diagram skill; this skill checks table existence, visible text, alignment, fonts, page layout, and obvious filename/structure issues.

## API Detail Excel Structure

- API list workbook naming follows `NEWDA_API_LIST_yyyyMMdd.xlsx` when that deliverable is in scope.
- Module-specific detail workbook naming follows `NEWDA_API_DETAIL_{ModuleEnglishName}_yyyyMMdd.xlsx`.
- API Detail workbooks should include `Api_List` or equivalent list sheet showing all interfaces.
- `Api_List` API names should hyperlink to the corresponding API worksheet.
- Each API worksheet should provide a return link to `Api_List`.
- API worksheets should contain standard visible sections such as `API  Name`, optional `Header`, `Request`, `Response`, `範例`, `For中台開發人員`, and `API 內部業務邏輯`.
- `Header` is not mandatory for every API sheet. Do not mark it missing only because the section is absent.
- Request and Response sections must be visible where the API has those contracts; format checking verifies structure, not whether the field contract is semantically correct.
- Examples should be visibly structured and consistent in layout; semantic response-code coverage belongs to design-sync.

## API Detail Excel Formatting

- Use the configured style source `configs/api-detail-excel-style.json` for executable checks and repairs.
- Treat `references/raw/Regression_Example.xlsx` and other examples as historical structure references, not as a live style-value source.
- API Detail visual repair scope should be semantic `A:G` to the last content row unless the user explicitly requests a wider scope.
- `Api_List` is not part of API Detail worksheet batch style repair. Only repair `Api_List` when the user or upstream handoff specifically names it, or when the checker finds an `Api_List` format/link issue in scope.
- Avoid using Excel `UsedRange` as the repair scope. Historical formatting pollution outside the semantic range is a visual risk or an explicit cleanup range, not permission to rewrite the whole workbook.
- On delivery workbooks that may contain media/OLE/embedded objects, use Excel COM for saving repairs where possible. Do not use `openpyxl` to save such workbooks unless it has been verified safe for that file.

## Report Boundary

- Classify findings as `Must fix`, `Should fix`, `Naming`, `Visual risk`, or `Covered`.
- Report format and structure findings with location, current state, suggested repair, reason, and impact.
- Do not rewrite API content, field names, request/response semantics, backend source, examples, or business logic unless the user explicitly asks the format checker to do content work.
- If an upstream skill edited only specific sheets, `Api_List` rows, or cell ranges, keep repair and font-slot operations inside that handoff range.
