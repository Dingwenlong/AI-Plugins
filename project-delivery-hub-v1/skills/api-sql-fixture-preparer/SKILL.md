---
name: api-sql-fixture-preparer
description: 为依赖 SQL 的 API 按 `.agent` 私有 SQL Server 目标配置准备表结构与最小测试数据。可选第 03 步：读取 `*_API_Spec.json` 与 `codeHandoff.queryContracts`，识别 SQL 表依赖，检查或补齐 schema/seed；无权威 schema、连接或安全边界不清时阻塞，供第 04 步接续执行。关键词：SQL fixture、queryContracts、schema、seed、fixtureStatus。
---

# 【开发落地】SQL 测试资料准备器

使用这个可选第 03 步技能在目标项目的 `.agent/context` 下补一层独立的 SQL fixture 准备执行面。它的职责不是生成 spec，也不是修改业务代码，而是判断当前 API 是否依赖 SQL 表，并按 `.agent/config/sql-fixture-targets.local.json` 指定的 SQL Server fixture 目标准备最小可运行的表结构与测试数据，供第 04 步 [$api-code-writer](<pluginRoot>/skills/api-code-writer/SKILL.md) 后续 build、test、integration test 使用。推荐链路是先 01，再 02，再 03（如需），再 04，最后 05（如需）。

默认优先解析插件本地 `references/local-workspaces.json`，可按 `workspaceKey` 指向对应集中 `.agent`。`project-root` 仍是实际代码分支目录，`agent-root` 是共享链路资料库。参数优先级为 `--agent-root/--workspace-root` > 环境变量 > 插件本地配置 > 旧逻辑 `<project-root>\.agent`。

SQL fixture 的专案默认值从规则库读取：`--rules-root` > `PROJECT_RULES_ROOT` / 专案环境变量 > `references/local-workspaces.json.rulesRoot` > `<agentRoot>/project-rules/<workspaceKey>`。若 `<rulesRoot>/catalog.json` 指向 `rules/sql-fixture/defaults.json`，本技能使用其中的默认数据库、环境标签与 sample literal。找不到规则库时只执行通用 fixture 判断，并把专案默认 DB/seed 规则缺口写入阻塞原因；不得从插件内旧个案 reference 偷读默认数据库名。

## SQL 连接目标配置

第 03 步默认只从共享 `.agent` 的私有配置读取数据库目标：

- 配置文件固定为 `.agent/config/sql-fixture-targets.local.json`
- 支持字段：`defaultTarget`、`targets.<name>.provider=sqlserver`、`environment`、`connectionString`、`targetDatabase`、`allowCreateTable`、`allowSeed`
- `connectionString` 可以是完整 SQL Server 连接串，但属于本机/项目私有配置；不得写入插件源码、交付包、打包产物、报告或聊天回报
- `targetDatabase` 必须匹配专案规则库 `rules/sql-fixture/defaults.json.defaultSqlServerDatabase` 或显式允许库；NEWDAWHO 当前目标库为 `DAWHO`
- 连接串中的 `Initial Catalog` 只用于连接来源，不决定建表/seed 目标库
- 缺少配置时，SQL 依赖 API 必须阻塞为 `missing_db_target`
- `sqlite:///...` 目标已禁用，传入时必须阻塞为 `sqlite_target_disabled`，不得创建本地 `.sqlite` 文件
- `--db-target` 仅可用于选择 `.agent` 已配置目标，例如 `agent-config:develop`；不得直接传完整连接串、appsettings connection name 或 SQLite 路径来绕过 `.agent` 私有配置

## 规则包启动检查

正式第 03 步判断 SQL fixture、补 schema 或 seed 前，必须先解析 `sqlFixture` 规则包：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack sqlFixture `
  --workspace-key "<workspaceKey>"
```

若用户明确给出规则库，改传 `--rules-root "<rulesRoot>"`。脚本输出的 `sql-fixture-defaults` 是默认数据库、环境标签与 sample literal 的唯一专案来源；`status=blocked` 时，不得猜测数据库名或 seed 规则，必须回写阻塞原因或要求用户提供 fixture 目标。

