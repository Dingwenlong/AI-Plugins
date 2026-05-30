---
name: docx-unittest-report
description: 生成 API 测试代码并写回 DOCX UT 测试报告。可选第 05 步：消费第 04 步测试交接，生成或维护 UnitTest / IntegrationTest / Service runtime validation，也可校验 Postman MCP 真实接口调用证据，执行或读取 `.trx`、代码检查、请求/响应 JSON 与状态截图，并输出 `{functionCode}_API_UT 测试报告 {yyyyMMdd}.docx`；不默认修改生产业务代码。关键词：UT 报告、TRX、mockExamples、testCodeHandoff、Postman MCP、真实接口调用。
---

# 【测试验收】API 测试代码与单元测试报告生成器

## 概览

当事实来源仍是 Word 测试报告，但执行证据必须来自 `.NET UnitTest`、`IntegrationTest`、Service runtime validation、Postman MCP 真实接口调用或直接代码检查，而不是浏览器自动化时，使用这个可选第 05 步技能。
建议链路中，在第 04 步业务代码路径与测试交接资料可用后运行本技能。
本步骤负责 UnitTest / IntegrationTest / Service runtime validation 测试源码的生成与维护，也负责把已由 Codex 调用 Postman MCP 取得的真实接口调用证据纳入报告。它消费第 04 步交接资料，创建或更新缺失测试代码，执行或消费测试结果，必要时检查代码路径，解析 `.trx` 或校验请求/响应 JSON 与状态截图，并把状态、实际结果与文字证据写回文件。
API 交付默认基准优先从专案规则库 catalog asset `utChecklistBaseline` 读取；需与每个 API Spec `mockExamples` 情境及第 04 步 runtime 交接一起套用。测试人员对照名单的权威位置是工作区 `<workspaceRoot>/.agent/config/feature-tester-map.json`。技能内 `assets/` 只保留兼容模板与回归 fixture。

Postman MCP 分支只作为「真实接口调用 / Postman MCP 实测」证据层，不得描述为 UnitTest。当前 agent 负责实际调用 Postman MCP，并在报告运行前保存静态 `request.json`、`response.json` 与 `status.png`；本技能脚本只校验证据完整性、敏感信息遮蔽与 HTTP 状态是否符合预期。当前环境若没有可用 Postman MCP 工具，必须将该分支标记为阻塞或待补，不得伪造通过。

默认优先解析插件本地 `references/local-workspaces.json`，可按 `workspaceKey` 指向对应集中 `.agent`。报告脚本可直接传 `--function-code` 解析集中 `.agent/context/<functionCode>`；若未配置集中 `.agent`，仍可显式传旧 `<project-root>\.agent\context\<functionCode>`。

专案规则读取顺序：`--rules-root` > `PROJECT_RULES_ROOT` / 专案环境变量 > `references/local-workspaces.json.rulesRoot` > `<agentRoot>/project-rules/<workspaceKey>`。UT 模板、检查清单、绑定规则与报告语言/层级规则都优先从 `<rulesRoot>/catalog.json` 的 asset 与 rules 读取；测试人员映射只允许从 `<agentRoot>/config/feature-tester-map.json` 读取。缺少规则库、缺少人员映射文件或缺少当前 `functionCode` 对应 Feature ID 时必须阻塞，不能回退到插件内旧 DAWHO 资产、project-rules 旧资产或当前登录名。

## 规则包启动检查

正式第 05 步生成测试源码、绑定证据或输出 DOCX 报告前，必须先解析 `unitTestReport` 规则包：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack unitTestReport `
  --workspace-key "<workspaceKey>"
```

若用户明确给出规则库，改传 `--rules-root "<rulesRoot>"`。脚本输出的 `utReportTemplate`、`utChecklistBaseline`、`utBindingRules` 与测试交接规则，加上工作区 `.agent/config/feature-tester-map.json` 中的测试人员映射，是正式报告的硬输入；`status=blocked` 时，不得输出“符合专案标准”的正式 UT 报告，只能输出草稿、缺口清单或要求补规则库。

## 工作流程

