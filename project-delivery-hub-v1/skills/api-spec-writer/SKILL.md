---
name: API 规格写入器
description: 把功能 handoff 转成可供开发消费的 API Spec JSON。第 02 步：从 `.agent/functions/<functionCode>/handoff` 与 inputs 生成 `{functionCode}_API_Spec.json`，回写共享 `.agent/context` 的 `spec*` 状态；缺少 handoff 时先回到设计梳理技能。关键词：API_Spec.json、codeHandoff、mockExamples、specStatus。
---

# 02 API 规格写入器

使用这个第 02 步技能在共享 `.agent/context` 下初始化或恢复一个按功能编号稳定落盘的 API 规格生成执行面。脚本会读取共享的 `execution-batch.json` 与当前 execution 目录，只更新 `spec*` 字段并保留 `code*` 历史。`functionCode` 必须保留 TSD 文件名中的完整功能编号，例如 `D.006`、`N.001.001`，不能裁切成上层编号。除现有 `businessLogic` 外，`*_API_Spec.json` 还会新增 machine-readable `codeHandoff`，把查询契约、映射规则、依赖提示、旧逻辑证据和约束显式交给第 04 步 [$api-code-writer](C:/Users/<username>/plugins/project-delivery-hub-v1/skills/api-code-writer/SKILL.md)。若 `.agent/Common/project-hard-constraints.json` 存在，本 skill 还会先校验该项目级 profile，再把命中的项目硬约束折进 `codeHandoff.constraints`、`legacyEvidence` 与必要的 `unresolved`。若需要初始化或刷新全局 reference，改用第 01 步 [$reference-index-importer](C:/Users/<username>/plugins/project-delivery-hub-v1/skills/reference-index-importer/SKILL.md)；本 skill 只消费已存在的 reference 索引。

默认优先解析插件本地 `references/local-workspaces.json`，可按 `workspaceKey` 指向对应集中 `.agent`。参数优先级为 `--agent-root/--workspace-root` > 环境变量 > 插件本地配置 > 旧逻辑 `<project-root>\.agent`。`project-root` 只代表当前代码分支目录，`agent-root` 代表共享链路资料库。

专案规则读取与 `.agent` 分离：`--rules-root` > `PROJECT_RULES_ROOT` / 专案环境变量 > `references/local-workspaces.json.rulesRoot` > `<agentRoot>/project-rules/<workspaceKey>`。02 生成 spec 时优先从 `<rulesRoot>/catalog.json` 读取 API contract、field KB、SQL/Redis/Appsetting 与其他规格规则；缺少规则库时只按通用流程继续，并把专案专属规则缺口写入 unresolved / review artifact，不得从插件内旧个案 reference 偷读默认规则。

## 规则包启动检查

正式第 02 步启动后、读取 handoff 与生成 `API_Spec.json` 前，必须先解析 `apiSpecWriter` 规则包：

```powershell
python "C:\Users\<username>\plugins\project-delivery-hub-v1\references\resolve_project_rule_pack.py" `
  --pack apiSpecWriter `
  --workspace-key "<workspaceKey>"
```

若用户明确给出规则库，改传 `--rules-root "<rulesRoot>"`。脚本输出的 `rules[].resolvedPath` 是 spec 生成前的必读规则；`status=blocked` 时，不得生成标记为正式完成的 spec，只能把缺口写入 `codeHandoff.unresolved` / review artifact，并停止自动推进。

若 `.agent/functions/<functionCode>/handoff/development-handoff.json` 已存在，02 可直接从 handoff 选择 TSD 与 inputs，跳过 01；若 handoff 标记 `blocked` 或 `developmentReady=false`，02 必须停止推进并说明阻塞原因。

