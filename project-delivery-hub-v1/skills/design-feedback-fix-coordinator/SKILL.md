---
name: design-feedback-fix-coordinator
description: 处理明确由客户、SA、IT review 或问题单反馈引发的设计交付物修正。读取反馈邮件/问题清单/TSD 客户反馈，识别 TSD、API Detail、CommonFunc、CommonUtil、Response Code、梳理稿、handoff 与时序图影响，复用「专案需求接口设计梳理」的 Design Leader 语义判断与多文件 file-claim 编排；涉及 Word/Excel 写入时转交 Office 交付文件编辑器；不复制 API contract 规则，不直接绘制 VSDX。关键词：反馈修改、TSD 问题、客户反馈、design-change-plan、file-claims、office-edit-plan、Design Leader。
---

# 【设计梳理】专案设计反馈修改协调器

本技能是客户反馈入口，不是第二套需求梳理规则。业务语义、API contract、命名、后端来源、CommonFunc/CommonUtil 复用与开发就绪判断，必须复用 `专案需求接口设计梳理` 的规则与 `Design Leader Mode`。涉及 TSD Word、API Detail Excel、CommonFunc/CommonUtil Excel 或 Response Code workbook 的实际写入时，不在本技能内直接保存文件；由 Design Leader 形成 file claim / `office-edit-plan` 后交给 `专案 Office 交付文件编辑器`。

## 适用场景

- 用户提供客户反馈邮件、SA 问题单、IT review 意见或 TSD 客户反馈。
- 用户要求“按问题清单修正 TSD/API Detail/Common”，且问题来源明确为客户/SA/IT/问题单反馈。
- 同一反馈影响多份设计交付物，需要组织 worker 或进行 file claim。

不适用：

- 纯格式问题，交给 `专案交付文件格式检查器`。
- 正式 VSDX 绘制或修图，交给 `专案原生 VSDX 时序图生成器`。
- 02-05 代码/测试并行，交给 `单功能多接口并行交付领导者`。
- 没有反馈来源、只要求“顺手调整文件”的一般编辑任务。

## 必读协议

进入多文件修正前读取：

- `references/design-leader-protocol.md`
- `references/office-deliverable-edit-protocol.md`（仅当反馈需要写入 `.docx` / `.xlsx`）
- `skills/api-detail-tsd-sync/SKILL.md` 中的 `Design Leader Mode`

只读分析且不写文件时，可只加载本文件和必要项目规则。

## 工作流程

1. 识别 `functionCode`、反馈来源、用户指定文件、`.agent/functions/<functionCode>` 既有分析与 handoff。
2. 解析反馈为 issue 列表，每项记录反馈原文摘要、证据文件、影响范围、建议裁决状态。
3. 进入 `专案需求接口设计梳理` 的语义判断：比对 PRD / TSD / API Detail / Common / Response Code / IT SPEC，决定正式设计口径。
4. 若需要写多份文件，按 `design-leader-protocol.md` 生成或更新：
   - `.agent/functions/<functionCode>/orchestration/design-change-plan.json`
   - `.agent/functions/<functionCode>/orchestration/file-claims.json`
   - `.agent/functions/<functionCode>/orchestration/office-edit-plan.json`（有 Word/Excel 写入时）
5. 按文件级 claim 分配 worker。`.docx`、`.xlsx`、`.vsdx` 必须整文件锁定，不按 sheet 或章节拆给不同 worker；Word/Excel worker 使用 `专案 Office 交付文件编辑器`。
6. worker 只改 claim 文件，并回报 `modifiedFiles`、摘要、验证命令、阻塞项与风险。
7. leader 校验 worker 输出后，串行更新梳理稿、handoff hash、状态与 `final-design-fix-report.json`。
8. 需要时调用格式检查器做 Word/Excel 只读或局部格式闭环；时序图只记录影响，除非用户明确要求立即处理。

## 资源

- `agents/openai.yaml`
- `references/design-leader-protocol.md`
- `references/office-deliverable-edit-protocol.md`
- `skills/api-detail-tsd-sync/SKILL.md` 的 `Design Leader Mode`

## 输出要求

最终回复必须说明：

- 采用的反馈来源与权威设计来源。
- 改了哪些主档与 `.agent` 副本。
- 哪些 issue 已解决、哪些仍待确认。
- 是否影响 CommonFunc/CommonUtil、Response Code、时序图。
- worker 是否存在越权修改；若未启用 worker，也说明由 leader 本地串行处理。
- 验证结果：内容检查、格式检查、JSON/handoff hash、Office 编辑器 `modifiedFiles`、临时文件清理。
