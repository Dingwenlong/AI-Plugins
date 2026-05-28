# DAWHO 命名与字段知识库规则

当需要统一 API 名称、方法后缀、字段名称、响应范例、业务逻辑文字，以及面向开发的设计建议时，使用这些规则。

> 本文件从原本较重的 `SKILL.md` 中拆出，让技能入口保持轻量。仅在对应工作流程启用时加载本文件。

## API 范例情境与响应码

`範例` 属于 API 设计的一部分，不是单纯的文档格式。

- 不要强迫每个 API 都使用相同四个情境标签。不同 API 可能需要不同的成功、无资料、下游错误、验证错误、权限、账号状态或业务规则情境。
- 情境标签应从当前 API 的 PRD/TSD 行为、API Detail 业务逻辑、后端来源说明与预期 UI 状态推导。
- 当 API 没有 request payload 或没有请求参数时，除非契约明确要求空 JSON 对象，否则 `Request` 范例格保持空白；不要为了填满表格而写 `{}`。
- 从已登记的 `tsdApiSpec` 目录搜索 `Api_Response_Codes*.xlsx` 来解析 Response Code 工作簿，优先使用最新版 `Api_Response_Codes_v1.0` 设计文件；若同日存在主版本与交付副本，以主版本/事实来源文件为准，交付副本只作一致性对照。
- 每个非成功范例 response 都必须确认其 `responseCode` 存在于 Response Code 工作簿，且讯息符合目标业务条件；当项目要求完全对照时，范例 JSON 的 `responseCode` / `responseMessage` 必须与 `Api_Response_Codes_v1.0` 设计文件完全一致。
- 匹配 `ResponseMessage` / 弹窗文案时，应以业务语义判断，不只看文字完全一致。跨模块共用错误（共用错误）如身份/会员资格、登录/认证、装置绑定、安全阻挡、余额/额度、系统忙碌等，应优先检查 `O_Common`。
- 若 `O_Common` 已有同语义 code，应复用。功能特有的弹窗条件、来源文件、按钮文案与页面/context 映射放入 `Remarks`；除非用户明确要求，不要覆盖共用 `ResponseMessage`。
- 若该 message 适合放入 `O_Common` 但尚无同语义 code，需询问用户是否新增共用 `O_Common` code，并提供拟定 code/message/来源证据；未经确认不得自行发明或新增共用 code。
- 只有功能专属业务错误才应在该功能专属 sheet 搜索，例如 L/payment 功能在 `L_Payment`。若专属 sheet 没有适合 code，新增前需请用户确认新的专属 code/message/来源。
- 若 API 需要某个情境，但 Response Code 工作簿没有适合且已确认的 code，或现有 code/message 与范例业务语义不一致，只读时应报告具体 `Must fix` / `Should strengthen` 项，并附拟定 code/message/sheet；编辑时只有在用户确认目标 sheet 与 code/message，或用户已明确提供这些细节后，才可新增或修改。
- 写入、更新或追加 Response Code workbook 行时，受影响的数据列必须设置 `WrapText=True`、水平靠左、垂直居中，并执行 Excel 行高 `AutoFit`。标题列保持视觉居中。长 `Remarks`、popup 对照与来源说明不得横向溢出到右侧空白列。
- 既有业务专属范例列有效时应保留；只有作为 API 设计决策时，才可重命名、新增、删除或合并范例情境，不得把它当成一般格式清理。
- 仅负责格式的技能可以调整 `範例` 表格边框、合并格、字体、换行与空白列，但不得用固定模板替换业务情境。

编辑 API Detail 工作簿时，若情境/code 关系变化，必须同步更新范例标签、request JSON、response JSON 与 Response Code 工作簿；在所有范例和 Response Code 完全一致前，不得标记为 100% 冻版。


## API Detail 契约规则

检查或编辑 API Detail 与 TSD `API清單` 内容时，套用 `P240301_永豐商銀新大戶_系統設計規範 v2.5 20260514` 中的下列规则：