若未找到 handoff，02 的默认动作不是跑 01，也不是直接消费 legacy `.agent/TSD`。必须先切回 `专案需求接口设计梳理`：完成梳理逻辑、确认开发会用到的 TSD / API Detail / Common / Response Code / DB / Redis 设计文件，并执行 `scripts/materialize_design_handoff.py` 生成 `.agent/functions/<functionCode>/inputs/` 与 `handoff/development-handoff.json`；然后再回到 02。开发规范另由 `专案规则分析器 --category code-guidelines` 接入 project-rules。只有用户明确要求兼容旧流程时，才可加 `--allow-legacy-input` 直接消费 `docx_ref` 或 `execution-batch`。

## 默认使用方式

1. 直接调用 `scripts/write_api_spec.py`
2. 默认读取集中 `.agent/context/execution-batch.json`；未配置集中 `.agent` 时回退 `<project-root>/.agent/context/execution-batch.json`
3. 启动后先检查 `.agent/functions/<functionCode>/handoff/development-handoff.json`
4. 若 handoff 不存在，停止当前 02，先执行梳理技能与 handoff 物化，不把 01 当作补救步骤
5. 默认落到 `.agent/context/<functionCode>/`
6. 若未指定 `--api-id`，只推进一支未完成 API
7. 每次运行结束后，必须读取共享 `execution-state.json` 与 `api-checklist.json` 汇报结果

## 命令行

```powershell
python ".\scripts\write_api_spec.py" `
  --project-root "D:\Repo\Project" `
  --workspace-key "PROJECT" `
  --function-code "D.006" `
  --design-handoff "D:\Repo\Project\.agent\functions\D.006\handoff\development-handoff.json"
```

```powershell
python ".\scripts\write_api_spec.py" `
  --project-root "D:\Repo\Project" `
  "TSD.D.006_換匯優利定存_v1.0_20260408.docx"
```

```powershell
python ".\scripts\write_api_spec.py" `
  --project-root "D:\Repo\Project" `
  --function-code "D.006"
```

```powershell
python ".\scripts\write_api_spec.py" `
  --project-root "D:\Repo\Project" `
  --function-code "N.001.001"
```

## 支持的输入参数

- 位置参数：`docx_ref`
- 选项：
  - `--project-root`
  - `--agent-dir`
  - `--agent-root`
  - `--workspace-root`
  - `--workspace-key`
  - `--rules-root`
  - `--context-root`
  - `--design-handoff`
  - `--allow-legacy-input`（只作旧流程兼容；默认不要使用）
  - `--api-id`
  - `--function-code`
  - `--new-author`

默认 `--context-root` 为 `<agent-root>/context`。若存在 handoff 或当前项可命中，`docx_ref` 可省略；没有 handoff 时，即使存在 batch 文件也应先生成梳理产物。

## 共享目录结构

- `.agent/functions/<functionCode>/handoff/development-handoff.json`
- `.agent/functions/<functionCode>/inputs/{tsd,api-spec,common,response-codes,reference}/...`
- `.agent/context/execution-batch.json`
- `.agent/context/<functionCode>/execution-state.json`
- `.agent/context/<functionCode>/api-checklist.json`
- `.agent/context/<functionCode>/spec-progress.md`
- `.agent/context/<functionCode>/code-progress.md`
- `.agent/context/<functionCode>/apis/<apiId>/manifest.json`
- `.agent/context/<functionCode>/apis/<apiId>/{functionCode}_API_Spec.json`

## 参考资料前置条件

- `.agent/reference/global` 属于前置全局参考库，不由本 skill 现场导入
- 若缺少外部 API / DB Schema 的全局 `catalog.json` / `indexes/*.json`，才使用可选第 01 步 `$reference-index-importer`
- 本 skill 读取顺序：功能专属 `.agent/functions/<functionCode>/inputs/reference` > 全局 `.agent/reference/global` > legacy `.agent/Reference`
- 若 `.agent/Common/project-hard-constraints.json` 存在，必须通过 `schemas/project-hard-constraints.schema.json` 校验；校验失败时直接阻塞

## 完成规则

