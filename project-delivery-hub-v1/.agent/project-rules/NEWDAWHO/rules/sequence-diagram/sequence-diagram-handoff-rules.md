# DAWHO Sequence Diagram Handoff Rules

Use these rules only to assess sequence-diagram impact and prepare handoff to the dedicated native VSDX/PlantUML sequence-diagram skill.

> Extracted from the former heavy `SKILL.md` so the entrypoint can stay lightweight. Load this file only when the matching workflow is active.

## 时序图 / PlantUML 工作流

当用户要求检查时序图、循序图、VSDX/SVG、PlantUML，或询问 API 设计变化后如何修改 Visio 时序图时，使用此流程。

当任务是真正产出或润色 `.puml` 时，本技能先解析权威 PRD/TSD/API Detail 来源与标准 API/字段名，然后载入并遵循下游 `专案 PlantUML 时序图生成器`。本父技能负责 API 权威来源与命名决策；下游技能负责 PlantUML 落版、DAWHO 渲染样式、参与者摆放、共用 SVG 参考与 PlantUML 验证。

输入可包含：

- 由功能文件路径配置解析出的冻结版或进行中的 PRD/TSD/API Detail 文件。
- 既有时序图文件，例如 `.vsdx`、`.svg`、`.puml`、截图或导出文本。
- DAWHO 时序图撰写标准，例如 `P240301_永豐商銀新大戶_时序图撰寫标准*.docx`。
- AI 绘图提示词文件，例如 Mermaid/AI 时序图技能范例。
- 用户提供的、可覆盖通用绘图偏好的落版规则。

产出 PlantUML 或交接原生 VSDX 生成前：

1. 使用 registry 解析 PRD/TSD/API Detail/Common 文件，并抽取权威 API 清单、API sheet、后端来源、request/response 字段与业务逻辑。
2. 识别目标 `functionCode` 的 PRD 页面/画面清单。该页面清单是下游 VSDX 的 Visio page tab 权威依据：一支功能产出一个正式 VSDX 文件，每个 PRD 页面/画面成为文件内一个 tab。
3. 若提供时序图标准，用 `python-docx` 读取。只抽取可执行绘图规则，例如 lifeline 顺序、request/response 配对、消息命名、`alt`/`opt`/`loop` 用法、POP 文案与 ref/跨页规则。
4. 若提供 AI 绘图提示词文件，读取并作为样式/流程指导，不作为 API 权威来源。
5. Inspect existing `.svg` text and, when possible, unpack `.vsdx` as a zip and read `visio/pages/page*.xml` to extract lifelines, messages, notes, stale wording, and whether Visio tabs are split by PRD page or incorrectly by API/scenario/step.
6. Compare the existing diagram against the frozen API contract:
   - Main API calls in TSD/API Detail.
   - Request/response pairing.
   - Backend source sequence and split/merge logic.
   - Error/no-data branches.
   - CommonUtil/CommonFunc usage.
   - Old field names or old-system implementation names that should not appear in the new design.
7. Report what to add, remove, split, or rename before generating code when the user only asks for analysis.

PlantUML generation rules:

- Prefer multiple smaller `@startuml ... @enduml` blocks only as analysis/reference drafts. For formal delivery, the downstream VSDX must remain one official VSDX file per `functionCode`, with tabs split by PRD page/screen rather than by API, backend call, success/failure scenario, step, or subflow.
- When handing off to `专案 PlantUML 时序图生成器`, pass the PRD page/screen list explicitly and state: same `functionCode` -> one VSDX file; one PRD page/screen -> one Visio tab. If PRD/TSD does not prove a page split, default to one tab and record the uncertainty in the landing note.
- Use `alt` for mutually exclusive branches, `opt` for optional work, `loop` for repeated calls, `group` for business stages, and `ref` only when the user or local standard allows cross-diagram references. `alt` must have at least two branches; when there is only one conditional block, use `opt`.
- Keep request and response messages paired. A synchronous API/backend call should have a return arrow unless the standard explicitly says otherwise.
- Write PlantUML content in Traditional Chinese for Taiwan. Convert Simplified Chinese wording from user input, draft notes, or source summaries before placing it on the diagram.
- When `alt`/`else` conditions include enum values, flags, query scopes, status codes, or similar technical values, lead with the Traditional Chinese business meaning and put the technical value in parentheses, for example `歷史定存查詢（fixedDepositQueryScope=HISTORY）`.
- Use DAWHO message naming:
  - User/UI operation: `點擊XXX`.
  - APP to Enterprise API: `Module/APIName` plus a second line for the Chinese function description.
  - DB call: `DBName.dbo.TableName` plus Chinese description.
  - IRIS call: `IRIS.XXX` plus Chinese description.
  - Prompt/popup: `POP: 提示內容`.
