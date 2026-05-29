---
name: api-detail-tsd-sync
description: 把 PRD、TSD 与 API Detail 梳理成可开发的 API 设计交接。用于比对 API contract、统一字段/API 命名、维护 Api_List/后端来源、产出功能设计梳理与开发就绪判断；也判断时序图影响，并在接近冻版时物化 handoff 给第 02 步 API 规格生成。多文件或 Office 交付物写入时作为 Design Leader 产出 edit plan/file claim，由 Office 交付文件编辑器执行 .docx/.xlsx 物理保存。关键词：PRD、TSD、API Detail、功能设计梳理、开发就绪、handoff、Design Leader、office-edit-plan。
---

# 【设计梳理】专案需求接口设计梳理

## Office Edit Plan Contract

When creating or handing off `office-edit-plan.json`, include `schemaVersion: "1.0.0"`, `claimId`, `targetFiles[]`, `allowedOperations[]`, `forbiddenOperations[]`, and `validation[]`. The Office editor result must echo the `claimId` and report `modifiedFiles` plus `validationCommands`.

## 上下文策略

保持默认入口轻量化。读取本文件后，先用本文件完成任务判断、证据收敛和高层流程控制；只有进入对应子任务时才读取参考文件。

先解析当前工作区与专案规则库：

- 参数优先级：`--rules-root` > `PROJECT_RULES_ROOT` / 专案环境变量 > `references/local-workspaces.json.rulesRoot` > `<agentRoot>/project-rules/<workspaceKey>`。
- 读取 `<rulesRoot>/catalog.json` 后，先解析 `rulePacks.apiDetailSync`，再按任务类别加载 `rules[*].path` / `rules[*].loadPath` 与 `assets`；例如 API contract、API Detail workbook、delivery format、sequence diagram、code guidelines、SQL fixture、field KB。
- 找不到规则库或 catalog 时，继续执行通用梳理流程，但 专案专属判断必须标记为“缺少专案规则”，不得从插件内旧 reference 偷读专案默认规则。

### 规则包启动检查

正式专案梳理、开发就绪判断、API Detail 语义编辑或 handoff 物化前，必须先解析梳理规则包：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack apiDetailSync `
  --workspace-key "<workspaceKey>"
```

若用户明确给出规则库，改传 `--rules-root "<rulesRoot>"`。脚本输出的 `rules[].resolvedPath` 与 `assets[].resolvedPath` 是本次必读规则包；`status=blocked` 时，只能保存草稿或标记 `缺少专案规则`，不得给出“符合专案规则 / 可进入开发”的结论。

若解析到 `workspaceKey=NEWDAWHO`，必须应用规则包中的 NEWDAWHO 后续改动强规则：历史获取账户信息/账户列表/转出账户类方法统一收敛为 `GetEC0001`（外部 `CommonUtil/GetEC0001`、内部 `CommonFunc.GetEC0001`），`TX_STATISTIC` 直接删除且不得作为后续接口设计来源保留。

外置规则命中后，按需加载 catalog 中对应规则。以下技能内 reference 只作为历史兼容、迁移说明或规则库尚未建立时的通用导航，不再作为专案规则默认来源：

- `references/path-registry-rules.md`：功能编号、PRD/TSD/API Detail/Common/Response Code/IT SPEC/旧项目路径解析。
- `references/system-design-standard-v2.5-api-contract-rules.md`：系统设计规范 v2.5 中与 API contract、TSD `API清单`、API Detail、命名、Redis/Appsetting/DB 设计证据相关的规则。
- `references/database-design-standard-v3/catalog.json`：只在任务涉及新增/调整数据库表、字段、PK/FK、索引、SP/View、审计字段、保留期限或敏感资料设计时读取；按 catalog 决定是否继续读取细则。
- `references/naming-and-field-kb-rules.md`：API 方法命名、字段知识库、功能设计命名、范例情境、Response Code 与开发修改建议。
- `references/design-summary-rules.md`：9 段式功能设计梳理稿、设计进度稿、开发就绪度百分比。
- `references/api-detail-workbook-rules.md`：Api_List、API sheet、后端来源、工作簿编辑、备份、字体、格式检查器交接与验证。
- `references/sequence-diagram-handoff-rules.md`：时序图影响判断与下游时序图技能交接。
- `references/field-kb/{Category}.md`：只在需要统一字段命名或新增字段决策时读取；不要默认全量加载。
- `.agent/config/design-source-registry.json`：只在用户给功能编号但未给文件路径时读取；记录 PRD/TSD/API Detail/Common/Response Code/IT SPEC/旧项目目录与功能编号索引。插件内 `references/api-file-registry.json` 只保留空模板与迁移说明，不再写入个人路径。