- 查询类 API 中，旧系统或草稿方法若使用 `Query`，应改为 `Get`；目的是避免在 URL 风格命名中暴露查询参数语感。
- API 名称、DB 表名与 DB 字段使用 PascalCase；API request/response 字段与 payload 内变量使用 camelCase。
- 交易流程类 API 使用 `{FunctionName}Init`、`{FunctionName}Confirm`、`{FunctionName}Result` 分别表示填表、确认与结果阶段。除非该 API 是单纯查询，或用户已经冻结另一个可接受名称，否则应遵守此流程阶段命名规则。
- 时间值默认使用 UTC+8 显示格式 `yyyy/MM/dd HH:mm:ss`，除非更具体的来源契约明确覆盖。
- Excel API Detail 中必须同时呈现 Request 与 Response。范例必须存在、与字段表一致，并足够完整，让开发者能理解成功、失败、验证错误与无资料行为。
- Header 参数不要求每个 API 都独立呈现成可见章节；但当 API 依赖 Header 值时，API 逻辑必须说明哪些值来自 Header。
- 必填旗标必须明确：`Y` 表示 response 字段一定返回；`N` 表示资料不存在时字段可省略。不得让 request/response 必填性停留在隐含状态。
- 字段资料型别必须反映真实 payload 型别；当 PRD/TSD/API 行为已证明有更具体型别时，不得使用泛用 string/json 型别。
- `responseData` 无资料行为默认是 `{}`，不是 `NULL`；除非来源系统契约明确要求不同结构。
- 面向 API 的契约不得使用 `password`；若概念无法避免，使用 `passwd`。当存在更清楚的业务名称时，也应避免把 `ID`、`Key`、`PWD`、`Password`、`Dept`、`No.` 等安全敏感或语义不清的词作为标准 API 字段名。
- 遮蔽/反遮蔽默认属于前端显示责任。API request/response payload 应承载契约需要的清楚值，而不是遮蔽后的显示字串；除非 PRD/TSD 明确定义 payload 必须为遮蔽值。


## API 内部业务逻辑规则

`API 內部業務邏輯` 必须让开发者可以追溯实现路径：

- 当 API 依赖 `BackendAPI` 或 DB 来源时，必须明确指出涉及的来源。若存在 `舊代碼{TSD名稱}.xlsx` 这类旧代码逻辑 Excel，应作为重要证据使用。
- 正式 `BackendAPI` / `後端來源` 文字必须使用业务来源或后端服务名称，不使用旧 code-behind 方法名、文件名，或 `*.ashx.cs` 这类旧实现片段；这些旧名只在必要时保留于证据报告、别名说明或迁移理由中。
- Common 调用写法必须区分外部 CommonUtil API 与内部 CommonFunc 方法：面向外部调用的 CommonUtil API 写为 `CommonUtil/{ApiName}`，例如 `CommonUtil/CheckPreLoginDeviceStatus`；内部可复用方法写为 `CommonFunc.{MethodName}`，例如 `CommonFunc.CheckPreLoginDeviceStatus`。不得把外部 CommonUtil API 写成 `CommonUtil.CheckPreLoginDeviceStatus`；产出分析说明或 workbook 后端来源文字时，也要规范旧写法如 `CommonUtilFunc->...` / `CommonFunc/...`。
- `涉及BackendAPI` 行中，每行只写一个后端来源。文字应紧凑并以来源为主，例如 `MMA->[dbo].[USER_STATUS](CPRTCD)`、`IRIS->EC0001`，或已确认后端服务名加简短中文用途；不要把多个来源串成一段很长的换行句。
- 若一个编号业务步骤包含多个实现动作，应在逻辑说明中使用 `1.1`、`1.2`、`2.1` 等层级子步骤，让开发者无需阅读大段文字也能追溯顺序。
- 查询逻辑必须说明 `WHERE` 条件、选取字段、必要的 `ORDER BY` / `GROUP BY`，以及任何资料转换、合并、过滤或裁切规则。设计文字中避免使用 `SELECT *`。
- 更新逻辑必须说明更新条件，以及每个被更新字段/值。
- 新增逻辑必须说明新增字段、写入值，以及涉及的 BackendAPI 或 DB 表。
- 删除逻辑必须说明删除条件。
- `responseData` 逻辑必须说明返回字段的来源与含义，尤其是字段值从后端资料映射、合并、衍生或过滤而来时。
- 若来源、SQL、BackendAPI、Response Code 或必要 Header 值尚未确认，应标记为 `todo` / `待確認` / `unresolved`，不得自行编造确定实现。

