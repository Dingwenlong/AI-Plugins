# 团队从零开始流程

## 适用前提

默认团队成员手上只有：

- 项目代码
- 他负责的 TSD
- 他负责的接口 Spec Excel
- Common 文件
- 外部 API / DB Schema
- 需要进入 04 的开发规范、框架说明、Redis/JWT/Session 规则文件

默认还没有：

- `.agent` 目录
- 任何技能

## 1. 先安装技能

建议至少安装这些技能：

- `专案需求接口设计梳理`
- `01 Reference Index Importer`
- `02 API Spec Writer`
- `03 Optional SQL Fixture Preparer`
- `04 API Code Writer`
- `05 Optional DOCX UnitTest Report`
- `专案规则分析器`

如果技能是别人直接打包给你，确保它们已经放进：

```text
<pluginRoot>\skills\
```

常见位置示例：

```text
<pluginRoot>\skills\
```

安装完成后，应该至少能看到：

- `<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md`
- `<pluginRoot>\skills\reference-index-importer\SKILL.md`
- `<pluginRoot>\skills\api-spec-writer\SKILL.md`
- `<pluginRoot>\skills\api-sql-fixture-preparer\SKILL.md`
- `<pluginRoot>\skills\api-code-writer\SKILL.md`
- `<pluginRoot>\skills\docx-unittest-report\SKILL.md`
- `<pluginRoot>\skills\project-rule-analyzer\SKILL.md`

推荐顺序是：`专案需求接口设计梳理 -> 可选 01 -> 02 -> 03 Optional -> 专案规则分析器(code-guidelines) -> 04 -> 05 Optional`

## 2. 在项目里建立 `.agent`

在项目根目录下建立这些目录：

```text
.agent\
.agent\functions\
.agent\context\
.agent\reference\
.agent\project-rules\
.agent\status\
```

第一阶段不需要手工建立 `.agent\reference\global` 或 `.agent\functions\<functionCode>`。

原因：

- `.agent\functions\<functionCode>` 会由 `专案需求接口设计梳理` 物化
- `.agent\reference\global` 会由 `$reference-index-importer` 重建
- 如果你先手工把外部文件丢进去，后面重建时可能被覆盖

## 3. 准备业务资料给需求梳理

主链路先从需求梳理开始。你要先准备这些来源文件，让 `专案需求接口设计梳理` 读取并整理：

- PRD
- TSD
- API Detail Excel
- Common 文件
- Response Code 或错误码文件
- DB / Redis / Appsetting 设计文件