- 不再写入 `.agent/api-spec-writer`
- 默认不再以 legacy `.agent/TSD` 作为 02 起点；缺 handoff 时回到梳理技能生成开发输入包
- `--allow-legacy-input` 是显式兼容开关，只用于历史项目或应急验证，不能作为默认流程
- 只更新共享 `execution-state.json`、`api-checklist.json`、`manifest.json` 的 `spec*` 字段和顶层聚合字段
- 若 `specSourceFingerprint` 变化，必须把对应 API 的 `codeStatus` / `codePhase` 回退为 `pending`
- `progress.md` 改为 `spec-progress.md`
- `*_API_Spec.json` 仍只由 spec writer 负责
- 新生成的 `*_API_Spec.json` 必须同时包含原始 `businessLogic` 和结构化 `codeHandoff`
- `codeHandoff` 至少包含 `logicFlow`、`queryContracts`、`mappingRules`、`dependencyHints`、`legacyEvidence`、`constraints`、`unresolved`
- `codeHandoff` 同时供第 04 步业务代码实现与第 05 步 UT 测试代码/报告生成消费；其中测试意图、DB/SQL runtime validation、fixture 缺口、身份/缓存/外部依赖风险必须能被 `docx-unittest-report` 直接判定证据层级
- Excel API Detail 的「范例 / 情境说明」区块中每个可解析的 Request / Response 情景都必须完整写入 `mockExamples`；不得只挑成功、失败代表样本，也不得因为多个情景共用同一个 responseCode 就合并或丢弃
- `mockExamples` 是第 05 步 `docx-unittest-report` 生成 UnitTest / IntegrationTest / Service runtime validation 测试代码与 UT 测报证据的权威情景来源；Excel 中的失败情景、营业日/时间窗情景、必填参数情景即使已写入 `businessLogic.errorCodeRules` 或 `codeHandoff.constraints`，也仍必须保留在 `mockExamples`
- 若 Excel 范例 payload 无法解析为结构化 JSON，必须写入 `rawAppendix.unparsedMockExamples` 或同等 raw appendix，并在 review artifact 中提示；不得静默忽略该情景
- `mockExamples` 交接必须保留可追溯信息：来源 sheet、来源区块/行号或序号、原始情境名称、requestPayload、完整 responsePayload、预期 `isSuccess/responseCode/responseMessage`，以及该情境需要由 UnitTest、IntegrationTest 或真实 Service runtime validation 覆盖的测试意图；不得只输出 response payload 而缺少测试目的。
- Excel 业务逻辑正文提到的依赖也必须结构化交接，不能只依赖「涉及BackendAPI」行：IRIS / CommonFunc / CommonUtil / Backend / DB 表 / SQL / Redis / 邮件推播等若出现在步骤说明、字段来源或 SQL 片段中，必须同步折进 `businessLogic.runtimeDependencies`、`businessLogic.sqlSpecs`、`codeHandoff.dependencyHints` 或 `codeHandoff.queryContracts`
- 对正文中带 `todo`、`待确认`、`是否还需要`、`未找到` 这类不确定语义的依赖，不得当成已确认实现或 fixture 需求；必须写入 `codeHandoff.unresolved`，说明 `blockedReason`、`missingFacts`、`suggestedOwner` 与 `nextDecisionNeeded`
- DB / SQL 依赖的结构化优先级必须足够让第 03 步消费：确定的 SQL 语句或表写入 `codeHandoff.queryContracts` 或 `businessLogic.sqlSpecs`；只有待确认的 DB 表写入 unresolved，不得仅藏在 `businessLogic.steps` 大段文字里
- 若 API 涉及 DB / SQL / SQL table / `queryContracts` / `backendApis.DB`，spec writer 必须在 `codeHandoff` 明确标记 `serviceRuntimeValidationRequired: true` 或同等语义，并交接真实 Service runtime validation 的最小验证范围：目标表、关键栏位、SQL 参数、seed 场景、预期笔数、排序、过滤条件、JOIN 行为、空资料行为、异常行为与逐字段映射规则。
- 对 DB / SQL API，`codeHandoff.queryContracts` 不得只保留一段不可消费的大 SQL 文本；必须拆出可供 fixture 与测试使用的结构化内容，例如 `connectionTarget`、`tables`、`seedRequirements`、`expectedResultShape`、`parameterSources`、`orderingRules`、`filterRules`、`joinRules` 与 `mappingAssertions`。若只能取得原始 SQL，仍须保留原文并在 `codeHandoff.unresolved` 标记缺少哪些 fixture/test facts。
- 若 DB / SQL API 缺少权威 schema、最小 seed、测试 DB 连接方式、当前用户/会话来源或必要 fixture 前置条件，spec writer 必须写入 `codeHandoff.unresolved`，不得把该 API 交接成“只需 mock SQL executor 即可完成正式业务验证”。
- 若存在 `.agent/Common/project-hard-constraints.json`，spec writer 必须把当前 API 命中的项目级硬约束折进 `codeHandoff.constraints`，并把来源写进 `codeHandoff.legacyEvidence`
- 若功能专属 `inputs/reference` 或专案规则库 `rules/code-guidelines/**` 下存在 JWT / Redis / Session 生命周期设计文档（如 `JWT_Redis_存储說明`），spec writer 只能把其中与当前 API 直接相关的 Redis key、JWT claim、会话主键、TTL / 续期规则写入 `codeHandoff.constraints` 与 `legacyEvidence`。第 01 步 `.agent/reference/global` 只保存外部 API / DB Schema 索引，不再作为开发规范来源
- 对这类设计文档，spec writer 不得只摘取零散字段名；必须明确区分“当前 API 直接依赖的规则”“跨模块背景规则”“当前仍未落地的前置条件”
- 若设计文档的核心模型依赖登录态主键、统一 session key 或共享 member hash，而当前 API 只消费其中一部分，`codeHandoff.unresolved` 必须显式标注这是“partial adoption risk”，避免 code writer 误把参考文档当成已完整接线的现状
- 若 handoff 涉及 Header 候选键扫描、Header / Redis fallback、字符串长度计算等实现细节，spec writer 应区分“可抽成共用解析模式”与“保留在业务层的具体规则”，避免 code writer 把业务常量和通用算法一起下沉到 `CommonStatic`
- 若当前 API 依赖“当前用户 / 当前会话 / 当前 CustId”这类运行时身份上下文，spec writer 必须在 `codeHandoff.constraints` 中显式写出身份来源、认证前提、claims / headers / Redis keys、session scope 与允许的 fallback；缺任一项都必须写入 `codeHandoff.unresolved`
- spec writer 不得把 `CurrentRuntimeContextAccessor` 一类基础设施当作当然存在；若仓库现状与参考设计文档不一致，必须明确标注“reuse existing context accessor”还是“identity model blocked”，而不是留给 code writer 自行脑补
- 若当前 API 涉及 Redis / Memory / 本地缓存，spec writer 必须在 `codeHandoff.constraints` 中显式区分 `authoritativeStore` 与 `cacheRole`，并写清 TTL、失效策略、空值处理、刷新策略、允许的 stale-read 范围；缺项时必须写入 `codeHandoff.unresolved`
- 若业务判定同时依赖数据库与缓存，spec writer 必须明确写出“重复判断/存在性判断/写后刷新”应以哪一个事实源为准；不得把 DB 与缓存都列出来却不说明优先级
- 按系统设计规范 v2.5 的 `数据检索顺序`，涉及资料读取或运算时必须交接 `dataRetrievalOrder` 或同等说明：优先从哪里取资料、何时可读 Redis/Memory cache、何时必须回权威 DB/API/BackendAPI、缓存未命中或资料不一致时如何处理；缺少顺序时写入 `codeHandoff.unresolved`
- 按系统设计规范 v2.5，Redis key 设计必须说明是简易模式共享 Hash/Member 生命周期，还是进阶模式自定义 Key；自定义 Key 只能使用 `[A-Za-z0-9]`、`_`、`:`，不得包含空格、换行、百分号等特殊字符，且不得把身份证号、完整卡号、密码等敏感资料放进 key
- Appsetting 交接必须使用 `appsettings.{Environment}.json` 形式，配置 Section/Key 使用 PascalCase 与层级化 JSON；第三方服务配置若接口数量超过 50 个，应标记是否需要独立配置文件。缺少目标环境、配置归属或文件拆分依据时写入 `codeHandoff.unresolved`
- DB 设计交接必须保留命名意图：表名/栏位名 PascalCase，stored procedure 使用 `sp_` 前缀，view 使用 `vw_` 前缀；若现有 DB 来源不符合，记录为 legacy evidence，不把旧名当作新设计命名依据
- 若 handoff 涉及缓存读优化，spec writer 应同时给出最小测试意图：缓存命中、缓存未命中、缓存与权威数据不一致、权威数据为空、写后刷新或失效
- 若请求字段存在基础输入约束，spec writer 必须优先判断其是否应落在 DTO 特性，并在 `codeHandoff.constraints` 中显式写出：
  - `field`
  - `validationLayer(dto_attribute|service_business|unresolved)`
  - `validationType`
  - `expectedCode`
  - `expectedMessage`
  - `customValidationAttributeNeeded`