### NEWDAWHO 后续改动强规则

- 遇到历史获取账户信息、账户列表、转出账户类方法时，统一收敛到 `GetEC0001`；外部共用 API 写作 `CommonUtil/GetEC0001`，内部共用方法写作 `CommonFunc.GetEC0001`。
- 需按上述规则替换或移除的历史方法名包括：`ShowAcctList`、`GetAcctKind`、`GetAccountInfo`、`GetTransDebitAccount`、`GetBankAccountList`、`GetBankAccountListFunc`、`GetEC001AccountInfoFunc`、`GetAccountListByAPNOKindFunc`。这些名称只能保留在历史证据、别名/迁移说明或问题清单中，不得作为新的 `BackendAPI` / `後端來源` / `涉及BackendAPI` 正式来源。
- 遇到 `TX_STATISTIC`，从后续接口设计中直接删除，不再作为 DB 来源、BackendAPI、业务逻辑步骤、范例说明、字段来源或时序图交接内容保留；若引用来自历史证据，只在分析稿中说明“历史引用已废弃”。


## API 方法命名

新系统 API 方法名应先描述业务目标，再描述操作阶段。

核心 API 方法命名规则：

- 方法名应以稳定业务对象或情境开头，例如 `{BusinessObject}{Stage}` 或 `{OwnerScope}{BusinessObject}{Stage}`。
- 当 `Init`、`Confirm`、`Submit`、`Notice` 等阶段/动作关键字代表流程阶段时，应放在方法名末尾。
- 交易式流程命名需对齐系统设计标准：填表、确认、结果页分别使用 `{FunctionName}Init`、`{FunctionName}Confirm`、`{FunctionName}Result`。
- 优先使用 `OwnSinopacCreditCardPaymentConfirm` 而不是 `ConfirmOwnSinopacCreditCardPayment`；优先使用 `OtherSinopacCreditCardPaymentSubmit` 而不是 `SubmitOtherSinopacCreditCardPayment`。
- 只有当 API 是单纯查询且不是命名流程阶段时，才使用 `Get`。若 `Init` 或 `Notice` 已表达查询/阶段语义，不要习惯性加前缀 `Get`。查询 API 中的旧式 `Query` 命名应改为 `Get`。
- 当 PRD 业务范围不同，即使旧实现复用了同一个泛用方法名，也应拆分 API 名称。例如，本人永豐卡費与他人永豐卡費若验证规则和字段不同，就不应同时暴露同一个泛用 `CreditCardPaymentConfirm`。
- 当旧 API 或草稿 API 把纯查询动作与写入/维护动作混在一起，例如同时包含 `QUERY` 与 `ADD` / `DELETE` / `UPDATE`，应拆分纯读查询与写入/维护 API。查询优先使用不带 `action` request 参数的 `Get{BusinessObject}`，写入/维护则使用 `Maintain{BusinessObject}` 或更具体的写入 API。例如，D.001/D.002 搜寻历史已冻结为 `GetDemandDepositSearchHistory` 与 `MaintainDemandDepositSearchHistory`，不是一个携带 `QUERY` / `ADD` / `DELETE` 的 `Manage...` API。
- 除非用户明确要求向后兼容，不要为了兼容保留旧代码 API 方法名；旧名只保留在别名、后端来源说明或迁移说明中。
- 重命名 API 方法时，必须同步更新 TSD `API清單`、API Detail `Api_List`、API sheet `API Name`、范例、业务逻辑文字、时序图，以及对应类别字段知识库的命名决策段落。


## 字段知识库

使用字段知识库，避免同一业务含义在不同模块中出现不同 API 字段名。

核心命名规则：