不要把全部参考文件当成默认必读材料。先判断任务类型，再最小化加载相关参考。

遇到“系统设计规范 v2.5 / 设计规范 / API contract 标准 / 命名标准 / Redis/Appsetting/DB 设计规则”相关任务时，先读取专案规则库中 `api-contract`、`api-detail-workbook`、`field-kb` 或相关 category；只有缺少外置规则且用户明确要求兼容旧资料时，才参考技能内 legacy reference。

遇到“新增数据库表 / 调整数据库表 / 字段设计 / 主键外键 / 唯一键 / 索引 / stored procedure / view / 审计字段 / 数据保留 / 敏感资料字段”相关任务时，先读取专案规则库的 DB/SQL 设计规则 catalog，再按 `path` / `loadPath` 读取命中的规则。当前若 catalog 标记 `sourceStatus=source_unreadable`，只能加载阻塞说明并把数据库设计规范列为待补证据；不得凭记忆或旧项目经验补造数据库设计规范细则。

若后续拿到可读 Markdown/JSON 或未受 DRM 保护的 Word，可用 `scripts/convert_database_design_standard.py` 先抽取 source，再人工拆成 catalog 指向的主题规则；转换失败时不得生成空规则或伪规则。

## 范围

当用户提出下列专案系统设计工作（含 既有专案）时，使用本技能：

- 梳理功能需求，确认 TSD 接口设计是否符合 PRD。
- 比对 PRD、TSD、API Detail Excel、Response Code、CommonUtil/CommonFunc、Customer IT SPEC 与旧系统证据。
- 产出 API 设计差异、开发修改建议、开发就绪度判断或功能设计梳理稿。
- 更新或规划 `NEWDA_API_DETAIL_*.xlsx` 的 `Api_List`、API sheet、Request/Response、范例、业务逻辑、`涉及BackendAPI`、`后端来源`。
- 梳理新增或调整数据库表、字段、索引、PK/FK、SP/View、审计字段、资料保留与敏感资料设计的待确认项。
- 根据分类字段知识库统一 API 字段命名，避免旧系统字段名直接流入新系统 contract。
- 评估是否可进入开发、是否接近 100% 冻版，以及还缺哪些证据。
- 判断时序图、PlantUML、SVG、VSDX 的影响范围，并把正式绘图/修图交给下游 `专案原生 VSDX 时序图生成器`。

优先使用用户指定的工作簿或文件。除非用户要求、目标文件被锁定，或权威文件无效，不要切换到备份档、历史交付包或所谓安全副本。

## 集中式开发交接

功能设计梳理稿不再默认散落在设计工作区 `output/`。当梳理结果达到“可进入开发”或近冻版时，必须把分析稿与开发所需文件物化到共享 `.agent/functions/<functionCode>/`：

- `analysis/`：当前功能设计梳理稿。
- `inputs/tsd`、`inputs/api-spec`、`inputs/common`、`inputs/response-codes`、`inputs/reference`：开发链需要的 TSD、API Detail、Common、Response Code、DB/Redis/开发规范等输入文件副本。
- `handoff/development-handoff.json`：记录来源路径、复制路径、hash 与开发就绪状态，供第 02 步优先消费；这是推荐交接物，不再是 02 的硬性前置。

