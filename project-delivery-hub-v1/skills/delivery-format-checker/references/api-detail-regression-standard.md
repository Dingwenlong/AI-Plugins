# API Detail Excel Regression Standard

This standard defines the structural checks for 既有专案 API Detail worksheets. Visible style values are configuration-driven and must be read from `configs/api-detail-excel-style.json`.

## Template Resource

- Style configuration: `configs/api-detail-excel-style.json`
- Historical structure reference: `references/raw/Regression_Example.xlsx`
- Validation scope: worksheet layout and visible formatting only.
- This standard does not validate API business semantics, field naming correctness, backend source correctness, or whether an API design is complete.
- The configuration file intentionally does not store source workbook, source sheet, or extraction date metadata.

## Style Configuration Priority

For API Detail formatting checks and repairs, load `configs/api-detail-excel-style.json` before applying any style rule. The configuration is the highest priority source for column widths, row heights, fills, fonts, bold flags, alignments, borders, and merged-cell border continuation. Fixed row heights must be written with the exact Excel height values from the configuration, such as `15.95`, `20.1`, and `17.1`; rounded integers are reporting aids only.

The `regions` object is authoritative for stable API Detail areas and must be applied per region:

- `apiNameDescription`: `API  Name` / `API Description`, method and description cells, and the `返回API_List` link.
- `header`: optional region. If a worksheet already has a `Header` section, check and repair its title, field header, and content rows; if it is absent, do not report it as missing and do not insert it automatically.
- `request`: `Request` title, field header, and Request content rows.
- `response`: `Response` title, field header, and Response content rows.
- `example`: `範例` title, scenario header, scenario rows, `B:C` / `D:F` merges, and JSON row height handling.
- `middleOffice`: `For中台開發人員` yellow title row.
- `internalLogic`: `API 內部業務邏輯` title, logic header, logic rows, and `B:F` merges.

`references/raw/Regression_Example.xlsx` remains useful for historical structure comparison, but it is not the style-value source during normal checks or repairs.

## Required Section Order

API Detail worksheets should keep this visible block order:

1. `API  Name` / `API Description`
2. `Request`
3. `Response`
4. `範例`
5. `For中台開發人員`
6. `API 內部業務邏輯`

Missing sections, duplicated section titles, or reversed section order are format/structure findings.

## Section Title And Separator Rows

- Worksheet names should default to `API alias + Chinese description`, while respecting Excel's 31-character sheet-name limit. Use `short API alias + Chinese description` only when the default `API alias + Chinese description` would exceed 31 characters or be truncated by Excel. The full API method remains in the API Detail `API Name` and the `Api_List` display text; do not shorten the interface name just because the worksheet tab uses a short alias. When the user or delivery context provides an official sheet-name list, that list has priority over older workbook names.
- For D.001/D.002 Taiwan/foreign-currency demand-deposit query scope, do not treat the old 3 D.001/D.002 sheets as the standard. The formal synchronized sheet set is:
  - `GetDDAccts取臺外幣活存帳號`
  - `GetDDTxns取活存交易明細`
  - `GetDDSrchHist取活存搜尋記錄`
  - `MaintainDDSrch維護活存搜尋記錄`
- For D.001.001/D.002.001 Taiwan/foreign-currency fixed-deposit query scope, choose the formal worksheet name by length:
  - `GetFixedDepositDetail取定存明細` fits within 31 characters, so use the full API alias plus Chinese description.
  - `PatchFixedDepositTitle修改定存名稱` fits within 31 characters, so use the full API alias plus Chinese description.
  - `GetFixedDepositInterestDetail取計息明細` exceeds 31 characters, so use short name `GetFDInterestDetail取計息明細`; the full API method remains `GetFixedDepositInterestDetail`.
