---
name: api-code-writer
description: 把已完成的 API Spec 落成 .NET 业务代码。第 04 步：在已绑定唯一 `.sln` 的工作区读取共享 `.agent/context/{functionCode}/`、`*_API_Spec.json` 与 `codeHandoff`，实现 Controller / Service / Entity 等业务代码并交接测试计划；不生成 UnitTest / IntegrationTest 测试源码。关键词：Controller、Service、Entity、change-plan、codeStatus。
---

# 【开发落地】API 业务代码写入器

使用这个第 04 步技能在目标项目的 `.agent/context` 下恢复或推进业务代码写入链路。脚本会先读取共享的 `execution-state.json`、`api-checklist.json` 与 API 级 `manifest.json`，只更新 `code*` 字段并保留 `spec*` 状态。读取 `*_API_Spec.json` 时，优先消费结构化 `codeHandoff`；若旧 spec 尚未升级，则会从 `businessLogic` 临时合成兼容 handoff。若 API 目录下存在 `review-notes.json`，也必须一并读取，并将评审意见转换成 `change-plan.json.analysis` 可执行约束；若缺少 `review-notes.json` 但 `.agent/Common/project-hard-constraints.json` 存在，`prepare` 必须即时按当前 API 条件合成 fallback review 约束。推荐链路：先 01 设计梳理 → 02 规格 →（如需）03 SQL fixture → 04 代码 →（如需）05 测试报告；『参考资料索引导入』为可选资料准备，按需在 02/03 前补做。

## 工作区与规则解析

默认优先解析插件本地 `references/local-workspaces.json`，可按 `workspaceKey` 指向对应集中 `.agent`。`project-root` 仍是实际代码分支目录，例如 `D:\Repo\Project\feature_common\P240301Git`；`agent-root` 是共享链路资料库。参数优先级为 `--agent-root/--workspace-root` > 环境变量 > 插件本地配置 > 旧逻辑 `<project-root>\.agent`。

专案规则读取与代码仓库分离，rulesRoot 优先级为：`--rules-root` > `PROJECT_RULES_ROOT` / 专案环境变量 > `references/local-workspaces.json.rulesRoot` > `<agentRoot>/project-rules/<workspaceKey>`。

## 规则包启动检查

正式第 04 步 `prepare` 前，必须先解析 `apiCodeWriter` 规则包：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack apiCodeWriter `
  --workspace-key "<workspaceKey>"
```

若用户明确给出规则库，改传 `--rules-root "<rulesRoot>"`。脚本输出的开发规范规则是生成 `change-plan.json` 前的硬输入；`status=blocked` 时，`prepare` 必须写入 `change-plan.json.analysis.devGuidelineGaps` / `unresolvedLogic` 并停止进入正式落码，不得凭可选『参考资料索引导入器』（资料准备旁路）的 reference、插件内旧 reference 或记忆补齐专案规范。

`scripts/write_api_code.py` 与 `scripts/materialize_review_notes.py` 依赖 Python `jsonschema` 进行 schema 校验。运行时若缺少该依赖，脚本会先以 dependency preflight 失败并提示安装方式；不得绕过 schema 校验继续写状态。

## 开发规范的加载（规范不在本文件内联）

本技能**不复述**具体编码规范。所有 .NET 落码细则、专案专用落点、命名/注释/校验/缓存/身份/数据访问/测试交接规则，统一从 `<rulesRoot>/catalog.json` 的 `codeGuidelineCatalog`（如 `rules/code-guidelines/<pack>/catalog.json`）按需加载：

- **专案专用**（EnterpriseAPI 框架槽位、NEWDAWHO `CommonFunc`/`CommonUtil` 落点、`Sinopac.*` 路径、固定验证命令）→ `rules/implementation-profile.md`
- **通用 .NET / C# 规范**（共享抽象、风格、注释、DTO 校验、缓存、身份/会话、数据访问、日志、配置、测试交接）→ `common-style.md`、`validation.md`、`cache.md`、`data-access.md`、`frontstage-session.md`、`backoffice-authz.md`、`logging-exception.md`、`config.md`、`test-handoff.md`

加载约束（渐进式披露）：

