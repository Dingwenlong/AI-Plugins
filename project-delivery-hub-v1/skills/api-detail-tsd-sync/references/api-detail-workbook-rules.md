# DAWHO API Detail Workbook Rules

Use these rules when editing API Detail workbooks, syncing Api_List, preserving workbook structure, handling backups, fonts, formatting handoff, and final workbook validation.

> Extracted from the former heavy `SKILL.md` so the entrypoint can stay lightweight. Load this file only when the matching workflow is active.

## API Detail 工作簿格式交接

当本技能在已保存的 `NEWDA_API_DETAIL_*.xlsx` 中创建、重命名、删除或编辑任何 API Detail 工作表、`Api_List` 行、request/response 表、范例区块、后端来源文本、业务逻辑文本、返回链接或其他内容时，最终用户报告前必须接续下游 `专案交付文件格式检查器`。

必要交接闭环：

1. 写回前依单一备份规则，刷新目标工作簿唯一 `.bak` 备份。
2. 先完成语义/API 设计编辑；不得用格式脚本补造缺失的 API 内容。
3. 载入并遵循 `delivery-format-checker`。
4. 执行 Excel 格式修复/检查顺序：确认本次变更范围 -> 只修变更范围格式 -> 只对变更范围执行字体槽位 -> 结构复验 -> artifact-tool inspect/render。
5. 最终报告需同时说明 `Must fix`、`Should fix`、`Naming`、`Visual risk`、`Covered` 状态与 API 设计发现。

若用户只要求只读分析，不要写回工作簿；以检查/只报告模式运行或建议运行格式检查器，并把格式问题列为后续风险。若本技能已经写回工作簿，在格式检查器显示 `Must fix = 0` 且 `Visual risk = 0` 前，不得宣称工作簿完成；对于用户要求的修复任务，也应尽量把 `Should fix` 推进到 `0`，除非剩余项是明确延后且已说明原因。

格式检查器负责行高、字体槽位、边框、合并单元格、返回链接、打印/渲染问题与右侧空白区污染等视觉/版面事项。本技能负责 PRD/TSD/API 语义、标准命名、工作簿内容与开发就绪度判断。

## 字体与格式范围护栏

本技能修改 Excel 内容时，必须把字体和格式影响范围限制在本次业务变更范围内。

范围规则：

- 默认只处理用户点名或本次实际编辑的 API sheets、`Api_List` 行、request/response/example/business-logic 单元格。
- 新增行、插入列、复制模板时，只从相邻同类行/列复制样式到新增或被改动的单元格。
- 同步 `Api_List` 的 `後端來源` 时，只改对应行的目标单元格；不得重设整张 `Api_List` 字体。
- 修改一个 API sheet 的字段、范例或业务逻辑时，只改该 sheet 的可视语义范围；不得遍历所有 API Detail sheets 做字体修复。
- 若需要调用下游格式检查器或字体槽位脚本，必须显式交接 sheet 名、`Api_List` 行号或单元格范围；不得使用会扫描全 workbook 或所有 API Detail sheets 的默认模式。
- 若无法确定受影响范围，先做只读检查并报告 `Visual risk`，不要为了保险对全 workbook 套字体。
- 只有用户明确要求“全工作簿统一字体/全 sheets 修格式”，才可扩大到全 workbook；最终回复必须说明这是用户明确授权的范围。

禁止事项：

- 不得遍历 `workbook.worksheets` 后对每个 sheet 执行字体替换。
- 不得用 Excel `UsedRange` 推导字体修复范围。
- 不得把 `H:AZ` 或其他历史污染空白区纳入字体/格式套用范围。
- 不得因一两个 API 内容变更，顺手重写所有 sheet 的 `Font.Name`、`Font.Size`、rich text runs 或 row/column default font。


## 来源规则

