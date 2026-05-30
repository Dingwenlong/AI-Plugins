# 团队端到端命令模板

## 使用前提

默认你已经完成：

1. 技能安装
2. 集中 `.agent` 已可写入
3. PRD / TSD / API Detail / Common / Response Code 等来源文件可被梳理技能找到
4. 外部 API / DB Schema 还在来源目录，尚未手工放进 `.agent\reference\global`
5. 开发规范、框架说明、Redis/JWT/Session 规则文件已准备给 `$project-rule-analyzer --category code-guidelines`

详细说明见：

- `team-onboarding-workflow.md`

## 先替换这些变量

- `<pluginRoot>`：当前已安装插件根目录，目录下应包含 `.codex-plugin\plugin.json`
- `<PROJECT_ROOT>`：项目根目录
- `<WORKSPACE_KEY>`：集中 `.agent` 的工作区 key，例如 `PROJECT`
- `<EXTERNAL_API_DIR>`：外部 API 资料目录
- `<DB_SCHEMA_DIR>`：DB Schema 资料目录
- `<CODE_GUIDE_1>`、`<CODE_GUIDE_2>`：开发规范、框架说明或 Redis/JWT/Session 规则文件
- `<FUNCTION_CODE>`：功能编号，例如 `D.006`
- `<SQL_FIXTURE_SKILL_PATH>`：`api-sql-fixture-preparer` 的 `SKILL.md` 路径
- `<UT_REPORT_DOCX>`：UT 报告 docx 路径
- `<DOCX_UT_REPORT_SKILL_PATH>`：`docx-unittest-report` 的 `SKILL.md` 路径

## 推荐顺序

先 01 设计梳理（`专案需求接口设计梳理`）→ 02 API Spec Writer → 03 Optional SQL Fixture Preparer → Project Rule Analyzer(code-guidelines) → 04 API Code Writer → 05 Optional DOCX UnitTest Report；可选『参考资料索引导入器』（资料准备旁路）按需在 02/03 前补做

## 0. 专案需求接口设计梳理：生成开发输入包

把下面整段发给 Codex：

```text
[$api-detail-tsd-sync](<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md)
请梳理 <FUNCTION_CODE> 功能设计，并在可进入开发时物化 handoff
project-root: <PROJECT_ROOT>
workspace-key: <WORKSPACE_KEY>
```

这一步必须先完成，后面的 02/04 才有可消费的 `.agent\functions\<FUNCTION_CODE>\handoff\development-handoff.json`。

## 1. 可选『参考资料索引导入器』（资料准备旁路）：建外部参考索引

把下面整段发给 Codex：

```text
[$reference-index-importer](<pluginRoot>\skills\reference-index-importer\SKILL.md)
请重建集中 .agent\reference\global
project-root: <PROJECT_ROOT>
external-api-dir: <EXTERNAL_API_DIR>
db-schema-dir: <DB_SCHEMA_DIR>
```

开发规范不要放在 01。需要接给第 04 步时，另跑 `$project-rule-analyzer`：

```text
[$project-rule-analyzer](<pluginRoot>\skills\project-rule-analyzer\SKILL.md)
请把开发规范转成 project-rules
project-root: <PROJECT_ROOT>
workspace-key: <WORKSPACE_KEY>
category: code-guidelines
source:
- <CODE_GUIDE_1>
- <CODE_GUIDE_2>
approve: true
```

## 2. 02 API Spec Writer：产出规格文件

把下面整段发给 Codex：

```text
[$api-spec-writer](<pluginRoot>\skills\api-spec-writer\SKILL.md) <FUNCTION_CODE>
```

## 3. 03 Optional SQL Fixture Preparer：按需准备 SQL fixture

如果当前 API 需要 SQL fixture，再把下面整段发给 Codex：

```text
[$api-sql-fixture-preparer](<SQL_FIXTURE_SKILL_PATH>) <FUNCTION_CODE>
```

## 4. 04 API Code Writer：产出代码

第 04 步的开发规范只读 `.agent\project-rules\<workspaceKey>`，不读 01 的 `.agent\reference\global`。如果开发规范尚未 approve，请先跑上面的 `$project-rule-analyzer`。

把下面整段发给 Codex：

```text
[$api-code-writer](<pluginRoot>\skills\api-code-writer\SKILL.md) <FUNCTION_CODE>
```

## 5. 05 Optional DOCX UnitTest Report：产出单元测试 UT 测试报告

如果需要正式 UT 报告，再把下面整段发给 Codex：

```text
[$docx-unittest-report](<DOCX_UT_REPORT_SKILL_PATH>) <UT_REPORT_DOCX>
```

## 一份可直接改值的完整模板

```text
0.
[$api-detail-tsd-sync](<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md)
请梳理 D.006 功能设计，并在可进入开发时物化 handoff
project-root: D:\Repo\Project
workspace-key: PROJECT

1.
[$reference-index-importer](<pluginRoot>\skills\reference-index-importer\SKILL.md)
请重建集中 .agent\reference\global
project-root: D:\Repo\Project
external-api-dir: D:\Refs\ExternalApi
db-schema-dir: D:\Refs\DbSchema

1.5.
[$project-rule-analyzer](<pluginRoot>\skills\project-rule-analyzer\SKILL.md)
请把开发规范转成 project-rules
project-root: D:\Repo\Project
workspace-key: PROJECT
category: code-guidelines
source:
- D:\Refs\Guidelines\JWT_Redis_存储說明.xlsx
- D:\Refs\Guidelines\框架説明.docx
approve: true

2.
[$api-spec-writer](<pluginRoot>\skills\api-spec-writer\SKILL.md) D.006

3.
[$api-sql-fixture-preparer](<pluginRoot>\skills\api-sql-fixture-preparer\SKILL.md) D.006

4.
[$api-code-writer](<pluginRoot>\skills\api-code-writer\SKILL.md) D.006

5.
[$docx-unittest-report](<安装后的 docx-unittest-report\SKILL.md 路径>) D:\Repo\Project\docs\D.006_UT_Report.docx
```

## 说明

- 第 0 步是主链路起点，会生成 `.agent\functions\<FUNCTION_CODE>\handoff`
- 第 1 步只是外部 API / DB Schema 索引支线；不需要外部参考时可以先跳过
- 第 3 步是可选步骤；只有当前 API 需要 SQL fixture 时才跑
- 第 2 步和第 4 步都是批次推进型；同一个功能编号下如果有多支 API，Codex 会持续推进到完成或阻塞点
- 第 5 步是可选步骤，产出的是 UT 报告 docx，不是 spec 文件