- PRD 中文业务含义是字段语义的事实来源。
- 先抽取面向 PRD 的精确中文含义，再由该含义选择或创建 API 字段名。
- 既有 API Detail 字段名若不符合 PRD 语义，就不能视为权威来源。
- 编辑 API 规格时，若既有字段名语义错误或容易误导，应直接重命名，并同步更新字段表、范例、业务逻辑与相关备注。
- 新系统 API 设计中，不要为了兼容而保留旧代码字段名。旧名只应放在别名或迁移说明中。
- 只有用户明确要求向后兼容时，才保留旧字段名；若保留，需记录为别名，并仍然建议标准字段名。
- 用户提供的文件是证据，不是命名限制。若 PRD/TSD/API Detail/IT SPEC 中出现旧系统或不顺的名称，例如 `tdAcct`、`tdAccountNo`、`queryAccountNo`、`currEName`、`currCName`、`depositCatgType`、`depositType`、`depositRollType`、`depositReceiveInterestType`，或泛用的 `type`/`flag`/`data`，在 API contract 冻版前应优化成清楚的新系统标准名称。
- 旧上游字段名只在来源说明（Source Description）中用于标识真实后端来源，例如 IRIS/DB 栏位名。不得把这些旧名暴露为 request/response 字段名、DTO 名称或 PlantUML message 字段。
- PRD 语义需要时，优先使用完整业务词，不使用缩写：用 `Account` 而不是 `Acct`，用 `Currency` 而不是 `Curr`，用 `Interest` 而不是 `Int`，用 `Amount` 而不是 `Amt`，用 `Original` 而不是 `Orig`，用 `Renewal` 而不是 `Roll`，用 `Number`/`Count` 而不是语义不清的 `No`/`Times`。
- response 字段若表示显示名称，后缀使用 `Name`；若表示代码，后缀使用 `Code`。例如后端 code 值使用 `fixedDepositRenewalTypeCode`，面向使用者的文字使用 `fixedDepositRenewalTypeName`。

位置：

- 主要技能全局知识库：当前技能目录下的 `references/field-kb/{Category}.md`。
- 可选项目本地覆盖知识库：当前项目/workspace 下的 `references/field-kb/{Category}.md`。
- 先加载技能全局知识库。若同类别存在项目本地知识库，将其视为当前项目的覆盖/补充；当两者明确冲突时，以项目本地决策为准。
- 新确认的标准字段默认更新到技能全局知识库。若用户说明该决策只适用于当前分支/项目，则改为更新项目本地知识库。

类别规则：

- 若存在 API list，应从 TSD `API清單` 的 `API類別` 推导类别，不从 PRD/function code 推导。
- 将 TSD `API類別` 规范化为首词首字母大写。
- 将 Common wrapper/helper 类别映射为 `Common`：
  - `CommonUtil` -> `Common`
  - `CommonFunc` -> `Common`
- 若该 API 没有 TSD `API類別`，但 workbook domain/API category 清楚，则回退使用该分类；只有在完全没有 API category 证据时，才回退到 PRD/function code 的第一个大写字母。
- 示例：
  - TSD `API類別=Deposit` -> 技能 `references/field-kb/D.md`，可叠加项目 `references/field-kb/D.md`
  - TSD `API類別=Exchange` -> 技能 `references/field-kb/E.md`，可叠加项目 `references/field-kb/E.md`
  - TSD `API類別=CommonUtil` / `CommonFunc` -> 技能 `references/field-kb/Common.md`，可叠加项目 `references/field-kb/Common.md`
  - 没有 API category 证据且仅有 `N.006` -> 技能/项目 `references/field-kb/N.md`

检查或编辑模块前：

1. 识别范围内所有 PRD/TSD 功能编号，以及所有 TSD `API清單` 行。
2. 对每个 API，按上述类别规则从 TSD `API類別` 推导知识库类别。
3. 若存在对应的技能全局字段知识库，先打开该文件；若同类别存在项目本地知识库，也一并打开，例如 `references/field-kb/D.md`、`references/field-kb/E.md` 或 `references/field-kb/Common.md`。
4. 将 API Detail request/response 字段与知识库比对：
   - 若相同语义已有标准字段名，优先使用该名称。
   - 若 API 使用了不同名称，将其报告为一致性问题，并建议重命名或按别名处理。
   - 若两个既有名称在不同情境下都有效，应记录情境边界。
   - 若 API 字段中文说明含糊，或明显从其他情境复制，应先改写中文说明使其符合 PRD，再调整字段名。
   - 若字段名只是旧系统/来源系统缩写，应视为别名候选，并将面向 API 的字段替换为新系统标准名称。