`api-sql-fixture-preparer` 的责任边界固定为：

1. 读取共享 `execution-state.json`、`api-checklist.json`、API 级 `manifest.json` 与 `*_API_Spec.json`
2. 优先消费 `codeHandoff.queryContracts`、`constraints`、`unresolved`，兼容旧 spec 的 `businessLogic.sqlSpecs` / `backendApis`
3. 识别当前 API 是否存在 SQL fixture 需求
4. 按 `.agent/config/sql-fixture-targets.local.json` 检查 SQL Server fixture 目标是否已存在目标表与最小测试数据
5. 只有在存在权威 schema 来源时才允许创建表
6. 对缺失数据执行幂等 seed；重复运行不能造成脏数据膨胀
7. 只更新共享状态中的 `fixture*` 字段，保留 `spec*` 与 `code*` 历史

它不是通用 migration 工具，也不是 DBA 替代品。若缺少 schema、连接、权限或环境边界不清，必须直接阻塞。

## 工作流契约

这个可选第 03 步技能不绑定固定前置步骤名称。只要共享 `.agent/context` 中已经存在 `specStatus=done`、`manifest.json` 与 `*_API_Spec.json`，就可以在第 02 步之后、或第 04 步 `apply` 前按需进入 fixture 准备；不要求调用者必须先显式经过某个特定命名的上游 workflow / skill。

本技能不是进入 [`api-code-writer`](<pluginRoot>/skills/api-code-writer/SKILL.md) 的硬前提。默认允许 code writer 先执行 `prepare` 与 AI 改码；只有当目标 API 的 `apply` / 验证阶段确实依赖 SQL fixture，且 `fixtureStatus` 仍非 `done|skipped` 时，才需要先补执行本技能。

只有当 `fixtureStatus=done|skipped` 时，依赖 SQL fixture 的 code writer `apply` 才应继续推进。

## 默认使用方式

1. 先调用 `scripts/prepare_sql_fixture.py --execution-mode prepare`
2. 默认读取集中 `.agent/context/execution-batch.json`；未配置集中 `.agent` 时回退 `<project-root>/.agent/context/execution-batch.json`
3. 默认读取 `.agent/config/sql-fixture-targets.local.json` 的 `defaultTarget`；需要切换目标时只允许 `--db-target agent-config:<targetName>`
4. 默认落到 `.agent/context/<functionCode>/`
5. 若未指定 `--api-id`，一次只推进一支 `specStatus=done` 且 `fixtureStatus` eligible 的 API
6. 读取 `*_API_Spec.json` 后，先判断是否存在 SQL fixture 需求
7. 若存在 SQL fixture 需求，再解析 schema authority、表存在性与 seed 需求
8. 若允许执行，再调用 `scripts/prepare_sql_fixture.py --execution-mode apply`
9. 每次运行结束后，必须读取共享 `execution-state.json` 与 `api-checklist.json` 汇报结果

## SQL 识别规则

按以下优先级判断当前 API 是否存在 SQL fixture 需求：

1. `codeHandoff.queryContracts`
2. `codeHandoff.constraints` 中显式声明的 DB fixture 约束
3. `businessLogic.sqlSpecs`
4. `backendApis` 中指向数据库表或 schema 的条目

满足以下任一条件视为“需要 SQL fixture”：

- 存在明确 SQL 查询契约
- 存在 `FROM` / `JOIN` / `INSERT INTO` / `UPDATE` 指向的表
- code handoff 明确要求本地或测试库准备表数据

若只有外部 API、Redis、Header、JWT 等依赖，没有数据库表依赖，则应直接回写 `fixtureStatus=skipped`。

## 权威来源规则

创建表前必须先找到权威 schema。可接受来源仅限：

1. `.agent/reference/global` 或功能专属 inputs/reference 已导入的 DB schema / DDL / catalog / index；legacy `.agent/Reference` 仅作兼容读取来源
2. 仓库现有 migration、建表 SQL、初始化脚本
3. handoff 中明确给出的建表脚本或 schema 文件

以下情况一律禁止自动创建表：

