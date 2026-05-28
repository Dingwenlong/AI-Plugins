---
name: 专案原生 VSDX 时序图生成器
description: 用于依专案冻版 PRD、TSD、API Detail、既有 VSDX/SVG/PlantUML 与本地时序图范例，产出或优化正式交付用的原生可编辑 Visio VSDX 时序图；兼容 既有专案 既有标准。PlantUML/SVG 只作为业务内容与视觉参考或明确降级输出。适用于使用者要求产出、优化、修正时序图、循序图、PlantUML、SVG、VSDX、Visio native shape、箭头、参与者、lifeline、alt/ref/opt/loop/group fragment、落版与 QA 规则时。兼容旧称：专案 PlantUML 时序图生成器。
---

# 专案原生 VSDX 时序图生成器

## 目的

作為 `專案需求接口設計梳理` 的下手技能使用。
父技能負責解析權威 PRD/TSD/API Detail 與 canonical API/欄位命名；本技能負責把凍版契約轉成正式交付用的 專案時序圖產物。

正式 VSDX 交付定位如下：

- `native-visio` 是正式 VSDX 的唯一正常交付模式。
- PlantUML/SVG 是內容整理、布局參考、視覺對照與工具缺失時的降級產物，不是正式 VSDX 的生成來源。
- 不得把整張 SVG 匯入 Visio 後交付為正式 VSDX；這類檔案只能標記為 `svg-import fallback`，且必須明確說明不可作為原生可編輯交付。
- 舊稱 `專案原生VSDX時序圖產生器` 只作為觸發別名保留，不代表產線以 PlantUML/SVG 匯入為優先。

## 输入

优先按顺序使用以下输入：

1. Frozen API Detail sheets: API Name, request/response fields, examples, `涉及BackendAPI`, business logic rows.
2. TSD `API清單` and sequence/structure notes.
3. Existing VSDX/SVG/PlantUML when the user wants a redesign or style alignment.
4. Local style examples, especially:
   - `2-2系統設計規範/01 時序圖標準範例`
   - `2-1系統設計書/v1.x Reference/共用svg`
   - Built-in current project delivery-style baseline:
     - `references/standard-examples/E001_native_reference.vsdx`
     - `references/standard-examples/E001_native_reference_preview.png`
     - `references/standard-examples/E001_native_reference.md`
   - Current project baseline, when available:
     - `v1.x Reference/E.001_01.vsdx`

不要把旧图视为比冻结版 API Detail 更权威。

## 内建标准范例

本技能在 `references/standard-examples/` 下内置冻结标准范例。

正式原生 VSDX 输出应以 E.001 原生参考作为主要视觉/样式基准：

- `E001_native_reference.vsdx`: current native VSDX baseline copied from project `v1.x Reference/E.001_01.vsdx`.
- `E001_native_reference_preview.png`: rendered visual QA baseline.
- `E001_native_reference.md`: extracted native structure and style rules.

当项目本地存在 `v1.x Reference/E.001_01.vsdx` 时，优先使用项目本地版本，因为它可能包含当前工作区最新调整。

原生 VSDX template/master 必须携带 专案 Visio theme。有效 theme 模板需包含 `visio/theme/theme1.xml`，并且文件关系 type 以 `/officeDocument/2006/relationships/theme` 结尾。不要用裸 Office UML stencil 或缺少该 theme 的 native master 构建正式交付，因为 Visio UML shape 使用 `THEMEVAL()` 公式，缺少 theme 时会回退成默认黑/灰色，而不是 E.001 红/绿样式。

专案 theme 已内置在本技能的 `references/standard-examples/E001_native_reference.vsdx`。当调用方提供的 `-TemplateVsdx` 缺少项目 theme 时，native builder 必须自动改用内置 E.001 参考作为 fallback 模板。若调用方模板与内置 fallback 都缺少 theme，应让构建失败，不要产出默认 Office 配色的 VSDX。

交付前，需将正式 VSDX 输出与 E.001 原生参考比对，重点检查过去容易漂移的项目：原生 User Actor 生命线、Object lifeline 参与者、附着式消息标签、原生 fragment master、Interaction operand 区域、居中标题带、分段双线间距、ref 橙色指示条、框体包覆、页边距与 VSDX 预览质量。

## 输出

项目本地输出放在：

```text
output/sequence_diagram/{functionCode}/
  vsdx/
```

默认文件：

- `{functionCode}_sequence.puml`
- `{functionCode}_plantuml_落版說明.md`

当一支功能包含多个完整业务情境时，将多个 `@startuml ... @enduml` 区块放在同一个 `.puml` 中，每个情境一个区块。这些区块只作为内容/参考草稿；正式 VSDX 交付仍以下方“一支功能一个文件、PRD 页面 tab”契约为准。

一般 專案交付时，始终先创建或刷新 native reconstruction spec，再保留一份与该 spec 对齐的单一 `@startuml` 完整 PlantUML 文件，供文本/内容审阅。PlantUML 文件应只声明一次参与者，并用 `== ... ==` 分隔线连接所有情境章节。默认不要渲染 SVG 或 PNG 参考图。正式 VSDX 必须从 native reconstruction spec 构建，不能从 SVG import 构建。不要把多个独立 SVG 用嵌套 `<svg>` 区块拼接，因为这样会造成模块间视觉断裂与生命线断开。

專案交付场景中，VSDX 是默认交付物。用户通过本技能要求产出或最终化时序图时，除非用户明确只要 `.puml`、只要 `.svg`、只要文本，或本机环境无法运行 PlantUML/Visio，否则需创建下方 VSDX 输出。不要要求用户在另一个窗口再单独说一次“VSDX”。

创建：

- `output/sequence_diagram/{functionCode}/vsdx/{functionCode}_01.vsdx`

若 `vsdx/` 文件夹不存在，需明确创建。将 native spec、PlantUML 文本草稿、落版说明与正式 VSDX 都保存在 `output/sequence_diagram/{functionCode}/` 下，方便其他会话直接找到完整输出包，不需要再搜索 `v1.x Reference/`。

正式 VSDX 文件/tab 契约：

- One function / one `functionCode` produces one official VSDX file: `vsdx/{functionCode}_01.vsdx`.
- The VSDX may contain multiple Visio page tabs. Tabs are split by coherent PRD/TSD user flows, not mechanically by every PRD page/screen, API, backend call, success/failure scenario, step, or subflow.
- One complete user flow may merge multiple PRD pages/screens into one Visio page tab when those pages are consecutive steps of the same user journey, such as fill-in, confirm, submit, and result. Use section dividers, `group`, `alt`, `opt`, `loop`, or `ref` to show the PRD page/stage boundaries inside that tab.
- Split into a separate formal tab only when the page/screen has an independent user entry action, an independent user goal, or the merged flow would become too dense to read. Name tabs by the PRD flow meaning, optionally prefixed with the function code, for example `L.003_申請扣繳`, `N.001.002_郵箱初始頁`, or `N.001.002_通訊地址變更確認頁`.
- Every formal Visio page tab must have at least one visible entry point from the user, normally `User -> APP: 點擊...`, near the top of the flow. Do not start a formal tab with backend-only processing, Enterprise self messages, or result mapping that has no user entry action.
- If PRD/TSD does not give a clear flow or page/screen split, default to one Visio page tab for the function and record the missing split evidence in the landing note.
- Do not create multiple formal VSDX files for the same `functionCode` because the feature has multiple PRD pages, APIs, scenarios, or flows. Extra VSDX files are allowed only as explicitly requested exploratory/debug artifacts and must not be reported as the official delivery.

正式 VSDX 必须通过 `scripts/build_native_visio_sequence.ps1`，从 `output/sequence_diagram/{functionCode}/{functionCode}_native_visio_spec.json` 产出，并使用 Visio UML masters 与原生 shape 模板库。若 native spec 缺失、过期，或 VSDX 构建命令没有使用该 spec，需先停止并修正；不得用 SVG-import VSDX 代替。专案系统设计标准 v2.5 要求交付 Visio source 且兼容 Visio 2013-2016；正式交接时需保留 native source VSDX，并在环境支持时保存/导出为 Visio 2013-2016 兼容格式。不要把新生成的功能图同步复制到 `v1.x Reference/` 作为标准交付步骤；官方生成输出应保留在 `output/sequence_diagram/{functionCode}/`。只有用户针对该次交付给出新的明确指示时，才额外创建 `v1.x Reference/` 副本，并记录为例外而非可复用规则。若因 PlantUML、Visio COM、必要 UML masters 或必要工具不可用而无法产出 VSDX，仍需产出 `.puml` 文本草稿，并明确报告缺少 native VSDX 是未完成交付项及具体阻塞原因。

