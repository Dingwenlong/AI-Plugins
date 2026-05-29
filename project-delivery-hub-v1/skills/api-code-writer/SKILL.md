---
name: 专案交付中枢：【开发落地】API 业务代码写入器
description: 把已完成的 API Spec 落成 .NET 业务代码。第 04 步：在已绑定唯一 `.sln` 的工作区读取共享 `.agent/context/{functionCode}/`、`*_API_Spec.json` 与 `codeHandoff`，实现 Controller / Service / Entity 等业务代码并交接测试计划；不生成 UnitTest / IntegrationTest 测试源码。关键词：Controller、Service、Entity、change-plan、codeStatus。
---

# 【开发落地】API 业务代码写入器

使用这个第 04 步技能在目标项目的 `.agent/context` 下恢复或推进业务代码写入链路。脚本会先读取共享的 `execution-state.json`、`api-checklist.json` 与 API 级 `manifest.json`，只更新 `code*` 字段并保留 `spec*` 状态。读取 `*_API_Spec.json` 时，优先消费结构化 `codeHandoff`；若旧 spec 尚未升级，则会从 `businessLogic` 临时合成兼容 handoff。若 API 目录下存在 `review-notes.json`，也必须一并读取，并将评审意见转换成 `change-plan.json.analysis` 可执行约束；若缺少 `review-notes.json` 但 `.agent/Common/project-hard-constraints.json` 存在，`prepare` 必须即时按当前 API 条件合成 fallback review 约束。推荐链路是先 01，再 02，再 03（如需），再 04，最后 05（如需）。

默认优先解析插件本地 `references/local-workspaces.json`，可按 `workspaceKey` 指向对应集中 `.agent`。`project-root` 仍是实际代码分支目录，例如 `D:\Repo\Project\feature_common\P240301Git`；`agent-root` 是共享链路资料库。参数优先级为 `--agent-root/--workspace-root` > 环境变量 > 插件本地配置 > 旧逻辑 `<project-root>\.agent`。

专案规则读取与代码仓库分离：`--rules-root` > `PROJECT_RULES_ROOT` / 专案环境变量 > `references/local-workspaces.json.rulesRoot` > `<agentRoot>/project-rules/<workspaceKey>`。第 04 步的开发规范、SQL fixture 默认值、UT 模板映射、字段知识库、框架说明等都只能从 `<rulesRoot>/catalog.json` 的规则与 asset 读取。开发规范不得再从第 01 步 `.agent/reference/global` 搜集；若缺少开发规范，先用 `专案规则分析器 --category code-guidelines --approve` 写入 project-rules。找不到规则库时只允许执行通用 code writer 流程，并把专案规则缺口写入 `change-plan.json.analysis.devGuidelineGaps` / `unresolvedLogic`；不得从插件内旧个案 reference 偷读默认规则。

## 规则包启动检查

正式第 04 步 `prepare` 前，必须先解析 `apiCodeWriter` 规则包：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack apiCodeWriter `
  --workspace-key "<workspaceKey>"
```

若用户明确给出规则库，改传 `--rules-root "<rulesRoot>"`。脚本输出的开发规范规则是生成 `change-plan.json` 前的硬输入；`status=blocked` 时，`prepare` 必须写入 `change-plan.json.analysis.devGuidelineGaps` / `unresolvedLogic` 并停止进入正式落码，不得凭第 01 步 reference、插件内旧 reference 或记忆补齐专案规范。

`scripts/write_api_code.py` 与 `scripts/materialize_review_notes.py` 依赖 Python `jsonschema` 进行 schema 校验。运行时若缺少该依赖，脚本会先以 dependency preflight 失败并提示安装方式；不得绕过 schema 校验继续写状态。

第 04 步的职责边界固定为：只实现或修改业务运行代码，并把测试情景、`unitTestTargetFiles`、`integrationTestTargetFiles`、SQL fixture 需求与 Service runtime validation 计划写入 `change-plan.json.analysis.testCodeHandoff` / handoff artifact。**不得新增、改写或补齐 UnitTest / IntegrationTest / Service runtime validation 测试源码**；这些测试代码统一由第 05 步 `skills/docx-unittest-report/SKILL.md` 生成、维护、执行并纳入 UT 测报。

这个技能不绑定固定前置步骤名称。只要共享 `.agent/context` 中已经存在可消费的 `spec*` 状态、`manifest.json` 与 `*_API_Spec.json`，就可以直接进入 code writer；不要求调用者必须先显式经过某个特定命名的上游 workflow / skill。

进入 code writer 前不强制先执行 `skills/api-sql-fixture-preparer/SKILL.md`。默认先跑 `prepare` 产出 `change-plan.json`、`implementation-template.md` 与 `implementation-template.json`；用户审阅或修改 Markdown 后，必须再跑 `--execution-mode confirm` 锁定当前范本，AI 才能开始真实改码。若目标 API 后续验证依赖 SQL fixture，再于 `apply` 前补执行 fixture。若 `apply` 时 `fixtureStatus` 仍非 `done|skipped`，则应回报 `waiting_fixture`，提示先补 fixture。

`prepare` 内建承担 precheck 的职责：会直接解析目标仓库框架槽位、模块落点、依赖、风险与验证命令，并生成 `change-plan.json`。因此这一步不依赖 `workflow-develop-precheck` 或其它外部 precheck skill。

开发规范采用渐进式披露：不得把整本专案开发规范加载进上下文。`prepare` 必须先读取由 `专案规则分析器` 维护的专案规则库 catalog 中的 `codeGuidelineCatalog` 或同类开发规范规则，根据 `API_Spec.json.source`、`codeHandoff`、`backendApis`、`runtimeDependencies`、TSD/API 名称、`apiCategory`、route/controller/module、identity/role/cache/DB 线索判断 `audienceProfile.scope = frontstage | midBackoffice | shared | unknown`，再只把命中的 `rules/*.md|json` 写入 `devGuidelineLoadHints`。禁止仅凭项目名判定前台或中后台；目标态规范也不能替代当前仓库接线事实。若命中前台/中后台专属规范但 handoff 或仓库证据不足，`prepare` 必须写入 `devGuidelineGaps` 并阻塞，不能由 AI 猜实现。

若项目已采用方案 A，并在 `.agent/Common/project-hard-constraints.json` 维护项目级硬约束，可先运行 `scripts/materialize_review_notes.py`，把项目级规则按 API 粒度展开成 `.agent/context/{functionCode}/apis/{apiId}/review-notes.json`。该脚本会先校验 `project-hard-constraints.schema.json`，再按 functionCode / apiCategory / apiName / 业务关键字条件筛选适用规则。

`api-code-writer` 现在是 **AI 编排运行时**，不是 deterministic code generator：