检查或编辑模块后：

1. 除非用户明确说明该决策仅限项目，否则将新确认的标准字段加入技能全局知识库。
2. 加入 workbook、PRD、TSD 或旧系统文字中出现的别名。
3. 记录 PRD 中文语义、TSD `API類別`、API 名称、function code/API 证据与最终决策。
4. 条目保持简洁，不粘贴大段 PRD/TSD 原文。
5. 除非用户明确要求写入具体交付文件，否则不要把临时说明行、底部 `備註`/`註記` 行、冻版命名说明或面向 reviewer 的理由直接加进交付 Excel/Word。理由应放在聊天回复、handoff note 或字段知识库中。若 workbook 已有标准 `備註` 栏，只编辑属于 API 规格的单元格；不要在 sheet 底部创建新的自由说明区。

不要强迫真正不同的业务含义共用同一个字段名。例如活存账号与定存存单号码不应共用同一个字段名。


## 功能设计命名

当用户要求優化功能設計命名、設計命名、命名優化，或 API 规格、业务逻辑、时序图、Redis key、功能开关中出现旧系统变量/API 标签时，使用这些规则。

核心规则：

- PRD 中文业务能力是事实来源。先命名中文业务能力，再推导英文设计名称。
- 除非用户明确要求兼容，否则新系统设计中不要保留旧系统字段、Redis key、controller、页面或开关名称。
- 系统设计 v2.5 明确规定：`舊大戶命名僅可作為參考，不可直接照搬`；旧 DAWHO 名称不得直接复制到新系统 Redis、config、interface 或字段名称中。
- 若必须提及旧系统名称，只能放在别名/迁移说明中，不作为新设计标准名称。
- 优先使用不受实现方案影响的稳定能力名称。避免名称绑定 page ID、旧开关、数据库或传输细节。

命名层级：

| 层级 | 规则 | 示例 |
| --- | --- | --- |
| 业务能力 | 基于 PRD 语义，使用 PascalCase 的 `{Domain}{Capability}` | 活存查詢使用 `DemandDepositInquiry` |
| 功能开关 key | `FeatureToggle:{Domain}:{Capability}` | `FeatureToggle:Deposit:DemandDepositInquiry` |
| 布尔变量 | `is{Capability}Enabled` / `can{Action}` / `has{Thing}` | `isDemandDepositInquiryEnabled` |
| API 名称 | 动词 + 业务对象/能力，不使用旧系统缩写 | 已冻结时可保留 `GetLivedDepositTransList`；新名称应优先使用清楚的业务英文 |
| 内部方法 | 动词 + 精确可复用动作；CommonFunc 方法描述可复用逻辑，不描述 UI/page 名称 | `GetOperationHour`、`AddIrisTransactionRecord` |
| 动作枚举 | 类动词操作值，使用大写 | `QUERY`、`ADD`、`DELETE` |
| 时序图标签 | 使用者可理解的操作或 API 能力，不使用旧字段名 | `查詢 D.001/D.002 活存查詢功能開關` |

功能开关设计：

- 使用 namespace 形式 `FeatureToggle:{Domain}:{Capability}`。
- Domain 通常应来自 TSD `API類別`，例如 `Deposit`、`Exchange`、`Setting`。
- Capability 应描述 PRD 功能，不描述 PRD code 或旧页面开关。
- 除非相同业务能力名称在不同业务域中确实会产生歧义，否则标准 key 不应包含 PRD code。
- 返回值或内部变量应为 boolean，并且在逻辑中读起来自然：
  - 推荐：`isDemandDepositInquiryEnabled == true`
  - 避免：`PageMExchangeTr == "10"`
  - 避免：当 `Deposit:DemandDepositInquiry` 已经唯一时，使用 `D001D002DemandDepositInquiryEnabled`

优化流程：

1. 从 API Detail sheets、`Api_List`、业务逻辑文字、response examples、时序图与生成报告中抽取当前名称。
2. 对每个可疑名称分类：
   - 旧系统/页面/开关名称。
   - 含糊的技术名称。
   - 错误的业务 domain。
   - 缩写字段名或方法名。
   - 枚举/action 值不匹配。