最终交付后保持输出目录干净。默认不要创建或刷新 `svg/`、`png/` 参考渲染目录。对于 `vsdx/`，只保留最终 `{functionCode}_01.vsdx`；不要创建 `.bak`、`.before_*`、时间戳备份或其他交付目录相邻备份。确需安全副本时使用版本控制或工具临时目录，并在交付前清理。

## 图面结构

- Use multiple smaller `@startuml` draft blocks only for analysis/readability. Formal VSDX output must still consolidate to one VSDX file per function and one Visio page tab per coherent PRD/TSD user flow.
- One formal Visio page tab should cover one complete user flow. Do not create extra formal tabs just because a flow contains multiple PRD pages, APIs, backend calls, scenarios, branches, confirmation steps, or result states.
- Each formal tab must include a visible user entry action. If a proposed tab has no `User -> APP` entry point, merge it back into the preceding flow tab or add the PRD/TSD-supported entry action before backend processing.
- Every function-level sequence diagram must state the functional entry points from the PRD/TSD before the main API flow starts. Include where the user comes from, the action that opens the function, and any PRD-defined default state such as default currency, default tab, default account, or query scope. Do not invent entry paths that are not in the source material.
- When the PRD/API Detail requires member type, member identity, or online-banking qualification validation, show it as an `alt` gate near the functional entry. The failure branch should show the PRD/API-defined popup or error prompt, and the success branch should continue into the main flow. Do not add generic member validation to functions whose PRD does not require it.
- Use `group` for business stages.
- Use `alt` for mutually exclusive branches.
- Use `opt` for optional calls.
- `alt` must contain at least two branch blocks; if there is only one conditional branch, use `opt` instead.
- Use `ref over` for reusable CommonFunc/CommonUtil SVG references, not for hidden backend calls. CommonFunc/CommonUtil method names must not be drawn as ordinary Enterprise self-calls or ordinary messages in the main flow. A common-method ref must include both the compact reference self-call and the bottom orange reference-file strip for the same method.
- Keep every synchronous call paired with a response arrow.
- Write diagram content in Traditional Chinese for Taiwan. Convert user-provided Simplified Chinese wording to Taiwan Traditional Chinese before placing it on the diagram.
- When `alt`/`else` conditions include enum values, flags, query scopes, status codes, or similar technical values, lead with the Traditional Chinese business meaning and put the technical value in parentheses, for example `歷史定存查詢（fixedDepositQueryScope=HISTORY）`.
- Do not dump request/response field lists on message labels or APP self-call labels. If a display/update step depends on multiple fields, summarize the business action in Traditional Chinese, and mention at most the most important canonical field in parentheses when needed. Avoid raw multi-line lists such as `fieldA + fieldB + fieldC` or long slash-separated response field lists on the diagram face.

## 参与者规则

默认从左到右顺序：

```text
User -> APP -> Enterprise -> IRIS -> DB -> Redis
```

Rules:

- `User`, `APP`, and `Enterprise` stay on the left side.
- Draw `User` as `actor User as User` in PlantUML only as a source marker for later styling. The formal DAWHO VSDX output, and any explicitly requested SVG output, must not leave PlantUML's default stick-actor output visible.
- For DAWHO/VSDX-style delivery SVG, SVG post-processing of `User` is mandatory: replace the rendered actor/stick figure with the project User participant style from the E.001 native reference: the Visio `動作項目生命線` task icon above, a separate bordered `User` label box below, and the lifeline starting from the label box center. The top icon must match the E.001 task/person icon, not a plain stick actor with horizontal arms. The icon stroke and label box border should visually match APP/Enterprise participant boxes; use black only when the user explicitly asks for black.
- VSDX output must be checked independently from SVG output. If native reconstruction leaves a default PlantUML actor, a plain `User` label, a different-sized stick figure, a stick actor in place of the task icon, or a black/default User label border, replace the VSDX User head from the E.001 native reference (`v1.x Reference/E.001_01.vsdx` or `references/standard-examples/E001_native_reference.vsdx`). Do not assume that a correct SVG User style automatically survives into the VSDX.
- If the final VSDX, or any explicitly requested SVG output, still shows a PlantUML default stick figure, a stick actor with horizontal arms, an unboxed `User` text label, a User border thinner than APP/Enterprise participant borders, a label box that is much shorter than APP/Enterprise participant boxes, or a lifeline that does not start from the boxed User label center, treat the output as not delivery-ready and repair before handoff.
- `DB` and `Redis` must never appear to the left of `Enterprise`.
- Draw `DB` or `Redis` only when the current main API flow directly calls them.
- Do not draw `DB`/`Redis` only because a referenced common SVG internally uses them.
- For project delivery, declare `DB` and `Redis` as boxed participants only: use `participant "DB" as DB` and `participant "Redis" as Redis`. Never use PlantUML `database`, `collections`, `queue`, or other icon participant keywords for them unless the user explicitly asks for non-standard exploratory output.
- The final VSDX, and any explicitly requested SVG output, must show `DB` and `Redis` with the same white boxed participant head style as `APP`/`Enterprise`/`IRIS`, not cylinder/storage icons. If the output contains an ellipse/cylinder head for either one, repair the source declaration/spec and regenerate before handoff.
- If a common method is referenced, put the CommonFunc/CommonUtil name, Chinese description, compact reference self-call, and SVG pointer inside the same `ref over Ent` block. Do not draw a separate CommonFunc self-call arrow outside the `ref`, and do not omit the bottom orange reference-file strip when the self-call exists. In final SVG output, post-process the ref block to insert a compact red folded self-call arrow inside the ref block; the arrow must be anchored on the referenced participant lifeline (usually Enterprise), placed on the reserved spacer row below the CommonFunc/CommonUtil description, and use the same folded geometry as a normal self-call, only red. The `ref` frame background should be transparent, with only the SVG pointer lines highlighted orange; all `ref` text should be black.
- Leave two spacer lines between the CommonFunc/CommonUtil Chinese description and the SVG pointer text so the inserted inner self-call arrow has its own visual row and cannot be covered by the orange pointer block. For long CommonFunc names, split the method name across lines to avoid an over-wide `ref` box.
- Treat `CommonFunc` as an Enterprise internal self-call or `ref over Ent`; do not draw it as a participant.
- Treat `CommonUtil` as an API requested through Enterprise only when APP actually calls that CommonUtil API in the current scenario.
- Visible common reference self-call notation is layer-sensitive: internal `CommonFunc` uses dot notation (`CommonFunc.MethodName`), while outward `CommonUtil` keeps slash notation (`CommonUtil/MethodName`). The orange pointer strip uses `循序圖請參考：` plus the SVG basename and Chinese description, for example `循序圖請參考：04_CommonFunc.GenFntTranSeq 取得交易序號`.
- Keep `IRIS&智慧收支帳本` as one participant only when the local standard or the specific feature requires that combined lifeline.
- Do not add PlantUML participant stereotypes such as `<<UI>>`, `<<Enterprise>>`, `<<Host>>`, or `<<Store>>`; PlantUML renders them as visible stereotype labels. Use plain declarations such as `participant "APP" as APP`.

## 消息命名