1. `prepare` 只负责共享状态整理、依赖解析、计划产出与状态回写
2. `prepare` 必须同时生成三层落码范本：项目结构、代码文件、文件内方法；确认前 AI 不得修改目标仓库业务代码
3. 用户确认或修改范本后运行 `--execution-mode confirm`，由脚本记录 Markdown hash；若确认后 Markdown 再被修改，`apply` 必须阻塞并要求重新确认
4. AI 必须根据已确认的 `implementation-template.md`、`change-plan.json`、`*_API_Spec.json`、框架说明与示例项目，直接修改目标仓库业务代码
5. `apply` 只接受 AI 已落盘的真实改动，负责检测修改文件、执行验证、产出报告并回写状态
6. 脚本不得再把 `queryContracts / mappingRules / legacyEvidence` 渲染成注释式 stub 代码
7. 脚本与 AI 都不得在第 04 步产出测试源码；测试源码生成、测试执行证据整理和 Word UT 测报由第 05 步负责

当专案规则库或 API Spec 指向 `EnterpriseAPI` 工作区 profile 时，落码规则固定为：

1. 先识别框架槽位，再决定复用或新建
2. 规则优先级固定为：专案规则库 catalog 指定的框架说明 > 示例项目 > 仓库局部相似文件
3. 不允许跨框架模糊落点，不得把 `EnterpriseAPI` 规格写到 `CustomerLogin`、`Common` 或其它 API 项目
4. 缺少 `Controller / Business.Interface / Business / Entity` 槽位时，必须直接阻塞并写入诊断；不再回退全仓库猜文件
5. 若模块不存在，则自动新建完整 `Controller -> Interface -> Service -> Entity` 业务骨架；测试骨架只写入第 05 步 handoff，不在第 04 步落盘

## 默认使用方式