1. 从 `.docx` 报告生成当前 manifest。
2. 从专案规则库 catalog asset `utChecklistBaseline` 读取标准化 API UT 检查清单基准，并按 `P0` -> `P1` -> `P2` -> `P3` 顺序处理。
3. 读取集中 `.agent/context/<functionCode>/apis/<apiId>/*_API_Spec.json` 下的每份 API Spec，并把每个 `mockExamples` 情境都纳入 `UT-01 功能接口范例单元测试`；不要只保留成功情境。
4. 若报告是模块范围，先运行 `analyze_module_scope.py` 产出 `module-scope.json`。
5. 运行 `classify_template_items.py`，在绑定测试前把检查清单章节标记为 `applicable` 或 `not_applicable`。当前 API 不具备的能力，例如 DB、邮件、上传、导出或仅 UI 行为，必须标记为 `接口未涉及`，不要伪造测试。
6. 运行 `build_coverage_gap.py`，检查哪些适用项目仍缺少正确的 UnitTest / IntegrationTest / Service runtime validation / code-inspection 证据。
7. 逐 API 从 `.agent/context/<functionCode>/apis/<apiId>/change-plan.json` 的 `analysis` 读取第 04 步交接，尤其是 `mockExamples`、`testScenarioPlan`、`testTargetFiles`、`serviceRuntimeValidationPlan`、SQL fixture 说明与阻塞项。
8. 对每个使用 DB / SQL 的 API，创建或更新默认 EnterpriseAPI configured-connection runtime validation：载入 EnterpriseAPI `appsettings.json` 连接字符串，使用正式 `SqlDbFactory` / `SqlExecutor` 路径，并对该配置数据库执行 Service SQL。可额外加入 LocalDB / fixture 测试作为辅助检查，但不得替代这项默认证据。在做 EnterpriseAPI configured-connection runtime validation 前，必须先读取第 03 步的 `.agent/context/<functionCode>/apis/<apiId>/db-fixture-report.json`，解析出 03 实际准备 fixture 的目标库（target name + targetDatabase + environment）。若该 API 依赖 SQL fixture，且 05 的 configured-connection 目标库与 03 的 fixture 目标库不一致，必须在报告中显式标记该不一致（例如「05 验证库与 03 准备库不同，seed 可能不在被验证库中」），不得静默当作已验证；无法确认被验证库包含 03 的 seed 时，该 `UT-07` / runtime 证据应标 `不通过` 并写 `原因：...`。
9. 若交付要求真实接口调用，由 Codex 调用 Postman MCP，并在 `.agent/context/<functionCode>/ut-report/postman-mcp/<apiId>/<scenarioId>/` 保存 `request.json`、`response.json` 与 `status.png`。保存前必须遮蔽 `Authorization`、`Cookie`、API key、token、password、secret 等敏感值。
10. 收集证据前，在测试项目下创建或更新缺失的 UnitTest / IntegrationTest / Service runtime validation 测试源码。手动编辑使用 `apply_patch`，除非用户明确要求修业务代码，否则不要改生产业务代码；若测试暴露生产业务代码缺陷，按「测试代码生成职责」写入 `test-defect-handoff.json` 回交第 04 步，并把对应检查清单项标为 `不通过`。
11. 可选运行 `apply_manifest_gap_fixes.py`，只套用安全修复：manual-mode 修正、code-inspection 配置与高可信测试绑定建议。
12. 填写 `metadata`、`unitTest`，以及可选的 `integrationTest`。
13. 每个 `unit_test` 或 `integration_test` 项目都需绑定明确的 `testBindings.testNames`；每个代码/文件/模板检查项目使用 `mode: "code_inspection"`，并填写对应证据路径与简短人工证据文字；每个真实接口调用项目使用 `mode: "api_runtime_call"`，并填写 `apiRuntimeCall.requestPath`、`responsePath`、`screenshotPath` 与 `expectedStatusCodes`。
14. 运行 `run_report_job.py`；它会按需执行已配置命令、解析 `.trx`、检查代码路径、校验 Postman MCP 证据并写回 DOCX。
15. 正式交付时，最终 Word 报告命名为 `功能编号_API_UT 测试报告 yyyyMMdd.docx`；其中 `功能编号` 使用当前 `.agent/context/<functionCode>` 目录名，`yyyyMMdd` 使用实际报告生成日期。
16. 正式交付时，运行 `compact_report_outputs.py`，只保留最终 `.docx`、最终 manifest、最终 results、可选 `.trx`，并保留 `postman-mcp/` 下被 manifest/results 引用的请求、响应与截图证据。
17. 视觉抽查最终 `.docx`；若版面精度重要，使用 `doc` 技能渲染闭环。

## 技能前提