- If both old and formal names exist, report `Naming` / `Should fix`: keep the formal sheet, remove or rename the old sheet, and update `Api_List` hyperlinks. If Excel truncates a formal sheet name to 31 characters, validate it by unique API method prefix plus the `Api_List` display text instead of treating it as missing.
- The `API  Name` first row should only style `A:B` as the visible two-cell title table. Cell `C1` may contain a `返回API_List` internal hyperlink pointing to `#'Api_List'!A1`; this link cell should keep normal hyperlink styling, including light blue `#0563C1` and underline, with no fill and no border. Cells `D:G` on that row should remain visually blank, with no fill, no border, and no unnecessary merge.
- `Api_List` entries in the current check/repair scope must also link back to their API worksheets:
  - The API-name column, usually column `E`, should display the API method name and contain an internal hyperlink/subAddress to the corresponding API worksheet `A1`.
  - Missing hyperlinks or links pointing to an unrelated API worksheet are `Should fix` findings.
  - Do not create duplicate API rows when repairing hyperlinks. If an API method already has an authoritative `Api_List` row in the current scope, update that existing row instead of appending a new one. Duplicate rows for the same API method in the current function scope are `Should fix`; keep the more complete/authoritative row, such as the row with fuller PRD coverage or the row explicitly selected by the user, and remove the extra duplicate row.
  - Resolve the target by actual worksheet name. Because Excel limits sheet names to 31 characters, long API method names may be truncated; prefix matching is acceptable only when it uniquely identifies the intended worksheet, such as `GetFixedDepositInterestDetail*` resolving to `GetFixedDepositInterestDetail取定`.
  - Repairs should preserve the displayed API method text and only update the internal hyperlink target, using normal hyperlink styling: underline plus the workbook theme hyperlink color, typically the light blue `#0563C1`. Do not hard-code pure blue `#0000FF` or use followed-link purple.
- The visible API Detail table is bounded by `A:G`. Data rows must not retain merges that cross beyond column `G`, such as `G:H`, because those merges make the remarks column right border misalign with adjacent rows. Repairs must not apply black borders, fills, or table styling from column `H` onward; accidental black borders in blank cells beyond `G` must be removed or converted to white/no-border styling. Rows below the last populated content row are also outside the content area and must not retain black table borders. Disable worksheet gridlines for API Detail sheets so the empty area outside the content range blends into the white background instead of looking like a table.
- Keep one truly blank separator row immediately above `Response`.
- Keep one truly blank separator row immediately above `範例`.
- Blank separator rows must have no content, no fill, and no border.
- Blank separator rows must also have no merged cells. When repairing a row that previously belonged to scenario merges such as `B:C` / `D:F`, unmerge it before clearing styles so merged-cell ghost borders do not remain visible.
- Do not delete the separator rows above `Response` and `範例` when cleaning blank rows inside field tables.
- Single-label blue title rows should merge their visible range when only the leftmost cell contains title text:
  - `Request` and `Response`: merge `A:G`.
  - `範例` and `API 內部業務邏輯`: merge `A:F`.
- After merging, every section title range must have a complete thin black outer frame on the merged range: left, right, top, and bottom. Do not rely only on the top-left cell's XML border or on the next row's border to visually complete the section title.
- Blue section title rows must follow the regression template per section, not a single global font:
  - `Request`, `Response`, and `API 內部業務邏輯`: `Times New Roman`, `10pt`, bold, fill `#BDD7EE`.
  - `範例`: `微軟正黑體`, `10pt`, bold, fill `#BDD7EE`.
  - Treat repaired `Microsoft JhengHei 11pt` or other blanket styling as format drift.

## Column Width And Row Height Baseline

Compare columns `A:G` and row heights against `configs/api-detail-excel-style.json`. A small tolerance is acceptable because Excel stores widths differently depending on renderer and DPI. For fixed rows, compare against the exact Excel row-height baseline, not the rounded integer display.

Configuration-derived widths:

- A: `24`
- B: `34`
- C: `12`
- D: `6`
- E: `41`
- F: `32`
- G: `72`

Configured fixed row heights use the baseline Excel values directly: section title `15.95`, table header `15`, normal content `20.1`, and middle-office title `17.1`. Use half-up rounding only when a report needs an integer explanation, for example `15.95 -> 16`, `17.1 -> 17`, and `20.1 -> 20`. Long content rows should wrap text, use Excel COM AutoFit, then round up while staying at or above the configured normal content row height.

## Scenario Block

The `範例` block must use the regression scenario table layout:

- Header row labels: `情境說明`, `Request`, `Response`
- Merge layout on the scenario header and every scenario row:
  - `B:C`
  - `D:F`
- Only the scenario header row should be bold. Scenario data-row labels in the `情境說明` column, including Chinese scenario descriptions, should use regular weight and must not be bold.
- Scenario labels and scenario count are API-design content. Do not force a fixed global list of scenario labels during format checking. Keep existing business-specific scenario labels unless the API design skill explicitly decides to change them.

Business-positive scenario cells usually contain both Request JSON and Response JSON. Non-positive scenarios usually leave Request blank and contain only Response JSON, but format repair must not delete or rewrite existing Request/Response content to enforce that convention.

The scenario block itself should not contain extra blank worksheet rows between scenario rows. If legacy formatting leaves internal blank rows that split or compress scenario rows in PDF output, remove those internal blanks and restore the affected scenario row borders, merges, and Response content. The only expected blank row around the block is the separator immediately above the `範例` title row.

## Middle-Office Block

The `For中台開發人員` row should merge `A:F`.