1. 先调用 `scripts/write_api_code.py --execution-mode prepare`
2. 默认读取集中 `.agent/context/execution-batch.json`；未配置集中 `.agent` 时回退 `<project-root>/.agent/context/execution-batch.json`
3. 默认落到 `.agent/context/<functionCode>/`
4. 读取 `implementation-template.md` 并让用户确认；用户若改 Markdown，只需改这个文件，不要手改同目录 JSON
5. 用户确认或改完范本后，调用 `scripts/write_api_code.py --execution-mode confirm`
6. `confirm` 通过后，AI 才能按已确认范本直接在目标仓库修改真实业务代码；脚本只负责 prepare/confirm/apply 编排，不代写 Controller / Service，也不写测试源码
7. 若目标 API 依赖 SQL fixture，且尚未执行或结果未达 `done|skipped`，则在 `apply` 前补执行 `skills/api-sql-fixture-preparer/SKILL.md`
8. 代码改完后，再调用 `scripts/write_api_code.py --execution-mode apply`
9. 若未指定 `--api-id`，一次只推进一支 `specStatus=done` 且 `codeStatus` eligible 的 API；`prepare` 不以 `fixtureStatus` 作为入口门槛
10. 每次运行结束后，必须读取共享 `execution-state.json` 与 `api-checklist.json` 向用户汇报结果
11. 在生成 `change-plan.json` 前必须先完成 `logic resolution`，显式解析 `queryContracts / mappingRules / dependencyHints / legacyEvidence / constraints`
12. 在生成 `change-plan.json` 时必须先完成专案开发规范选择：先判 `audienceProfile`，再查专案规则库 catalog 指定的开发规范 catalog，只选择必要的 `devGuidelineRulesSelected` 与 `devGuidelineLoadHints`；不得整本加载规范
13. 若同目录存在 `review-notes.json`，`prepare` 必须先合并评审约束，再生成 `change-plan.json.analysis.reviewConstraintsSelected / fileRequirements / responseLifecycleRules / failureDisposition / languagePolicy`
14. 对 `EnterpriseAPI`，默认映射到固定业务槽位：
   - `API/EnterpriseAPI/EnterpriseAPI/Controllers/<Module>Controller.cs`
   - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness.Interface/I<Module>Service.cs`
   - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/<Module>/<Module>Service.cs`
   - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/<Module>/<Module>Service.<ApiName>.cs`
   - `BusinessLogicLayout/EnterpriseApi/EnterpriseApiEntity/<Module>/...Info.cs`
   - 测试目标文件仅写入 `testCodeHandoff` / `change-plan.json.analysis.unitTestTargetFiles` / `change-plan.json.analysis.integrationTestTargetFiles`，例如 `Test/UnitTesting/...` 与 `Test/IntegrationTesting/...`；不得由第 04 步创建或修改
15. 若专案采用多项目分层架构，必须先按功能类别、专案规则库和仓库既有项目分层判断落点，再生成 Controller / Service / Entity / Common 类库计划。不得只按 API 名称或单一 `EnterpriseAPI` profile，把所有功能都写进同一个项目。
16. NEWDAWHO 当前 `P240301Git` 布局下，若 `apiCategory=CommonFunc` 且存在 `Libray/Sinopac.CommonFunc/Sinopac.CommonFunc.csproj`，必须强制使用 CommonFunc 类库落点：
   - `Libray/Sinopac.CommonFunc/IFuncService/ICommonFuncService.cs`
   - `Libray/Sinopac.CommonFunc/FuncService/CommonFuncService.cs`
   - `Libray/Sinopac.CommonFunc/FuncService/CommonFuncService.<ApiName>.cs`
   - `Libray/Sinopac.CommonFunc/Dto/<ApiName>Info.cs`
   - `Libray/Sinopac.CommonFunc/ResponseCodes/O_Common.resx`
   - `controllerFile` 必须为空，`codeTargetFiles` 不得包含 `CommonFuncController`，也不得再落到 `EnterpriseApiBusiness/CommonFunc`
17. NEWDAWHO 的 `CommonFunc` 是实现类库，承载可复用业务方法；`CommonUtil` 是对外调用入口，用来包装并暴露 `CommonFunc` 能力。若某 API 内部逻辑需要调用 CommonFunc，而目标方法尚不存在，第 04 步必须把 CommonFunc 内部方法也列入落码范本和 `codeTargetFiles`；不得只写 CommonUtil 外壳。内部方法调用 CommonFunc 时按方法调用处理，不视为外部 API 调用。
18. `CommonUtil` 仍保留 EnterpriseAPI Controller / Service 结构；第 04 步只允许为了编译引用 CommonFunc DTO / interface 调整 namespace，不得把 CommonUtil 搬入 `Sinopac.CommonFunc`
10. 先复用共享抽象，再补模块代码：若仓库已有 `CommonStatic`、共用 helper、response factory、header 解析器、错误码封装或 SQL executor 包装，不得在单个 service 内重复新增同类 helper
11. 对 `TransactionResult<T>` 封装，优先复用公共 factory；不得在每个 service 内重复创建 `BuildSuccess` / `BuildFailure` 之类的局部方法，除非该 helper 明确包含模块专属业务语义
12. 不得为单支 API 落码便利而预支公共抽象；只有仓库已存在同类模式，或至少 2 个 API / 模块会明确复用时，才允许新增 `CommonStatic` 级 SQL executor、response helper 或其它基础设施包装
13. 若专案规则库 `rules/code-guidelines/**` 或功能专属 `inputs/reference` 存在 JWT / Redis / Session 生命周期设计文档，必须先判断其是否为“目标态规范”还是“当前仓库已接线事实”；禁止把目标态规范中的零散 key 名、claim 名片段式搬进代码，形成半套实现。`.agent/reference/global` 是第 01 步外部 API / DB Schema 索引，不再作为开发规范来源
14. 对 JWT / Redis 设计文档，只有在 handoff 已明确给出“当前 API 直接依赖哪些字段、这些字段从哪里来、上游登录态是否已落地”时，才允许落运行时上下文、Redis key 或 session helper；否则必须在 `prepare` 阶段标记 `spec_handoff_gap` 或 `framework_gap`
15. 若设计文档以 `auth_sn`、统一 session key、member hash 等为核心主键，code writer 不得用全局 Redis key、临时 Header 候选列表或局部 fallback 伪装成“已符合规范”；未完整接线时只能按 handoff 标记差异，不得自行脑补补齐
16. 对 `Header` 读取、候选键扫描、Header / Redis fallback、Response envelope 组装这类“重复解析模式”，若仓库中已出现相同算法或至少两个模块会复用，应优先提升到 `CommonStatic`；不要在每个 service 内复制相同循环或判空逻辑
17. 对 `CountTextElements`、格式转换、空值规范化等“纯工具函数”，只有在跨 API / 模块出现明确复用时才下沉到共用层；单一业务规则附近的一次性私有方法可以保留在模块内，但若该方法只是单次调用、单层转发、单行映射或简单包装，则默认直接内联，避免把模块文件切碎成过多私有方法
18. 共用层与业务层的边界必须明确：共用层只承载无业务语义的解析算法或基础工具；候选 Header 列表、字段优先级、错误文案、长度上限等业务规则仍应保留在模块代码或 handoff 中
19. `CommonStatic.cs` 默认只放跨域、稳定、低业务语义的基础方法；单点使用的字串裁剪、空值转空字串、轻量格式转换等小工具，不得因为“看起来通用”就直接塞进 `CommonStatic.cs`
20. `CurrentRuntimeContextAccessor`、`RequestContextAccessor`、`UserContextAccessor` 等“当前请求身份上下文”类代码属于高风险基础设施，不得因单支 API 落码方便而自动生成；只有当 handoff 已明确给出身份来源、会话主键、上游登录态落地方式与 source of truth 时才允许新增或扩展
21. 运行时身份上下文的 source of truth 必须单一且可审计：允许来源只能是已验证 JWT claim、session-scoped Redis key、或框架既有认证上下文；禁止生成“任意 Header 候选 + 全局 Redis key + 局部 fallback”混搭实现
22. 若 handoff 没有明确说明 `CustId` / `KeyId` / `auth_sn` / `sub` 等字段到底来自哪里、是否经认证、Redis key 是否 session-scoped，则 code writer 必须阻塞；不得自行发明 `CurrentRuntimeContextAccessor` 或补全其 fallback 规则
23. 对运行时身份上下文，`Header` 只能作为上游网关或认证层已经明确保证的透传载体；若缺少这层保证，不得把业务 Header 候选列表当成身份事实来源
24. 对 Redis 身份缓存，若 key 不是绑定 `auth_sn`、session id 或等价会话主键的 scoped key，一律视为不合格身份来源；不得用全局 `CustID` / `KeyId` 之类 key 读取“当前用户”
25. 对 Redis / Memory / 本地缓存，code writer 必须先判断该数据是“缓存”还是“业务事实来源”；若 handoff 未明确，默认视为缓存，不得把缓存值当成权威状态去做业务判定
26. 若同一 API 同时依赖数据库与缓存，必须显式指定 authoritative store；禁止生成“用缓存判断是否重复、用数据库判断是否存在、成功后再盲写缓存”这类混合事实源实现
27. 新增业务缓存时必须同时定义 TTL、失效/刷新策略、空值处理与并发更新策略；若 handoff 或设计文档未给出，code writer 必须阻塞或保持不缓存，不能默认写成永久缓存
28. 对用户资料、昵称、地址、会员资料等可被外部流程更新的数据，若使用缓存，必须在 change-plan 中说明 stale-read 风险与接受条件；不能因为仓库已有 `IRedisService.SetRedisValue(key, value)` 就默认长期缓存
29. 若缓存只用于读优化，业务判定应优先基于 authoritative store 或已明确允许的单一事实源；缓存可用于短路返回，但不得在数据不一致时覆盖权威判定
30. 对 DB + cache 双写路径，必须说明写库成功、写缓存失败、缓存陈旧、空结果缓存、删除/失效策略分别如何处理；未说明时，不得自行生成“永久写缓存”的默认行为

系统设计规范 v2.5 的开发落码补充规则：

- 外部资源交互场景默认使用 async/await，包括 HTTP、Database、webservice、文件读写、FTP、上传下载、Email 等；方法名应以 `Async` 为后缀，返回 `Task` 或 `Task<T>`，调用异步方法不得使用 `.Result`。
- NEWDAWHO 专案反向约束：没有 DB、HTTP、Redis、文件、网络、外部服务等异步操作的方法，不得为了统一样式强行返回 `Task` / `Task<T>`，也不得加 `Async` 后缀。
- 资料检索代码必须遵守系统设计规范 v2.5 的 `数据检索顺序`，以及 handoff 中的 `dataRetrievalOrder` 或同等说明。若 DB/cache/API 优先级、cache miss、资料不一致或权威来源未定义，code writer 必须阻塞或标记 handoff gap，不得自行决定检索顺序。
- Redis key 落码必须先确认简易模式共享 Hash/Member 生命周期或进阶模式自定义 Key；自定义 Key 只能使用 `[A-Za-z0-9]`、`_`、`:`，不得包含空格、换行、百分号等特殊字符，且不得包含身份证号、完整卡号、密码等敏感资料。
- Appsetting 落码必须使用 `appsettings.{Environment}.json` 既有环境文件规则；配置 Section/Key 使用 PascalCase 与层级化 JSON。第三方服务配置量超过 50 个时，应依 handoff 或既有仓库模式拆到独立配置文件；缺少依据时不得自行新建随意命名的配置文件。
- DB 对象命名遵循系统设计规范 v2.5：表名/栏位名 PascalCase，stored procedure 使用 `sp_` 前缀，view 使用 `vw_` 前缀。若仓库既有 legacy DB 名不同，只能按 legacy evidence 使用，不得把旧名扩散成新对象命名规则。

31. 对所有请求 DTO，基础输入约束默认优先放在实体类特性，不得先写进 service；可由实体类特性表达的规则包括必填、长度、格式、枚举范围与单字段约束
32. service 中禁止保留与 DTO 特性重复的基础输入校验，例如 `request is null`、`string.IsNullOrWhiteSpace(...)`、简单长度判断、格式判断；service 仅保留业务语义、运行时上下文、DB/缓存状态与跨字段规则
33. 若字段规则是“最多 N 个文字元素”而不是 UTF-16 长度，默认生成公共自定义 `ValidationAttribute`；不得为了省事退化成 `StringLength` / `MaxLength` 或继续留在 service 私有方法
34. 若 spec 给了精确错误码/文案，特性校验返回必须映射到 spec 定义；不得直接落成现有通用 `ValidateModelStateFilter` 的 `400 + Validation failed`
35. 公共验证能力默认落在 `CommonStatic`：可复用 `ValidationAttribute`、特性错误到 `TransactionResult` / spec code/message` 的映射逻辑、统一字段错误结构；不允许模块各自发明一套 `AliasLengthAttribute` 和局部错误映射
36. 若仓库当前缺少“特性错误映射到 spec code/message”的公共基础设施，`prepare` 必须先在 change-plan 中标记为公共差口；不得绕回 service 手写重复校验充当替代方案
37. 服务方法返回契约默认保持 `Task<TransactionResult<TResponse>>`，不要为了失败分支少写一行代码，把泛型参数改成 `TResponse?`
38. 对 `TransactionResult<TResponse>`，失败时默认允许 `ResponseData = null`；若 spec 或既有接口没有明确要求失败时返回空对象 `{}`，不得生成 `new TResponse()` 作为默认失败 payload
39. 因此失败分支应优先生成 `TransactionResults.Failure<TResponse>(code, message)`，而不是 `TransactionResults.Failure(code, message, new TResponse())`
40. 只有在 spec、旧接口契约或前端消费约定明确要求“失败也必须返回空对象结构”时，才允许在 failure path 传入 `new TResponse()`；此时必须在 `change-plan.json.analysis.keepLocalReason` 说明原因
41. 对新增 `Controller`、`Service` 等需要依赖注入的业务类型，默认优先使用 C# 主构造函数；不要再默认生成“私有字段 + 传统构造式注入”的旧写法。`IntegrationTest fixture` 的写法由第 05 步负责。
42. 使用主构造函数时，字段应直接由主构造参数初始化并保留必要的 `null` 防御，例如 `private readonly IFooService _fooService = fooService ?? throw ...;`；凡是依赖注入后赋值到栏位的成员，命名一律使用 `_camelCase`，首字固定底线，不得生成 `CtxAccessor`、`Logger` 这类 PascalCase 栏位
43. 对使用主构造函数的 `Controller`、`Service`，XML 注释必须补齐到类型声明上；除了 `<summary>` 之外，还要为每个主构造参数写 `<param name="...">...说明...</param>`。测试 fixture 的注释规则交由第 05 步执行。
44. 主构造函数参数说明不得留空；至少要写明依赖职责，例如 `logger` 写 `Logger`、`ctxAccessor` 写 `执行上下文存取器`、`redis` 写 `Redis 服务`、`sqlExecutor` 写 `SQL 执行器`
45. 只有在以下情况才允许回退传统构造函数：仓库目标框架不支持主构造函数、既有同文件 partial/type 结构与主构造函数冲突、或项目现有模块已明确统一使用旧风格且必须保持一致；回退原因必须写入 `change-plan.json.analysis.keepLocalReason`
46. 成员、字段与局部参数命名默认采用“简化但语义仍清楚”的风格；不要机械重复完整类型名或模块名，例如优先 `_service`、`_sqlExecutor`、`_ctxAccessor`、`ctx`，而不是 `_settingService`、`_sqlQueryExecutor`、`runtimeContext`；其中依赖注入栏位必须统一为 `_camelCase`
47. 对匿名对象初始化也适用相同简化原则：若属性名可由表达式自然推导，优先使用 C# 匿名对象简写，例如 `new { ctx.CustId, ctx.Ip, ctx.DeviceInfo, Alias = alias }`，不要默认展开成 `CustId = ctx.CustId`
48. 只有在短名会造成歧义、需要改名避冲突、或匿名对象属性名必须与目标参数名显式不一致时，才扩展成长名或显式赋值；若因既有风格保留长名，可在 `change-plan.json.analysis.keepLocalReason` 说明
49. 对服务实现类库，模块代码必须包裹在模块文件夹中；新增 `SettingService.cs`、`SettingService.<ApiName>.cs` 这类文件时，默认落到 `EnterpriseApiBusiness/Setting/`，不得平铺在 `EnterpriseApiBusiness/` 根目录
50. 对服务层中的 SQL 语句，默认使用 C# Raw String Literals（`"""`）语法；不要再生成 `@"..."` 逐行 SQL 字面量
51. 使用 Raw String Literals 时，SQL 必须按关键字换行并保持可读布局，例如 `SELECT` / `FROM` / `WHERE` / `INSERT INTO` / `VALUES` / `UPDATE` / `SET` 各自独立成段，不要压成单行或半行拼接
52. 对 `FROM` / `LEFT JOIN` / `INNER JOIN` / `WHERE` 这类 SQL 主子句，默认采用“关键字单独成行，下一行再放表名、连接目标或条件主体”的版式；不要生成 `FROM Table`、`LEFT JOIN Table`、`WHERE Condition` 这种挂尾式写法
53. 服务层 SQL 变量默认写成 `var sql = """ ... """;`。`SELECT` 字段一行一个，第二个字段开始逗号放在字段行前；字段引用默认使用 `表名.字段名` 或 `别名.字段名`，避免裸字段造成来源不清。
54. SQL 中不得出现 `dbo.`。若 legacy evidence 明确带 schema，不能直接照抄到新 SQL；必须在落码范本或诊断中说明 schema 来源和沿用理由，等待用户确认后才可处理。
53. 对 `partial` service / controller 的分拆实现文件，必须自行补齐本文件实际用到的 `using`；像 `ILogger.LogError` / `LogWarning` 这类 extension method 不得假设会从同名主文件透进来，若当前文件直接调用扩展方法，必须显式引入 `Microsoft.Extensions.Logging`
54. 对 C# `file` local type，只有在该类型不会出现在非 `file` local 类型的成员签名中时才允许使用；若 helper type 会出现在 `Service` / `Controller` 的方法返回型别、参数、局部集合型别或私有方法签名中，必须改为类内 `private` / `internal` nested type，或改为同文件非 `file` local 顶层型别
55. 对集合空值回退与 `??` 运算，左右两侧型别必须保持一致；若左侧是 `List<T>` 就使用 `[]` 或 `new List<T>()`，若左侧是 `IReadOnlyList<T>` 就统一投影成相同接口型别，不得生成 `List<T> ?? T[]` 这种会触发 `CS0019` 的组合
56. 对数组型别使用集合判定时，默认使用 `Length` 而不是 `Count`；只有在目标型别确实为 `ICollection<T>` / `List<T>` / LINQ 查询结果时才用 `Count`
57. 所有新增源码文件默认必须保留文件级头部说明，不得只留下 `using` 或省略文件头；头部至少包含 `文件说明`、`新增人员`、`新增时间`、`修改人员`、`修改时间`、`修改说明`
58. `文件说明` 必须写文件职责或模块语义，例如 `Setting 模组控制器`、`Setting 模组服务`、`更新使用者暱称资料结构`；不得写空值、`TODO` 或与文件不符的泛称
59. 文件级头部说明默认沿用仓库既有风格，但 `Controller` 文件一律使用 XML `/// <summary>` 形式，与当前 `Service` 风格保持一致；不要为 `Controller` 生成 `/* ... */` 块注释头
60. 新增文件头部说明时，`新增人员` 默认写当前 author，`新增时间` 使用当前执行日期的 `yyyy/MM/dd`；`修改*` 栏位保留空白占位，不要擅自编造修改记录
61. 文件级头部说明属于 `Controller`、`Service`、`Entity`、`Runtime`、`Validation` 等业务源码的共同约束；类型 XML 注释不能替代文件头规则。`UnitTest`、`IntegrationTest` 文件头由第 05 步负责。
62. 对 service / helper 方法中的非直观逻辑，默认补“分段说明型”行内注释；尤其是身份上下文解析、缓存命中与回退、唯一性校验、写库分支、异常回退、跨来源判定前后，都应在代码块前给出一句注释
63. 方法内部注释必须解释“为什么这里这样做”或“这一段在业务上承担什么职责”，不要写成逐行复述；像 `// 赋值给变量`、`// 调用方法` 这类废话注释禁止生成
64. 中文注释必须自然、通俗、像维护者会写的话；避免英文直译腔、抽象空话和 AI 感强的表达。不要写“执行资料获取以进行后续处理”这类拗口句，应改成“先查出资料，后面组回传结果会用到”。
64. 若逻辑只是简单 getter / setter / 单行转发，可不写方法内部注释；只有多分支、跨依赖、易误解或需要维护者快速建立上下文的代码块才要求补注释
65. 对 SQL 前置判定，优先在 SQL 之前说明“为何先查缓存 / 为何先判重复 / 为何根据存在性决定 insert/update”，而不是在每一行 SQL 参数旁重复解释
66. 对 `Service` 实现方法，若 `API_Spec.json` 或 `change-plan.json.analysis.businessSteps` 已提供大逻辑步骤，只有直接映射到这些 Spec 步骤的代码块才使用 `step + title` 的编号式注释，例如 `// 1. 操作邏輯：...`、`// 2. DB執行sql語句：...`
67. 这类 Spec 步骤注释只要求落在 `Service` 实现及其私有 helper 中，并且应放在真正对应的代码块之前，而不是只堆在方法开头；若某个步骤被拆到 helper 方法，也要在 helper 上保留对应的步骤编号或标题映射
68. 不属于 Spec 步骤映射的补充性逻辑说明，一律使用普通说明句，不写编号；例如例外处理原因、实现取舍、维护性提示等，都不要伪装成 `1.`、`2.` 这类步骤注释
69. `Controller`、DTO、Test 不强制复述 Spec 大步骤；这一条只约束 `Service` 实现层，避免把业务步骤注释扩散到不承载业务逻辑的文件
70. `API_Spec.json.mockExamples` 是测试情景的权威来源之一；`prepare` 必须把每个范例逐条写入 `change-plan.json.analysis.mockExamples` 与 `testScenarioPlan`，至少保留 `scenario`、`requestPayload`、完整 `responsePayload`、预期 `responseCode/responseMessage/isSuccess` 与来源序号，供第 05 步生成测试代码。
71. 第 04 步不得根据 `testScenarioPlan` 生成 `UnitTest` / `IntegrationTest` 源码；只能记录建议的测试文件、测试层级、测试命名、断言重点、fixture 需求与阻塞原因。
72. 若某个 `mockExamples` 情景因缺少 fixture、后端替身、时钟/营业日上下文或依赖接线而无法规划测试，code writer 必须在 `change-plan.json.analysis.unresolvedLogic` 或后续诊断中明示阻塞/缺口；不得静默跳过该情景。
73. 对 `mockExamples` 的测试计划必须要求第 05 步断言完整输出契约：`isSuccess`、`responseCode`、`responseMessage`、必要的 `responseDT` 格式，以及 responseData 中每个规格字段的值、空值、集合笔数和关键顺序。不得只规划 HTTP 200、`IsSuccess` 或单一代表字段后宣称覆盖该范例。
74. 对含 DB / SQL / `queryContracts` / `backendApis.DB` / SQL table 依赖的 API，必须在 handoff 中写清：Mock `ISqlExecutor` 的 Service UnitTest 只能算“范例情景与映射逻辑验证”，不能算 SQL 正确性或正式环境业务验证。
75. 真实 Service runtime validation 计划必须要求第 05 步使用真实 Service 实例与接近正式依赖边界的测试替身：保留真实业务 Service、真实 SQL executor 或等价测试 DB executor、测试 DB/SQL fixture、可审计的当前用户/会话上下文；只允许替换认证上下文、时钟、外部网络调用等不可控边界。不得 mock 掉被验证 API 的业务 Service 本身。
76. 对 DB / SQL API，必须规划至少一组真实 SQL fixture 测试，验证 SQL 在 SQL Server 或项目认可的测试数据库上可执行，并覆盖表名/栏位名、参数绑定、JOIN、过滤条件、排序、TOP/LIMIT、空资料行为、异常行为与 response 字段映射。缺少测试 DB、schema 或 seed 时，必须标记 `waiting_fixture` / blocked，不得降级为仅 mock SQL executor。
77. Controller IntegrationTest 若用于证明业务链路，测试计划必须要求走真实 Service；mock `I<Module>Service` 的测试只能标记为 route/auth/serialization smoke test，不得作为 Service 业务逻辑或 SQL 正确性的证据。
78. 当 API 同时存在 Excel 范例情景与真实 DB/SQL 依赖时，测试计划必须分层写清：`spec_example_unit_tests` 覆盖每个 mockExample 的输出契约，`service_runtime_tests` 覆盖真实 Service + SQL fixture，`api_integration_tests` 覆盖路由、授权、序列化与必要的真实 Service 链路。三层缺任一层时，必须在 `change-plan.json.analysis.unresolvedLogic` 说明原因。
81. Spec 步骤注释允许在不改变原意的前提下做最小归纳，但不得凭空改写业务顺序、合并掉关键步骤，或把 `businessSteps` / `logicFlow` 中的编号信息全部丢失
82. 若 `businessLogic / backendApis / dependencyHints / queryContracts` 指向了明确后端依赖（例如 `CommonFunc.GetRateEnquiryFunc`），而仓库当前并无等价实现或接线事实，code writer 不得静默改接到名称相近的其它接口充当替代；必须在 `change-plan` 明示“当前以何接口暂代、为何可接受”，否则应阻塞或等待澄清
83. 若 spec `mappingRules` 明确给出多个不同来源字段（例如 `listRate`、`doneRate`、`etsTime`、`deductionAmt`、`payeeAmt`），实现与测试都必须逐字段保真映射；不得为了方便把多个响应字段压成同一个来源值、系统当前时间或原始 request 值
84. 对 ResponseCode / ResponseMessage，默认先识别“公共 catalog”与“模块私有 catalog”的归属，再落盘成成对 definition；禁止在 `TransactionResults.Success(...)` / `Failure(...)` 直接写字面值，或在单支 service 中散落重复的局部 code/message 常量
85. 若仓库已存在公共 response catalog，优先复用；只有当响应码明确属于模块私域、且不会跨模块共享时，才新增模块内私有 response definition。公共 catalog 与模块私有 catalog 的命名、职责与落点必须清楚分层，避免同一响应码在多个位置重复定义