- User/UI operation: `點擊XXX`.
- APP to Enterprise: `Module/APIName` plus Chinese API description.
- IRIS call: `IRIS.XXX` plus Chinese source description.
- DB call: `DBName.dbo.TableName` plus Chinese source description.
- Prompt/popup: `POP: 提示內容`.
- Response arrow text starts with `Response`.
- Every participant-to-participant Request and Response arrow must have a meaningful label. Backend-related request labels must include the DB table name or API English name plus Chinese meaning; do not leave direct APP/Enterprise arrows unlabeled or labeled only as `App` / `Enterprise`.
- Enterprise 回 APP 的 response 以實線箭頭呈現，例如 `Ent -> APP: Response ...`；不要使用虛線 `Ent --> APP`。
- `User` is a trigger/source only. Do not draw `APP -> User`, `APP --> User`, or any `Response ...` arrow targeting `User`; represent page display, popup, refresh, and visible UI feedback as APP self-call messages instead.
- Participant-to-participant messages should show only the English API/source name plus the key Traditional Chinese meaning. Do not list Request or Response parameters on arrows.
- APP internal self-call messages should also be business-readable. Use Traditional Chinese display/state/update wording first; do not use APP self-calls as a place to show raw parameter formulas, long field lists, or copied response paths.
- If adjacent APP self-calls express the same UI result using different wording, keep only one self-call with the most complete business meaning; do not draw parallel folded arrows for `action/display/prompt` variants of the same outcome.
- Do not add bottom notes that merely restate the frozen API name.
- Do not put API method names as title subtitles, for example `GetFixedDepositDetail / GetFixedDepositInterestDetail / PatchFixedDepositTitle`. Keep API method names on the actual request arrows where needed.
- Use canonical request/response field names from API Detail and field KB.
- Do not put legacy field/method names on the diagram face just to say they were removed.

## 标准命名

PlantUML must follow the new-system contract:

- Use canonical API names and fields from the frozen API Detail.
- Do not preserve old names such as `tdAcct`, `tdAccountNo`, `queryAccountNo`, `currEName`, `currCName`, `depositCatgType`, `depositType`, `depositRollType`, `depositReceiveInterestType`, `GetDepositInterestDetail`, or `PatchFixedDepositName`.
- Source-system fields such as IRIS/DB columns may appear only when the message is the actual backend integration payload and is necessary for implementation clarity.
- For high-level flow, prefer Chinese business semantics over backend source-field names.

## DAWHO PlantUML 样式

PlantUML is the source/reference diagram format, not the formal VSDX renderer. Embed style directly inside every `@startuml` block so the file works in `https://editor.plantuml.com/uml` without external includes, but do not let PlantUML-only styling override native VSDX rules.

创建或刷新图时，使用 `references/sequence-style.puml` 样式模板。

Style principles learned from local SVG examples:

- white background;
- participant borders, lifelines, dividers, and `alt`/`else`/`opt`/`group` borders use the DAWHO green `#1E5054`; note borders keep the note rule below.
- font rule: Traditional Chinese text uses `Microsoft JhengHei` (`微軟正黑體`); pure English, numbers, and symbols use `Times New Roman`. For mixed labels, prefer `Microsoft JhengHei` so Chinese stays readable.
- `alt`/`else`/`opt`/`group` branch separators should be DAWHO green `#1E5054`; in native VSDX, direct `else` operand separators use visible dashed lines carried by the native UML `Interaction operand` shape, while section divider double-lines remain solid. Keep the first `if` operand without an extra top separator, keep every following `else` operand separator visible, and bring section dividers plus native else separators to the top z-order so lifelines, frames, or messages cannot cover them. Do not add hand-drawn or overlay separator lines for `else`; each `else` head should have exactly one native operand separator.
- Do not use PlantUML's old implicit black arrow / black arrow-text default for project delivery references. The SVG reference should use the current DAWHO message policy from `references/sequence-style.puml`, currently project red `#B01513` for message arrows and message labels unless a feature-specific rule explicitly says otherwise.
- Enterprise 回 APP 的 response arrow must be a solid arrow; its color follows the current message-color policy in SVG references and the native `messageStyle` policy in VSDX. Do not encode response behavior by switching back to old black-only defaults.
- `ref` frame backgrounds should be transparent/white and the `ref` border should use DAWHO green `#1E5054`. Do not rely on PlantUML `SequenceReferenceBackgroundColor #F4A100` for the ref block itself; set ref backgrounds to white/transparent in the style template, then add the orange pointer rectangle by SVG post-processing. Only the `循序圖請參考：...` SVG pointer text block keeps orange background; all `ref` text stays black. Apply SVG post-processing when PlantUML renders the whole `ref` as orange or leaves the border black.
- When the rendered SVG needs breathing room from the page edge, add equal left/right outer canvas margins by post-processing the SVG root `viewBox`/`width` and wrapping the rendered content in a translated `<g>`. Do not use PlantUML `skinparam Padding` for this, because it changes the internal sequence layout instead of only the exported canvas edge.
- yellow note fill `#FFF2A1` with black note border;
- `hide footbox`;
- `responseMessageBelowArrow true`;
- no `autonumber`; do not show sequence numbers unless the user explicitly asks for numbered messages;
- participant labels visually boxed and bold.
- Use only global participant `skinparam`; do not use `skinparam participant<<...>>` stereotype styling because the stereotype label becomes visible in exported SVG.
- For PlantUML/SVG reference output, APP internal self-calls use red text and a red folded/self-call arrow with this exact pattern: `APP -[#B01513]> APP: <color:#B01513>檢核輸入內容</color>`. For native VSDX, do not force APP self-calls to fixed RGB red under the default `messageStyle.policy = "e001-reference"`; let them inherit the E.001/Visio theme style unless the spec explicitly marks a message as project red emphasis.
- UI display, prompt, refresh, or page-state changes after APP receives Enterprise response should be drawn as APP internal self-calls. A visible user action must be followed by a business-readable APP self-call that shows the screen response; do not add a separate response arrow back to `User`.
- For multi-line APP internal self-call messages, wrap each line independently, for example `APP -[#B01513]> APP: <color:#B01513>檢核輸入內容</color>\n<color:#B01513>顯示錯誤提示</color>`.
- In final VSDX, and any explicitly requested SVG output, self-call labels must be visually tied to the folded self-call arrow: place the text block immediately to the right of the folded return arrow, left-align the paragraph, and vertically center it with that return arrow when post-processing allows it. Use this standard for APP and backend/internal self-calls. If the label floats far above the folded arrow, overlaps an unrelated frame, or reads like a detached note, treat the output as not delivery-ready.
- Small technical parameters inside a self-call label, such as `currencyCode` in parentheses, must use the same text color/style as the surrounding Chinese label. Do not leave parameter snippets in a different inherited character color.

## 共用 SVG 参考

当功能调用已记录为 SVG 的可复用共用逻辑时：

1. Find the SVG in `v1.x Reference/共用svg`.
2. Put the CommonFunc/CommonUtil name, Chinese description, compact reference self-call, and SVG pointer inside the same `ref over Ent` block.
3. Do not create lifelines for participants that only exist inside the common SVG.
4. In the landing note, list referenced SVG filenames to be packaged with the delivery.
5. In new deliveries, `Ref僅代表外部引用，無下方[]內容`: keep the ref body concise, with no embedded process flow and no lower `[]` content. Already-delivered diagrams do not need retroactive ref-only repair unless the user asks.
6. Use the exact reference wording:
   - Common SVG visible text: `{CommonFunc.MethodName}` or `{CommonUtil/MethodName}` + `\n{中文說明}\n　\n　\n{SVG basename without .svg}{中文說明}`
   - Other supporting material: `循序圖請參考：{某某資料}`
7. The visible Common SVG display name must remove `循序圖請參考`, `共用SVG資料夾`, the leading `/`, and `.svg`, then append the Chinese method description from the CommonFunc catalog; only the landing note/package trace list keeps the exact `.svg` filename.

Example:

```plantuml
ref over Ent : CommonFunc.GetAccountInfo\n取得帳戶資訊\n　\n　\n30_CommonFunc.GetAccountInfo取帳戶信息
```

落版說明或交付追溯清單中的實際檔名仍需能對上 `v1.x Reference/共用svg` 下的 SVG，例如 `28_CommonFunc.GetCurrEName.svg` 或 `67_CommonFunc.GetCENCurrFunc.svg`；但圖面 ref 橙色說明條不得顯示 `循序圖請參考`、`共用SVG資料夾` 或 `.svg`。

## VSDX 交付

从技能输出产出 VSDX 时：

0. Treat this section as mandatory for normal DAWHO sequence-diagram delivery. Skip it only when the user explicitly requests PlantUML/SVG-only output or when the environment makes native VSDX generation impossible; in that case, state the blocker in the final handoff and in the landing note.