- Word 文件中的第一张表是报告表头。
- 后续表格是 UT/UAT 章节。
- 两列表格是检查清单式章节。
- 三列表格是需求/实际结果对照章节。
- 美化版模块模板由 `build_module_visual_report.py` 处理，不再交给旧检查清单解析器。
- `build_module_visual_report.py` 同时支持旧版四表美化模块模板与当前分类 API UT 模板。
- `build_module_visual_report.py` 默认使用专案规则库 catalog asset `utReportTemplate`。除非调用者明确传入 `--template-docx`，否则使用该模板。
- 专案规则库中的分类模板是后续模板编辑的唯一事实来源。桌面副本与技能内置副本仅作为交付/调试或兼容副本，不得作为并行模板维护。
- 分类模板包含报告表头与 `编号 / 测试内容 / 测试结果` 检查清单表。生成时必须替换 `{功能编号}_{功能名称}`、`{Today:yyyy/MM/dd}`、`{姓名}` 等模板占位符。
- 正式分类报告的页眉必须呈现为 `UT自测报告`；不要保留模板专用文字 `UT自测报告模板`。
- 正式分类报告的页眉、封面文字、汇总表、API 标题、检查清单表与生成替换文字都必须使用 `微软雅黑`。
- 正式分类报告的第一笔 `Revision History` 需写入初版记录、日期 `{Today:yyyy/MM/dd}`，说明为 `初版，由 {测试人员} 测试。`，并使用与汇总表一致的测试人员姓名。相关栏位及其值都必须置中。
- 分类报告中，功能显示名称应从 `execution-state.specDocxPath` 解析成 `{functionCode} {TSD title}`，例如 `B.003 登录前检核与公告`；若可取得 TSD 标题，不要回退成 `{functionCode} 功能模块`。
- 报告证据/检查清单列只显示模板要求的业务 API 路径或测试内容；最终表格不要输出原始 `API ID`。
- 分类报告中，`实际测试结果` 行必须使用正式计数格式 `通过 x 项 / 不通过 y 项 / 不适用 z 项`。该行不要追加 `如预期结果` 或 `未如预期结果`。
- 分类报告中，`实际测试结果` 计数必须以可见检查清单行结果为事实来源，而不是以底层 UnitTest/IntegrationTest 方法数量为准。因此总汇总与每个 API 区块结果都必须和生成清单中标记为 `通过` / `不通过` / `不适用` 的行一致。
- 只有在同一全通过条件成立时，才能勾选 `符合需求`；任何失败、跳过、待处理或其他非通过测试都会保持 `不符合需求` 勾选。
- 正式分类报告在 `汇总` 表后不得输出功能级整体 Test Explorer 截图；只保留 `汇总` 结果表，然后继续生成各 API 明细章节。
- 模板不得显示字面占位符 `{UnitTest VS执行总截图}`，分类模板也不应保留空白的整体截图占位行。
- 分类模板中，每个 API 明细章节的 API 显示名称应作为 Word `Heading 1` 放在表格外。因为 `汇总` 是第一个导航标题，API 标题必须从 `二、Setting/GetUserAlias` 开始，再依序为 `三、...`。不要把 `测试 API：{API名称}` 放在正式报告的表格单元格内。
- 每个 API 明细章节包含该 API 的通过/失败计数表、该 API 的 UnitTest 证据截图，以及该 API 自己的检查清单行。正式报告中不要渲染字面标题 `测试内容清单`。
- 每份生成的 API 检查清单中，`UT-01 功能接口范例单元测试`、`UT-02 API 契约与回应格式` 以及后续类别名称，都应作为 Word `Heading 2` 段落放在检查清单表外。表格本身只包含 `编号 / 测试内容 / 测试结果` 行。
- 每个生成的 API 区块都必须复制标准化检查清单类别。复制后的清单中，`UT-01` 会把当前 API Spec Excel / `mockExamples` 的每个情境展开成 `UT-01-01`、`UT-01-02` 这类独立行；`UT-02` 与后续检查类别也要复制到同一 API 下。
- 检查清单内容文字在适用时必须使用一致结构：原始测试项目、`验证重点：...`、`适用判定：...`、`验证方式：...`。正式报告不要使用旧标签 `建议验证方式：`。
- `UT-01` 的 mockExamples 行保留第一行为情境内容，只补 `验证方式：UnitTest`；不要额外加入会重复显而易见信息的通用 `验证重点` 或 `适用判定`。
- `UT-01` 动态生成行必须使用与后续 UT 行相同的检查清单正文字号；分类模板当前为 9pt。
- 当检查清单行被归类为当前 API 范围外时，`测试结果` 单元格必须填写 `不适用`；不要因为该 API 已执行测试全部通过就填 `通过`。汇总行也要维持相同边界，把这些行计入 `不适用 z 项`。
- 每个 API 及整体模拟截图只能来自当前功能 API 选定的测试。不要为了让截图更饱满而展示无关功能、模块或项目的测试。
- 若 Word 模板用带边框的空白段落模拟封面边框，生成报告时必须改用第一节页面边框，让封面边框覆盖整个第一页，且不要出现在第二页或报告正文页。
- 分类报告中，`测试人员` 只允许从工作区 `<workspaceRoot>/.agent/config/feature-tester-map.json` 读取，并用报告 `functionCode` 匹配项目计划中的 `Feature ID`。不要沿用之前按秒数轮换的规则；若 map 中缺少 Feature ID，必须阻塞并维护 `.agent` 名单，不得回退为当前登录显示名。
- 仅靠文件文字不足以推断测试名称。每个启用的 `unit_test` 或 `integration_test` 项目都必须绑定明确的 `testBindings.testNames`。
- 接口契约、验证规则、响应 schema、查询结构、下载与通知流程等检查项，在无需 runtime 测试时可用直接代码检查验证。
- 自动化结果可以来自 `.trx`，也可以来自直接代码检查证据。
- 真实接口调用结果可以来自 Postman MCP 保存的静态请求/响应 JSON 与状态截图；它是 `api_runtime_call` 证据层，不是 UnitTest，也不替代应有的 UnitTest / IntegrationTest / Service runtime validation。
- 如果第 04 步提供了测试交接，但引用的测试缺失或已过期，本技能必须先生成或修补测试。不要把缺失测试写成通过报告项目。
- 本技能负责维护相关测试文件，例如 `Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/*ControllerTest.cs`、`Test/UnitTesting/EnterpriseAPI/EnterpriseApiUnit/*ServiceTests.cs`、`Test/IntegrationTesting/EnterpriseAPI/EnterpriseApiIntegration/*ControllerTests.cs` 及相关测试支持 fixture。
- 第 05 步可新增或更新测试源码注释与方法名，让证据更易读。对生成或大幅修改的测试，优先使用包含 `测试目的`、`验证情境`、`预期结果` 的 XML 注释。
- 标准化 API UT 检查清单只是基准，不是伪造测试的理由。检查项超出当前 API 范围时，只有在文字或证据需要说明时写 `接口未涉及`，并将检查清单 `测试结果` 设为 `不适用`。
- 分类 UT 报告中，`UT-01` 保留给当前 API Spec Excel / `API_Spec.json.mockExamples` 情境。标准化 API UT 检查清单类别从 `UT-02` 开始。
- 生成 API 测试或撰写报告证据前，先查看 `references/api-ut-layering-rules.md`。