## 命令行

```powershell
python ".\scripts\write_api_code.py" `
  --project-root "D:\Repo\Project" `
  --workspace-key "PROJECT" `
  --solution-path "D:\Repo\Project\App.sln" `
  --execution-mode "prepare"
```

用户审阅或修改 `implementation-template.md` 后确认范本：

```powershell
python ".\scripts\write_api_code.py" `
  --project-root "D:\Repo\Project" `
  --workspace-key "PROJECT" `
  --solution-path "D:\Repo\Project\App.sln" `
  --function-code "D.006" `
  --api-id "D.006.deposit.addexchangedepositinit" `
  --execution-mode "confirm"
```

```powershell
python ".\scripts\materialize_review_notes.py" `
  --project-root "D:\Repo\Project"
```

```powershell
python ".\scripts\write_api_code.py" `
  --project-root "D:\Repo\Project" `
  --workspace-key "PROJECT" `
  --solution-path "D:\Repo\Project\App.sln" `
  --function-code "D.006"
```

AI 在目标仓库完成真实改码后，再执行：

```powershell
python ".\scripts\write_api_code.py" `
  --project-root "D:\Repo\Project" `
  --solution-path "D:\Repo\Project\App.sln" `
  --function-code "D.006" `
  --api-id "D.006.deposit.addexchangedepositinit" `
  --execution-mode "apply"
```

