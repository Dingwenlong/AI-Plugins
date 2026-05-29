---
name: 专案交付中枢：【流程编排】单功能多接口并行交付领导者
description: 显式 leader 入口，用当前对话统筹一支 functionCode 下多个 API 的 01-05 交付流程；负责设计冻版复核、子 agent 分工、文件 claim、串行共享状态写入、最终需求符合性鉴定。关键词：multi-api leader、sub-agent、orchestration、file-claims、final-assessment。
---

# 【流程编排】单功能多接口并行交付领导者

本技能只在用户明确要求“多接口并行交付领导者”“启动多个子 agent”“一支功能多个 API 协同开发”时使用。它不承诺插件在所有环境中自动后台启动 agent；当前对话是 leader，负责决定是否 spawn 子 agent、给出指令、收敛结论。

## 边界

- 范围是一支功能 `functionCode` 下多个 API，共用同一个代码分支和项目目录。
- 不默认创建多 worktree，不跨多功能并行开发。
- leader 串行写共享 `.agent/context/<functionCode>/` 状态。
- worker 只能读共享 `.agent`，并且只能修改 `file-claims.json` 中分配给自己的代码或测试文件。
- 写入目标重叠的 API 必须进入同一 `workGroup`，由同一 worker 串行处理。
- 02/03/04/05 的最终状态、manifest、UT DOCX 报告和最终评估都由 leader 汇总落盘。

## Orchestration State

leader 在 `.agent/context/<functionCode>/orchestration/` 下维护：

- `leader-run.json`：本轮 leader run、阶段、worker 分工、阻塞项、最终状态。
- `api-workgroups.json`：按 API 写入文件重叠关系生成的工作组。
- `file-claims.json`：代码/测试文件到 owner/workGroup 的租约。
- `final-assessment.json`：需求符合性、01-05 gate、UT 结论和未决项。

## Workflow

1. 设计冻版：leader 可派只读 reviewer 子 agent 分别检查 API contract、DB/SQL、Common/旧逻辑、UT 验收口径。只读 reviewer 不写文件，结论交回 leader；leader 汇总阻塞项并迭代。若有 `development-handoff.json`，优先以 `developmentReady=true` 作为交接依据；若没有 handoff，可用明确 `docx_ref` 或 `execution-batch.json` 命中的 TSD 继续 02。
2. 01-03：leader 运行规则包检查与共享状态写入。01 只在需要全局 reference 时执行；02 按 API 生成 spec；03 按 SQL 依赖准备 fixture 或标记 skipped/not_required。
3. 04 prepare/confirm：leader 对每个 API 串行执行 code writer prepare，生成每个 API 的 `change-plan.json`、`implementation-template.md` 与 `implementation-template.json`；所有 API 的 Markdown 范本都经用户确认并执行 `--execution-mode confirm` 后，才可进入 worker 规划。
4. 04 worker：leader 运行本技能脚本建立冲突图和文件 claim，再将无文件重叠的 workGroup 并行派给 worker；重叠 API 合并给同一 worker 串行处理。任一 API 缺少 `change-plan.json` 或范本未确认时，plan 阶段必须 blocking，不能生成可执行 worker claim。worker 不写 `.agent/context`，不写测试源码。
5. 04 apply/verify：leader 校验 worker 输出的 `modifiedFiles` 未越权，再串行 apply/验证，写回 codeStatus 和测试交接。
6. 05：leader 基于第 04 步 `testCodeHandoff`、mockExamples、trx/Postman/code-inspection 证据分配测试文件 claim，最终汇总测试代码、manifest/results 与 DOCX UT 报告。
7. 最终鉴定：聚合根层与 `apis/<apiId>/` 下所有相关 status/results 文件；任一 API 或任一 gate 失败、缺失、blocking，或存在过期 file claim，`final-assessment.json` 都必须失败。只有 02 spec、03 fixture、04 code validation、05 UT/report 全部无 blocking，且 `final-assessment.json` 通过，才输出“符合需求”。

## Script Usage

生成工作组与文件 claim：

```powershell
python ".\scripts\orchestrate_multi_api.py" `
  --project-root "D:\Repo\Project" `
  --agent-root "D:\Repo\Project\.agent" `
  --function-code "D.006" `
  --mode plan
```

包含测试文件 claim：

```powershell
python ".\scripts\orchestrate_multi_api.py" `
  --project-root "D:\Repo\Project" `
  --agent-root "D:\Repo\Project\.agent" `
  --function-code "D.006" `
  --mode plan `
  --include-tests
```

生成最终评估：

```powershell
python ".\scripts\orchestrate_multi_api.py" `
  --agent-root "D:\Repo\Project\.agent" `
  --function-code "D.006" `
  --mode assess
```

## Worker Contract

给 worker 的指令必须包含：

- `functionCode`
- `workGroupId`
- `apiIds`
- 可修改文件列表
- 禁止写入 `.agent/context`、UT 报告、manifest/results
- 要求返回 `modifiedFiles`、验证命令、风险与阻塞项

leader 必须用 `file-claims.json` 校验 worker 的 `modifiedFiles`。任何越权文件或过期 claim 都视为 blocking，不能进入 apply。

## Tests

运行本技能回归：

```powershell
python ".\tests\run_regressions.py"
```

覆盖点：API 分组、文件重叠检测、缺少 change-plan blocking、范本未确认 blocking、claim 租约、过期 claim、worker 输出校验、最终评估全量 status 聚合。
