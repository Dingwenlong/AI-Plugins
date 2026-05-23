# Sample-Derived TSD DOCX Standard

Baseline source: `TSD.N.006_登入記錄查詢_v1.2_20260312.docx`.

This standard is intentionally sample-derived. Treat hard structural requirements as `FAIL`, and filename/version drift or style mismatches as `WARN` unless the user asks for strict enforcement.

## File Naming

Expected pattern:

```text
TSD.<module>.<number>_<function-name>_v<major.minor>_<yyyymmdd>.docx
```

Example:

```text
TSD.N.006_登入記錄查詢_v1.2_20260312.docx
```

## Document Skeleton

Expected visible order:

1. Cover page text:
   - `新大戶系統`
   - `系統規格設計書`
   - `版本 x.y`
2. `版本修訂`
3. Revision table with columns:
   - `版本`
   - `修改日期`
   - `修改人`
   - `PRD版本`
   - `修改記錄`
4. `目錄`
5. TOC entries for:
   - `1. 功能目的(Functional Description)`
   - `2. 功能結構圖(Functional Structure Diagram)`
   - `3. 循序圖(Sequence Diagram)`
   - `4. 參考訊息來源(Reference)`
   - `5. API清單`
6. Body heading 1 chapters:
   - `功能目的(Functional Description)`
   - `功能結構圖(Functional Structure Diagram)`
   - `循序圖(Sequence Diagram)`
   - `參考訊息來源(Reference)`
   - `API清單`

The sample uses Word `Heading 1` style for the five body chapters and `TOC1` / `toc 1` for TOC lines.

## Section Content Rules

- `功能目的(Functional Description)`: require at least one non-empty paragraph before the next heading.
- `功能結構圖(Functional Structure Diagram)`: require at least one embedded image before the next heading.
- `循序圖(Sequence Diagram)`: require a table with header `編號`, `檔名`, `內容說明`.
- `參考訊息來源(Reference)`: require non-empty content. `無。` is acceptable.
- `API清單`: require a table with header `API類別`, `API 名稱`, `功能說明`, plus at least one data row.

## Language Rules

- All Chinese content must use Traditional Chinese.
- Simplified Chinese characters are blocking compliance errors and should be converted to their Traditional Chinese equivalents.
- The bundled structural checker scans visible paragraphs and table cells for common Simplified Chinese characters and reports representative locations.
- Visible TSD wording must not use `校驗`. Use `驗證` for validation flow, validation result, validation rule, or system-side validation behavior; use `檢核` for checklist items, manual checking, review checks, or control/check items.
- Report `校驗` as a terminology issue even though it is not Simplified Chinese; it is a project delivery wording preference.

## Revision Rules

- Revision table must have at least one data row.
- Revision version values should match `major.minor`, such as `1.3`.
- Revision dates should match `yyyy/mm/dd`.
- `修改人`, `PRD版本`, and `修改記錄` should be non-empty.
- Latest revision table version should match the cover page `版本 x.y`.
- Data cells should keep vertical center alignment.
- Data cells should keep the sample Chinese font family pattern (`微軟正黑體` / `SimSun`); `DengXian` indicates likely accidental formatting drift.
- Chinese content should use `微軟正黑體`; non-Chinese Latin/numeric content should use `Times New Roman`.
- Data cells should use 12 pt font size, matching `TSD.E.001_匯率表_v1.7_20260511.docx`.
- Long `修改記錄` cells should not be center-aligned because it changes line wrapping. The sample uses default/justified wrapping for longer note cells.

## Table Formatting Rules

### 循序圖(Sequence Diagram)

- Data row cells should keep vertical center alignment.
- `編號` and `檔名` data cells should be horizontally centered.
- `內容說明` data cells should not use two-side `both` alignment; keep the sample default/left-like alignment.

### API清單

- Data rows should not use italic formatting.
- `API類別` and `API 名稱` data cells should not be bold.
- `功能說明` may be bold in the sample, but should not be italic.
- Header and data cells should use 10 pt font size, matching `TSD.E.001_匯率表_v1.7_20260511.docx`.
- The API list heading and table should not be split into a few rows on one page and the remaining rows on the next page. For short API lists that fit on one page, start the `API清單` section on a new page and keep table rows from splitting across pages. For long API lists, repeat the header row and still prevent individual rows from splitting.

## Page and Footer Rules

Expected page setup:

- A4 portrait: width `11906`, height `16838` twips.
- Margins: top `1440`, bottom `1440`, left `1083`, right `1083` twips.
- Footer text includes `版權所有：昱勝資訊股份有限公司 All Rights Reserved`.

## Known Limits

- Automatic TOC page numbers and hidden numbering fields may need Word rendering for perfect validation.
- Embedded diagram content is only checked as "image exists", not semantically inspected.
- The sample filename version/date may differ from the internal latest revision after later edits, so filename-to-cover mismatch should be a warning by default.