默认优先解析插件本地 `references/local-workspaces.json`，并按 `workspaceKey` 指向对应集中 `.agent`。PRD / TSD / API Detail 等设计来源目录统一读取 `<agentRoot>/config/design-source-registry.json`，不要再写入技能目录。

可使用 `scripts/materialize_design_handoff.py` 将已有梳理稿物化为开发 handoff：

```powershell
python ".\scripts\materialize_design_handoff.py" `
  --project-root "D:\Repo\Project\feature_common\P240301Git" `
  --workspace-key "PROJECT" `
  --function-code "D.006" `
  --summary "D:\Path\To\D.006_功能设计梳理_20260522.md"
```

若分析稿未达到可进入开发，仍可保存到 `analysis/`，但 `development-handoff.json` 必须标记 `status=blocked` / `developmentReady=false`，第 02 步不得自动推进。

## Design Leader Mode

当新需求梳理或反馈修正需要同步多份设计交付物时，本技能就是设计阶段 leader。业务语义、API contract、命名、后端来源、CommonFunc/CommonUtil 复用、Response Code 与开发就绪判断仍由本技能负责；worker 只处理已分配文件。TSD Word 与 API Detail/Common/Response Code Excel 的物理写入交给 `专案 Office 交付文件编辑器`，本技能只负责裁决和生成可执行 edit plan。

触发条件：

- 用户要求“梳理新需求并改文件”“推进到 100% / 冻版”“文件已解锁，按问题改改”。
- 同一功能影响 TSD Word、API Detail Excel、CommonFunc、CommonUtil、Response Code、梳理稿、handoff 或时序图交接中的两类以上文件。
- 用户明确要求使用多个子 agent、worker、并行修改或 leader 组织修改。

进入此模式前，读取 `references/design-leader-protocol.md`。涉及 `.docx` / `.xlsx` 写入时同时读取 `references/office-deliverable-edit-protocol.md`。若任务只是只读梳理或单文件小改，可不生成 orchestration artifacts，但仍需遵守本技能的业务裁决规则。

Design Leader 状态面：

```text
.agent/functions/<functionCode>/orchestration/
  design-change-plan.json
  file-claims.json
  office-edit-plan.json
  worker-results.json
  final-design-fix-report.json
```

不要把设计阶段 orchestration 状态写入 `.agent/context/<functionCode>/`；`.agent/context` 留给 02-05 开发执行链。`development-handoff.json` 仍保留在 `.agent/functions/<functionCode>/handoff/`，由 leader 在验证后串行更新。

Leader 职责：

- 解析 `functionCode`、registry、规则库、权威 PRD/TSD/API Detail/Common/Response Code 来源。
- 产出或更新 `design-change-plan.json`，列出 issue、业务裁决、目标文件、预计验证。
- 产出或更新 `file-claims.json`，按文件重叠关系分配 worker；`.docx`、`.xlsx`、`.vsdx` 必须整文件 claim，不按 sheet/章节并行写同一文件。
- 若 claim 目标是 Word/Excel，产出或交付 `office-edit-plan.json`，将实际保存动作交给 `专案 Office 交付文件编辑器`。
- 可 spawn 只读 reviewer 检查 contract、Common/旧逻辑、DB/SQL、验收口径；reviewer 不写文件。
- 可 spawn worker 修改互不重叠的 TSD、API Detail、CommonFunc、CommonUtil、Response Code 或分析稿文件；Office 文件 worker 必须使用 Office 编辑器边界。
- 校验 worker 回报的 `modifiedFiles` 未越权，再接受结果。
- 串行更新分析稿、handoff hash、状态与 `final-design-fix-report.json`。
- 调用格式检查器验证 Word/Excel；如格式检查器要求写入修复，再由 Office 编辑器执行。时序图只记录影响，除非用户明确要求立即绘制或修图。

Worker 约束：

- 只能修改 `file-claims.json` 分配给自己的文件。
- 可以读取共享 `.agent`、project rules、source registry 与分析稿。
- 不得写 `.agent/functions/<functionCode>/handoff/*`、`.agent/functions/<functionCode>/orchestration/*`、`.agent/status/*`、`.agent/context/*`、最终报告或 package metadata。
- 必须回报 `modifiedFiles`、改动摘要、验证命令/结果、阻塞项与风险。