Windows / .NET 工作区若遇到 `obj/refint/*.dll`、`bin/*.dll`、`GenerateDepsFile` 或 `MSB3248` 文件锁，优先使用技能内稳定验证脚本。该脚本会先执行 `dotnet build-server shutdown`，清理 `VBCSCompiler` / `testhost` 常驻进程；传入 `-KillDotnet` 时也会清理 `dotnet` 进程；并自动为 `dotnet build` / `dotnet test` 补 `-m:1`：

```powershell
powershell -ExecutionPolicy Bypass `
  -File "<pluginRoot>\skills\api-code-writer\scripts\dotnet-stable-verify.ps1" `
  -ProjectRoot "D:\Repo\Project" `
  -KillDotnet `
  -Command @(
    'dotnet build "Sinopac.DawhoEnterprise/API/EnterpriseAPI/EnterpriseAPI/EnterpriseAPI.csproj"',
    'dotnet test "Sinopac.DawhoEnterprise/Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/EnterpriseAPIUnit.csproj"',
    'dotnet test "Sinopac.DawhoEnterprise/Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/EnterpriseAPIIntegration.csproj"'
  )
```

## 支持的输入参数

- `--project-root`
- `--solution-path`
- `--agent-dir`
- `--agent-root`
- `--workspace-root`
- `--workspace-key`
- `--rules-root`
- `--context-root`
- `--function-code`
- `--api-id`
- `--execution-mode`
- `--validation-check`
- `--modified-file`
- `--new-file`