3. 提出标准名称，并将理由关联到 PRD/TSD/API 类别。
4. 若用户要求修正，应同步更新所有出现位置：
   - 相关 workbook 字段表、范例、业务逻辑与 `Api_List` 后端文字。
   - PlantUML/VSDX/SVG 指引与生成报告。
   - 当决策可复用时，更新字段知识库或命名说明。
5. 使用旧名称全文搜索验证，并列出任何刻意保留的别名/迁移说明。


## 常见 DAWHO API 设计检查

对于存款/活存/定存查询类功能，检查：

- 搜索/筛选覆盖：类别、日期、关键字、币别/账号，以及组合筛选顺序。
- 关键字搜索规则：长度限制、比对字段、包含式模糊比对、金额比对时忽略千分位。
- 日期规则：快捷区间、自定义区间最大长度、可回查范围、单日与区间参数差异、结束日是否涵盖整天。
- 分页：默认每页笔数与续查行为。
- 资料来源拆分：主机资料与智能帐本资料；API 是否暴露足够旗标，例如 `dataSource`。
- 类别歧义：收入/支出可能有重复类别名称；必要时需提供方向或代码。
- 币别/金额规则：TWD/外币小数位、JPY 整数、汇率小数位、约当台币换算时点规则。
- 账号规则：活存 API 避免使用定存/存單术语；适用时使用活存帳號/accountNo。
- 搜索历史：前 N 笔、排序、重复关键字更新或新增（upsert）、功能/客户隔离、输入长度。
- Response 一致性：字段表、范例与 DTO 预期中的字段名必须一致。
- 错误/无资料状态：当 PRD 预期为空画面时，应区分硬失败与成功但为空结果。


## 开发修改建议

若 API 名称、request/response 字段或内部字段语义不符合需求，需明确提出面向开发的修改建议。建议必须具体且可实施。

覆盖下列情况：

- API 名称不匹配：建议能反映 PRD 能力与目标业务域的名称。
  - 优先使用业务对象在前、流程阶段后缀在后的名称，例如使用 `OwnSinopacCreditCardPaymentConfirm`，而不是 `ConfirmOwnSinopacCreditCardPayment`。
  - 示例：活存 API 字段避免命名得像定存/存單；活存帳號应将 `tdAccountNo` 改为 `accountNo`。
- 字段缺失：提出新字段名、资料型别、必填旗标、范例与值来源。
  - 示例：PRD 关键字搜索可新增 `keyword: string, N, max 15 chars`。
- 字段过于含糊：建议拆分字段或新增 enum/code 字段。
  - 示例：单靠类别名称无法区分收入/支出的重复类别；应新增 `incomeExpenseFlag` 或类别代码。
- 字段语义不清：说明后端返回的是原始值，还是格式化显示值。
  - 示例：API 返回 decimal amount，由前端格式化千分位与 JPY 小数位。
- 必填旗标不匹配：说明字段何时可选、何时必填。
  - 示例：`inputDate` 与 `inputStartDate/inputEndDate` 应是互斥模式，不应全部必填。
- 范例不匹配：更新 JSON 范例，使其与字段表完全一致。
- 来源/规则不匹配：指出正确的上游来源或业务规则。
- 可复用共用逻辑：若内嵌 SQL/query/transformation 区块是小型可复用模块，建议移至或调用既有 CommonFunc 方法。不得把 CommonUtil 当成内部可复用实现来源；CommonFunc 是程序内部可复用共用方法层，CommonUtil 是面向外部的共用 API/wrapper 层。CommonUtil 实作通常应先验证登录/session 状态，再直接调用对应 CommonFunc 方法。做此调整时，应同步更新功能 API sheet 的 `涉及BackendAPI`、业务逻辑文字、目标 CommonFunc Method Detail，以及任何 `Api_List` 后端来源文字，确保调用链完整。若同时涉及 CommonUtil 对外 API，应保留其作为 public wrapper，负责调用 CommonFunc 并记录登录状态验证责任。

每条建议需包含：

- 当前问题。
- 建议修改。
- 与 PRD/TSD 需求相关的理由。
- 对 request/response 或后端逻辑的影响。