反馈修改入口：

- 客户/SA/IT 反馈可先进入 `专案设计反馈修改协调器`，由其解析问题单与影响范围。
- 正式业务裁决仍回到本技能的 Design Leader Mode；反馈技能不得复制或覆盖本技能的 API contract 规则。

## 不在本技能内完成的事

- 不直接生成或修正式 VSDX。只记录时序图影响、更新点和交接信息。
- 不把 PlantUML/SVG 当成正式交付图。正式图由下游原生 VSDX 技能负责。
- 不做纯格式美化闭环。API Detail 语义编辑后，格式、字体、边框、渲染和视觉 QA 交给 `delivery-format-checker`。
- 不为缺失证据补业务规则。缺少 DB/SP、旧代码链路、外部接口地址、返回映射或异常口径时，标记 `todo` / `待确认` / `unresolved`。
- 不把设计来源 registry 写进 01-05 开发链 `.agent/context` 状态面；`.agent/context` 只放执行状态，设计目录配置放 `.agent/config/design-source-registry.json`。

## 权威文件与冻版目标

证据优先级：

1. 最新 PRD。
2. 最新主 TSD `.docx`，尤其 `5. API清单`。
3. 最新主 API Detail workbook，尤其 `Api_List` 与对应 API sheet。
4. Response Code workbook。
5. CommonUtil/CommonFunc workbooks。
6. Customer IT SPEC / API Doc。
7. 旧系统代码、DB/SP、配置、外部接口地址与字段映射。
8. 历史交付副本、`.bak`、`before_*`、临时文件只作为对照证据。

100% 冻版不是只给百分比，而是让开发人员可直接实现：API Name、Header、Request、Response、字段语义、来源、范例、业务逻辑、SQL/DB 条件、异常状态与 Response Code 口径都必须能追溯。

若用户要求“梳理到 100%”“尽量达到 100% 冻版”，优先推进 TSD/API Detail/Response Code/API Doc 的一致性修正或明确修改建议，而不是停留在聊天级结论。

## 默认主流程

当用户要求梳理某功能设计、接口设计、设计进度、开发就绪度，或要求把某功能推进到 100% 冻版时，默认按以下顺序执行：

1. 解析功能编号，例如 `D.003`、`L.004`、`N.001.001`。
2. 若用户未给文件路径，读取 `references/path-registry-rules.md`，再从 `<agentRoot>/config/design-source-registry.json` 解析 PRD/TSD/API Detail/Common/Response Code/IT SPEC/旧项目目录。
3. 以 PRD 对齐最新版主 TSD 与 API Detail，确认 TSD API 清单、Api_List、API sheet、API Name、Request、Response、范例、业务逻辑、Response Code 当前状态。
4. 若任务涉及系统设计规范或命名/完整性判断，读取 `references/system-design-standard-v2.5-api-contract-rules.md`，用 v2.5 规则检查 API 命名、必填、范例、`responseData`、Header 来源、旧命名边界、Redis/Appsetting/DB 设计证据。
5. 若任务涉及新增或调整 DB table / column / key / index / SP / view / audit / retention / sensitive data 设计，读取 `references/database-design-standard-v3/catalog.json`；只按命中项加载细则，若 source unreadable 则标记阻塞/待补证据。
6. 读取 Customer IT SPEC / API Doc 与旧系统线索；旧方法名、旧页面、旧 code-behind、旧 API 名称只作为 evidence/alias，不直接成为新系统正式 BackendAPI。
7. 若有旧项目目录，追踪配置地址、DB/SP、服务调用链、字段映射、过滤条件、异常口径与旧业务分支。
8. 优化新系统 contract：API Name、字段名、BackendAPI、`涉及BackendAPI`、CommonFunc/CommonUtil 调用、范例情境与 Response Code。
9. 与当前主档对比，产出梳理稿、修改建议、工作簿编辑或开发就绪判断。
10. 若写回 API Detail workbook，读取 `references/api-detail-workbook-rules.md` 并完成格式检查器交接。
11. 若影响时序图，读取 `references/sequence-diagram-handoff-rules.md`，只整理交接事项；正式绘图由下游技能执行。