- 对可由 DTO 特性承载的单字段规则，例如必填、长度、格式、枚举范围，spec writer 必须标注为 `dto_attribute`；不得默认把这些规则留给 service
- 对“最多 N 个文字元素”这类标准 DataAnnotations 无法准确表达的单字段规则，spec writer 必须显式标注需要公共自定义 `ValidationAttribute`，不能模糊写成“长度校验”
- 若 spec、Excel 或项目约束中存在响应码目录，spec writer 必须先区分哪些属于“公共 response catalog”，哪些属于“模块私有 response catalog”，并把这个归属写进 `codeHandoff.constraints`；不得只抄 code/message 字面值而不说明所有权
- 对响应码交接，spec writer 必须优先输出“成对定义 + catalog 归属”的实现意图，而不是暗示 code writer 在 `TransactionResults.Success(...)` / `Failure(...)` 现场写字面值；若当前仓库缺少对应 catalog，也必须在 handoff 中明确标注是“复用缺口”还是“需新增模块私有 definition”
- 若 spec 只有文案没有错误码，或给了错误码/文案但当前仓库只有通用 `ValidateModelStateFilter`，spec writer 必须把它标注为公共验证基础设施差口，而不是暗示 code writer 在 service 层补重复判断
- 若 handoff 涉及请求参数校验，spec writer 应同时给出最小测试意图：DTO 特性命中、自定义文字元素长度、多字节字符行为、service 仅保留业务/上下文校验

## 高风险交接规则

以下场景 spec writer 必须直接写入 `codeHandoff.unresolved`，不得模糊交接：

1. 当前用户身份依赖 JWT / Session / Redis，但文档未说明字段来源、认证前提或 session scope
2. 参考设计文档是目标态，而仓库现状只落地了局部 key / 局部 helper
3. 业务同时依赖 DB 与缓存，但未定义 authoritative store
4. 要求新增共用基础设施，但没有说明复用范围或现有相似模式
5. 需要缓存、身份上下文或会话模型相关测试，但未提供最小测试意图
6. 字段校验规则存在，但未说明应落 DTO 特性还是 service，或未给 spec 错误码/文案映射方式

对上述场景，spec writer 必须显式写出：
- `blockedReason`
- `missingFacts`
- `suggestedOwner`（spec / framework / upstream auth）
- `nextDecisionNeeded`

## 资源

- `scripts/runtime.py`
- `scripts/write_api_spec.py`
- `scripts/reference_support.py`
- `schemas/api-spec.schema.json`
- `schemas/manifest.schema.json`
- `schemas/project-hard-constraints.schema.json`
