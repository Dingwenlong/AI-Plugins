# DAWHO Naming And Field KB Rules

Use these rules when standardizing API names, method suffixes, field names, response examples, business logic wording, and developer-facing design recommendations.

> Extracted from the former heavy `SKILL.md` so the entrypoint can stay lightweight. Load this file only when the matching workflow is active.

## API 范例情境与响应码

`範例` 属于 API 设计的一部分，不是单纯的文档格式。

- 不要强迫每个 API 都使用相同四个情境标签。不同 API 可能需要不同的成功、无资料、下游错误、验证错误、权限、账号状态或业务规则情境。
- 情境标签应从当前 API 的 PRD/TSD 行为、API Detail 业务逻辑、后端来源说明与预期 UI 状态推导。
- 当 API 没有 request payload 或没有请求参数时，除非契约明确要求空 JSON 对象，否则 `Request` 范例格保持空白；不要为了填满表格而写 `{}`。
- 从已登记的 `tsdApiSpec` 目录搜索 `Api_Response_Codes*.xlsx` 来解析 Response Code 工作簿，优先使用最新版 `Api_Response_Codes_v1.0` 设计文件；若同日存在主版本与交付副本，以主版本/source-of-truth 文件为准，交付副本只作一致性对照。
- 每个非成功范例 response 都必须确认其 `responseCode` 存在于 Response Code 工作簿，且 message 符合目标业务条件；当项目要求完全对照时，范例 JSON 的 `responseCode` / `responseMessage` 必须与 `Api_Response_Codes_v1.0` 设计文件完全一致。
- 匹配 `ResponseMessage` / popup 文案时，应以业务语义判断，不只看文字完全一致。跨模块共用错误（共用错误）如身份/会员资格、登录/认证、装置绑定、安全阻挡、余额/额度、系统忙碌等，应优先检查 `O_Common`。
- 若 `O_Common` 已有同语义 code，应复用。功能特有的 popup 条件、来源文件、按钮文案与页面/context 映射放入 `Remarks`；除非用户明确要求，不要覆盖共用 `ResponseMessage`。
- 若该 message 适合放入 `O_Common` 但尚无同语义 code，需询问用户是否新增共用 `O_Common` code，并提供拟定 code/message/来源证据；未经确认不得自行发明或新增共用 code。
- 只有功能专属业务错误才应在该功能专属 sheet 搜索，例如 L/payment 功能在 `L_Payment`。若专属 sheet 没有适合 code，新增前需请用户确认新的专属 code/message/来源。
- 若 API 需要某个情境，但 Response Code 工作簿没有适合且已确认的 code，或现有 code/message 与范例业务语义不一致，只读时应报告具体 `Must fix` / `Should strengthen` 项，并附拟定 code/message/sheet；编辑时只有在用户确认目标 sheet 与 code/message，或用户已明确提供这些细节后，才可新增或修改。
- 写入、更新或追加 Response Code workbook 行时，受影响的数据列必须设置 `WrapText=True`、水平靠左、垂直居中，并执行 Excel 行高 `AutoFit`。标题列保持视觉居中。长 `Remarks`、popup 对照与来源说明不得横向溢出到右侧空白列。
- 既有业务专属范例列有效时应保留；只有作为 API 设计决策时，才可重命名、新增、删除或合并范例情境，不得把它当成一般格式清理。
- 仅负责格式的技能可以调整 `範例` 表格边框、合并格、字体、换行与空白列，但不得用固定模板替换业务情境。

编辑 API Detail 工作簿时，若情境/code 关系变化，必须同步更新范例标签、request JSON、response JSON 与 Response Code 工作簿；在所有范例和 Response Code 完全一致前，不得标记为 100% 冻版。


## API Detail 契约规则

Apply these rules from `P240301_永豐商銀新大戶_系統設計規範 v2.5 20260514` when checking or editing API Detail and TSD API-list content:

- Replace legacy or draft method wording that uses `Query` with `Get` for query APIs; the purpose is to avoid exposing query parameters in URL-style naming.
- API names, DB table names, and DB table fields use PascalCase; API request/response fields and in-payload variables use camelCase.
- Transaction-style APIs use `{FunctionName}Init`, `{FunctionName}Confirm`, and `{FunctionName}Result` for fill, confirm, and result stages. Use this workflow-stage rule unless the API is a plain query or the user has already frozen a different accepted name.
- Time values use UTC+8 display format `yyyy/MM/dd HH:mm:ss` unless a more specific source contract overrides it.
- Request and Response must both be represented in the Excel API detail. Examples must be present, consistent with the field tables, and complete enough for developers to understand success, failure, validation, and no-data behavior.
- Header parameters are not mandatory as a separate visible section for every API, but API logic must state which values are obtained from Header when the API depends on them.
- Required flags must be explicit: `Y` means the response field always returns; `N` means the field may be omitted when data does not exist. Do not leave request/response requiredness implicit.
- Field data types must reflect the true payload type; do not use a generic string/json type when the PRD/TSD/API behavior proves a more specific type.
- `responseData` no-data behavior is `{}` and not `NULL`, unless a source system contract explicitly requires a different shape.
- The API-facing contract must not use `password`; use `passwd` when the concept is unavoidable. Also avoid exposing `ID`, `Key`, `PWD`, `Password`, `Dept`, `No.` and similar security-sensitive or unclear words as canonical API field names when a clearer business name exists.
- Masking/unmasking is a frontend display responsibility by default. API request/response payloads should carry clear values needed by the contract, not masked display strings, unless the PRD/TSD explicitly defines a masked payload.


## API 内部业务逻辑规则

`API 內部業務邏輯` must make the implementation path traceable for developers:

- Always identify the involved `BackendAPI` or DB source when the API depends on one. Use old-code logic Excel files such as `舊代碼{TSD名稱}.xlsx` as important evidence when they exist.
- Formal `BackendAPI` / `後端來源` text must use business-source or backend-service names, not old code-behind method names, file names, or legacy implementation snippets such as `*.ashx.cs`; keep those only in evidence reports, alias notes, or migration rationale when needed.
- Common call notation must distinguish external CommonUtil APIs from internal CommonFunc methods: write outward-facing CommonUtil API references as `CommonUtil/{ApiName}` such as `CommonUtil/CheckPreLoginDeviceStatus`; write internal reusable method calls as `CommonFunc.{MethodName}` such as `CommonFunc.CheckPreLoginDeviceStatus`. Do not write external CommonUtil APIs as `CommonUtil.CheckPreLoginDeviceStatus`, and normalize legacy `CommonUtilFunc->...` / `CommonFunc/...` wording when producing analysis notes or workbook backend-source text.
- In the `涉及BackendAPI` row, write one backend source per line. Keep it compact and source-oriented, for example `MMA->[dbo].[USER_STATUS](CPRTCD)`, `IRIS->EC0001`, or a confirmed backend service name plus short Chinese purpose; do not concatenate several sources into one long wrapped sentence.
- If one numbered business step contains multiple implementation actions, use hierarchical substeps in the logic explanation such as `1.1`, `1.2`, and `2.1` so developers can trace the order without reading a paragraph wall.
- Query logic must state the `WHERE` conditions, selected fields, required `ORDER BY` / `GROUP BY`, and any data conversion, merge, filtering, or trimming. Avoid `SELECT *` in design text.
- Update logic must state the update conditions and every field/value being updated.
- Insert logic must state the inserted fields, values, and any BackendAPI or DB table involved.
- Delete logic must state the delete conditions.
- `responseData` logic must explain the source and meaning of returned fields, especially when values are mapped, merged, derived, or filtered from backend data.
- If the source, SQL, BackendAPI, Response Code, or required Header value is not confirmed, mark it as `todo` / `待確認` / `unresolved` instead of inventing a definitive implementation.


## API 方法命名

新系统 API 方法名应先描述业务目标，再描述操作阶段。

核心 API 方法命名规则：