## API Contract 核心原则

- TSD `API清单` 是开发入口；开发人员必须能从 TSD 的 API 类别、API 名称、功能说明定位到 API Detail 的 `Api_List` 与 API sheet。
- PRD 中文业务含义是字段语义事实来源；旧系统字段名、旧 API 名称、旧方法名只能作来源、别名或迁移证据。
- 系统设计规范 v2.5 的具体命名、完整性、Header、`responseData`、`passwd`、Redis/Appsetting/DB 证据规则放在 `references/system-design-standard-v2.5-api-contract-rules.md`；不要把整份规范内容复制进入口。
- 若既有字段名与 PRD 语义不符，直接提出 rename，并同步考虑字段表、范例、业务逻辑与相关说明。
- CommonFunc 是内部共享方法层；CommonUtil 是外部 wrapper/API 层。能复用现有 CommonFunc/CommonUtil 时，不新增重复共用逻辑。
- `涉及BackendAPI` 与 `后端来源` 必须能追溯；不确定 DB/SP、配置 key、外部 URL、过滤条件或字段映射时，标记待确认。
- 若需要设计新增/调整数据库表或字段，必须同时说明表用途、权威来源、字段语义、数据类型、必填/可空、PK/FK/唯一键、索引意图、更新频率、预计资料量、保留期限、审计字段与敏感资料分类；缺少任一关键事实时标记 `待确认` / `unresolved`，不得替用户补表设计。
- API 范例情境、Response Code 与业务逻辑必须保持一致；不要因为多个情境共用 response code 就合并掉测试/范例语义。
- 字段、API、功能开关、布尔旗标、动作与内部方法命名需要用新系统语义重整，避免 legacy naming 污染正式 contract。

需要详细命名规则时，读取 `references/naming-and-field-kb-rules.md` 和对应 `references/field-kb/{Category}.md`。

## 功能设计梳理稿

当用户要求 `梳理 {functionCode} 功能设计`、`梳理 {functionCode} 功能设计进度`、`功能设计梳理`、`功能进度` 或同等表述时，默认输出完整功能设计梳理稿，而不是短进度 memo。

默认稿件要求：

- 使用 `references/design-summary-rules.md`。
- 默认简体中文写说明、状态、风险、todo；官方证据、API 名、字段名、sheet 名、Response Code、BackendAPI、DB/SP、路径保持原文。
- 使用 9 段式结构：总体判断、依据文件、功能定位、已确认交付物、TSD/API 清单、主流程设计、开发前收敛状态、API Contract 摘要、前后端责任边界；若有 Customer IT SPEC，`开发前收敛状态` 必须内嵌 `Customer IT SPEC 差异矩阵` 摘要。
- 不编造时序图、Response Code、IT SPEC、DB/SP、BackendAPI、popup 文案、页码或完成度。
- 若证据不足，写 `待确认` 或 `未发现`，并说明对开发的影响。
- 梳理稿完成后，若用户目标是后续开发，运行 `scripts/materialize_design_handoff.py`，把分析稿、开发输入包与 `development-handoff.json` 放入集中 `.agent/functions/<functionCode>/`。
- Customer IT SPEC 与现行 TSD/API Detail 差异较大时，先运行 `scripts/generate_it_spec_diff_matrix.py` 生成 `analysis/it-spec-diff-matrix.md` 与 `analysis/it-spec-diff-matrix.json`；未裁决或 `readinessImpact=blocking` 的矩阵项会阻塞 handoff ready。

## 开发就绪度

当用户询问完成度、是否可开发、是否 ready for dev，或分析显示 API 规格已大致对齐 PRD/TSD 时，给出简洁开发就绪度判断。

默认表达：

- 先给近似百分比，例如 `约 85% 完成`。
- 再判断 `可进入开发` 或 `需补齐后再开发`。
- 分开说明已完成/对齐项、剩余风险/开发前强化项、最终判断。

