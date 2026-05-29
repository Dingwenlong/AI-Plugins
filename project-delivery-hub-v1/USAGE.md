# project-delivery-hub-v1 使用说明

`project-delivery-hub-v1` 是专案交付中枢插件，覆盖 PRD/TSD/API Detail 梳理、客户反馈设计修正、Office 交付文件编辑、原生 VSDX、交付格式检查、API Spec、SQL fixture、.NET 业务代码写入、UT 报告与企业微信智能表格异动记录。

## 安装与工作区

插件包应包含：

```text
plugins/project-delivery-hub-v1/
  .codex-plugin/
  references/
  skills/
  .agent/
  USAGE.md
```

项目工作区建议集中维护：

```text
<workspaceRoot>/
  .agent/
  <feature-branch-folder>/
```

`.agent` 是共享交付状态根目录。插件中的 `references/local-workspaces.json` 用于记录 `workspaceRoot`、`agentRoot`、`rulesRoot` 与默认代码目录；真实项目可在本机维护私有配置，不要把私有路径、SQL 连接串、WeDoc WebHook 或运行日志打进交付包。

## 常规 01-05 链路

```text
【资料准备】参考资料导入 -> 【设计梳理】冻版（推荐） -> 【开发落地】API Spec -> 【开发落地】SQL fixture -> 【开发落地】API 业务代码 -> 【测试验收】UT 测试报告
```

- 01 只在需要外部 API/DB Schema 全局参考索引时执行。
- 设计梳理可输出 `.agent/functions/<functionCode>/handoff/development-handoff.json`，作为 02 的优先输入。
- 02 优先从 handoff 生成各 API 的 `*_API_Spec.json`；没有 handoff 时，也可从明确 `docx_ref` 或 `execution-batch.json` 命中的 TSD 直接生成。TSD/API Detail 仍是接口字段与响应契约主源；当前功能的时序图可作为更细业务逻辑证据进入 02，用于补强流程、依赖、校验、错误分支与测试意图，冲突时写入 blocking unresolved。
- 03 根据 SQL 依赖和 `.agent/config/sql-fixture-targets.local.json` 私有 SQL Server 目标配置准备 schema/seed，或标记 `skipped/not_required`；SQLite 本地建表路径已禁用。
- 04 先生成 `implementation-template.md/json` 落码范本；用户确认或修改 Markdown 并执行 confirm 后，才写业务代码，不生成 UnitTest/IntegrationTest 测试源码。
- 05 消费第 04 步 `testCodeHandoff`、mockExamples 与验证证据，生成测试代码和 DOCX UT 报告。

## 设计阶段 Design Leader

`【设计梳理】专案需求接口设计梳理` 在新需求梳理、冻版推进或多文件同步时可作为 Design Leader。`【设计梳理】专案设计反馈修改协调器` 是客户/SA/IT 反馈入口，会把问题单、邮件或 TSD 反馈转成修正项，再回到 Design Leader 进行业务裁决。

Design Leader 维护：

```text
.agent/functions/<functionCode>/orchestration/
  design-change-plan.json
  file-claims.json
  office-edit-plan.json
  worker-results.json
  final-design-fix-report.json
```

并行策略：

- 业务语义、API contract、命名、后端来源、CommonFunc/CommonUtil 复用、Response Code 与开发就绪判断由 `api-detail-tsd-sync` 负责。
- worker 只能修改 `file-claims.json` 分配的 TSD、API Detail、CommonFunc、CommonUtil、Response Code 或分析文件；Word/Excel worker 必须遵守 Office 编辑器协议。
- `office-edit-plan.json` 描述 `.docx` / `.xlsx` 的实际写入范围、允许操作、禁止操作与验证命令。
- `development-handoff.json`、hash、状态与最终报告由 leader 串行写入。
- `.docx`、`.xlsx`、`.vsdx` 以整文件 claim，不按 sheet 或章节并行写同一文件。
- 时序图默认只记录影响，除非用户明确要求立即交给 VSDX 技能处理。
- 共用协议见 `references/design-leader-protocol.md` 与 `references/office-deliverable-edit-protocol.md`。

## 【交付文件】Office 交付文件编辑器

`【交付文件】专案 Office 交付文件编辑器` 是 Word/Excel 物理写入层。它接收 Design Leader、格式检查器或用户明确给出的 `office-edit-plan` / file claim，只修改被 claim 的 `.docx` / `.xlsx` 文件。

职责边界：