- Do not invent backend calls. Use API sheet `涉及BackendAPI` and business logic rows as authority.
- Do not preserve legacy field names in PlantUML if the API Detail has been canonicalized. Use the canonical request/response names from the workbook and field KB.
- Prefer business-level request/response field names and Chinese semantics in PlantUML. Avoid showing source-system field names or old aliases on the diagram face unless the source field is the actual message payload being sent to that backend call and is necessary to understand the integration.
- Do not list old names in PlantUML notes just to say they are removed; keep such alias/migration details in the landing note, report, or field KB when needed.
- Do not add PlantUML participant stereotypes such as `<<UI>>`, `<<Enterprise>>`, `<<Host>>`, or `<<Store>>`; they become visible labels in exported SVG. Use plain declarations such as `participant "APP" as APP`.
- Participant-to-participant arrows should contain only the English API/source name plus the key Traditional Chinese meaning; do not display Request or Response parameters on arrows.
- Enterprise 回 APP 的 response 以黑色實線箭頭呈現，例如 `Ent -> APP: Response ...`；不要使用虛線 `Ent --> APP`。
- Use black arrows and black text by default. Use a transparent `ref` frame and keep only the `循序圖請參考：...` pointer block on orange background with black text. For APP internal self-calls, always use red text and a red folded/self-call arrow, for example `APP -[#B01513]> APP: <color:#B01513>檢核輸入內容</color>`; never leave APP self-calls as the default uncolored arrow style.
- APP 收到 Enterprise response 後的畫面顯示、提示、刷新、頁面狀態變更，畫成 APP 內部自呼叫，不畫 `APP -> User`。
- Common SVG references should put the CommonFunc/CommonUtil name, Chinese description, and SVG pointer inside the same `ref` block. Do not draw a separate CommonFunc self-call arrow outside the `ref`. Example: `ref over Ent : CommonFunc/GenFntTranSeq(NTFXT4000)\n取得交易序號\n循序圖請參考：共用SVG資料夾\n/04_GenFntTranSeq.svg`.
- For new deliveries after system-design v2.5, `Ref僅代表外部引用，無下方[]內容`: keep the ref body concise and point to the referenced location; do not add lower `[]` flow content inside or below the ref block. Already-delivered diagrams do not need retroactive ref-only repair unless the user asks.
- Final SVG should post-process Common SVG `ref` blocks to insert a compact red folded self-call arrow inside the `ref` block, because PlantUML cannot natively draw a message arrow inside `ref`. The arrow must be anchored on the referenced participant lifeline, usually Enterprise, placed on the reserved spacer row below the CommonFunc/CommonUtil description, and use the same folded self-call shape as normal message self-calls. The `循序圖請參考：...` pointer text must have an orange background strip that fully covers the pointer text, while the surrounding `ref` frame remains transparent.
- Common SVG `ref` blocks should reserve two spacer lines between the CommonFunc/CommonUtil Chinese description and the SVG pointer text; long CommonFunc names may be split across lines to keep the ref width compact.
- If an APP internal self-call message has multiple lines, wrap each line with its own red color tag so every rendered line stays red.
- Use DAWHO green `#1E5054` for participant borders, lifelines, dividers, and `alt`/`else`/`opt`/`group` borders unless the user explicitly requests another line color; note borders keep their note-specific color.
- `alt`/`else`/`opt`/`group` 外框與多分支條件分隔線使用 DAWHO 綠色 `#1E5054` 實線；若 PlantUML SVG 產出為虛線，只後處理非 message 的水平分支分隔線，不改後端 response 虛線或內部 message 箭頭。
- Common SVG `ref` 框本體背景需透明，ref 外框使用 DAWHO 綠色 `#1E5054`；只有 `循序圖請參考：...` SVG 指引文字區塊保留橙色背景，且橙色底色需完整包住指引文字與檔名。
- 若渲染後 SVG 需要與畫面邊緣留距，使用 SVG 外層畫布後處理：同步增加 `viewBox`/`width`，並以外層 `<g transform="translate(...,0)">` 平移內容，形成左右等距 margin；不要用 PlantUML `skinparam Padding`，避免改動時序圖內部排版。
- Common SVG `ref` 文字一律使用黑色；橙色指引區塊也使用黑字。
- Common SVG references must include `{CommonFunc/MethodName}\n{中文說明}\n循序圖請參考：共用SVG資料夾\n/{序號}_{MethodName}.svg` inside the same `ref` block; avoid repeating `CommonFunc` in the displayed SVG filename. Other supporting references use `循序圖請參考：{某某資料}`.
- Do not add bottom notes that only restate the frozen API name.
- Do not put API method names as PlantUML title subtitles; keep API method names on request arrows where they identify the actual API call.
- Do not use `autonumber` or show message sequence numbers unless the user explicitly asks for numbered messages.
- If one complete SVG is needed for VSDX conversion, ask the PlantUML sub-skill to produce a single continuous `@startuml` diagram with participants declared once and module dividers such as `== 進入定存查詢 ==`; avoid nested-SVG stitching because it causes visible breaks between modules.
- If one function contains multiple PRD pages, ask the VSDX sub-skill to keep them in the same formal `{functionCode}_01.vsdx` and create one Visio tab per PRD page. Do not request separate formal VSDX files just because the pages have different APIs or scenarios.
- Output PlantUML under a project-local path such as `output/sequence_diagram/{functionCode}/` unless the user specifies another location.
- Also create a short landing note when useful, listing: diagrams included, VSDX/SVG changes to make, stale words to remove, and frozen source files used.