估算必须基于证据，不基于乐观判断。综合 API 覆盖、request/response contract、业务规则、来源追溯、命名一致性、范例、错误/无资料行为。

详细百分比区间与模板读取 `references/design-summary-rules.md`。

## API Detail 工作簿编辑

只读分析时，不写回 workbook。需要写回时：

- 遵守当前工作区 `AGENTS.md`：默认不要在项目、程序或交付目录生成 `.bak`、`.before_*`、时间戳备份等副本；若项目规则另有明确要求，先说明冲突并以当前工作区最高优先本地约束为准。
- 读取 `references/api-detail-workbook-rules.md`。
- 语义/API 设计编辑裁决由本技能完成；实际 `.xlsx` 保存由 `专案 Office 交付文件编辑器` 执行；格式修复不能补造缺失 API 内容。
- 生成 `office-edit-plan` 时，内容编辑、字体继承与格式修复必须限于本次实际变更的 API sheets、`Api_List` 行或明确语义范围；禁止因为修改少量内容而遍历全 workbook 或所有 sheets 改字体。
- `office-edit-plan` 必须记录本次实际变更的单元格/合并范围，并要求尽量保留未变更文字的既有字体。只有实际新增或替换后的字符/词组使用专案规则库 `apiDetailExcelStyle` 的字型槽位（中文 `微軟正黑體`、英文数字 `Times New Roman`、字号 10）并以红色字体标示；不得整格、整行或整段标红。
- 若写入会影响列高，`office-edit-plan` 必须要求目标 workbook 的所有工作表已用行或明确范围执行 Excel COM 行高自适应；含换行文字或合并格的行需按可见内容补足行高，避免文字裁切；同时要求 Office 编辑器不得把一般内容行改成顶端对齐，行高调整后需保持或恢复水平靠左、垂直居中与自动换行。
- 补充设计说明时避免重复灌入多个位置：`涉及BackendAPI` / `後端來源` 只保留调用关系和来源摘要，Redis、fallback、排序等细节放在对应业务逻辑行或字段说明中，除非客户模板明确要求重复列示。
- Office 编辑器保存 API Detail workbook 后，必须交给 `delivery-format-checker` 做格式检查闭环；若检查器产出修复计划，再回到 Office 编辑器保存。
- 交接格式检查器时必须列出本次变更的 sheet 名、`Api_List` 行或范围；若范围无法确认，只做只读检查并先报告风险，不执行全 workbook 字体槽位。
- 在格式检查器显示 `Must fix = 0` 且 `Visual risk = 0` 前，不宣称 workbook 完成。
- 若目标文件被锁定或需要另存，最终报告必须说明。

工作簿格式、`Api_List` 新增、匹配、字体、备份、验证细则都在 `references/api-detail-workbook-rules.md`。

## 时序图交接

本技能只判断时序图影响，不默认生成或修改时序图。

只有在 API contract 已达冻版或近冻版，且用户明确要求更新时序图时，才交给 `native-vsdx-sequence-writer` / `专案原生 VSDX 时序图生成器`。

交接时提供：

- 冻版 PRD/TSD/API Detail/Response Code/Common 证据。
- 需要体现的用户入口、主流程、错误分支、CommonFunc/CommonUtil 引用。
- 需要移除的旧字段、旧 API、旧按钮、旧系统命名。
- VSDX/SVG/PlantUML 现有文件路径与缺口。

详细规则读取 `references/sequence-diagram-handoff-rules.md`。

## 最终回复要求

最终回复需直接说明：

- 使用了哪些权威文件或 registry 条目。
- 改了哪些主档；如果只读分析，也说明未写回。
- 发现的设计缺口、命名问题、来源待确认项。
- 是否可进入开发、是否接近冻版。
- 若交由 Office 编辑器写回 workbook，说明 `office-edit-plan` 范围、`modifiedFiles`、格式检查器交接和验证结果。
- 若有时序图影响，说明已整理为下游交接项，而不是假装已完成 VSDX。