- 方法名应以稳定业务对象或情境开头，例如 `{BusinessObject}{Stage}` 或 `{OwnerScope}{BusinessObject}{Stage}`。
- 当 `Init`、`Confirm`、`Submit`、`Notice` 等阶段/动作关键字代表流程阶段时，应放在方法名末尾。
- 交易式流程命名需对齐系统设计标准：填表、确认、结果页分别使用 `{FunctionName}Init`、`{FunctionName}Confirm`、`{FunctionName}Result`。
- 优先使用 `OwnSinopacCreditCardPaymentConfirm` 而不是 `ConfirmOwnSinopacCreditCardPayment`；优先使用 `OtherSinopacCreditCardPaymentSubmit` 而不是 `SubmitOtherSinopacCreditCardPayment`。
- 只有当 API 是单纯查询且不是命名流程阶段时，才使用 `Get`。若 `Init` 或 `Notice` 已表达查询/阶段语义，不要习惯性加前缀 `Get`。查询 API 中的旧式 `Query` 命名应改为 `Get`。
- Split API names when the PRD business scope differs even if the legacy implementation reused one generic method name. For example, 本人永豐卡費 and 他人永豐卡費 should not both expose the same generic `CreditCardPaymentConfirm` if their validation and fields differ.
- Split pure-read query actions from write/maintenance actions when a legacy or draft API combines `QUERY` with `ADD` / `DELETE` / `UPDATE`. Prefer a `Get{BusinessObject}` query API with no `action` request parameter plus a `Maintain{BusinessObject}` or specific write API for mutations. For example, D.001/D.002 search history is frozen as `GetDemandDepositSearchHistory` and `MaintainDemandDepositSearchHistory`, not one `Manage...` API carrying `QUERY` / `ADD` / `DELETE`.
- 除非用户明确要求向后兼容，不要为了兼容保留旧代码 API 方法名；旧名只保留在别名、后端来源说明或迁移说明中。
- When renaming an API method, update the TSD `API清單`, API Detail `Api_List`, API sheet `API Name`, examples, business logic text, sequence diagrams, and the relevant category field KB naming-decision section together.


## 字段知识库

使用字段知识库，避免同一业务含义在不同模块中出现不同 API 字段名。

核心命名规则：

- PRD 中文业务含义是字段语义的事实来源。
- 先抽取面向 PRD 的精确中文含义，再由该含义选择或创建 API 字段名。
- 既有 API Detail 字段名若不符合 PRD 语义，就不能视为权威来源。
- When editing an API spec and an existing field name is semantically wrong or misleading, directly rename it and update the field table, examples, business logic, and related notes together.
- For new-system API design, do not preserve legacy-code field names for compatibility. Legacy names belong in aliases/migration notes only.
- Only preserve an old field name when the user explicitly asks for backward compatibility; if preserved, document it as an alias and still recommend the canonical field name.
- Provided documents are evidence, not naming constraints. If PRD/TSD/API Detail/IT SPEC contains old-system or awkward names such as `tdAcct`, `tdAccountNo`, `queryAccountNo`, `currEName`, `currCName`, `depositCatgType`, `depositType`, `depositRollType`, `depositReceiveInterestType`, or generic `type`/`flag`/`data`, optimize them to clear new-system canonical names before freezing the API contract.
- Use old upstream field names only in Source Description when they identify the real backend source, for example IRIS/DB column names. Do not expose them as request/response field names, DTO names, or PlantUML message fields.
- Prefer full business words over abbreviations: `Account` over `Acct`, `Currency` over `Curr`, `Interest` over `Int`, `Amount` over `Amt`, `Original` over `Orig`, `Renewal` over `Roll`, `Number`/`Count` over ambiguous `No`/`Times` when the PRD meaning requires it.
- When a response field is a display name, suffix with `Name`; when it is a code, suffix with `Code`. For example use `fixedDepositRenewalTypeCode` for backend code values and `fixedDepositRenewalTypeName` for user-facing text.

Location:

- Primary skill-global KB: `references/field-kb/{Category}.md` under this skill directory.
- Optional project-local override KB: `references/field-kb/{Category}.md` under the current project/workspace.
- Load the skill-global KB first. If a project-local KB for the same category exists, treat it as an override/supplement for the current project; project-local decisions win when they explicitly conflict.
- When adding newly confirmed canonical fields, update the skill-global KB by default. If the user says the decision is only for the current branch/project, update the project-local KB instead.

Category rule:

- Derive the category from the TSD `API清單` `API類別`, not from the PRD/function code, when an API list is available.
- Normalize the TSD `API類別` to the first word with its first letter uppercase.
- Map Common wrapper/helper categories to `Common`:
  - `CommonUtil` -> `Common`
  - `CommonFunc` -> `Common`