## API Logic Block

The row after `API 內部業務邏輯` is the logic header row and should follow the template header shape.

Every populated logic row below it should merge `B:F`, including:

- `#`
- `涉及BackendAPI`
- numbered logic step rows

Logic rows should wrap text, keep one step per line, and use leading two spaces for sub-step indentation when sub-steps are present. This is a format/readability rule; do not judge whether the business logic itself is correct in this skill.

## JSON And Wrapped Text

- Request / Response field-table example cells use a single-line JSON field fragment, not a bare sample value:
  - Use `"fieldName":value` for every populated example cell.
  - Quote string values, for example `"responseCode":"0000"` and `"responseMessage":"成功！"`.
  - Use JSON-native lowercase booleans and null, for example `"isSuccess":true` or `"isSuccess":false`.
  - Use compact object/array fragments for parent fields, for example `"responseData":{}` and `"debitAccountList":[]`.
  - Do not use bare `TRUE`, `0`, `成功！`, Excel date values, scientific-notation account/card numbers, or a fragment whose key does not match the row field name.
  - Leave child-field examples blank when that scenario does not return those fields; do not fill failure scenarios with successful account/card data.
- JSON examples in `範例` should be pretty-printed with line breaks and indentation.
- Use Excel line feed (`LF` / Alt+Enter style) inside cells rather than extra worksheet rows.
- Wrapped content rows must have sufficient row height so PDF rendering does not hide text.
- Request/Response cells inside `範例` should be vertically centered.
- Request/Response JSON cells in `範例` must not be bold. When repairing mixed-font JSON, clear `Bold=True` on both the cell fallback font and each visible rich-text run.
- JSON mixed-font display should be repaired first with the skill's Excel COM dual-font-slot mode, not by default rich-text splitting. In visible Excel rendering, English letters, digits, JSON punctuation, spaces, and other half-width characters should use `Times New Roman`; Chinese/CJK/full-width characters should use `微軟正黑體`.
- Only use per-character/rich-text run repair when the COM dual-font-slot mode still fails visible rendering and the user accepts deep rich-text changes.
- Short enum notes in field remarks should use in-cell line feeds when a single-line rendering would touch or overflow the right border. For example, `ONCE` / `DAILY` / `MONTHLY` style remarks should be split into one enum per line and row height recalculated.

## Terminology

- API Excel visible text must not use `校驗`.
- Use `驗證` when the wording refers to validation flow, validation result, validation rule, or system-side validation behavior.
- Use `檢核` when the wording refers to checklist items, manual checking, review checks, or a control/check item.
- Report `校驗` as a wording issue even though it is not Simplified Chinese; it is a project delivery terminology preference.

## Request / Response Field Table Borders

- Request and Response field tables must keep complete visible borders across the `A:G` table range, including the field header row. The header row should have all four borders so it remains complete even if the section-title border above is stored differently by Excel.
- Prefer Excel COM when repairing border drift in delivery workbooks, especially workbooks with media/OLE objects. Apply borders to the visible table cells and then render PDF/PNG to confirm the visual result.
- Be careful when validating with `openpyxl`: Excel may store a visible grid line as the left/top border of the adjacent cell rather than as every cell's right/bottom border. Do not fail a workbook solely because individual XML cells lack `right` or `bottom` when Excel COM or rendered output confirms the visible table line exists.

## Formatting Baseline

Apply the general API XLSX rules from the skill in addition to the configuration-driven regional layout:

- Font size: `10`
- Chinese/CJK/full-width visible text: `微軟正黑體`
- English/numeric/half-width visible text: `Times New Roman`
- For repair, prefer Excel COM font slots (`NameFarEast=微軟正黑體`, `Name/NameAscii/NameOther=Times New Roman`) over rich-text run splitting. After any non-COM save path, rerun the COM font-slot repair and validate visible font with `Characters(start, length).Font.Name` samples: Chinese/CJK characters should show `微軟正黑體`, while English, numbers, and half-width symbols should show `Times New Roman`.
- Region-specific fills, bold flags, alignments, row heights, and borders must come from `configs/api-detail-excel-style.json`.
- Border-only Excel COM repairs must preserve those configured fills. In particular, table headers and the internal-logic label column use `fills.tableHeaderLight` (OpenXML theme `9`, tint `0.5999938962981048`, visual sample RGB `FFC6E0B4`; Excel COM writes this as `ThemeColor=10`, `TintAndShade=0.5999938962981048`); do not replace it with hard-coded bright green such as `FFCCFFCC`.
- Content rows must also have a closed outer frame. `Request` / `Response` content extends through column `G`; `範例` and `API 內部業務邏輯` content extends through column `F`. Before repairing those edges, clear black borders from rows below the last populated API Detail row so blank bottom space does not look like part of the table.
- `API Description` content uses the configured gray fill `FFF2F2F2`.
- `For中台開發人員` uses the configured yellow fill `FFFFFF00` and row height `17.1`.
- Merged title, scenario, and logic regions must use the configured border presets so the visible outer frame and continuation lines survive after merging.
- Alignment follows the skill-wide API XLSX rule:
  - A-column sequence cells matching `^\d+(\.\d+)*$`, plus `#`, `Number`, and `序號`, are horizontally centered and vertically centered.
  - Other populated cells are horizontally left-aligned and vertically centered, including multiline JSON, code-like text, and business-logic cells.