- 可写 TSD Word、API Detail Excel、CommonFunc/CommonUtil Excel、Response Code workbook。
- 不裁决 API contract、字段命名、后端来源、Common 复用或开发就绪。
- 不判定 Must fix / Visual risk；这些由格式检查器负责。
- 不写 handoff、orchestration、context、status、final report 或 package metadata。
- 输出 `modifiedFiles`、改动摘要、验证命令/结果、blocker 与风险。

## 【流程编排】多接口并行交付领导者

显式入口：

```text
执行【流程编排】单功能多接口并行交付领导者
```

适用边界：

- 一支功能 `functionCode` 下多个 API 并行交付。
- 当前对话作为 leader spawn/指挥子 agent。
- 不默认创建多 worktree，不跨多个功能并行。
- leader 串行写共享 `.agent/context/<functionCode>/` 状态。
- 子 agent 只能读共享 `.agent`，并且只能修改已 claim 的代码或测试文件。

leader 维护：

```text
.agent/context/<functionCode>/orchestration/
  leader-run.json
  api-workgroups.json
  file-claims.json
  final-assessment.json
```

并行策略：

- 设计冻版阶段可派只读 reviewer 子 agent 检查 API contract、DB/SQL、Common/旧逻辑、UT 验收口径；`development-handoff.json` 是推荐交接物，不再是 02 的硬性前置。
- 02/03 的共享状态由 leader 串行写入。
- 02 会把命中的时序图 path/hash 写入 `source.sequenceDiagrams` 与 manifest source fingerprint；时序图内容变化会触发后续代码阶段重新待处理。
- 04 先由 leader 按 `--api-id` 串行 prepare 所有 API，收集 `change-plan.json` 与 `implementation-template.md/json`。
- 所有 API 的 Markdown 范本经用户确认并执行 `--execution-mode confirm` 后，`multi-api-leader` 脚本才按文件重叠关系生成 workGroup 与可执行 file claim；任一范本未确认时必须 blocking。
- 文件重叠 API 归同一 worker 串行处理，无重叠组可并行。
- worker 不写 `.agent/context`，不写测试源码，返回 `modifiedFiles`、验证命令、阻塞项。
- leader 校验 `modifiedFiles` 未越权后再串行 apply/验证。
- 05 的测试代码也按 file claim 分配；DOCX 报告、manifest/results 和 `final-assessment.json` 由 leader 汇总落盘。

运行编排脚本：

```powershell
python "skills/multi-api-leader/scripts/orchestrate_multi_api.py" `
  --project-root "<workspaceRoot>/<feature-branch-folder>" `
  --agent-root "<workspaceRoot>/.agent" `
  --function-code "<functionCode>" `
  --mode plan
```

最终评估：

```powershell
python "skills/multi-api-leader/scripts/orchestrate_multi_api.py" `
  --agent-root "<workspaceRoot>/.agent" `
  --function-code "<functionCode>" `
  --mode assess
```

只有 02 spec、03 fixture、04 code validation、05 UT/report 均无 blocking，且 `final-assessment.json` 判定通过，leader 才能输出“符合需求”。

## 命名与打包卫生

- 命名标准见 `references/artifact-naming-standard.md` 与 `references/artifact-naming-standard.json`。
- 打包前运行 `skills/plugin-packager/scripts/package_project_delivery_hub.ps1 -DryRun`。
- 不携带 `.bak`、`*.tmp`、`*.log`、`*.pyc`、`__pycache__`、私有 SQL fixture 连接配置、私有 WeDoc 配置、运行期子 agent 记录或内部调试输出。
- 三张架构 SVG、集中 `.agent` 快照、USAGE 与命名标准必须随结构变化同步。

## 【开发落地】04 Code Style Reviewer

Use `skills/code-style-reviewer` when old C# business code needs to be checked against the current 04 `api-code-writer` constraints and the live `apiCodeWriter` project rule pack. It is read-only: it writes `code-style-review.json` and `code-style-review.md` under `.agent/context/<functionCode>/`, and it does not edit source code, test code, `manifest.json`, `execution-state.json`, or `codeStatus`.

Default usage starts from existing context change plans:

```powershell
python "skills/code-style-reviewer/scripts/review_code_style.py" `
  --project-root "<workspaceRoot>/<feature-branch-folder>/P240301Git" `
  --agent-root "<workspaceRoot>/.agent" `
  --workspace-key "NEWDAWHO" `
  --function-code "<functionCode>"
```

Use `--api-id` for one API, `--file` plus `--scope files` for explicit files, or `--scope project` only when a full C# source scan is intentionally requested.