默认 `--context-root` 为 `<agent-root>/context`；未配置集中 `.agent` 时回退 `<project-root>/.agent/context`。

## 共享目录结构

- `.agent/context/execution-batch.json`
- `.agent/context/<functionCode>/execution-state.json`
- `.agent/context/<functionCode>/api-checklist.json`
- `.agent/context/<functionCode>/spec-progress.md`
- `.agent/context/<functionCode>/code-progress.md`
- `.agent/context/<functionCode>/repo-snapshot.json`
- `.agent/context/<functionCode>/apis/<apiId>/manifest.json`
- `.agent/context/<functionCode>/apis/<apiId>/{functionCode}_API_Spec.json`
- `.agent/context/<functionCode>/apis/<apiId>/change-plan.json`
- `.agent/context/<functionCode>/apis/<apiId>/implementation-template.md`
- `.agent/context/<functionCode>/apis/<apiId>/implementation-template.json`
- `.agent/context/<functionCode>/apis/<apiId>/implementation-report.md`
- `.agent/context/<functionCode>/apis/<apiId>/diagnosis-report.json`
- `.agent/context/<functionCode>/apis/<apiId>/review-notes.json`

## 完成规则

- 不再读取 `.agent/api-spec-writer` 或 `.agent/api-code-writer`
- 不再接受 `--upstream-root`
- 只消费共享 `manifest.json` 的 `spec*` 字段和同目录 `*_API_Spec.json`
- 必须同时读取并保留共享 `manifest.json` / `api-checklist.json` / `execution-state.json` 中的 `fixture*` 字段；不得在回写 code 状态时覆盖或清空 SQL fixture 状态
- 只更新共享 `execution-state.json`、`api-checklist.json`、`manifest.json` 的 `code*` 字段和顶层聚合字段
- code writer 不绑定固定前置步骤名称；只要共享 `.agent/context` 产物齐备即可进入
- 进入 code writer 前不强制先执行 `skills/api-sql-fixture-preparer/SKILL.md`
- 若目标 API 在 `apply` 时的 `fixtureStatus` 仍非 `done|skipped`，则应回报 `waiting_fixture`，提示先补执行 fixture
- `codeHandoff` 优先级高于旧 `businessLogic`，本地相似文件只能补实现风格，不能替代 handoff 缺失的原业务逻辑
- `EnterpriseAPI` 控制器固定保留 `[ApiVersion]` 与版本路由，不写 `[ApiController]`
- `EnterpriseAPI` 新增 `Controller` / `Service` 默认使用主构造函数；除非框架版本、partial 结构或既有模块风格明确不允许
- `EnterpriseAPI` 的服务实现文件默认使用模块文件夹布局，例如 `BusinessLogicLayout/EnterpriseApi/EnterpriseApiBusiness/Setting/SettingService.cs`
- NEWDAWHO `CommonFunc` 是共享类库，不生成、不规划 `CommonFuncController`；接口固定在 `IFuncService`，实现固定在 `FuncService`，DTO 与 response resource 分别固定在 `Dto` / `ResponseCodes`
- `EnterpriseAPI` 返回值固定使用 `TransactionResult<T>`
- 发现 `AddBusinessScoped()` 已存在时，不把修改 `Program.cs` / `ProgramExtensions.cs` 当成常规步骤
- `change-plan.json.analysis` 必须写明 `frameworkProfile`、`moduleName`、`controllerFile`、`interfaceFile`、`serviceFiles`、`entityFiles`、`codeTargetFiles`、`unitTestTargetFiles`、`integrationTestTargetFiles`、`testCodeHandoff`、`creationMode`，以及 `logicSourcesUsed`、`queryContractsSelected`、`mappingRulesSelected`、`legacyEvidenceUsed`、`constraintsApplied`、`unresolvedLogic`。`unitTestTargetFiles` / `integrationTestTargetFiles` / 汇总型 `testTargetFiles` 只用于第 05 步测试代码 handoff，不代表第 04 步可写入测试源码。
- `change-plan.json.analysis` 必须写明 V6.2 渐进式披露结果：`audienceProfile`、`devGuidelineProfile`、`devGuidelineRulesSelected`、`devGuidelineLoadHints`、`devGuidelineGaps`。`devGuidelineLoadHints` 只是 AI 后续按需读取的 reference 路径；若 `audienceProfile.scope=unknown` 且命中前台/中后台专属规范，必须阻塞要求补调用者或入口方向证据。
- 若 API 目录下存在 `review-notes.json`，`change-plan.json.analysis` 还必须写明 `reviewSources`、`reviewConstraintsSelected`、`fileRequirements`、`responseLifecycleRules`、`failureDisposition`、`languagePolicy`、`externalApiName` 与 `internalAsyncMethod`
- 若 API 规格存在 `mockExamples`，`change-plan.json.analysis` 必须写明 `mockExamples`、`testScenarioPlan`、`testScenarioCoverageRequired` 与 `testScenarioSource`，供第 05 步规划并生成 UnitTest / IntegrationTest / Service runtime validation 测试代码
- 若 API 规格或 handoff 标记 DB / SQL 依赖、`serviceRuntimeValidationRequired`、`queryContracts`、`backendApis.DB` 或 SQL table，`change-plan.json.analysis` 必须额外写明 `serviceRuntimeValidationPlan`、`sqlFixturePlan`、`realServiceIntegrationTests`、`mockSqlUnitTestsPurpose` 与 `runtimeValidationBlockers`。其中 `mockSqlUnitTestsPurpose` 必须明确限制为范例情景/映射逻辑验证，不得写成 SQL 正确性验证。
- `review-notes.json` 中的 blocking 约束若引用了 spec / handoff 不存在的 request/response 字段，`prepare` 必须以 `review_constraint_gap` 阻塞，不能带着矛盾约束继续生成计划
- AI 写入的中文注解、字串、文件说明与角色要求统一使用繁体中文；若 `review-notes.json` 已显式提供语言约束，则以 review-notes 与当前技能规则的交集为准，不得回退为简体中文
- 若识别到重复的 Header 解析 / fallback / 文本工具模式，`change-plan.json.analysis` 应说明 `sharedPatternCandidates`、`keepLocalReason` 或 `promoteToCommonReason`，避免 AI 凭感觉决定是否抽共用
- 若 API 规格或项目约束给出了响应码目录，`change-plan.json.analysis` 必须说明 `responseCatalogSource`、`responseCatalogOwnership(common|module)`、`responseDefinitionsToReuse` 与 `responseDefinitionsToCreate`，避免 AI 直接回退为字面值
- 若涉及 `CurrentRuntimeContextAccessor` 或同类运行时身份上下文，`change-plan.json.analysis` 必须额外写明 `identitySourceOfTruth`, `identityCarrier(jwt|authContext|sessionRedis|header)`, `identityClaimsUsed`, `identityRedisKeysUsed`, `identityScope(session|global)`, `headerTrustBoundary`, `fallbackPolicy`, `identityGenerationMode(reuse|extend|block)` 与 `identityRisks`
- 若涉及缓存，`change-plan.json.analysis` 必须额外写明 `cacheKeysUsed`, `cacheRole(cache|session|source_of_truth)`, `authoritativeStore`, `cacheTtl`, `cacheRefreshPolicy`, `cacheInvalidationPolicy`, `nullCachingPolicy`, `consistencyModel`, `staleReadRisk` 与 `cacheFallbackPolicy`
- 若涉及请求 DTO 校验，`change-plan.json.analysis` 必须额外写明 `requestValidationPlan`, `dtoAttributeRules`, `customValidationAttributesNeeded`, `validationResponseMappingMode`, `serviceValidationsRetained` 与 `validationInfrastructureGap`
- `prepare` 只允许生成 change-plan 与状态文件；不得直接创建或改写业务代码文件
- `prepare` 还必须生成三层 `implementation-template.md` 与机器锁 `implementation-template.json`；用户只改 Markdown，不手改 JSON
- `confirm` 必须锁定当前 Markdown hash；确认后若 Markdown 又被修改，`apply` 必须以 `template_modified_after_confirmation` 阻塞
- `apply` 必须基于已确认范本和 AI 已写入的真实仓库改动；如果未确认范本或未检测到真实改动，必须阻塞
- 默认验证策略：显式 `validation-check` 优先；未提供时 `EnterpriseAPI` 固定执行 API build，并可运行仓库既有 unit test / integration test 作为回归验证；第 04 步不得为了通过验证而新增或修改测试源码。默认 API build、unit test、integration test 都必须使用 `-m:1` 降低 MSBuild 并行度，测试项目默认正常 build/test，不使用 `--no-build` 依赖既有 DLL
- Windows 下显式 `validation-check` 必须在命令字符串内部使用双引号包住含空格路径，例如 `dotnet build "D:\Repo\App.csproj"`；不要把 PowerShell 单引号路径直接塞进 `validation-check`
- Windows 下手工验证或显式验证若需要固定清理常驻进程，优先调用 `scripts/dotnet-stable-verify.ps1`；需要强制清理 `dotnet` 进程时显式传入 `-KillDotnet`
- 新增或修改 C# 源码时默认使用 file-scoped namespace；修改既有业务文件时，除非文件结构不允许，应一并从 block-scoped namespace 收敛为 file-scoped namespace。
- AI 交付前必须清理未使用的 `using`；若编译器或 IDE 可直接判定为未使用，则不得保留在最终代码中
- 对象建立默认使用简化写法；目标型别可由声明、赋值、回传型别、集合初始化或参数位置明确推导时，使用 `new()`，只有存在可读性、重载解析或类型推断风险时保留完整型别。匿名对象初始化若属性名可由成员访问尾段自然推导，默认使用 `new { ctx.CustId, ctx.Ip }` 这类简写；只有在需要改名或避免歧义时才显式写成 `CustId = ctx.CustId`
- 集合或数组初始化在目标型别明确时优先使用 C# collection expression，例如 `[]` / `[item1, item2]`；只有型别推断、重载解析、可读性或框架兼容性有风险时，才保留 `new[] { ... }`、`new T[] { ... }` 或 `new List<T> { ... }`
- 私有方法拆分必须服务于复用、独立业务语义或多分支可读性；对于只在单一方法中调用一次的轻量格式转换、字典映射或单字段包装，默认保留在当前方法内，不要为了“结构化”而额外拆方法
- 代码行间说明按用途加标签：`// [業務]：` 用于 PRD/TSD/API Detail / 旧系统继承下来的业务规则、业务判断与业务限制；`// [意圖]：` 用于说明查询顺序、异常降级、兼容旧资料、避免重复调用、避免空值误判等代码意图。标签注释优先放在相关代码块前，不做逐行复述
- 防呆 `if` 与 defensive branch 也必须在前一行加标签注释；业务限制用 `// [業務]：`，空值保护、状态防误判、部分更新防护用 `// [意圖]：`
- 访问外部状态或服务的 `await` 前必须加即时 `// [意圖]：` 注释，范围包含 DB 查询/写入、交易建立/提交/回滚、登入上下文、CommonFunc / 外部 API / Redis / cache、文件与网络访问
- 对 Service / helper 中承载业务语义的显式控制流程区块，`if` / `else if` / `foreach` / `for` / `while` / `switch` / 有业务语义的 `case` 前方都必须补一句标签注释；注释要说明这个判断、迭代或分派在做什么，以及为什么要在这里短路、跳过、汇总、映射或分流，不能只对 `if` 补注释而让 `foreach`、`switch` 裸露
- `switch` 不按条件数量硬套；只有同一判断维度、状态枚举或明确 pattern matching 时才使用，像交易日这类多字段业务判断默认保留 `if` / `else if`
- 私有方法默认必须补齐显式说明，至少让维护者一眼看懂「这个方法负责什么」与「何时会被调用」；优先使用 XML 注释，若仓库该位置不适合 XML，则至少在方法前补一行职责说明注释。只有简单到无需解释的单行 getter / setter / 纯转发方法才可省略
- 对公开方法、接口实现方法与控制器动作，默认写与当前职责一致的显式 XML 注释；不要用 `inheritdoc` 充当占位，除非上游接口本身已经提供完整且完全适配当前语义的注释
- `return` 前默认留一空行；特别是在 `if` / `catch` / 主要成功路径中，避免日志、赋值或其它语句与 `return` 紧贴在一起
- `apply` 执行验证前应先清理可恢复文件锁相关常驻状态；遇到 `assembly_locked`、`GenerateDepsFile`、`ref/*.dll` 等可恢复文件锁时，应做有限次数的验证重试与退避；重试前可清理 `dotnet` / `VBCSCompiler` / `testhost` 常驻进程并执行 `dotnet build-server shutdown`
- 若 `dotnet build` 最终仅因 `assembly_locked` / `GenerateDepsFile` / `ref/*.dll` 这类可恢复文件锁失败，且同轮 `EnterpriseAPIUnit` 与 `EnterpriseAPIIntegration` 的 `--no-build` 验证均通过，则该轮 `apply` 可视为降级通过，回写 `tests_passed`；但必须在 `implementation-report.md` 与执行讯息中明确标注「build 因文件锁失败、依规则降级通过」
- 验证重试只用于可恢复环境锁；代码编译错误、测试断言失败、handoff 缺失等非锁类问题不得被重试掩盖，最终仍应按原始失败分类回写
- handoff 缺失或歧义时必须阻塞，不允许继续模糊猜测业务逻辑；诊断需区分 `spec_handoff_gap`、`framework_gap`、`environment_issue`、`code_issue`
- 验证失败时，`diagnosis-report.json` 必须区分代码问题与环境/基础设施问题，例如文件锁或外部依赖不可用
- `repo-snapshot.json` 对比时排除整个 `.agent/`
- `change-plan.json.analysis` 若引用 JWT / Redis / Session 设计文档，必须额外写明 `sessionModel`, `jwtClaimsUsed`, `redisKeysUsed`, `sessionSourceOfTruth`, `adoptionMode(full|partial|blocked)` 与 `designDocGaps`
- 若 API 引入缓存或事实源切换，必须在第 05 步 handoff 中要求单元测试至少覆盖：缺少身份上下文、缓存命中、缓存未命中、缓存与权威数据不一致、写库成功但缓存需刷新、权威数据为空时的返回策略。
- 若 API 引入或调整 DTO 特性校验，必须在第 05 步 handoff 中要求单元测试至少覆盖：特性命中时返回 spec 指定 code/message、自定义文字元素长度特性对中文/英文/emoji 行为正确、service 不再重复执行同一基础输入校验。
- 若 API 涉及 DB / SQL，必须在第 05 步 handoff 中把测试分成两类：一类是以 mock SQL executor 验证 Excel 范例情景、错误码和映射逻辑；另一类是以真实测试 DB/SQL fixture 验证 Service runtime、SQL 可执行性与正式依赖边界。只有两类证据都存在，后续测报才能描述为“Service 业务逻辑已完成接近正式环境的验证”。