- 只有 SELECT SQL，没有任何权威表结构定义
- 只能从业务 SQL 反推字段名和型别
- 连接到的数据库环境不是显式标记的 local/test fixture 库

此时必须阻塞，并写入 `fixtureBlockReason=missing_schema_authority`。

## 环境规则

此技能只允许操作 `.agent/config/sql-fixture-targets.local.json` 中明确配置的 SQL Server fixture 目标。`environment` 必须标记为 `local`、`test`、`fixture`、`sandbox`、`integration` 或 `develop`。

禁止默认操作：

- 正式库
- UAT / SIT / Staging，除非当前 skill 配置明确允许
- 无环境标签的共享数据库

若无法证明当前连接来自 `.agent` 私有配置，或 `targetDatabase` 不符合专案规则默认/允许库，必须阻塞，并写入 `fixtureBlockReason=unsafe_database_target`。

## 表规则

对每个解析出的目标表，必须执行以下检查：

1. 表是否存在
2. 若存在，结构是否符合权威 schema 的最小要求
3. 若结构不符，是否允许由初始化脚本修复
4. 若存在且结构可接受，是否已有当前 API 所需最小数据

若表不存在：

- 有权威 schema：允许创建
- 无权威 schema：阻塞
- 若 SQL 只写到 `dbo.Table` 或裸表名、未声明所属数据库，默认数据库必须来自专案规则库 `sql-fixture/defaults.json`；缺少该规则时不得猜测数据库名，必须阻塞或要求用户提供目标 fixture DB。

若表已存在但空表：

- 允许按 seed plan 补最小测试数据

若表已存在且有数据：

- 必须进一步检查这些数据是否覆盖当前 API 的 where/join/filter 场景
- 若不足，则补充最小 seed
- 若已满足，不重复插入

## 测试资料填充规则

seed 必须满足以下要求：

1. 幂等：重复执行不能不断累积重复数据
2. 最小：只补当前 API 能跑通所需数据
3. 可追踪：每笔 seed 必须能追踪来源 API
4. 可回放：必须保留生成的 seed SQL 或等价计划

推荐做法：

- 使用业务主键或组合键先查后插
- 为 fixture 数据补 `fixture_api_id`、`fixture_batch_id`、`fixture_source` 等标识字段；若现有表结构不允许新增字段，则在外部 manifest 记录 seed 身份
- 避免用随机值；同一 API 的 seed 默认稳定可复现

若当前表是既有业务表，不能新增跟踪字段时，必须在 `seed-manifest.json` 中记录：

- `table`
- `primaryKey`
- `insertedKeys`
- `apiId`
- `seedReason`

## 共享状态

执行面需要新增以下聚合字段：

- `fixtureStatus`
- `fixturePhase`
- `fixtureUpdatedAt`
- `fixtureCurrentApiId`
- `fixtureSummary`
- `fixtureLastMessage`

每个 checklist item 需要新增：

- `fixtureStatus`
- `fixturePhase`
- `fixtureBlockReason`

每个 API manifest 需要新增：

- `fixtureStatus`
- `fixturePhase`
- `fixtureUpdatedAt`
- `fixtureBlockReason`
- `fixtureArtifacts`

推荐状态值：

- `pending`
- `in_progress`
- `done`
- `skipped`
- `blocked`
- `error`

## API 级产物

每支 API 默认落在：

- `.agent/context/<functionCode>/apis/<apiId>/db-fixture-report.json`
- `.agent/context/<functionCode>/apis/<apiId>/table-checks.json`
- `.agent/context/<functionCode>/apis/<apiId>/seed-plan.sql`
- `.agent/context/<functionCode>/apis/<apiId>/seed-executed.sql`
- `.agent/context/<functionCode>/apis/<apiId>/seed-manifest.json`

其中：

- `db-fixture-report.json` 记录总结果、阻塞原因、目标环境、schema authority 与执行摘要
- `table-checks.json` 记录每张表的存在性、结构判定、数据判定
- `seed-plan.sql` 记录计划执行的 SQL
- `seed-executed.sql` 记录实际执行过的 SQL
- `seed-manifest.json` 记录插入键值、来源 API、批次与幂等追踪信息