- `prepare` 必须先读取规则库 catalog 的 `codeGuidelineCatalog`，根据 `API_Spec.json.source`、`codeHandoff`、`backendApis`、`runtimeDependencies`、TSD/API 名称、`apiCategory`、route/controller/module、identity/role/cache/DB 线索判断 `audienceProfile.scope = frontstage | midBackoffice | shared | unknown`，再只把命中的 `rules/*.md|json` 写入 `devGuidelineLoadHints`。
- **不得整本加载**规范，不得仅凭项目名判定前台/中后台；目标态规范也不能替代当前仓库接线事实。命中前台/中后台专属规范但 handoff/仓库证据不足时，写入 `devGuidelineGaps` 并阻塞。
- 开发规范**只能**来自 rulesRoot。不得从可选『参考资料索引导入器』（资料准备旁路）维护的 `.agent/reference/global`、技能内 `references/dev-guidelines/**`（仅历史回归 fixture）或记忆里偷读默认规范。找不到规则库时，只允许执行通用 code writer 流程，并把缺口写入 `change-plan.json.analysis.devGuidelineGaps` / `unresolvedLogic`。

## 职责边界

第 04 步只实现或修改业务运行代码，并把测试情景、`unitTestTargetFiles`、`integrationTestTargetFiles`、SQL fixture 需求与 Service runtime validation 计划写入 `change-plan.json.analysis.testCodeHandoff` / handoff artifact。**不得新增、改写或补齐 UnitTest / IntegrationTest / Service runtime validation 测试源码**；这些统一由第 05 步 `skills/docx-unittest-report/SKILL.md` 生成、维护、执行并纳入 UT 测报。

这个技能不绑定固定前置步骤名称：只要共享 `.agent/context` 中已存在可消费的 `spec*` 状态、`manifest.json` 与 `*_API_Spec.json`，即可直接进入 code writer，不要求先显式经过某个特定命名的上游 workflow / skill，也不强制先执行 `skills/api-sql-fixture-preparer/SKILL.md`。——本链路按**产物就绪驱动**，而非调用顺序驱动；『推荐链路』只是常见顺序，实际放行以共享 `.agent/context` 产物是否齐备为准。03 SQL fixture 的「何时必需 / 何时可跳过 / 与 04 门禁关系」以 `skills/api-sql-fixture-preparer/SKILL.md` 的「何时需要 03 / 何时可跳过」权威小节为准，本文件不再各自重述。

## AI 编排运行时（prepare / confirm / apply）

`api-code-writer` 是 **AI 编排运行时**，不是 deterministic code generator：

1. `prepare` 只负责共享状态整理、依赖解析、计划产出与状态回写，并内建 precheck（直接解析目标仓库框架槽位、模块落点、依赖、风险与验证命令），不依赖外部 precheck skill。
2. `prepare` 必须同时生成三层落码范本：项目结构、代码文件、文件内方法（`implementation-template.md` + 机器锁 `implementation-template.json`）；确认前 AI 不得修改目标仓库业务代码。用户只改 Markdown，不手改同目录 JSON。
3. 用户确认或修改范本后运行 `--execution-mode confirm`，脚本记录 Markdown hash；确认后若 Markdown 再被修改，`apply` 必须以 `template_modified_after_confirmation` 阻塞。
4. `confirm` 通过后，AI 才能依据已确认的 `implementation-template.md`、`change-plan.json`、`*_API_Spec.json`、框架说明与示例项目，直接修改目标仓库业务代码。
5. `apply` 只接受 AI 已落盘的真实改动，负责检测修改文件、执行验证、产出报告并回写状态；未确认范本或未检测到真实改动时必须阻塞。
6. 脚本不得把 `queryContracts / mappingRules / legacyEvidence` 渲染成注释式 stub 代码；脚本与 AI 都不得在第 04 步产出测试源码。

`confirm` 锁定的只是 `implementation-template.md` 的实现结构（脚本只对该 Markdown 取 sha256），**不锁** `change-plan.json` 里的测试契约字段。`change-plan.json.analysis` 中的测试契约字段（`mockExamples`、`testScenarioPlan`、`testScenarioCoverageRequired` 等）仍是第 05 步 [`docx-unittest-report`](<pluginRoot>/skills/docx-unittest-report/SKILL.md) 的权威来源。因此：若用户对范本的修改改变了测试相关情景/契约（例如新增/调整范例情景、改变期望响应码或覆盖要求），**必须重跑 `prepare` 让 `change-plan.json` 同步**，不得只 `confirm` 范本就 `apply`；否则 05 会基于过期 `change-plan` 生成测试。`confirm` 通过且范本未再改动只代表实现结构已确认，不代表 `change-plan` 的测试契约已随范本同步。

落码前必须先完成 `logic resolution`（显式解析 `queryContracts / mappingRules / dependencyHints / legacyEvidence / constraints`）与开发规范选择（先判 `audienceProfile`，再按上节加载命中规则）。具体 EnterpriseAPI / 多项目分层落点与编码细则一律以 rulesRoot 的 `implementation-profile.md` 及通用规则文件为准，本文件不再重复。

