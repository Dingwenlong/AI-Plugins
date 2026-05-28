# DAWHO Design Summary Rules

Use these rules when producing full function design summaries, design progress notes, readiness percentages, and development-readiness judgments.

> Extracted from the former heavy `SKILL.md` so the entrypoint can stay lightweight. Load this file only when the matching workflow is active.

## 功能设计梳理说明

当用户要求 `梳理 {functionCode} 功能设计`、`梳理 {functionCode} 功能设计进度`、`功能设计梳理`、`功能进度` 或同等表述时，产出完整 Markdown 功能设计梳理说明，而不是短进度 memo。

梳理稿结构保持下列 9 段式顺序不变；不要为了记录新证据链新增大章节或调整章节顺序。PRD/TSD/API Detail/IT SPEC/旧项目代码/Response Code/Common 的证据链应填入对应章节，尤其是 `依据文件`、`主流程设计`、`开发前收敛状态`、`API Contract 摘要` 与 `前后端责任边界`。

Language rule:

- Generated function-design summary notes should default to Simplified Chinese for section titles, prose, status text, risk notes, and todo descriptions.
- Preserve official source text when it is evidence or an identifier: file paths, file names, API names, field names, sheet names, TSD/API Detail table headers, Response Code values/messages, BackendAPI names, DB/SP names, PRD/TSD/API Detail quoted wording, and legacy system names.
- Do not translate identifiers or source evidence just to make the note look fully simplified; explain them in Simplified Chinese around the preserved original text.

默认输出路径与命名：

- For development-chain work, save or copy the final note under centralized `.agent/functions/<functionCode>/analysis/`. If the user is only doing design-workspace analysis and not entering the development chain yet, the historical `output/{functionCodeWithoutDots?}_api_design/` folder can still be used as a working draft location.
- Use filename style `{functionCode}_功能设计梳理_{yyyyMMdd}.md` by default. If the user explicitly asks for "进度", still use the full design-summary structure; do not downgrade to a terse progress memo.
- When the note is intended to feed implementation, run `scripts/materialize_design_handoff.py` after the note is complete. It copies the note and referenced TSD/API Detail/Common/Response Code/reference inputs into `.agent/functions/<functionCode>/` and writes `handoff/development-handoff.json`.

必要章节顺序：

1. `总体判断`: combine the readiness percentage, whether it can enter development, and the frozen/not-frozen conclusion.
2. `依据文件`: list PRD, TSD, API Detail, Response Code, IT SPEC, legacy source, and other evidence actually used.
3. `功能定位`: 用简体中文概述业务目的与范围内能力；每条核心能力句末都要标注参考 PRD 页码，例如 `（prd:1~4）`。页码必须来自实际 PRD 内容或用户明确指定，不能为了填满模板而臆造；若能力来自 TSD/API Detail 而 PRD 未直接覆盖，写 `（prd:未发现直接页码；TSD/API Detail 补充）`。
4. `已确认交付物`: list the delivery assets that development and review must be able to locate. At minimum include TSD, API Detail, Response Code, Common, and sequence diagrams; PRD may also be listed when useful, but not as a substitute for those assets. Common must separately check `CommonUtil` and `CommonFunc` workbooks, because a function may use both, one, or neither; mark `未发现` or `未确认引用` instead of guessing. Sequence diagrams must be split into the function's own diagrams and external/common diagrams referenced by `ref`; list both `.svg` and `.vsdx` when available, and explicitly mark the missing format when only one exists.
5. `TSD/API 清单`: list APIs from TSD/API Detail, their category, method, description, backend source, and current status.
6. `主流程设计`: describe the end-to-end user/API/backend flow in implementation-facing order.
7. `开发前收敛状态`: combine aligned items, unresolved risks, TODOs, non-frozen items, and concrete pre-development actions. 本节必须包含接口名与接口字段合理性专项盘点；若尚未逐项完成，统一标为 `待专项盘点 | 接口名与接口字段合理性`，用于检查 TSD/API Detail/API Contract 中 API 名称、Request/Response 字段命名、旧字段残留、字段说明与示例一致性。
8. `API Contract 摘要`: summarize each API's request/response contract, key fields, response/no-data/error behavior, and backend-source mapping at a developer-usable level.
9. `前后端责任边界`: state which layer owns validation, masking, display formatting, popup copy, backend calls, response-code mapping, persistence, and notification behavior.