- Section/header rows use their configured regional fills and visible borders.
- Blank separator rows should remain visually blank: no fill and no border. The area outside the configured content range, including the blank area below the last content row, should also be visually blank; remove black borders first, then use `showGridLines=false` and a white/no-border viewport fallback only where Excel would otherwise still show visible lines.
- Page setup should fit width to one page for PDF review.

## Operational Repair Rules

Use these rules when a check result turns into an actual repair. They intentionally live in this reference file so `SKILL.md` can stay focused on workflow and boundaries.

- API Detail whole-sheet cleanup should prefer the rebuild-from-text flow: extract the target worksheet's visible `A:G` semantic text and standard sections, create a clean worksheet, and refill it from `configs/api-detail-excel-style.json`. If the worksheet has formulas, comments, external hyperlinks, shapes, images, controls, OLE embeddings, or important content outside `A:G`, stop and report `Visual risk` before choosing custom extraction or narrow in-place repair.
- `Api_List` full-page cleanup should read the `apiList` configuration before changing layout. The configuration carries `A:J` widths, header styling, data-row styling, sort behavior, row AutoFit, API-name hyperlink styling, and `後端來源` styling. The preferred flow is: extract `A:J` text and API-name internal links, validate that rebuild is safe, recreate `Api_List`, sort/fill rows, restore hyperlinks, apply configured style, AutoFit, then recheck.
- Do not repair `Api_List` by repeatedly patching old borders, fills, or row heights when a full-page rebuild is in scope. Use narrow in-place repair only for explicitly scoped hyperlink/style/bottom-border fixes.
- The top `API  Name` area is intentionally narrow: only `A:B` use the visible two-cell table style. Keep `A1:B1` at `15.95`, `A2:B2` at `20.1`, preserve the right border on `B1:B2`, place `返回API_List` in `C1` when repairing the return link, and keep `D:G` blank with no fill, border, or unnecessary merge.
- Return-link target should be `#'Api_List'!A1`. If a legacy workbook puts the return link in `E1` or another non-table cell, report `Should fix`, move it to `C1`, and clear the old cell content/style.
- API Detail content boundaries must be repaired at the real visible edge: `Request` / `Response` content closes through column `G`, while `範例` and `API 內部業務邏輯` close through column `F`. Clear residual borders below the last populated row before restoring the valid content frame.
- Bottom borders must be visually complete on the final visible row of every section. Evaluate merged ranges by their visible merged extent, not only by the top-left XML cell.
- For `For中台開發人員`, keep one truly blank separator row above it, merge the title row as `A:F`, use the configured yellow fill, and never apply the normal blue section-title style to this row.
- For `API 內部業務邏輯`, merge every continuous populated logic row as `B:F` until the first truly blank separator row. Do not merge across blank rows into appended tables or non-logic content. If cells `C:F` contain text before merge, merge content left-to-right into `B` and do not silently drop text.
- After any non-COM `.xlsx` save path, run the Excel COM dual-font-slot pass before claiming font compliance. Use `Characters(start, length).Font.Name` samples for visible Chinese and Latin/numeric characters because mixed-font cells may return a blank `Range.Font.Name`.
- Short enum notes in remarks, such as `ONCE` / `DAILY` / `MONTHLY`, should use in-cell line feeds and recalculated row height when a single-line version would touch or overflow the right border.

## Multi-Sheet Workbook Handling

Many DAWHO API Detail workbooks contain multiple API worksheets plus list sheets such as `Api_List`. For regression checking:

1. Treat each API worksheet as an independent `API_Detail`-style sheet.
2. Exclude list/index sheets unless the user explicitly asks to check them.
3. If using a single-sheet regression checker, copy the target API worksheet to a temporary workbook and apply structure checks there; style validation must still use `configs/api-detail-excel-style.json`.
4. Preserve the original workbook and embedded objects; use Excel COM for saving delivery workbooks that contain OLE/media.