这些文件可以继续留在设计工作区或来源目录；不要把它们先手工塞进 `.agent\reference\global`。梳理完成后，技能会把当前功能真正会用到的文件复制到 `.agent\functions\<functionCode>\inputs\`，并生成 `handoff\development-handoff.json`。

## 4. 外部文件不要先放 `.agent\reference\global`

外部 API 与 DB Schema 应该先放在“来源目录”，例如：

- `D:\Refs\ExternalApi`
- `D:\Refs\DbSchema`

这些来源目录里通常只交给 01：

- 外部 API Excel
- DB Schema Excel

然后再交给 `$reference-index-importer` 导入。开发规范、JWT / Redis / Session 说明、框架说明文档不要交给 01，应交给 `$project-rule-analyzer --category code-guidelines` 写入 `.agent\project-rules\<workspaceKey>`。

## 5. 手工确认一次资料是否放对

在开始跑技能前，至少确认：

1. PRD / TSD / API Detail / Common / Response Code 等来源文件能被梳理技能找到
2. 外部 API / DB Schema 都在来源目录里
3. 开发规范已用 `$project-rule-analyzer --category code-guidelines` 转成 active project rules，或确认第 04 步会因缺规则阻塞
4. 项目根目录下还没有错误或过期的 `.agent\reference\global`

## 6. 先用 `专案需求接口设计梳理` 生成开发输入包

这一步是主链路起点，不是可选项。它的职责是：

- 梳理 PRD / TSD / API Detail / Common / Response Code
- 判断功能是否可进入开发
- 产出功能设计梳理稿
- 把开发会用到的文件复制到 `.agent\functions\<FUNCTION_CODE>\inputs\`
- 生成 `.agent\functions\<FUNCTION_CODE>\handoff\development-handoff.json`

对话模板：

```text
[$api-detail-tsd-sync](<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md)
请梳理 <FUNCTION_CODE> 功能设计，并在可进入开发时物化 handoff
project-root: <PROJECT_ROOT>
workspace-key: <WORKSPACE_KEY>
```

这一步完成后，至少要看到：

- `.agent\functions\<FUNCTION_CODE>\analysis\`
- `.agent\functions\<FUNCTION_CODE>\inputs\`
- `.agent\functions\<FUNCTION_CODE>\handoff\development-handoff.json`

## 7. 可选第 01 步：用 `$reference-index-importer` 建外部参考索引

这一步的职责是：

- 导入外部参考资料
- 生成 `.agent\reference\global\raw`
- 生成 `.agent\reference\global\indexes\*.json`
- 生成 `.agent\reference\global\catalog.json`

对话模板：

```text
[$reference-index-importer](<pluginRoot>\skills\reference-index-importer\SKILL.md)
请重建集中 .agent\reference\global
project-root: <PROJECT_ROOT>
external-api-dir: <EXTERNAL_API_DIR>
db-schema-dir: <DB_SCHEMA_DIR>
```

这一步完成后，项目里应该出现：

- `.agent\reference\global\catalog.json`
- `.agent\reference\global\indexes\external-api-index.json`
- `.agent\reference\global\indexes\db-schema-index.json`

## 8. 第 02 步：再用 `$api-spec-writer` 产出规格文件

第 02 步优先读取第 6 步生成的 `development-handoff.json`，再生成可供开发消费的 `API_Spec.json`。

原因：

- 没有 handoff 时，02 不应该直接回退到旧 `.agent\TSD`
- 如果缺外部 API / DB Schema 索引，才补跑可选第 01 步

对话模板：

```text
[$api-spec-writer](<pluginRoot>\skills\api-spec-writer\SKILL.md) <FUNCTION_CODE>
```

示例：

```text
[$api-spec-writer](<pluginRoot>\skills\api-spec-writer\SKILL.md) D.006
```

这一步 AI 会做的事：

1. 读取 `.agent\functions\<FUNCTION_CODE>\handoff\development-handoff.json`
2. 读取 `.agent\functions\<FUNCTION_CODE>\inputs\`
3. 按需读取 `.agent\reference\global` 的外部 API / DB Schema 索引
4. 生成 `*_API_Spec.json`
5. 把可用于开发的约束、映射、依赖、旧逻辑证据写进 `codeHandoff`

产物位置通常会在：

```text
.agent\context\<FUNCTION_CODE>\
.agent\context\<FUNCTION_CODE>\api-checklist.json
.agent\context\<FUNCTION_CODE>\execution-state.json
.agent\context\<FUNCTION_CODE>\apis\<API_ID>\manifest.json
.agent\context\<FUNCTION_CODE>\apis\<API_ID>\<FUNCTION_CODE>_<VERSION>_API_Spec.json
```

如果同一份 TSD 里有多支 API，AI 会继续推进，直到：

- `specStatus=done`
- 或出现 `blocked`

## 9. 可选第 03 步：如需 SQL fixture，用 `$api-sql-fixture-preparer`

如果当前 API 需要本地或测试库中的 SQL fixture，先补跑这一步：

```text
[$api-sql-fixture-preparer](<pluginRoot>\skills\api-sql-fixture-preparer\SKILL.md) <FUNCTION_CODE>
```

这一步的目标是：

1. 判断当前 API 是否真的需要 SQL fixture
2. 若需要，则准备或复用本地 / 测试数据库中的表与最小测试数据
3. 回写 `fixtureStatus`

如果当前 API 不依赖数据库表，这一步通常会回写 `skipped`。

## 10. 第 04 步：规格完成后，用 `$api-code-writer` 产出代码

进入第 04 步前，若当前专案还没有 active 开发规范规则，先用 `$project-rule-analyzer --category code-guidelines --approve` 把开发规范接入 `.agent\project-rules\<workspaceKey>`。第 04 步不再从 01 的 `.agent\reference\global` 读取开发规范。

对话模板：

```text
[$api-code-writer](<pluginRoot>\skills\api-code-writer\SKILL.md) <FUNCTION_CODE>
```

示例：

```text
[$api-code-writer](<pluginRoot>\skills\api-code-writer\SKILL.md) D.006
```

这一步 AI 会做的事：

1. 读取 `.agent\context\<FUNCTION_CODE>` 下的共享状态
2. 读取已经完成的 `*_API_Spec.json`
3. 按 spec 的 `codeHandoff` 落代码
4. 修改 Controller / Interface / Service / Entity / Test
5. 跑 build
6. 跑 unit test
7. 跑 integration test
8. 回写 code 状态

你要看的关键结果通常是：

- `.agent\context\<FUNCTION_CODE>\execution-state.json`
- `.agent\context\<FUNCTION_CODE>\api-checklist.json`
- `.agent\context\<FUNCTION_CODE>\apis\<API_ID>\implementation-report.md`

## 11. 可选第 05 步：最后用 `$docx-unittest-report` 产出 UT 报告

这一步产出的是：

- 单元测试 / UT 测试报告 docx

不是：

- API spec 文件

对话模板：

```text
[$docx-unittest-report](<pluginRoot>\skills\docx-unittest-report\SKILL.md) <UT_REPORT_DOCX>
```

示例：

```text
[$docx-unittest-report](<pluginRoot>\skills\docx-unittest-report\SKILL.md) D:\Repo\Project\docs\D.006_UT_Report.docx
```

## 12. 一句话版本

正确顺序就是：

1. 安装技能
2. 建 `.agent` 基础目录
3. 准备 PRD / TSD / API Detail / Common / Response Code 等来源文件
4. 先跑 `专案需求接口设计梳理`，生成 `.agent\functions\<FUNCTION_CODE>\handoff`
5. 如需外部 API / DB Schema 索引，跑 `$reference-index-importer`
6. 跑 `$api-spec-writer`
7. 如需 SQL fixture，跑 `$api-sql-fixture-preparer`
8. 如需开发规范，先跑 `$project-rule-analyzer --category code-guidelines --approve`
9. 跑 `$api-code-writer`
10. 如需正式 UT 报告，跑 `$docx-unittest-report`

## 13. 最容易搞错的点

### 错法 1

先手工把外部文件丢进 `.agent\reference\global`

改法：

先放来源目录，再让 `$reference-index-importer` 导入

### 错法 2

跳过需求梳理，直接跑 02 或 04

改法：

先跑 `专案需求接口设计梳理`，生成 `.agent\functions\<FUNCTION_CODE>\handoff\development-handoff.json`，再进入 02

### 错法 3

把最后一步理解成“再产一次 spec 文件”

改法：

`$docx-unittest-report` 产出的是 UT 报告 docx