## 默认使用方式

1. 先调用 `scripts/write_api_code.py --execution-mode prepare`。
2. 默认读取集中 `.agent/context/execution-batch.json`；未配置集中 `.agent` 时回退 `<project-root>/.agent/context/execution-batch.json`，并落到 `.agent/context/<functionCode>/`。
3. 读取 `implementation-template.md` 让用户确认；用户改范本只改这个 Markdown，不要手改同目录 JSON。
4. 用户确认或改完后调用 `scripts/write_api_code.py --execution-mode confirm`。
5. `confirm` 通过后，AI 按已确认范本直接在目标仓库改真实业务代码；脚本只做 prepare/confirm/apply 编排，不代写 Controller / Service，也不写测试源码。
6. 若目标 API 依赖 SQL fixture 且结果未达 `done|skipped|not_required`，在 `apply` 前补执行 `skills/api-sql-fixture-preparer/SKILL.md`（判定口径见该技能「何时需要 03 / 何时可跳过」权威小节）。
7. 代码改完后调用 `scripts/write_api_code.py --execution-mode apply`。
8. 若未指定 `--api-id`，一次只推进一支 `specStatus=done` 且 `codeStatus` eligible 的 API；`prepare` 不以 `fixtureStatus` 作为入口门槛；`apply` 时 `fixtureStatus` 仍非 `done|skipped|not_required` 则回报 `waiting_fixture`。
9. 每次运行结束后，必须读取共享 `execution-state.json` 与 `api-checklist.json` 向用户汇报结果。
10. 若同目录存在 `review-notes.json`，`prepare` 必须先合并评审约束再生成 `change-plan.json`。

## review-notes 与项目硬约束

若项目采用方案 A，并在 `.agent/Common/project-hard-constraints.json` 维护项目级硬约束，可先运行 `scripts/materialize_review_notes.py`，把项目级规则按 API 粒度展开成 `.agent/context/{functionCode}/apis/{apiId}/review-notes.json`。该脚本先校验 `project-hard-constraints.schema.json`，再按 functionCode / apiCategory / apiName / 业务关键字筛选适用规则。`review-notes.json` 中的 blocking 约束若引用 spec / handoff 不存在的字段，`prepare` 必须以 `review_constraint_gap` 阻塞。

## 第 05 步缺陷回交（test-defect-handoff）

第 05 步 [`docx-unittest-report`](<pluginRoot>/skills/docx-unittest-report/SKILL.md) 发现生产业务代码缺陷时，不会静默改生产码，而是在同一 API 目录写入回交物 `.agent/context/<functionCode>/apis/<apiId>/test-defect-handoff.json`（字段含 `apiId`、`defectSummary`、`failingTests`/`evidencePaths`、`suspectedFiles`、`classification`、`suggestedOwner: "04-api-code-writer"`、`nextDecisionNeeded`、`status`）。

`prepare` 若发现同目录存在 `status=open` 的 `test-defect-handoff.json`：

- 必须把该 API 的 `codeStatus` 视为需返工，回退为 **`pending`**（既有状态，勿造新值），不得沿用上一轮的 `tests_passed`。
- 必须把该缺陷折进 `change-plan.json.analysis` 后再正式落码：可并入 `reviewConstraintsSelected`，或写入新增的 `testDefectFollowups` 字段（保留 `defectSummary`、`suspectedFiles`、`failingTests`、`nextDecisionNeeded` 与来源路径）。
- 落码修复后由用户/leader 把回交物 `status` 改为 `resolved`；`status=open` 期间该 API 不应被判为已完成。

> 说明：`scripts/write_api_code.py` 的 `prepare` 在重算 `codeStatus` 时，对存在 `status=open` 回交物的 API 会强制回退为 `pending`（见 `build_writer_item` 钩子与回归 `tests/run_regressions.py`），避免在 spec 未变、上一轮已 `tests_passed` 的情况下回交闭环被状态保留逻辑破坏。

## 命令行