DAWHO D.001/D.002-style sequence rules learned from current project usage:

- Mainline order is left to right and must not flow right to left.
- Keep `User -> APP -> Enterprise` fixed on the left side.
- Draw `User` as `actor User as User` when the target DAWHO/VSDX style or user request expects the small person icon above the User lifeline. Use plain `participant "User" as User` only when the user explicitly wants boxed participant labels for every lifeline.
- For final DAWHO/VSDX-style SVG output, the User head should match `v1.x Reference`: Visio `動作項目生命線` task/person icon above and bordered `User` label box below. The top icon is not a plain stick actor with horizontal arms, and the `User` label box height and border stroke should visually match the APP/Enterprise participant boxes. Use the current DAWHO participant border color by default, and never leave PlantUML's default stick actor or an unboxed `User` text label in SVG/VSDX.
- Split `DB` and `Redis` into separate participants when both are directly used.
- For DAWHO delivery diagrams, `DB` and `Redis` must be plain boxed participants (`participant "DB" as DB`, `participant "Redis" as Redis`), not PlantUML `database`/storage/cylinder icons. The final SVG/VSDX should show them with the same boxed participant head style as APP/Enterprise/IRIS.
- Keep `IRIS&智慧收支帳本` as one participant when the local diagram standard or user says so.
- Treat `CommonFunc` as an Enterprise internal self-call; do not draw it as a separate participant.
- Treat `CommonUtil` like other APIs requested through Enterprise; do not draw it as a separate participant unless the user explicitly asks.
- For new-system design, replace old-system switch/field names with semantic names. Example: do not use `PageMExchangeTr`; use a namespaced new-system feature toggle such as `FeatureToggle:{Domain}:{Capability}` and boolean response semantics such as `is{Capability}Enabled == true`.
- If a prior SVG/VSDX includes UI navigation to unrelated features, screenshots, eye-mask behavior, fixed-deposit pages, or other PRD modules, move those to notes or separate diagrams unless they are part of the current API contract.

Validation for PlantUML outputs:

- Count `@startuml` and `@enduml`; they must match.
- Search the generated `.puml` for stale words identified during analysis, for example old action names, old field names, old-system switches, or mixed simplified/traditional terms.
- Reject delivery `.puml` that declares `DB` or `Redis` with `database`, `collections`, `queue`, or any non-boxed participant keyword unless the user explicitly requested a non-standard exploratory diagram.
- After rendering, inspect the top participant row: User must use the DAWHO Visio task-icon + bordered-label style, and DB/Redis must be boxed heads aligned with APP/Enterprise/IRIS. If User still looks like a plain stick actor, its label box is much shorter than APP, or its border is thinner than APP/Enterprise, repair and regenerate before handoff.
- If PlantUML is installed locally, render the file and inspect the output; otherwise state that only text-level validation was performed.
- When the user will manually update Visio, provide a concise checklist of exact text replacements and branch additions.