- TSD `.docx` edit boundary: when modifying a TSD Word document, preserve the original content of section `1. 功能目的(Functional Description)` and section `4. 參考訊息來源(Reference)` unless the user explicitly asks to rewrite those sections. Do not use these two sections to carry API-design refinements, source clarifications, naming rationale, or issue-ticket conclusions.
- TSD `.docx` bottom-note boundary: do not append extra supplemental information, free-form notes, frozen naming notes, issue-ticket explanations, or follow-up reminders at the bottom/end of a TSD document. Put such information in the chat response, a handoff note under `output/`, or the relevant field KB instead, unless the user explicitly asks to add it to the TSD body.
- TSD API list authority: Word table under `5. API清單`.
- TSD `API清單` should list APIs that the TSD explicitly calls as external/wrapper interfaces for the feature. Do not keep `CommonFunc` internal helper calls in the TSD API list just because implementation logic uses them.
- If a row in TSD `API清單` points to a Common/internal helper that is only called inside another API sheet, recommend deleting that TSD API-list row instead of adding it to the feature workbook.
- Common layer boundary: `CommonFunc` is for program-internal shared methods; `CommonUtil` is for externally callable common APIs. A CommonUtil API is a wrapper around CommonFunc and should describe login/session-state validation before calling the underlying CommonFunc. Therefore, TSD/API清單 and API Detail outward-facing rows should reference CommonUtil when the caller is another module or external API consumer, while internal implementation/backend-source rows may reference the underlying CommonFunc call chain. Use slash notation for external CommonUtil APIs, for example `CommonUtil/CheckPreLoginDeviceStatus`, and dot notation for internal CommonFunc method calls, for example `CommonFunc.CheckPreLoginDeviceStatus`.
- API sheet authority: each API sheet's `A2` API name and `B2` API description, with sheet name as fallback when `A2` has a typo.
- `Api_List` `後端來源`: copy from the matching API sheet's `API 內部業務邏輯` row where column A contains `涉及BackendAPI`; use that row's column B text.
- Do not invent backend sources from memory or from PRD prose.
- Common workbooks (`CommonUtil`, `CommonFunc`) are reference files. Do not add CommonUtil/CommonFunc/Exchange rows into a Deposit `Api_List` unless the user explicitly requests cross-workbook rows.


## API 规格编辑规则

当用户要求修 API 规格时，仅做范围明确的工作簿编辑：

- Prefer editing only the relevant API sheets and `Api_List`.
- Preserve original unrelated sheets.
- Preserve fonts and styles on unrelated sheets and unrelated cells. Do not run broad workbook-level font normalization after a scoped content edit.
- When adding, renaming, or rebuilding API Detail sheets for a scoped function, keep the worksheet tab order aligned with the corresponding `Api_List` row order. Do not leave renamed sheets at the end of the workbook if the `Api_List` sequence is already authoritative.
- Rebuild field semantics from PRD Chinese wording first. Field Chinese description must贴紧 PRD meaning, not legacy implementation wording.
- Prefer canonical field names from the category field KB.
- Treat old wording in supplied files as improvable draft text, not as a freeze requirement. When the user asks to fix or freeze an API spec, proactively rename awkward old-system fields and methods to canonical new-system names unless backward compatibility is explicitly requested.
- If an existing API field name is misleading, copied from another domain, or does not match PRD meaning, directly rename it in the workbook when the user asked to fix the spec.
- When renaming a field, update every occurrence in the request/response table, JSON examples, business logic, report, PlantUML/sequence notes, and the category field KB alias/canonical sections.
- If source wording is clearly copied from another domain, correct it. Example: remove定存/存單 wording from活存 account APIs.
- Keep backend source names in source descriptions only when they identify IRIS/DB/CommonFunc fields or real integration payload. Pair them with canonical API field names so developers can map source-to-contract without leaking legacy names outward.
- Align field names across request/response tables and JSON examples.
- Add missing request fields only when PRD requires them, such as `keyword` for PRD keyword search.
- Add response fields when needed for PRD UI decisions, such as `dataSource` for host vs smart-book display behavior.
- Add business logic text for rules that developers need to implement, not only UI display notes.
- If a rule belongs to the frontend formatting contract rather than backend, say so in the note instead of forcing a display field.


## Api_List 新增规则

Only add a row when all are true:

- The API appears in the current TSD `API清單`.
- The target API Detail workbook has a matching interface sheet.
- The API belongs to the target workbook's domain, usually `Deposit` for `NEWDA_API_DETAIL_Deposit_*.xlsx`.

不要因为 TSD 中出现 `CommonUtil`、`CommonFunc` 或 `Exchange` 行，就把它们加到 Deposit 工作簿。

若 TSD API 清单行只是 `CommonFunc` 内部调用，应移除或标记该 TSD 行；不要在功能工作簿中为它创建 `Api_List` 行。