## Prepare 输出要求

`prepare` 阶段至少要写出：

- 是否检测到 SQL fixture 需求
- 目标数据库环境识别结果
- schema authority 来源
- 目标表列表
- 每张表的判定动作：
  - `reuse`
  - `create`
  - `seed`
  - `seed_more`
  - `blocked`
  - `skip`

若阻塞，必须明确：

- `blockedReason`
- `missingFacts`
- `unsafeTarget`
- `requiredAuthority`

## Apply 输出要求

`apply` 阶段只允许执行 `prepare` 已明确批准的动作：

- 建表
- 幂等 seed
- 报告落盘
- 状态回写

不得在 `apply` 时临时扩大范围，例如：

- 新增未在 plan 中出现的表
- 更换数据库目标
- 推断 schema
- 大批量导入无关测试数据

## 完成规则

- 只消费共享 `.agent/context`
- 只更新共享状态中的 `fixture*` 字段
- 本技能不限制固定前置步骤名称；只认共享 `.agent/context` 产物是否齐备
- 若 `specSourceFingerprint` 变化，必须把对应 API 的 `fixtureStatus` / `fixturePhase` 回退为 `pending`
- `fixtureStatus=done` 只表示 fixture 就绪，不代表代码通过
- `fixtureStatus=skipped` 只用于确认当前 API 不依赖 SQL fixture
- 无论最终结果是 `done`、`skipped`、`blocked` 或 `error`，都表示本技能已经实际执行过一次；其中只有 `done|skipped` 允许依赖 SQL fixture 的 code writer `apply` 继续
- 若目标库被判定为非 local/test，必须阻塞，不允许继续
- 若缺少权威 schema，必须阻塞，不允许从查询 SQL 脑补建表
- 若表已存在但数据不足，允许补最小 seed
- 若表已存在且数据已覆盖当前 API 场景，必须复用，不重复灌数

## 高风险阻塞项

以下场景必须阻塞：

1. 只有查询 SQL，没有 schema authority
2. 数据库连接目标无法证明为 local/test fixture 环境
3. 表结构与权威 schema 冲突，但没有受控修复脚本
4. 无法判定最小 seed 的主键或幂等策略
5. 当前 API 依赖多表 join，但 spec / handoff 未说明最小数据覆盖面
6. 目标表为共享业务表，seed 会污染其它 API 场景，但缺少隔离策略

阻塞时至少输出：

- `fixtureBlockReason`
- `missingFacts`
- `authorityGap`
- `environmentRisk`
- `nextDecisionNeeded`

## 建议命令

```powershell
python ".\scripts\prepare_sql_fixture.py" `
  --project-root "D:\Repo\Project" `
  --solution-path "D:\Repo\Project\App.sln" `
  --execution-mode "prepare"
```

```powershell
python ".\scripts\prepare_sql_fixture.py" `
  --project-root "D:\Repo\Project" `
  --solution-path "D:\Repo\Project\App.sln" `
  --function-code "N.006" `
  --api-id "N.006.setting.queryuserloginlog" `
  --execution-mode "apply"
```

## 建议输入参数

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
- `--db-target`（仅支持 `agent-config:<targetName>`；不传时使用 `.agent/config/sql-fixture-targets.local.json.defaultTarget`）
- `--schema-authority-root`
- `--allow-create-table`
- `--allow-seed`

## 资源

- `scripts/prepare_sql_fixture.py`
- `scripts/runtime.py`
- `schemas/db-fixture-report.schema.json`
- `schemas/table-checks.schema.json`
- `schemas/seed-manifest.schema.json`

## Leader Mode

当由 `multi-api-leader` 显式编排时：

- 03 SQL fixture 的状态写入由 leader 串行完成。
- 子 agent 只能只读检查 schema、seed、queryContracts 与 SQL 安全边界。
- 无权威 schema、连接信息或安全边界不清时必须阻塞，不能让 worker 自行补写 fixture 状态。
- `fixtureStatus` 必须由 leader 最终标记为 `done`、`skipped` 或 `not_required` 后，第 04 步才可继续。