## 高风险阻塞项

以下场景默认属于高风险生成，`prepare` 阶段必须阻塞或标记为 `blocked`，不得由 code writer 自行脑补实现：

1. 身份模型不清：
   - `CustId` / `KeyId` / `auth_sn` / `sub` 等字段来源不明
   - 未说明字段是否来自已验证 JWT、既有认证上下文或 session-scoped Redis
   - 只看到业务 Header 名，没有上游信任边界说明
2. 会话模型不清：
   - 设计文档依赖 `auth_sn`、统一 session key、member hash，但仓库现状未接线
   - handoff 未说明当前 API 属于 `full`、`partial` 还是 `blocked` adoption
3. 缓存事实源不清：
   - 未说明 `authoritativeStore`
   - 同时列出 DB 与缓存，但未说明重复判断、存在性判断、写后刷新以谁为准
   - 未给 TTL / 失效策略 / 空值策略，却要求新增业务缓存
4. 共用抽象边界不清：
   - 要求新增 `CommonStatic` helper / accessor / executor，但没有现成模式或明确复用面
   - 把业务常量、错误文案、候选 Header 列表与通用算法混在一起下沉
5. 测试意图不清：
   - 引入身份上下文、缓存或事实源切换，但 handoff 未给最小测试覆盖面
   - 仓库现有测试模式不足以承接改动，且未写明如何补齐