## 测试代码生成职责

- 第 04 步之后，本技能是 UnitTest / IntegrationTest / Service runtime validation 测试源码生成的事实来源。
- 不要期待 `api-code-writer` 创建或修改测试源码；应消费它提供的 `testScenarioPlan`、`testTargetFiles`、`serviceRuntimeValidationPlan`、SQL fixture 说明与阻塞项，作为测试实现简报。
- 生成的测试必须覆盖 `API_Spec.json.mockExamples` 所代表的每一个 API Spec Excel 范例。若现有测试已覆盖某个范例，则复用并绑定精确测试名称；否则创建或修补测试。
- 报告检查清单中，应把 `mockExamples` 在 `UT-01 功能接口范例单元测试` 下展开为 `UT-01-01`、`UT-01-02` 等行。若没有可解析范例，保留一条说明性的 `UT-01-01` 行，并把证据标为阻塞或需要补齐 spec/example；不要伪造通过测试。
- 范例单元测试必须断言完整输出契约，包括 `isSuccess`、`responseCode`、`responseMessage`、`data`、验证失败形状与重要映射字段，不要只检查是否未抛异常。
- 只在正确边界使用 mock。参数验证、DTO 验证、Controller model binding、Controller 契约测试与外部系统隔离，可在测试目的限于该层时使用 mock 依赖。Service 业务行为测试必须执行真实 Service 方法；不要 mock Service 本身后声称已验证 Service 逻辑。
- 对有 DB / SQL / `queryContracts` / `backendApis.DB` 的 API，默认至少生成两类证据：用于情境与映射覆盖的 mock-based UnitTests，以及会载入 EnterpriseAPI `appsettings.json` 连接字符串、使用正式 `SqlDbFactory` / `SqlExecutor` 路径，并对配置数据库执行 Service SQL 的 IntegrationTest / Service runtime validation。
- LocalDB / SQL fixture 测试可作为受控 seed、映射、join 与排序的辅助证据，但不能替代默认的 EnterpriseAPI configured-connection runtime validation。不要把 configured-connection validation 放进狭窄的 UnitTest 项目，不要静默用 LocalDB 证据替代它；当配置数据库登录、权限、schema 或网络不可用时，也不要把它标为通过。
- Mock SQL executor 测试可以证明 request 映射、分支选择、参数绑定与 response 转换，但不得描述为已经证明 SQL 语法、join、排序或 production runtime 行为正确。
- 用 mock Service 替代 Service 的 Controller IntegrationTests 只属于 route、authentication、serialization 与 envelope smoke test。业务行为必须由真实 Service 测试证明，或明确标记为等待 fixture 证据。
- 如果检查清单项目声称验证 “Service logic”、“business rules”、“DB / SQL”、“field mapping from persistence”、“transaction result” 或任何下游 Service 执行行为，证据必须包含真实 Service-method 执行路径。窄范围 UnitTest 分支覆盖可以 mock `ISqlExecutor`、Redis 或外部 gateway，但它不能作为下游 runtime 行为的唯一证据。
- 当测试暴露生产业务代码缺陷时，不要在报告步骤中静默修改生产代码，而是回交第 04 步：在 `.agent/context/<functionCode>/apis/<apiId>/test-defect-handoff.json` 写入回交物，字段至少为 `apiId`、`defectSummary`、`failingTests`/`evidencePaths`、`suspectedFiles`、`classification`（沿用既有 `code_issue` 等口径）、`suggestedOwner: "04-api-code-writer"`、`nextDecisionNeeded`、`status`（`open`/`resolved`）。同时把对应 UT 检查清单项的证据标为 `不通过` 并写 `原因：…`，不得写成通过。除非用户明确要求本技能也修补业务代码，否则生产代码修改仍属于第 04 步；第 04 步 `prepare` 检测到 `status=open` 的该回交物会把该 API 回退为 `pending` 返工。
- 正式报告文字必须便于人工阅读。用自然中文描述已验证的业务行为与结果；除非模板要求，不要把内部测试方法名、JSON key、fixture 接线或自动化术语堆进用户可见单元格。