```powershell
# prepare（生成 change-plan 与三层范本）
python ".\scripts\write_api_code.py" `
  --project-root "D:\Repo\Project" `
  --workspace-key "PROJECT" `
  --solution-path "D:\Repo\Project\App.sln" `
  --execution-mode "prepare"

# 用户审阅 implementation-template.md 后确认范本
python ".\scripts\write_api_code.py" `
  --project-root "D:\Repo\Project" --workspace-key "PROJECT" `
  --solution-path "D:\Repo\Project\App.sln" `
  --function-code "D.006" --api-id "D.006.deposit.addexchangedepositinit" `
  --execution-mode "confirm"

# 可选：展开项目级硬约束为 review-notes
python ".\scripts\materialize_review_notes.py" --project-root "D:\Repo\Project"

# AI 在目标仓库完成真实改码后 apply
python ".\scripts\write_api_code.py" `
  --project-root "D:\Repo\Project" --solution-path "D:\Repo\Project\App.sln" `
  --function-code "D.006" --api-id "D.006.deposit.addexchangedepositinit" `
  --execution-mode "apply"
```

Windows / .NET 工作区若遇到 `obj/refint/*.dll`、`bin/*.dll`、`GenerateDepsFile` 或 `MSB3248` 文件锁，优先使用技能内稳定验证脚本 `scripts/dotnet-stable-verify.ps1`（会先 `dotnet build-server shutdown`，清理 `VBCSCompiler` / `testhost`，传 `-KillDotnet` 时也清理 `dotnet`，并为 `dotnet build` / `dotnet test` 自动补 `-m:1`）：

```powershell
powershell -ExecutionPolicy Bypass `
  -File "<pluginRoot>\skills\api-code-writer\scripts\dotnet-stable-verify.ps1" `
  -ProjectRoot "D:\Repo\Project" -KillDotnet `
  -Command @( 'dotnet build "<csproj>"', 'dotnet test "<unit-csproj>"', 'dotnet test "<integration-csproj>"' )
```

> 各专案的具体 `.csproj` 路径与固定验证命令（例如 NEWDAWHO 的 `Sinopac.DawhoEnterprise/...` build/test 命令）由 rulesRoot 的 `implementation-profile.md` → *Test Handoff And Validation* 提供，本文件不再硬列。

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
- `.agent/context/<functionCode>/apis/<apiId>/test-defect-handoff.json`（第 05 步回交物；`prepare` 读取，`status=open` 时把该 API 回退为 `pending`）

> 计划类产物职责区分：`change-plan.json` 是交给下游（尤其第 05 步）的**数据契约**（`analysis` 内含 mockExamples / testScenarioPlan 等）；`implementation-template.md` 是**人审确认**的三层落码范本（确认后 hash 锁定，再改要重跑 confirm）；`implementation-template.json` 是其机器锁，勿手改；`implementation-report.md` 是 `apply` 后的执行报告。范本只锁实现结构、不锁 `change-plan.json` 的测试契约——范本改动若涉及测试情景，必须重跑 `prepare` 同步 change-plan（见上「AI 编排运行时」）。

## prepare 输出契约（`change-plan.json.analysis` 必须写明）

> 以下是第 04 步交付给下游（尤其第 05 步）的**数据契约**，是技能机制而非编码规范；具体取值规则仍以 rulesRoot 规则文件为准。

- 落点与产物：`frameworkProfile`、`moduleName`、`controllerFile`、`interfaceFile`、`serviceFiles`、`entityFiles`、`codeTargetFiles`、`creationMode`。
- 逻辑解析：`logicSourcesUsed`、`queryContractsSelected`、`mappingRulesSelected`、`legacyEvidenceUsed`、`constraintsApplied`、`unresolvedLogic`。
- 规范选择（渐进式披露）：`audienceProfile`、`devGuidelineProfile`、`devGuidelineRulesSelected`、`devGuidelineLoadHints`、`devGuidelineGaps`。
- 测试交接（仅 handoff，**不写测试源码**）：`unitTestTargetFiles`、`integrationTestTargetFiles`、`testCodeHandoff`；若有 `mockExamples` 还须 `mockExamples`、`testScenarioPlan`、`testScenarioCoverageRequired`、`testScenarioSource`。
- DB/SQL 依赖时额外：`serviceRuntimeValidationPlan`、`sqlFixturePlan`、`realServiceIntegrationTests`、`mockSqlUnitTestsPurpose`（必须限定为范例情景/映射逻辑验证，不得写成 SQL 正确性验证）、`runtimeValidationBlockers`。
- 命中 `review-notes.json` 时额外：`reviewSources`、`reviewConstraintsSelected`、`fileRequirements`、`responseLifecycleRules`、`failureDisposition`、`languagePolicy`、`externalApiName`、`internalAsyncMethod`。
- 命中身份/缓存/校验/JWT-Redis-Session 设计文档时，按 `implementation-profile.md` 要求补写对应的 `identity*` / `cache*` / `requestValidationPlan` / `sessionModel` 等字段（详细字段清单见 rulesRoot 规则文件）。

## 完成 / 回写规则

- 不再读取 `.agent/api-spec-writer` 或 `.agent/api-code-writer`；不再接受 `--upstream-root`。
- 只消费共享 `manifest.json` 的 `spec*` 字段和同目录 `*_API_Spec.json`；只更新 `execution-state.json`、`api-checklist.json`、`manifest.json` 的 `code*` 字段和顶层聚合字段。
- 必须读取并保留共享状态中的 `fixture*` 字段，不得在回写 code 状态时覆盖或清空 SQL fixture 状态。
- `codeHandoff` 优先级高于旧 `businessLogic`；本地相似文件只能补实现风格，不能替代 handoff 缺失的原业务逻辑。
- `repo-snapshot.json` 对比时排除整个 `.agent/`。
- 默认验证策略：显式 `--validation-check` 优先；未提供时按 `implementation-profile.md` 规定执行（默认 API build + 既有 unit/integration 回归，均补 `-m:1`，不以 `--no-build` 为默认）。第 04 步不得为通过验证而新增或修改测试源码。
- `apply` 验证遇 `assembly_locked` / `GenerateDepsFile` / `ref/*.dll` 等**可恢复文件锁**时，做有限次重试与退避（可清理 `dotnet` / `VBCSCompiler` / `testhost` 并 `dotnet build-server shutdown`）；若 build 最终仅因文件锁失败、而同轮 `--no-build` 的 unit/integration 验证均通过，可降级回写 `tests_passed`，但须在 `implementation-report.md` 明确标注。代码编译错误、断言失败、handoff 缺失等非锁类问题不得被重试/降级掩盖。
- handoff 缺失或歧义必须阻塞；诊断须区分 `spec_handoff_gap`、`framework_gap`、`environment_issue`、`code_issue`，写入 `diagnosis-report.json`。

## 高风险阻塞项

以下场景默认属于高风险生成，`prepare` 必须阻塞或标记 `blocked`，不得脑补实现（具体判定与允许来源见 rulesRoot `implementation-profile.md` 的 *Identity, Session, And Cache* / *Request Validation* / *Shared Abstractions*）：

1. **身份模型不清**：`CustId/KeyId/auth_sn/sub` 等来源不明，或未说明是否来自已验证 JWT / 既有认证上下文 / session-scoped Redis。
2. **会话模型不清**：依赖统一 session key / member hash 但仓库未接线；handoff 未说明 adoption 为 `full|partial|blocked`。
3. **缓存事实源不清**：未说明 `authoritativeStore`、DB 与缓存以谁为准、TTL/失效/空值策略。
4. **共用抽象边界不清**：要求新增 `CommonStatic` helper/accessor/executor 但无现成模式或明确复用面。
5. **测试意图不清**：引入身份/缓存/事实源切换但 handoff 未给最小测试覆盖面。
6. **请求校验策略不清**：未说明落在 DTO 特性还是 service、错误码如何映射、是否需要公共自定义 `ValidationAttribute`。

阻塞时最低输出：在 `change-plan.json.analysis` 写明 `blockedReason`；在 `unresolvedLogic` 或 `designDocGaps` 指出缺失字段/规则；诊断优先归类为 `spec_handoff_gap` 或 `framework_gap`，不得继续生成猜测性代码。

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
- 专案规则库 catalog 中的 `codeGuidelineCatalog`（专案专用 `implementation-profile.md` + 通用规则文件）
- 技能内 `references/dev-guidelines/**` 仅保留历史回归 fixture；运行时不得作为 active 开发规范来源
- `tests/run_regressions.py`

## Leader Mode

当由 `multi-api-leader` 显式编排时：

- leader 必须先按 `--api-id` 串行 prepare 全部 API，生成每个 API 的 `change-plan.json`。
- prepare 完成后运行 `skills/multi-api-leader/scripts/orchestrate_multi_api.py --mode plan`，根据 planned files 生成 `api-workgroups.json` 与 `file-claims.json`。
- 文件目标重叠的 API 必须进入同一 workGroup，由同一 worker 串行处理；无重叠 workGroup 才能并行。
- worker 只能修改 `file-claims.json` 分配给自己的代码文件，不能写 `.agent/context`，不能生成 UnitTest/IntegrationTest 测试源码。
- worker 返回的 `modifiedFiles` 必须由 leader 校验无越权后，leader 再串行 apply/验证并写回 `codeStatus`、`testCodeHandoff` 与相关共享状态。