Evidence and honesty rules:

- Do not invent sequence diagrams, Response Code workbooks, IT SPEC files, DB/SP names, BackendAPI sources, field mappings, popup wording, or completion percentages to fill the template.
- If evidence is not found, write `待确认` or `未发现`, and explain the impact in `开发前收敛状态`.
- Customer IT SPEC is a required analysis target for interface-design summaries. The `依据文件` table must include a `Customer IT SPEC` row; if no matching file is found, write `Customer IT SPEC | 未找到 | 已搜索 customerItSpec 目录；作为显式风险，不自动阻塞 developmentReady`.
- A missing Customer IT SPEC is an explicit risk by default, not an automatic readiness blocker. Block development only when the missing customer evidence leaves API coverage, backend source, field mapping, or error behavior undecidable.
- When a Customer IT SPEC file exists, the note must include a `Customer IT SPEC 差异矩阵` subsection under `开发前收敛状态`, and the centralized analysis folder must include `it-spec-diff-matrix.md` plus `it-spec-diff-matrix.json`.
- Each matrix item must record `Customer IT SPEC 口径`, `现行 TSD/API Detail 口径`, `差异类型`, `影响等级`, `裁决结论`, `裁决理由`, and `ready 影响`. High-impact differences may be development-ready only after an explicit decision and reason are recorded; unresolved or customer-confirmation items block `developmentReady`.
- If only historical/reference sequence diagrams exist, label them as reference material, not current frozen output.
- Do not include historical reference diagrams or visual QA artifacts in `已确认交付物` by default. Mention them only when the user explicitly asks for historical comparison, visual QA evidence, or layout validation details.
- Keep the note practical for developers: prefer concise tables and concrete field/API names over narrative audit prose.
- If the note is generated after workbook edits, run the required downstream format-check handoff first; if it is read-only analysis, do not write the workbook.


## 开发就绪度评估

当用户询问“完成程度”、“完成度”、“是否可開發”、“能不能進開發”、“ready for dev”，或分析显示 API 规格已大致对齐 PRD/TSD 时，加入简洁的开发就绪度估算。

输出格式：

- Start with an approximate percentage, for example: `約 85% 完成`.
- State whether the spec can enter development:
  - `可進入開發`: core PRD capabilities, TSD API list, API Detail rows/sheets, request/response fields, backend sources, and major business rules are aligned; remaining items are clarifications or low/medium-risk refinements.
  - `需補齊後再開發`: missing APIs, missing blocking fields, unclear source systems, incompatible examples, or business rules that would block acceptance.
- Separate the assessment into:
  - 已完成/對齊項目.
  - 剩餘風險/開發前強化項目.
  - 最終判斷.

Suggested percentage bands:

- `90-100%`: development-ready and near frozen; only minor wording, examples, or non-blocking cleanup remain.
- `75-89%`: development-ready, but still has several clarification risks such as date boundaries, source merge behavior, formatting responsibility, error-state mapping, or Common wrapper wording.
- `50-74%`: partial design; core flow exists but key fields, API coverage, or business rules need more work before implementation can be stable.
- `<50%`: not ready; major PRD capabilities or API contracts are missing.

Estimate from evidence, not optimism. Consider these dimensions together: API coverage, request/response contract, business-rule coverage, source/backend traceability, naming consistency, examples, and error/no-data behavior.

除非用户要求，不要把就绪度估算扩展成长篇审计。若功能已足够进入开发，用直白结论表达，例如：`規格已可進入開發，但還不到完全凍版；建議開發前再精修日期/資料來源/格式化/錯誤狀態。`