1. Create or refresh `output/sequence_diagram/{functionCode}/{functionCode}_native_visio_spec.json`.
2. Build the formal VSDX with `scripts/build_native_visio_sequence.ps1`.
3. Run `scripts/validate_native_visio_output.ps1` on the VSDX. The output is not formal delivery if validation reports a single SVG-import group, `ForeignData`, `visio/media`, `visio/embeddings`, non-native fragments, member overflow, message/fragment overlap, unglued message endpoints, sparse/non-uniform participant connection-point rows, or message rows off the participant connection-point grid. Do not add per-message lifeline connection rows merely to raise `Page.Connects.Count`; only a full, uniform UML-native connection-point grid is allowed.
4. Use Visio UML masters for User/Object lifelines, Message, Self Message, Return Message, Alternative fragment, Optional fragment, Loop fragment, Interaction operand, and Other fragment where the native spec requires them.
5. Use `references/native-shape-library/manifest.json` and its templates as the style registry; fail clearly when a required UML master/template is missing.
6. Keep message labels on their Visio UML connector/message shapes when possible, so selecting or double-clicking the arrow edits the label in the normal Visio way.
7. Keep every nested `group` / `alt` / `opt` / `ref` frame, orange pointer block, and note fully inside its containing frame. If a child block becomes wider than the parent, shorten or wrap the label first, then widen the parent only within the outer frame boundary. A business `group` is the outer semantic stage when it names the stage, so a request/response judgment `alt` inside that stage must be fully enclosed by the group rather than becoming a sibling or parent of the group.
8. Every native `Message`, `Return Message`, and `Self Message` arrow must leave at least one connection-point interval from other visual shapes, including fragment frames, group/ref/alt headers, section divider/title boxes, notes, and orange pointer strips. One interval means the vertical distance between two adjacent default connector points on the participant lifeline, not a fixed inch value. Self Message folded arrows are taller and must reserve double vertical spacing: two participant connection-point intervals above and two below. Move the message row or the neighboring shape; do not allow arrows to touch, overlap, or visually merge with another shape.
9. Orange pointer backgrounds must be inset inside their `ref` frame on left, right, and bottom. Never let the orange background touch or cross the ref border; resize the orange rectangle and its text together.
10. `alt` / `else` condition labels must use the native UML fragment condition/operand slots. Header tabs from `alt`, `opt`, `ref`, or business `group` frames must never cover or clip condition text such as `[無計息資料]` or `[歷史定存查詢（fixedDepositQueryScope=HISTORY）]`.
11. Final VSDX graphics must fit completely inside the Visio page. Remove excessive right-side page whitespace and fix long text fragments that enlarge selection bounds beyond the visible diagram before page fitting. On short-flow tabs, calculate the page width from the participant/content bounds instead of reusing a wide page from another tab, and horizontally center the participant group within the page.
12. Do not export SVG or PNG reference images by default. If the user explicitly requests image output, handle it as an extra artifact and do not make it part of the normal VSDX acceptance gate.
13. If the target VSDX already exists, overwrite only through the requested output path. Do not create adjacent `.bak`, `.before_*`, timestamp, or other delivery-directory backup copies unless the user explicitly asks and the active workspace rule allows it.
14. When Visio COM supports it, save/export the final VSDX in Visio 2013-2016 compatible form for customer delivery and mention compatibility in the handoff. If compatibility export cannot be verified, report it as a remaining delivery risk rather than silently claiming it.

### 原生 Visio 重建模式

生成正式 VSDX 输出时，或用户要求 VSDX 内部使用与参考附件相同的可编辑 Visio 图形（例如原生箭头、参与者、`group`/`alt`/`ref` 框或真实连接器关系）时，使用原生重建：