## API UT 检查清单与证据分层

- 默认 API 检查清单基准：专案规则库 catalog asset `utChecklistBaseline`。
- 默认分层规则：`references/api-ut-layering-rules.md`。
- 分类报告必须把 `UT-01` 保留给 API Spec Excel / `mockExamples` 中的功能接口范例 UnitTests；标准化基准检查清单从 `UT-02` 开始映射。
- 含 DB / SQL 类别的分类报告在 DB query/add/update/delete 类别前包含 `UT-07 DB / SQL 执行环境验证`。没有 DB / SQL 依赖的 API，该类别每一行都必须标为 `不适用`。
- 不要把宽泛环境前提 `EnterpriseAPI 配置连接字符串可正常开启` 纳入单一功能检查清单。它属于专门的 configured-connection IntegrationTest / Service runtime validation 套件；功能报告只保留 API 相关的 SQL 执行、schema/table/column 与 DB 权限行，作为 DB-backed API 的 runtime 证据边界。
- DB-backed API 缺少 EnterpriseAPI configured-connection runtime 证据时，受影响的 `UT-07` 检查清单结果必须显示 `不通过`，并用简短 `原因：...` 说明缺失证据，例如缺少 configured-connection Service SQL 执行、缺少配置数据库 schema/table/column 检查，或缺少 DB 权限检查。
- `UnitTest` 覆盖 API 范例、DTO 验证、Service 业务分支、response code、边界值与 mock 依赖失败。
- `Controller integration` 覆盖 route、HTTP method、model binding、authorization、filters、serialization 与 envelope wiring。若 Service 被 mock，不要描述为业务逻辑证据。
- `Service runtime validation` 覆盖完整 Service 逻辑链，尤其是真实 SQL 执行、join、排序、字段映射与交易结果。
- 不要把 “mock-free” 当成目标；目标是证据处在正确层级。验证与契约检查可 mock 下层依赖；Service 下游逻辑必须真实执行 Service method，并在 DB / SQL 行为属于需求时使用 runtime validation。
- `IntegrationTest` 覆盖关键 Controller + Service + fixture 接线与 runtime 边界。
- `Code inspection` 在 runtime 测试不必要时，覆盖 route attributes、authorization annotations、logging、sensitive-data masking 与 static configuration。
- `API runtime call` 通过 Postman MCP 调用已部署或本地运行的 API，覆盖真实 HTTP 入参、回包、状态码与接口可达性；它必须保存静态 request/response JSON 与 status PNG，且不得携带未遮蔽敏感信息。
- `File inspection` / `Template inspection` 覆盖导出文件、邮件模板、生成文档内容、文件命名与模板变量；不要发送真实邮件，也不要依赖真实打印机。
- 仅 UI 项目、前端控件行为、固定环境效能阈值、真实外部系统交付，以及没有相关能力的 API，不得被硬塞进 UnitTest。应标记为 `接口未涉及`、`code_inspection` 或适当的非 UnitTest 证据层。
- DB / SQL configured-connection 证据因登录、权限、schema、seed data、网络或配置测试连接缺失而不可用时，只保留 mock-based UnitTest 作为情境/映射覆盖证据，并用克制的人类可读文字报告 configured-connection runtime validation 缺口。不要把默认要求降级为仅 LocalDB 证据。
- EnterpriseAPI configured-connection SQL 执行、Service SQL runtime 执行、schema/table/column 一致性与最小权限 DB 权限检查，只适用于 DB-backed API。上线准备行 `上线前环境验证条件需保留确认记录` 是上线前确认项目，应在 UT 报告中标为 `不适用`，不要因 UnitTest 结果而自动通过。

## 快速开始

初始化 manifest：

```powershell
python "<pluginRoot>\skills\docx-unittest-report\scripts\bootstrap_manifest.py" `
  "D:\Path\To\Report.docx"
```

manifest 完成后运行完整流程：

```powershell
python "<pluginRoot>\skills\docx-unittest-report\scripts\run_report_job.py" `
  "D:\Path\To\Report.job.json"
```

若 `.trx` 已存在且只需写回 DOCX：

```powershell
python "<pluginRoot>\skills\docx-unittest-report\scripts\apply_report_results.py" `
  "D:\Path\To\Report.job.json" `
  "D:\Path\To\Report.results.json"
```

美化版模块报告需生成一份模块级 DOCX，每个 API 对应一张浏览器截取的 Visual Studio 风格证据图。

```powershell
python "<pluginRoot>\skills\docx-unittest-report\scripts\build_module_visual_report.py" `
  --context-root "D:\Path\To\.agent\context\B.003"