- If no TSD `API類別` exists for the API, fall back to the workbook domain/API category when clear; only fall back to the first uppercase letter of the PRD/function code when no API category evidence exists.
- Examples:
  - TSD `API類別=Deposit` -> skill `references/field-kb/D.md`, optionally overlaid by project `references/field-kb/D.md`
  - TSD `API類別=Exchange` -> skill `references/field-kb/E.md`, optionally overlaid by project `references/field-kb/E.md`
  - TSD `API類別=CommonUtil` / `CommonFunc` -> skill `references/field-kb/Common.md`, optionally overlaid by project `references/field-kb/Common.md`
  - No API category evidence and `N.006` only -> skill/project `references/field-kb/N.md`

检查或编辑模块前：

1. Identify all PRD/TSD function codes and all TSD `API清單` rows in scope.
2. For each API, derive the KB category from its TSD `API類別` using the category rule above.
3. Open the matching skill-global field KB file if it exists, then open the project-local KB file for the same category if it exists, for example `references/field-kb/D.md`, `references/field-kb/E.md`, or `references/field-kb/Common.md`.
4. Compare API Detail request/response fields against the KB:
   - If the same meaning has a canonical field name, prefer that name.
   - If the API uses a different name, report it as a consistency issue and recommend rename or alias handling.
   - If two existing names are both valid in different contexts, document the context boundary.
   - If the API field's Chinese explanation is vague or copied from another context, rewrite the Chinese explanation to match the PRD first, then adjust the field name.
   - If the field name is merely a legacy/source-system abbreviation, treat it as an alias candidate and replace the API-facing field with a new-system canonical name.

检查或编辑模块后：

1. Add newly confirmed canonical fields to the skill-global KB unless the user explicitly says the decision is project-only.
2. Add aliases found in the workbook, PRD, TSD, or legacy wording.
3. Record the PRD Chinese meaning, TSD `API類別`, API name, function code/API evidence, and the decision.
4. Keep entries concise; do not paste long PRD/TSD text.
5. Do not add ad hoc explanatory rows, bottom `備註`/`註記` rows, frozen naming notes, or reviewer-facing rationale directly into delivery Excel/Word files unless the user explicitly asks for that exact document content. Put rationale in the chat response, a handoff note, or the field KB instead. When a workbook already has a standard `備註` column, only edit cells that belong to the API specification; do not create new free-form note sections at the bottom of a sheet.

不要强迫真正不同的业务含义共用同一个字段名。例如活存账号与定存存单号码不应共用同一个字段名。


## 功能设计命名

当用户要求優化功能設計命名、設計命名、命名優化，或 API 规格、业务逻辑、时序图、Redis key、功能开关中出现旧系统变量/API 标签时，使用这些规则。

Core rule:

- PRD Chinese business capability is the source of truth. First name the business capability in Chinese, then derive the English design name.
- Do not preserve old-system field, Redis key, controller, page, or switch names in new-system design unless the user explicitly asks for compatibility.
- System-design v2.5 is explicit: `舊大戶命名僅可作為參考，不可直接照搬`; old DAWHO names must not be copied directly into new-system Redis, config, interface, or field names.
- If an old-system name must be mentioned, put it only in an alias/migration note, not as the canonical new design.
- Prefer capability names that are stable across implementation choices. Avoid names tied to page IDs, legacy switches, databases, or transport details.

Naming layers:

| Layer | Rule | Example |
| --- | --- | --- |
| Business capability | `{Domain}{Capability}` in PascalCase, based on PRD meaning | `DemandDepositInquiry` for 活存查詢 |
| Feature toggle key | `FeatureToggle:{Domain}:{Capability}` | `FeatureToggle:Deposit:DemandDepositInquiry` |
| Boolean variable | `is{Capability}Enabled` / `can{Action}` / `has{Thing}` | `isDemandDepositInquiryEnabled` |
| API name | Verb + business object/capability, no legacy abbreviations | `GetLivedDepositTransList` may remain if already frozen; new names should prefer clear business English |
| Internal method | Verb + exact reusable action; CommonFunc methods describe reusable logic, not UI/page names | `GetOperationHour`, `AddIrisTransactionRecord` |
| Action enum | Verb-like operation values in uppercase | `QUERY`, `ADD`, `DELETE` |
| Sequence label | User-facing operation or API capability, not old field name | `查詢 D.001/D.002 活存查詢功能開關` |

功能开关设计：