6. 请求校验策略不清：
   - 未说明字段校验应落在 DTO 特性还是 service
   - spec 给了错误码/文案，但未说明如何映射到特性校验返回
   - 文字元素长度规则存在，但未说明是否需要公共自定义 `ValidationAttribute`

阻塞时的最低输出要求：
- 在 `change-plan.json.analysis` 写明 `blockedReason`
- 在 `unresolvedLogic` 或 `designDocGaps` 中指出缺失字段或缺失规则
- 诊断需优先归类为 `spec_handoff_gap` 或 `framework_gap`，而不是继续生成猜测性代码

## 资源

- `agents/openai.yaml`
- `scripts/runtime.py`
- `scripts/state_io.py`
- `scripts/handoff_analysis.py`
- `scripts/framework_plan.py`
- `scripts/chain_workspace.py`
- `scripts/project_rules.py`
- `scripts/dev_guidelines.py`
- `scripts/convert_dev_guidelines.py`
- `scripts/validation_runner.py`
- `scripts/reporting.py`
- `scripts/write_api_code.py`
- `scripts/materialize_review_notes.py`
- `scripts/dotnet-stable-verify.ps1`
- `schemas/upstream-manifest.schema.json`
- `schemas/upstream-api-spec.schema.json`
- `schemas/review-notes.schema.json`
- `schemas/project-hard-constraints.schema.json`
- 专案规则库 catalog 中的 `codeGuidelineCatalog`
- 专案规则库 `rules/code-guidelines/**`
- 技能内 `references/dev-guidelines/**` 仅保留历史回归 fixture；运行时不得作为 active 开发规范来源
- `tests/run_regressions.py`

## Leader Mode

当由 `multi-api-leader` 显式编排时：

- leader 必须先按 `--api-id` 串行 prepare 全部 API，生成每个 API 的 `change-plan.json`。
- prepare 完成后运行 `skills/multi-api-leader/scripts/orchestrate_multi_api.py --mode plan`，根据 planned files 生成 `api-workgroups.json` 与 `file-claims.json`。
- 文件目标重叠的 API 必须进入同一 workGroup，由同一 worker 串行处理；无重叠 workGroup 才能并行。
- worker 只能修改 `file-claims.json` 分配给自己的代码文件，不能写 `.agent/context`，不能生成 UnitTest/IntegrationTest 测试源码。
- worker 返回的 `modifiedFiles` 必须由 leader 校验无越权后，leader 再串行 apply/验证并写回 `codeStatus`、`testCodeHandoff` 与相关共享状态。