```

若省略 `--output-docx`，`build_module_visual_report.py` 会写到：

```text
.agent/context/<functionCode>/ut-report/<functionCode>_API_UT 測試報告 <yyyyMMdd>.docx
```

显式提供 `--output-docx` 时也使用同一文件命名规则。保留 `.docx` 扩展名，不要输出 `.docs`。

为无界面的 Postman MCP 调用结果补状态截图：

```powershell
python "<pluginRoot>\skills\docx-unittest-report\scripts\postman_mcp_evidence.py" render-status `
  --request ".agent\context\<functionCode>\ut-report\postman-mcp\<apiId>\<scenarioId>\request.json" `
  --response ".agent\context\<functionCode>\ut-report\postman-mcp\<apiId>\<scenarioId>\response.json" `
  --output ".agent\context\<functionCode>\ut-report\postman-mcp\<apiId>\<scenarioId>\status.png" `
  --expected-status 200
```

美化版模块报告交付/内容规则：

- 每个功能/模块生成一份正式 UT 报告，不要把多个功能编号合并成单一交付报告。
- 使用分类模板的模块模式报告中，`汇总` 页面只放汇总结果表；其后按 API 循环生成完整 API 小节：API 名称作为 `Heading 1`、通过/失败计数、API 证据图，以及该 API 自己的检查清单行。
- 分类模板输出中，顶部汇总表必须在第一个 API detail `Heading 1` 前结束；不要把 API detail 行合并进汇总表。
- 分类模板输出中，封面保留在第 1 页，`Revision History` 在第 2 页，`汇总` 章节从第 3 页开始。
- 旧模块模式报告模板中，每个 API 占一行证据列：左格放一张 Visual Studio 风格证据图，右格只放 API 显示名与简洁实际结果文字。
- 交付文件名不得包含字面 token `auto`。
- 不输出 `自动化证据摘要` 内容，也不渲染标题文字 `自动化证据摘要`。
- 最终 API/证据区域不要输出 `相关测试` 标签或测试名称清单。
- 若项目不属于当前 API/模块范围，写 `接口未涉及`；不要写 `未纳入本次执行`。
- 优先使用 UnitTest/IntegrationTest 证据；但当检查清单项目无法只靠测试有效覆盖时，应直接检查代码路径并使用代码检查证据，避免适用项目仅因没有 runtime test 而空着。
- 正式报告文字必须像人工撰写的 UT 报告，而不是原始自动化输出。摘要应以自然繁体中文描述已验证的业务行为、情境覆盖与结果；除非模板明确要求，避免暴露内部测试类名、方法名堆叠、JSON key、工具术语或实现产物。
- 当 API 有 DB / SQL / 真实 Service runtime validation 要求时，应以人能理解的方式区分证据类型：mock-based UnitTests 可描述为「依规格范例验证输出契约与映射逻辑」，LocalDB/fixture tests 可描述为「以测试资料库验证 Service 查询、排序、Join 与栏位转换」，EnterpriseAPI configured-connection tests 可描述为「以 EnterpriseAPI 设定连线验证正式 SQL 可执行」。不得让 mock SQL 或 LocalDB fixture 证据暗示已经验证 configured database SQL 执行。
- 若 DB-backed API 缺少或未通过 EnterpriseAPI configured-connection 证据，报告需使用克制且可读的说明，例如「本次已完成规格范例与 Service 映射逻辑验证；EnterpriseAPI 设定连线 SQL 执行因测试资料库连线、权限或环境资料未就绪，需补齐后确认。」不得把该 API 描述为已完成完整 production-runtime 验证。
- 最终正式文字中，摘要/结果文字不要出现 `待补`。除非用户明确要求额外状态分类，模块实际结果文字只保留交付版通过/不通过视角。
- 最终正式文字中，若分类检查清单把部分行标为不属于当前 API/模块范围，应包含 `不适用` 数量。
- 最终实际结果文字不要提及生成了多少张证据图。
- 最终结果文字中，所有非通过状态都计为 `不通过`；不要输出 `如预期结果` / `未如预期结果`，只有功能收集到的测试全部通过时才勾选 `符合需求`。
- 写入最终 DOCX 时，保留所选模板的页眉/页脚，并保留 `报告日期` 单元格底边框。
- 用 `yyyy/MM/dd` 格式的实际生成日期替换报告日期占位符与过期模板日期。更新封面独立日期段落、`报告日期` 单元格与 `测试日期` 单元格；不要改写文件名日期 token，或测试名称、路径、日志、来源证据中的历史日期。
- 交付报告中的表格单元格内容应保持垂直居中；脚本改写单元格时，段落 `段后` 间距应使用 auto。

美化版模块报告证据图规则：

- 模块报告模板默认使用专案规则库 catalog asset `utReportTemplate`。只有明确需要覆盖时才传入 `--template-docx`。
- 生成的 UI 文字保持繁体中文。
- 只使用真实测试结果数据进行确定性 HTML/CSS 渲染；不要用 AI 生成图片或之前生成的图片作为视觉证据。
- 使用 Playwright/Chromium 截取生成的本地 HTML 页面，并在每张证据 PNG 旁保留同名 `.html` 文件，供视觉微调。
- 只渲染普通 Test Explorer 证据区：已完成运行状态列加结果表格。除非用户明确要求，不要渲染标题栏、工具栏/功能按钮、搜索框或右侧详情面板。
- 分类报告不要生成或插入功能级整体截图。每张 API 截图只包含该 API 选定测试。
- 所有状态图标必须使用相同宽高。已执行且成功的行一律使用绿色勾选图标；最近一次成功执行分支使用实心绿色勾选，其他成功行使用空心绿色勾选。蓝色空心菱形感叹号表示未执行，失败行使用红色关闭图标。
- 展开最近一次执行分支下的每个已执行项目，让所有已执行测试案例都能在证据图中看见。
- Visual Studio Test Explorer 的 IDE UI 源码并不公开；应根据用户提供的真实截图与公开的 Visual Studio Test Explorer 行为文档调整 HTML/CSS，不要声称做到源码级一致复刻。

## Manifest 规则

- 顶层执行区块是 `unitTest`、可选 `integrationTest` 与每个 case 的 `apiRuntimeCall`，不是 `playwright`。
- `mode` 只允许 `unit_test`、`integration_test`、`api_runtime_call`、`code_inspection`、`manual` 或 `skip`。
- 当前 manifest 不使用 `driver`、`request`、`steps`、`assertions` 与截图捕获区块。
- 启用的 `unit_test` 与 `integration_test` 行必须提供 `testBindings.testNames`。
- 启用的 `code_inspection` 行必须提供 `codeInspection.evidencePaths` 与必要 token 规则。
- 启用的 `api_runtime_call` 行必须提供 `apiRuntimeCall.requestPath`、`responsePath`、`screenshotPath` 与 `expectedStatusCodes`；它不需要 `.trx` 或 `testBindings.testNames`。
- 默认匹配规则为 `matchMode: "all_pass"`。
- 当 `allowMissing: false` 时，缺少测试结果默认视为阻塞。
- 当源工作区受到 `bin/obj/ref/*.dll` 锁定影响时，`integrationTest.cleanWorkspace` 可在执行测试命令前准备一份干净 repo 副本。

## 写回行为

- 表头表格：
  - `metadata.apiDisplayName`、`tester` 与 `testDate` 更新报告表头。
  - 除非明确覆盖，`actualSummary` 与 `overallStatus` 由 `results.json` 计算。
- 两列表格：
  - 左栏只使用交付版正式状态。
  - 优先使用 `通过` / `不通过` / `不适用`；除非用户明确要求草稿风格报告，正式分类检查清单结果中不要出现 `失败` 或 `待补`。
  - 当项目不属于当前 API/模块范围时，使用 `接口未涉及`。
- 三列表格：
  - 中间栏写入 `actualResult`。
- 每个处理过的章节都要新增或复用一个合并摘要行。
- 摘要行必须保持精简：
  - 只保留类似 `共 a 项检查，已执行 b 项，其中通过 c 项、失败 d 项。` 的一句话。
  - 若必须显示不适用/范围外数量，只追加一句类似 `另有 e 项接口未涉及。` 的文字。
  - 不要使用 `已回填` 等措辞。
  - 不要提及生成图片数量。
  - 不要写 `自动化证据摘要` 或类似标题。
  - 不要写结论、失败细节、待办清单、绑定关系或附件路径。

## 失败规则

- 若第 04 步交接说明某情境需要 UnitTest / IntegrationTest / Service runtime validation，但没有合适源码测试，报告前必须生成或修补测试。若必要 fixture 或依赖不可用，应将证据标为阻塞，不得写出误导性的通过结果。
- 若检查清单项目仅属于 UI、前端控件、固定环境性能、真实外部交付，或超出当前 API 功能范围，不要生成假的 UnitTest。应按实际范围标为 `接口未涉及`、`skip` 或 `code_inspection` 证据。
- `testBindings.testNames` 完整前，不要启用 `unit_test` 项目。
- `testBindings.testNames` 完整前，不要启用 `integration_test` 项目。
- `codeInspection.evidencePaths` 完整前，不要启用 `code_inspection` 项目。
- `apiRuntimeCall` 的请求 JSON、响应 JSON、状态截图与预期 HTTP 状态码完整前，不要启用 `api_runtime_call` 项目。
- Postman MCP 证据中若出现未遮蔽的 `Authorization`、`Cookie`、API key、token、password 或 secret，应先清理证据并重新生成，不得写成通过。
- API 实际调用返回状态码不符合 `expectedStatusCodes` 时，应保留失败证据并写成不通过；缺少证据、JSON 无法解析或状态码不可解析时必须阻塞。
- 不要从 DOCX 文字推断测试名称。
- 若提供 `unitTest.command` 或 `integrationTest.command`，它必须产出本技能可消费的 `.trx`。
- 若 `failIfTrxMissing` 为 `true` 且无法解析 `.trx`，需停止。
- 若绑定测试缺失且 `allowMissing` 为 `false`，需停止，不要写入误导性的通过结果。
- 若测试失败指向生产代码，保留失败证据并分类缺陷，写入 `.agent/context/<functionCode>/apis/<apiId>/test-defect-handoff.json`（`status=open`、`suggestedOwner: "04-api-code-writer"`，字段见「测试代码生成职责」），并把对应检查清单项标为 `不通过` 且写明 `原因：…`。除非用户明确扩大本步骤范围，否则生产代码修改属于第 04 步；不得为了让报告通过而静默改生产码或把回交项写成通过。

## 脚本

- `scripts/bootstrap_manifest.py`
  - 解析 Word 报告并产出起始 manifest。
- `scripts/analyze_module_scope.py`
  - 读取 `.agent/context/<moduleCode>`，产出包含模块 API、代码路径、测试路径与高层特征的 `module-scope.json`。
- `scripts/classify_template_items.py`
  - 读取 `module-scope.json` 与 `template-outline.json`，产出章节/项目适用性与建议测试层级。
- `scripts/build_coverage_gap.py`
  - 将分类结果与 manifest/results 比对，产出 `coverage-gap.json` 与可读的改进计划。
- `scripts/apply_manifest_gap_fixes.py`
  - 只套用 coverage-gap 输出中的安全 manifest 修复：manual-mode 修正、code-inspection 配置与强规则测试绑定建议。弱规则匹配保留在 autofix 报告中待审。
- `scripts/trx_result_utils.py`
  - 解析 `.trx` 并规范化 UnitTest 结果。
- `scripts/collect_unittest_results.py`
  - 可选执行已配置的 UnitTest/IntegrationTest 命令、检查代码路径、解析 `.trx`、校验 Postman MCP 真实接口调用证据并产出 `results.json`。
- `scripts/postman_mcp_evidence.py`
  - 校验 Postman MCP `request.json` / `response.json` / `status.png` 证据，检查敏感信息遮蔽与 HTTP 状态；也可为无界面调用结果生成确定性的状态截图。
- `scripts/apply_report_results.py`
  - 更新 DOCX 表头、项目状态与文字证据列。
- `scripts/run_report_job.py`
  - 编排 UnitTest/IntegrationTest/Postman MCP 证据收集与 DOCX 写回。
- `scripts/compact_report_outputs.py`
  - 将最终 manifest/results 提升为标准名称，保留 Postman MCP 证据目录，并删除正式交付不需要的调试旁支文件。
- `scripts/build_module_visual_report.py`
  - 读取 `.agent/context/<moduleCode>`，从 `report-job.results.json` 或 `.trx` 收集各 API 结果，渲染确定性的繁体中文 Visual Studio Test Explorer HTML 页面，用 Playwright/Chromium 截图，并把美化版模块报告按每张图片一行填入。

## 参考

- JSON 契约见 [references/manifest-format.md](references/manifest-format.md)。
- API UT 检查清单分层、非 UnitTest 项目与报告措辞规则见 [references/api-ut-layering-rules.md](references/api-ut-layering-rules.md)。

## 资源

- `assets/sample-results.trx`
  - 技能回归测试使用的小型 `.trx` fixture。
- project-rules catalog asset `utBindingRules`
  - 可配置的强/弱绑定规则，用于把检查清单项目映射到既有测试名称。
- project-rules catalog asset `utReportTemplate`
  - 默认 Word UT 报告模板。`UT-01` 保留给来自 API Spec Excel / `mockExamples` 的功能接口范例；标准化 API UT 检查清单类别从 `UT-02` 开始。
- project-rules catalog asset `utChecklistBaseline`
  - 默认标准化 API UnitTest 检查清单基准，包含 P0/P1/P2/P3 优先级排序与非 API 删除说明。
- `<workspaceRoot>/.agent/config/feature-tester-map.json`
  - 从专案计划来源抽取的 Feature ID 到 `测试人员` 映射；分类报告以此作为唯一测试人员事实来源。
- `.agent/context/<functionCode>/apis/<apiId>/test-defect-handoff.json`
  - 当测试暴露生产业务代码缺陷时，本步骤写入的缺陷回交物（`status=open`、`suggestedOwner: "04-api-code-writer"`）；由第 04 步 `prepare` 读取并把该 API 回退为 `pending`，修复后改 `status=resolved`。
- `UnitTest/`
  - Python `unittest` regression coverage for the skill.

## Leader Mode

当由 `multi-api-leader` 显式编排时：

- 05 的测试代码也必须按 `file-claims.json` 分配，避免多个 worker 同时写同一测试文件。
- worker 只能写已 claim 的测试代码或测试辅助文件，不能写最终 DOCX 报告、manifest/results 或 `final-assessment.json`。
- leader 汇总第 04 步 `testCodeHandoff`、mockExamples、trx/Postman/code-inspection 证据，统一生成或更新 UT 报告。
- `final-assessment.json` 只能由 leader 生成；只有 02/03/04/05 gate 全部通过时，才可判定“符合需求”。