- Use namespace form `FeatureToggle:{Domain}:{Capability}`.
- Domain should normally come from TSD `API類別`, for example `Deposit`, `Exchange`, `Setting`.
- Capability should describe the PRD function, not the PRD code or old page switch.
- Do not include PRD code in the canonical key unless the same business capability name is genuinely ambiguous across domains.
- Return or internal variable should be boolean and read naturally in logic:
  - Good: `isDemandDepositInquiryEnabled == true`
  - Avoid: `PageMExchangeTr == "10"`
  - Avoid: `D001D002DemandDepositInquiryEnabled` when `Deposit:DemandDepositInquiry` is already unique.

Optimization workflow:

1. Extract the current names from API Detail sheets, `Api_List`, business logic text, response examples, sequence diagrams, and generated reports.
2. Classify each suspicious name:
   - legacy system/page/switch name.
   - vague technical name.
   - wrong business domain.
   - abbreviated field or method name.
   - enum/action value mismatch.
3. Propose a canonical name with reason tied to PRD/TSD/API category.
4. If the user asks to fix, update all occurrences together:
   - workbook field table, examples, business logic, and `Api_List` backend text when relevant.
   - PlantUML/VSDX/SVG guidance and generated report.
   - field KB or naming notes when the decision is reusable.
5. Validate with a text search for the old name and list any intentional remaining mentions as alias/migration notes.


## 常见 DAWHO API 设计检查

对于存款/活存/定存查询类功能，检查：

- Search/filter coverage: category, date, keyword, currency/account, and combined filtering order.
- Keyword search rules: length limit, fields matched, fuzzy contains matching, amount matching ignoring thousand separators.
- Date rules: quick ranges, custom range max length, lookback limit, single-day vs range parameters, end date including the whole day.
- Pagination: default page size and continuation behavior.
- Data source split: host data vs smart-account-book data; whether API exposes enough flags such as `dataSource`.
- Category ambiguity: income/expense may have duplicate category names; require direction/code if needed.
- Currency/amount rules: TWD/foreign decimals, JPY integer, exchange-rate decimals, approximate TWD conversion timing rules.
- Account rules: avoid定存/存單 terminology in活存 APIs; use活存帳號/accountNo where appropriate.
- Search history: top N, sort order, duplicate keyword upsert, function/customer isolation, input length.
- Response consistency: field names must match between field table, examples, and DTO expectations.
- Error/no-data states: distinguish hard failure from empty successful result where PRD expects empty UI.


## 开发修改建议

若 API 名称、request/response 字段或内部字段语义不符合需求，需明确提出面向开发的修改建议。建议必须具体且可实施。

Cover these cases:

- API name mismatch: recommend naming that reflects the PRD capability and target domain.
  - Prefer business-object-first names with workflow stage suffixes, for example `OwnSinopacCreditCardPaymentConfirm` instead of `ConfirmOwnSinopacCreditCardPayment`.
  - Example: avoid活存 API fields named like定存/存單; rename `tdAccountNo` to `accountNo` for活存帳號.
- Field missing: propose new field name, data type, required flag, example, and where the value comes from.
  - Example: add `keyword: string, N, max 15 chars` for PRD keyword search.
- Field too ambiguous: propose split or enum/code fields.
  - Example: category name alone cannot distinguish income/expense duplicate categories; add `incomeExpenseFlag` or category code.
- Field semantics unclear: state whether the backend returns raw value or formatted display value.
  - Example: decimal amount returned by API, frontend formats thousand separators and JPY decimals.
- Required flag mismatch: explain when a field is optional vs required.
  - Example: `inputDate` vs `inputStartDate/inputEndDate` should be mutually exclusive modes, not all required.
- Example mismatch: update JSON examples to match the field table exactly.
- Source/rule mismatch: point to the correct upstream source or business rule.
- Reusable common logic: if an inline SQL/query/transformation block is a small reusable module, recommend moving it to or calling an existing CommonFunc method. Do not use CommonUtil as the internal reusable implementation source; CommonFunc is the program-internal reusable common method layer, while CommonUtil is the outward-facing common API/wrapper layer. CommonUtil implementation should normally validate login/session state first, then directly call the corresponding CommonFunc method. When making this change, update the feature API sheet's `涉及BackendAPI`, business logic text, the target CommonFunc Method Detail, and any `Api_List` backend-source text together so the call chain remains complete. If a CommonUtil outward API is also involved, keep it as the public wrapper that calls CommonFunc and documents the login-state validation responsibility.

每条建议需包含：

- Current issue.
- Suggested change.
- Reason tied to PRD/TSD requirement.
- Impact on request/response or backend logic.