- Keep PlantUML text drafts and the native reconstruction spec aligned to the same business content and visual layout.
- Create or update a native reconstruction spec such as `output/sequence_diagram/{functionCode}/{functionCode}_native_visio_spec.json` before producing the formal VSDX. If no native spec exists, the output is not native-delivery ready.
- Every formal native spec must declare `messageStyle.policy`. Default to `e001-reference`, which follows `v1.x Reference/E.001_01.vsdx` / `references/standard-examples/E001_native_reference.vsdx` for native line/master behavior, while message / return / self-call label font color defaults to black `RGB(0,0,0)` unless an explicit local `textColor` override is required. Use `project-red` only when the user explicitly wants all message arrows/labels red. Use `preserve-native` only when the user explicitly wants raw Visio master colors. Do not leave message color policy implicit.
- Use a reference VSDX only as a Visio master/template source; do not inherit its old business text.
- Use `scripts/build_native_visio_sequence.ps1` with a JSON spec to create native participant heads/lifelines, `Message`, `Self Message`, `Return Message`, and frame shapes while keeping the reference VSDX masters available as style/template sources.
- Before Visio shape dropping, run the native layout planner. The builder must first resolve page skeleton, tabs, participants, section titles, fragment frames, alt operands, and ref blocks into connection-point rows, then draw regular message arrows last. Do not use post-build coordinate repair as the normal way to fix overlaps.
- Native layout order is fixed: create page/tab skeleton, place participants, place section titles, place native fragments, estimate and set fragment/member heights from their content, adjust fragment positions against non-fragment content, then fill message arrows. `ref` is atomic: when its frame is placed, set its six-connection-point height, internal CommonFunc/CommonUtil self-call, and inset orange pointer together; a ref self-call without the same-method orange pointer strip is invalid. Keep main-flow messages outside it. Native `Interaction operand` headers consume real height, so first branch messages need a header guard, self messages reserve double rows around the full `BeginY` to `EndY` folded span, and a self message followed immediately by another fragment needs one extra guard row.
- When a business group contains a downstream request/return judgment, determine the group frame first and then place the native `alt` inside that group. For the interest-detail flow, `查詢計息資料` is the outer group and the ED0005/ED0009 `[系統異常] / [查詢成功]` native `alt` must sit inside it while wrapping the IRIS requests/returns, CommonFunc ref, Response 9001, and downstream interest assembly content.
- For native VSDX stability, the script must load `references/native-shape-library/manifest.json` first. Each reusable visual component should live in its own small template file under `references/native-shape-library/templates/`; formal delivery must use the template/native-master path and fail clearly when required components are unavailable.
- When a visual issue is fixed repeatedly, update or add a native shape template instead of burying another coordinate tweak in the generator. Current template components include `page-title`, `user-participant-head`, `object-participant-lifeline`, `uml-fragment-frame`, `actor-head`, `participant-head-box`, `clipped-header-tab`, `section-divider`, `orange-pointer-strip`, `alt-condition-label`, `note-card`, and `ref-common-svg-block`.
- Native VSDX output should include the same top page title style as the E.001 native reference. Use the `page-title` template with `page.title.text`, centered near the page top, and add a title band / top offset instead of crowding participant heads.
- The top page title is the function-level title, for example `L.003 自動扣繳申請`. Do not use a flow/tab name such as `L.003 扣繳總覽` as the main title. Put the flow/tab meaning in a smaller centered subtitle below the function title, or in section dividers when no separate subtitle is needed.
- The native `actor-head` template is diagnostic only. Formal VSDX delivery must use the Visio UML `Actor lifeline / 動作項目生命線` master or a matching template lifeline, so the User icon stroke and proportions match a native stencil drop.
- Native participant heads should preserve the master/template style by default. Do not force DAWHO green, bold text, or fixed line weights onto `Actor lifeline` / `Object lifeline` children; only change text content, position, lifeline length, and connection rows.
- The native `user-participant-head` template owns the composite User participant strategy. In preserve-native-style mode, drop a fresh `Actor lifeline` master from the template document instead of reusing a stale page instance, then move it into the generated participant position. Keep the UML lifeline's built-in dashed line as the message connector target; do not generate a separate dashed lifeline or invisible anchor for formal native delivery.
- The native `object-participant-lifeline` template owns non-User participants such as `APP` and `Enterprise`. In preserve-native-style mode, drop a fresh Visio `Object lifeline / 物件生命線` master or matching template object lifeline, preserve its native visual style, read the UML master's native default connection-point interval, and normalize the visible lifeline to a complete uniform row set using that interval. Place message arrows only on those existing rows. Do not add per-message connection-point rows merely for connector glue or statistics.
- Native reconstruction specs may use `texts[].template` for reusable text-like visuals, for example `note-card` and `orange-pointer-strip`. Do not use manual `texts[]` coordinate boxes for the first condition inside an `alt`; put that value on the native frame as `frames[].condition` so the generator replaces the UML Alternative fragment's initial operand/condition slot.
- For future CommonFunc/CommonUtil ref blocks, prefer the `refCommonSvgBlocks` composite entry backed by the `ref-common-svg-block` template when the block does not need a Visio UML self-message label bound to the arrow. When arrow-label editability matters, keep the method text on `Self Message` and use the template only for surrounding notes / pointer strips.
- Validate the template registry after editing the library: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_native_shape_library.ps1`. If validation fails, repair the template library before generating delivery VSDX files.
- The final VSDX must pass `scripts/validate_native_visio_output.ps1`: more than one page shape, no `ForeignData`, no `visio/media`, no `visio/embeddings`, a project Visio theme part/relationship, native UML fragments, message rows on the participant connection-point grid, every message/return/self-call endpoint glued to an existing participant connection point, full uniform UML-native lifeline connection rows, and no per-message generated lifeline connection-point rows.
- Formal VSDX delivery must preserve real Visio operation experience, not only visual similarity. A recipient should be able to select a participant as a native UML lifeline, select an arrow as a single native `Message` / `Self Message` / `Return Message`, edit labels on the shape itself, drag expected yellow control points, and move/resize native fragments without detached text boxes or hand-drawn replacement geometry breaking the interaction.
- Reject any handoff note that does not clearly state the VSDX was produced by native reconstruction through `scripts/build_native_visio_sequence.ps1`, and reject notes that say or imply the formal VSDX was produced by `SVG 匯入 Visio`.
- Do not export an official preview PNG by default. When the user explicitly requests image output, treat preview cleanup as an extra artifact task and keep it outside the normal VSDX delivery gate.
- Native VSDX frames must clear Visio master placeholder text such as `選用`, `標題`, `[條件]`, `迴圈`, `替代`, and `[參數]`; only explicit labels from the JSON spec may remain visible.
- Native `alt` / `opt` / `loop` / `ref` / business `group` frames should use Visio UML fragment masters in preserve-native-style mode. Use the UML sequence stencil's `替代片段 / Alternative fragment` for every `alt`, but keep the delivery diagram header text as `alt`; use `Optional fragment` for `opt`, `Loop fragment` for `loop`, and `Other fragment` for business `group` when no dedicated group master exists. Do not use hand-drawn clipped-card frames for formal native delivery.
- Native `alt` fragments must own their internal diagram content through Visio container membership where the master supports it. After all frame and message geometry is finalized, add internal messages, self-calls, nested `ref`/`alt`/`group` frames, and orange pointer blocks as members of the smallest containing UML fragment; exclude participant lifelines/heads so moving a fragment does not drag the participants themselves. Direct if/else `Interaction operand` regions must be inserted with Visio `ContainerProperties.InsertListMember(...)`, not only `AddMember(...)`, so `ContainerProperties.GetListMembers()` returns those operand IDs and selecting/dragging an operand highlights the owning `alt` frame in Visio. A formal native `alt` with zero members or operand members but empty list members is not acceptable when it visually contains branch regions.
- Native fragment defaults such as `選用`, `迴圈`, `標題`, `替代`, `[參數]`, and `[條件]` must be replaced with explicit generated labels. For `alt`, set the header text to `alt` and put the first branch condition from `frames[].condition` by replacing the native `[條件]` placeholder exposed by the Alternative fragment master, not by dropping a separately positioned text box or extra condition shape. Branch separator / else-condition regions should use the native `Interaction operand` master instead of ordinary hand-drawn separator lines.
- Native `alt` / `else` condition text must always be bracketed. The first branch condition and every direct `Interaction operand` separator label must render as `[condition]`; generator code may normalize bare spec labels into brackets, but formal output with naked `else` condition text is invalid.
- Native `opt` fragments must keep a real Visio UML fragment operation experience with header text `opt`. Prefer a native fragment master that exposes container membership, the right-side resize control, and a native `[條件]` / `Interaction operand` slot; if Visio's `Optional fragment` master lacks those behaviors, use the native `Alternative fragment` variant with the displayed operator changed to `opt`. Put the optional condition from `frames[].condition` into that native condition slot, not only in the header tab or as a plain text box.
- Native `alt` operand regions must be normalized after layout: the first branch operand spans from just below the header to the first `else` separator but hides its line so the `if` condition head has no extra visible top segment; each later `Interaction operand` starts at its `else` separator, uses one visible DAWHO green dashed separator line from the native operand itself, and extends to the next separator or to the frame bottom. The final operand bottom must stay tight to the `alt` frame bottom. Formal output must not use same-position dashed overlay lines or ordinary hand-drawn lines to represent `else` separators.
- Native `alt` operand height must be explicitly planned before Visio output: every non-final `Interaction operand` is sized from its current branch top to the next operand separator, and the final operand is sized to the final branch bottom. Do not rely on the UML master's default operand height after `ContainerProperties.InsertListMember(...)`; Visio may shrink the if operand and make if-branch content appear under the else separator. After layout is finalized, write each direct operand's `PinY`, `Height`, and `LocPinY` back as editable constants; do not leave cross-member `Sheet.*!Height` / `Sheet.*!PinY` formulas in formal delivery, because they invert or distort the user's native drag behavior.
- Native `alt` operand visual order must match the spec branch order: the frame condition is the first `if` branch, and direct `separators[]` become following `else` operands sorted from top to bottom. Finalizers may add missing fragment membership, but must not blindly reinsert existing `Interaction operand` shapes at list position `0`, because that reverses branches and pushes the no-line `if` operand to the bottom.
- When normalizing nested native `alt` operands, resize only direct operands: either an `else` operand whose left and right bounds already align with the current `alt` frame, or the first condition operand that sits near the current frame header. Never let an outer `alt` normalize a nested child `alt` operand, because that pulls the child `else` condition label outside its own fragment lane.
- A first-condition operand for a nested `alt` must start at or below that `alt` frame's top edge. A bracketed operand that sits above a child `alt` frame is an outer-branch separator, not the child frame's first condition, even when it is horizontally aligned with the child.
- Operand-driven sizing must be non-destructive: direct if/else operands may expand an `alt` frame's left/right/bottom bounds, but a default short separator operand must not shrink an existing frame and push branch content outside.
- After native operand normalization, formal editable `alt` output must use the Visio UML master variant that exposes the yellow right-side list-size control (`Alternative fragment.52` when available) and the matching operand variant (`Interaction operand.53` when available). Bind the `alt` frame width to `Controls.Row_1`, keep the frame left edge fixed, insert direct if/else operands as native list members in branch order, and set their width to `IFERROR(LISTSHEETREF()!Controls.ROW_1,User.UserWidth)` with `PinX` tied to `LISTSHEETREF()!PinX`; do not leave operands as ordinary container members with `ListMembers=[]`. After every `InsertListMember` batch, immediately restore `Controls.Row_1.X`, `Width`, and `PinX` from the pre-insertion frame bounds because Visio can shrink a list container to the operand master's default width; then lock membership when needed so branch regions cannot be dragged out of the `alt` frame. Vertically, use the generated separator top distances only during layout calculation, then freeze direct operand vertical cells as constants so hand-editing behaves like a normal Visio UML fragment rather than a scripted formula chain.
- For nested native fragments, only smaller child fragment frames (`alt`/`ref`/`opt`/`loop`/`group`) that are fully contained inside the parent frame may become members or push a parent `alt` branch bottom downward. Do not treat following sibling fragments, section dividers, lifelines, or ordinary messages outside the branch as child content, or moving/resizing an earlier `opt`/`alt` will incorrectly drag later sibling `ref` blocks or stretch across the next section. When a child fragment extends below the current final operand, bind that final operand bottom to the child frame bottom plus a small padding, then let the parent `alt` follow the operand.
- Nested child fragments must keep a visible hierarchy inset from the parent fragment. Do not let a child `group`/`alt`/`ref` share the exact same left or right border as its parent; broad child fragments should be inset by about one participant connection-point interval on both sides, and they must keep at least two participant connection-point intervals from the parent fragment top/header when they start immediately under that parent. Example: inside an `alt` success/else branch, a business group such as `查詢定存存單資料` must sit slightly inside the parent `alt`, not flush with the `alt`/`else` frame edge.
- Success-like `else` branches such as `[會員身份符合]`, `[帳號檢核通過]`, `[查詢成功]`, `[參數有效]`, or `[有資料]` are not visual continuation markers. If the following group/ref/message occurs only when that `else` condition holds, the owning `alt` and its final `Interaction operand` must extend to cover that full success branch, and the nested group/ref/messages must become members of the owning `alt`. Do not end the `alt` immediately after the `else` separator and place the main-flow group just below it; this creates the false appearance that content belongs to `else` while Visio treats it as a sibling outside the branch.
- When a flow performs downstream requests and then judges their response, and the delivery visual standard requires the request/response/ref and follow-up assembly to sit inside that judgment domain, move the same native `alt` upward and extend it to wrap the whole domain. Do not duplicate the request messages or change business order. Example: `GetFixedDepositInterestDetail` must wrap ED0005/ED0009 IRIS request/response, `CommonFunc.GetCENCurrFunc` ref, `Response 9001`, and interest-data assembly inside the `[ED0005 或 ED0009 系統異常] / [查詢成功]` native `alt`.
- Native `alt` frame width and height must cover the complete content of every branch, including nested `ref` frames, orange pointer strips, response arrows, and follow-up APP self-calls that semantically belong inside the branch. If branch content overflows, widen or extend the `alt` frame and separator right edge / bottom before preview export, then rerun list-member insertion and container membership. A frame that has correct `ListMembers` but is narrower than its member messages is still not delivery-ready.
- After native VSDX `SaveAs`, run `scripts/finalize_native_visio_fragments.ps1` before preview export if fragment masters can materialize default `[條件]` operands. PowerShell placeholder matching should build Traditional Chinese strings from Unicode code points or otherwise be BOM-safe, so Windows PowerShell code pages cannot break cleanup.
- Native fragment headers must keep the Visio UML master style and must not cover condition labels or message labels.
- Native `alt` frames should show explicit first-branch condition text in the native condition area under the `alt` header when the branch meaning would otherwise be ambiguous. Do this by setting `frames[].condition`; the generator must directly replace the native `[條件]` placeholder from the Alternative fragment master. Avoid feature-specific left/top tuning for that condition unless a real collision remains after native placement.
- Native `ref` / `alt` / `opt` / `loop` header text should be centered within the UML header tab and use the same DAWHO green as the frame border.
- Native alt/operand condition labels, including first-branch labels and `Interaction operand` separator labels, should use the same DAWHO green as the fragment border and must keep square brackets such as `[查詢成功]`. Do not leave condition labels in default black when the frame border is green.
- Section divider label text should use the same DAWHO green as the divider lines and label-box border, and should be bold enough to read as the section title.
- Section divider / 子功能 title 的中央標題框要依文字長度自動加寬；中文標題優先擴框，不縮字、不折行。標題框仍需留在分隔線可用寬度內，並保持可編輯邊框。
- Section divider / 子功能 title 下方若緊接第一個業務 fragment，兩者之間至少保留兩段參與者連接點，不可讓 section title、外層 business group、內層判斷 `alt` 擠在同一條水平帶。例：`查詢與組裝計息資料` title、`查詢計息資料` group、ED0005/ED0009 判斷 `alt` 三層需逐層下沉，形成清楚層級。
- Section divider double-lines must follow the participant/content width, not the old full-page width. In native specs, set divider `left` / `right` to the first/last participant or content bound plus a small symmetric padding; do not let dividers stretch into empty right-side canvas on short-flow tabs.
- Formal native VSDX pages must not auto-resize when a downstream editor adjusts a section divider or edits the centered section-title border. Set the page `DrawingResizeType=0` and `ResizePage=FALSE` after applying the fixed page size.
- Section divider long lines are layout guides, not page-size handles. Lock their horizontal sizing and calculation behavior (`LockWidth=1`, `LockHeight=1`, `LockCalcWH=1`, `LockAspect=1`, `LockMoveX=1`) while leaving vertical movement available (`LockMoveY=0`) so editors can move the section up/down without expanding the page.
- Centered section-title boxes must remain Visio-editable. Do not lock `LockWidth`, `LockHeight`, or `LockCalcWH` on the title box; users should be able to drag the title border wider/narrower while the fixed page size prevents the page itself from growing.
- Native UML lifelines must preserve real Visio secondary-edit behavior by exposing full connection-point rows along the visible dashed lifeline. The row interval is the Visio UML master native default interval, discovered from the dropped lifeline, not a hard-coded inch value. It is acceptable and expected that selecting User/APP/Enterprise/IRIS/DB/Redis lifelines shows a full column of gray connection dots; this lets downstream editors add or reroute messages naturally. Generated message heads/tails must glue to the nearest existing connection row on the lifeline, not create extra per-message connection rows, so the diagram remains clean and behaves like a manually edited Visio UML diagram.
- Nested fragments must leave visible breathing room around branch separators, self-call arrows, and follow-up steps. When a business step belongs after an inner `alt`, place it below the inner frame with clear gap instead of touching the inner frame border; when a self-call sits before an operand separator, move the separator or message so the dashed line does not cross the folded arrow or its label.
- Message arrows must also clear non-message shapes by at least one connection-point interval. This applies to top/bottom edges of native fragment frames, group/ref/alt header tabs, section divider lines/title boxes, notes, and orange pointer strips. If a message row is visually adjacent to a frame/header/strip, move the arrow row down/up or move the frame so a full connection-point gap remains. For `Self Message`, use double clearance: two connection-point intervals above and below the full folded-arrow span.
- Branch fit checks must use the real occupied range of each message, not only the message row's top coordinate. A native `Self Message` occupies the full folded-arrow span from `BeginY` to `EndY`; the if/else separator must be at least two connection-point intervals below the folded arrow's lower end and at least two connection-point intervals above the next relevant message or shape. If a self-call crosses or crowds a native `Interaction operand` separator, the output is wrong even when the message's nominal `top` value belongs to the intended branch.
- The `clipped-header-tab` template is diagnostic only; do not use it for formal preserve-native UML fragment output.
- If participant masters leave faint duplicate borders, uneven label boxes, or non-obvious selection artifacts in the preview, repair the master/template reuse path while preserving native style. Do not rebuild participant heads manually for formal delivery, because manual rebuilding can drift from Visio stencil appearance.
- When rebuilding the `User` participant natively, prefer the project reference VSDX style when the user provides one, such as `v1.x Reference/E.001_01.vsdx`: use the Visio `Actor lifeline`-style open outline person with small circle head, side arms, body, and legs above the separate `User` label box. Do not replace it with a hard rectangular torso icon or PlantUML's default unboxed stick actor.
- Keep the first section divider, such as `進入匯率表`, visibly below the participant label boxes. In native specs, leave a clear vertical gap of roughly `0.35 in` or more between the participant label bottom and the double-line section divider so the divider does not crowd the participant heads.
- Only use generated dashed lifeline segments in diagnostic runs outside formal delivery. For formal native delivery, fail clearly if `Actor lifeline` / `Object lifeline` masters or template shapes cannot be resolved; do not silently switch to hand-drawn lifelines or hidden anchors.
- Read native reconstruction JSON specs as UTF-8 explicitly so Traditional Chinese labels cannot be corrupted by the host PowerShell code page.
- If the reference/template VSDX is open in Visio and locked, copy it to the feature output folder, clear any read-only attribute on the copy, and use that themed copy as the native master source. Reuse an existing generated VSDX only when it already contains the required UML masters and the project Visio theme part/relationship. Do not stop the visual refinement only because the reference copy is open.
- Native self-call labels must be stored on the Visio UML `Self Message` shape itself, not as a separate parallel text box, so selecting or double-clicking the arrow edits the message in the normal Visio/UML way. The native spec must declare a `messageStyle.policy`: use `e001-reference` by default, `project-red` when the delivery needs all project red arrows/labels, or `preserve-native` when the user explicitly wants raw Visio master styling. Do not rely on implicit PlantUML black/default text.
- Native self-call labels must expose an adjustable text-position control point on the same `Self Message` shape. `TxtPinX` and `TxtPinY` should use `SETATREF(Controls.TextPosition.X/Y)` instead of fixed formulas, so the user can reposition the label in Visio without detaching it from the arrow.
- Native self-call text should default to `labelSide = "right"`: paragraph left-aligned, placed just to the right of the folded arrow. Treat `labelSide = "center"` as a layout smell in formal delivery unless the user explicitly asks for that local exception via `allowCenteredLabel`.
- Native participant-to-participant message and return-message labels must sit directly above their arrow on the same UML message shape, using a compact default text offset around `0.04 in`. Do not rotate the label vertically, drop it below the arrow, or detach it as a separate text box.
- In native reconstruction mode, use the Visio UML `Self Message` master for self-calls so the arrow remains a single editable UML self-message shape instead of three independent line segments. Manual line segments or detached labels are not formal delivery output unless the user explicitly accepts that tradeoff.
- In native VSDX, CommonFunc/CommonUtil text belongs on the native reference self-call arrow inside the `ref` frame; do not draw it as a main-flow Enterprise self-call, and do not leave a separate text box that collides with the arrow or orange pointer strip.
- In native VSDX, `ref` is a reusable-reference fragment, not a main-flow container. It may contain exactly the compact CommonFunc/CommonUtil native reference self-call arrow that identifies the referenced common method, plus the inset orange SVG pointer/description. The pointer strip text must be `循序圖請參考：` + SVG basename without `.svg` + a Chinese description, for example `循序圖請參考：116_CommonFunc.GetFrontContentParamFile 取得DAWHO.sitemap文件數據`; do not show `共用SVG資料夾`, a leading `/`, or `.svg` on the strip. Do not mix real request, response, return, APP display self-calls, or Enterprise business-processing self-calls into a `ref`; place those flow messages outside the `ref` with fixed connector-point spacing. Conversely, if a main-flow message/self-call label begins with `CommonFunc.` / `CommonFunc/` / `CommonUtil.` / `CommonUtil/`, the spec is wrong and must be rewritten as a `ref` fragment before VSDX delivery. Inside the `ref`, reject `CommonFunc/MethodName` and `CommonUtil.MethodName`; use `CommonFunc.MethodName` and `CommonUtil/MethodName`.
- In native VSDX, request/self-call/return arrows should use the corresponding Visio UML `Message`, `Self Message`, and `Return Message` masters. Color and label color are controlled by explicit native spec policy: `messageStyle.policy = "e001-reference"` follows the E.001 reference/native theme for arrow/master behavior, ignores generic `red=true` RGB forcing, and sets all message / return / self-call label fonts to black by default; `messageStyle.policy = "project-red"` applies project red `RGB(176,21,19)` to message line and label; `messageStyle.policy = "preserve-native"` keeps raw master defaults except where the native spec declares `textColor`. Use explicit per-message `lineColor` or `textColor` only when a local override is truly required.
- In native VSDX, keep message labels out of group/ref header tabs. Move request rows down or move frames down rather than allowing labels such as `Exchange/GetRateList` or `CommonUtil/EditCommonCurrency` to cover group headers.
- Supporting reference notes inside `ref` frames, such as `循序圖請參考：E.002 ...`, should use the same orange pointer-strip style as CommonFunc/CommonUtil SVG references when the user asks for visual consistency. Increase the containing `ref` height and spacing so the orange strip, self message arrow, and arrow label never overlap.

## 样式一致性关卡

交付前，需将最终原生 VSDX 与 E.001 原生参考比对，而不只比对原始 PlantUML 文本。以下失败模式必须在交付前修复：

- final files do not exist as feature-local `{functionCode}_native_visio_spec.json` and `vsdx/{functionCode}_01.vsdx` under `output/sequence_diagram/{functionCode}/`;
- formal delivery creates more than one official VSDX file for the same `functionCode`, or reports scenario/API-specific VSDX files as official output instead of the single `vsdx/{functionCode}_01.vsdx`;
- formal VSDX tabs are split by API, success/failure scenario, step, subflow, or every small PRD page instead of coherent user flow; one continuous fill-in/confirm/submit/result journey must not be scattered across multiple official tabs unless the PRD gives independent user entries;
- default delivery creates SVG/PNG reference renders even though the user did not explicitly request image output;
- landing note says VSDX is a future optional step, such as `若後續要做 VSDX`;
- `User` is still the default PlantUML stick actor, a plain stick figure with horizontal arms, a too-short label box, a thinner border than APP/Enterprise, or an unboxed `User` label instead of the DAWHO Visio task-icon participant head;
- `Redis` or `DB` is rendered as PlantUML's `database` cylinder/storage icon instead of the same boxed participant style as APP/Enterprise/IRIS;
- the whole `ref` block is orange instead of only the SVG pointer strip;
- formal VSDX does not have a sibling `{functionCode}_native_visio_spec.json`, or the spec was not used by `scripts/build_native_visio_sequence.ps1`;
- formal VSDX or its native master is missing `visio/theme/theme1.xml` / the document theme relationship, causing UML `THEMEVAL()` colors to render as default Visio black/gray instead of the DAWHO E.001 red/green template;
- native validation fails because the VSDX is a single top-level SVG-import group, contains `ForeignData`, contains `visio/media` / `visio/embeddings`, uses non-native fragments, has fragment member overflow, or has message arrows too close to other shapes;
- the VSDX only looks correct in preview but does not operate like Visio UML: participant labels are plain boxes instead of native lifelines, arrows are manual lines instead of glued native message shapes, self-call labels are detached text boxes, expected text-position / resize controls are missing, or resizing an operand/frame does not update the owning native shape;
- the sequence diagram does not state the function entry points required by PRD/TSD;
- member type / member qualification validation is missing when the PRD/API Detail requires it, or is added without PRD/API Detail evidence;
- in native mode, branch regions are hand-drawn ordinary lines instead of `Interaction operand`;
- a native `alt` visually contains messages/conditions but `ContainerProperties.GetMemberShapes(...)` returns zero members, or direct `Interaction operand` branch regions exist as members while `ContainerProperties.GetListMembers()` is empty or missing those operand IDs;
- a native `alt` has valid `GetListMembers()` but its frame bounds no longer cover member messages or branch content after list insertion;
- a native `alt` has valid `GetListMembers()` but a message or self-call crosses an `Interaction operand` separator line, causing if content to appear in the else branch;
- an `alt`/`else` condition label is a plain text box instead of a native UML `Interaction operand` shape;
- the `if` first-branch condition has an extra visible line above it, the last `else` operand bottom floats above the `alt` bottom border, or branch content such as a nested `ref`, response, or APP self-call is visibly outside the `alt` frame that owns it;
- a success-like `else` condition is followed immediately by a group/ref/message just outside the `alt` bottom border; this content must be inside the final `Interaction operand`, not a sibling after the `alt`;
- a child `group`/`alt`/`ref` shares the same left or right border as the parent fragment, making the nested structure look flat instead of visibly inset;
- a business `group` has only a title tab and no enclosed message/ref/alt/opt/group content; if it is just a section label, use a section divider, and if it is a semantic stage frame, expand it and make the child fragments native members;
- a native `ref` frame contains request/response/main-flow self-message arrows, or lacks the compact CommonFunc/CommonUtil reference self-call when the ref is pointing to a common SVG;
- a nested `alt` operand separator or condition label is stretched to an outer `alt` frame boundary instead of staying inside its own child fragment;
- APP self-calls or any message/return labels in native `e001-reference` output use fixed red/theme text instead of black `RGB(0,0,0)`, unless the native spec explicitly declares a local `textColor` override;
- self-call labels are centered over the folded arrow instead of left-aligned to its right side, float above the folded arrow, contain raw field dumps, or show technical parameter snippets in a different text color than the Chinese label;
- long condition labels are clipped by `alt`/`opt`/`ref` header tabs;
- first-branch condition labels overlap the UML header tab text such as `alt` or `ref`, or condition labels are black while the frame border is green;
- section divider label text is black instead of matching the green divider border;
- section divider / 子功能 title box is too narrow and wraps Chinese title text instead of widening by label length;
- dragging or resizing a section divider title border can enlarge the Visio page, `DrawingResizeType` is not `0`, `ResizePage` is not `FALSE`, divider lines are not locked as horizontal layout guides, or centered section-title boxes are locked against normal border resizing;
- ED0005/ED0009 IRIS interest-query request/response, CommonFunc ref, or interest-data assembly sits outside its `[ED0005 或 ED0009 系統異常] / [查詢成功]` native `alt` judgment domain, or that native `alt` sits outside / wraps around the `查詢計息資料` business group instead of being enclosed by it;
- selecting a lifeline in Visio shows only sparse message attachment points instead of full UML-native connection-point rows along the dashed lifeline, shows non-uniform or clustered connection dots around message/self-message arrowheads, or arrow heads/tails are not glued to the nearest visible connection point;
- a message / return / self-call arrow is less than one connection-point interval from any frame border, fragment/group/ref/alt header, section divider/title box, note, or orange pointer strip;
- an inner `alt` border touches the next business self-call, or an operand separator crosses a self-call arrow/text;
- orange SVG pointer backgrounds touch or cross the `ref` frame border;
- optional image output, when explicitly requested, contains pure yellow Visio control-handle artifacts from editable text-position/shape controls;
- excessive right-side whitespace remains, section divider double-lines run far beyond the participant group/content width, participants sit awkwardly against the left edge on short-flow tabs, or the diagram selection bounds exceed the page.

## 工作流程

1. Resolve authoritative API sources through the parent design skill or user-provided paths.
2. Extract API names, descriptions, request/response fields, backend sources, and business logic.
3. Identify the PRD/TSD user flows for the `functionCode`, merge consecutive PRD pages/screens that form one continuous user journey, and map each coherent flow to a Visio page tab inside the single formal VSDX.
4. Choose participants strictly from actual main-flow calls.
5. Create or refresh the native reconstruction spec as the execution source for formal VSDX.
6. Draft/update PlantUML from the same content as a text/content reference source, using the style template and canonical field names.
7. Add `ref over Ent` blocks for common SVG references in PlantUML and matching native `Other fragment` / orange pointer-strip entries in the native spec.
8. Run the native layout planner against the spec before Visio COM rendering. The planner must express all vertical positions as participant connection-point rows, keep fragment/member content enclosed, set `ref` blocks as six-row atomic units, and leave at least one row between message arrows and other shapes; self messages reserve two rows above and below their folded span, plus an extra guard row before a following native fragment when needed to account for Visio master boundary offsets.
9. Unless the user explicitly requested PlantUML/SVG-only output, build the formal VSDX with `scripts/build_native_visio_sequence.ps1`; the builder should draw skeleton/participants/section titles/fragments first and regular message arrows last, then run the native VSDX validator and fail if it detects old SVG-import structure or overlap risks.
10. Create or update the landing note with diagrams, frozen sources, common SVG references, VSDX output paths, and validation result. If VSDX was skipped or failed, record the exact reason instead of silently omitting it. The landing note must not contain forward-looking wording such as `若後續要做 VSDX` when the user asked for normal DAWHO sequence-diagram delivery; VSDX is already part of the default deliverable. Do not list SVG/PNG reference renders unless the user explicitly requested them.
11. Validate.

## 验证

始终执行文本验证：

- `@startuml` count equals `@enduml` count.
- No stale names identified during analysis.
- No `DB`/`Redis` lifelines unless directly used in the main flow.
- The generated `.puml` must not contain `database "DB"`, `database "Redis"`, `collections`, or `queue` declarations for delivery diagrams; `DB` and `Redis` must be plain boxed `participant` declarations.
- Common SVG filenames referenced in `ref over` exist in the common SVG directory when available.
- In formal VSDX delivery output, `User` uses the DAWHO Visio task-icon participant head, not PlantUML's default stick actor. Fail validation if the output still contains an unboxed `User` label, the default stick-actor drawing, a plain stick figure with horizontal arms, a User border thinner than APP/Enterprise, or a User label box visibly shorter than the APP/Enterprise participant boxes.
- In formal VSDX delivery output, `DB` and `Redis` use boxed participant heads. Fail validation if either head contains cylinder/ellipse/storage icon geometry or visually differs from the APP/Enterprise/IRIS participant head style.
- The final delivery paths exist under `output/sequence_diagram/{functionCode}/` as `{functionCode}_native_visio_spec.json` and `vsdx/{functionCode}_01.vsdx` unless an explicit blocker is reported.
- The formal VSDX is the single official VSDX file for the `functionCode`. Its page tabs correspond to coherent PRD/TSD user flows; tabs must not be split merely by API, backend call, scenario, step, subflow, or every small PRD page/screen.
- Default delivery does not create SVG/PNG reference renders. If the user explicitly requested image output, keep those artifacts clearly separate from the normal VSDX acceptance gate.
- Formal VSDX has a current `{functionCode}_native_visio_spec.json` and the landing note states it was built by `scripts/build_native_visio_sequence.ps1`, not by SVG import.
- Formal VSDX passes `scripts/validate_native_visio_output.ps1 -VsdxPath <path>`: more than one top-level shape, no `ForeignData`, no `visio/media`, no `visio/embeddings`, a project Visio theme part/relationship, `DrawingResizeType=0`, `ResizePage=FALSE`, locked section-divider line horizontal sizing, editable section-title box borders, no too-narrow section title boxes, no section-to-fragment spacing collapse, native participant lifeline masters for participant labels, full visible non-clustered and non-sparse connection-point rows on all lifelines using the UML-native interval, message heads/tails glued to existing participant connection-point rows without adding per-message generated rows, black message / return / self-call label fonts, editable self-message text-position controls, native `alt` resize controls, direct condition operands present as true Visio list members of the owning `alt` via `GetListMembers()`, no cross-member vertical formula lock on `Interaction operand` cells, nested child fragments not flush to their parent fragment edges, `EmptyGroupFragments=0`, `RefDisplayNamesMissingPointerPrefix=0`, ED0005/ED0009 interest-query judgment content wrapped by the same native `alt`, and that judgment `alt` fully enclosed by the `查詢計息資料` native group.
- Formal VSDX and the native master include the project Visio theme (`visio/theme/theme1.xml` and a document theme relationship). This is required even when shapes are native, because UML master colors are theme-driven.
- Final VSDX `ref` blocks use transparent/white frames with DAWHO green borders; fail validation if the entire ref block or header tab remains orange. CommonFunc/CommonUtil ref self-call arrows must be folded arrows anchored to the referenced participant lifeline and use the native message style policy from the spec. Any CommonFunc/CommonUtil method drawn outside a native `ref` fragment is a validation failure. Only the `循序圖請參考：...` pointer background may be orange, and it must be inset inside the ref frame while fully covering the pointer text.
- In native mode, branch regions should use Visio UML `Interaction operand` style and should not be ordinary hand-drawn separator lines.
- Self-call labels are business-readable and visually tied to their folded arrows. Fail validation if self-call labels are raw field dumps, long `+`/slash-separated parameter lists, floating far above the folded arrow, detached from the arrow shape, centered instead of left-aligned to the right of the arrow, or contain technical parameter snippets in a different color from the Chinese label.
- The landing note lists actual VSDX output paths or a concrete blocker. Fail validation if it says VSDX is only a future optional step for a normal project delivery request. Do not list SVG/PNG output paths unless the user explicitly requested those extra artifacts.
- If VSDX is produced, verify the VSDX opens in Visio, `visio/media` count is `0`, `visio/embeddings` count is `0`, and no Visio XML entry contains `ForeignData`.
- If VSDX is produced, inspect the native VSDX directly in Visio when visual confirmation is needed. Check the red-flag areas: top participant layout, right-side whitespace, User participant style consistency, left-aligned group/ref headers, centered section dividers, `ref` blocks, orange pointer text, APP self-calls, section divider spacing, duplicate frame borders, nested `alt`/`group` layering, and whether message labels/control points behave from the main native shape in Visio. When a user reports a mismatch from Visio, trust the Visio operation and fix the native ShapeSheet/master binding.

若本机可用 PlantUML，执行：

```powershell
java -jar plantuml.jar -checkonly path\to\file.puml
```

默认验证闭环中不要渲染 SVG 或 PNG 参考图。只有用户明确要求 SVG 输出时，才运行 SVG 专属参与者/后处理关卡。

当存在正式 VSDX 时，始终运行原生结构关卡：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <pluginRoot>\skills\native-vsdx-sequence-writer\scripts\validate_native_visio_output.ps1 -VsdxPath path\to\file.vsdx
```

交接前必须通过此关卡。若 VSDX 出现 `TopLevelShapes = 1`、`ForeignData`、`visio/media`、`visio/embeddings`、手工 fragment 覆盖框、fragment/member 外溢、讯息贴框、讯息端点未 GlueTo、lifeline 连接点稀疏/不均匀，或讯息跨 operand separator，代表旧式/降级结构，不是正式原生交付。不要为了追求 `Connects` 统计值额外加单箭头专属 lifeline connection-point rows。

报告验证类型：仅文本验证、原生 VSDX 验证，或用户明确要求的额外 SVG/图片验证。