为了方便查找，若既有 `Api_List` 行合并了多个 PRD，可在用户要求或筛选需要时新增独立 PRD-only 行，同时保留原合并行。

Example:

- Existing: `D.001.001 D.002.001 D.007.002 / Deposit / GetFixedDepositDetail`
- Add lookup row: `D.001.001 D.002.001 / Deposit / GetFixedDepositDetail`


## 匹配说明

Normalize API names before matching:

- Trim whitespace.
- Remove invisible spaces such as `\u2002`.
- Treat sheet-name prefixes as fallback matches.
- If TSD `API清單` has a case/spelling mismatch against the authoritative API sheet name, and the intended API is otherwise clear, update the TSD `API 名稱` to match the API sheet name exactly instead of preserving the typo as an alias.
- Example: TSD `GetCenCurr` should be corrected to CommonUtil API sheet `GetCENCurr`.

Known Deposit workbook mismatch:

- `Api_List`: `PatchFixedDepositTitle`
- Sheet `A2` may say `PatchFixedDepositName`
- Treat it as the same sheet when syncing `後端來源`.


## 工作簿编辑

除非当前工作区规则要求其他保存方式，直接更新工作簿时可使用 `openpyxl`。若当前工作区 `AGENTS.md` 或项目级指令要求用 Excel COM 保存 API Detail 工作簿，则项目规则优先于本技能默认 `openpyxl` 写回建议。对于可能包含 OLE/EMF 或其他内嵌对象的既有交付 `.xlsx` 文件，`openpyxl` 只用于只读检查/不保存分析；修改保存需使用 Excel COM。

对于已经使用 rich text 的工作簿，载入方式：

```python
load_workbook(path, rich_text=True)
```

插入列时：

- Copy style, border, fill, alignment, protection, number format, and row height from a nearby row.
- Preserve existing combined PRD rows.
- Write new cells with the workbook's existing rich-text font pattern if the user asked for aggressive mixed fonts.

编辑后：

- Unhide all `Api_List` rows.
- Set `ws.auto_filter.ref = f"A1:K{ws.max_row}"`.
- Reopen the workbook and print/verify the relevant rows.
- Verify that unrelated worksheets were not modified when the task only changed scoped API content.


## 备份

不要每次操作都创建新备份。用户指定的源文件保持为当前有效目标。

仅在以下情况创建备份：

- The user asks.
- A destructive broad change is requested.
- You are about to repair or overwrite a file that Excel may have modified.

如需备份，只保留一个清楚命名的源文件备份，不要每一步都创建备份。


## 字体处理

字体处理不是默认全 workbook 操作。只有下列情况才处理字体：

- 新增或修改的单元格需要继承同区块字体。
- 用户明确要求修复当前变更范围的字体。
- 下游格式检查器在本次变更范围内报告字体问题。

若用户要求当前范围字体：

- Chinese: `微軟正黑體`
- Other text: `Times New Roman`

There are two approaches:

- Safer: apply `微軟正黑體` to cells containing Chinese and `Times New Roman` to other cells.
- Aggressive: split text cells into rich text runs by character, Chinese/CJK punctuation as `微軟正黑體`, Latin/digits/symbols as `Times New Roman`.

Warn that aggressive rich text can trigger Excel's "repair content" prompt even when API content is intact. If the user accepts this, continue with aggressive mode.

执行限制：

- 只处理本次实际编辑的 cells/ranges，或用户明确点名的 sheet/range。
- 对 API Detail sheets，默认语义可视范围是 `A:G` 到最后内容列/行；对 `Api_List`，默认只处理本次涉及的行和列。
- 若调用 `delivery-format-checker` 的字体脚本，必须传入明确 `-Sheets` / 范围参数；不要使用会处理所有 API Detail worksheets 的默认命令。
- 不要对 workbook 每张 sheet 做“补一遍字体”的收尾动作。


## 验证清单

最终回复前：

- Reopen the exact target workbook.
- Confirm `Api_List` rows are visible (`row_dimensions[r].hidden == False`).
- Confirm expected PRD/API rows exist.
- Confirm `後端來源` for changed rows equals the matching sheet's `涉及BackendAPI` text.
- Confirm category field KB was checked and updated when new or inconsistent field names were found.
- Confirm unrelated sheets' fonts/styles were not changed when the task scope was limited to specific sheets or rows.
- Mention if the target file was locked and an alternate filename was created.
