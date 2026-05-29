---
name: 专案交付中枢：【交付文件】专案交付文件格式检查器
description: 检查 TSD Word 与 API Excel 的交付格式，产出格式问题清单、office-edit-plan 与验收结论。用于文件命名、章节/工作表结构、必要表格、可见栏位、字体、对齐、繁体中文、版面与视觉 QA；实际 .docx/.xlsx 写入交给专案 Office 交付文件编辑器；不判断业务逻辑、接口语义或字段业务含义。关键词：TSD DOCX、API XLSX、格式检查、office-edit-plan、视觉 QA。
---

# 【交付文件】专案交付文件格式检查器

## Office Edit Plan Contract

When creating or handing off `office-edit-plan.json`, include `schemaVersion: "1.0.0"`, `claimId`, `targetFiles[]`, `allowedOperations[]`, `forbiddenOperations[]`, and `validation[]`. The Office editor result must echo the `claimId` and report `modifiedFiles` plus `validationCommands`.

## 上下文策略

入口只保留格式检查流程、格式规则裁决、修复计划与验收。先解析当前 workspace，读取 `<rulesRoot>/catalog.json`，再按 `delivery-format`、`api-detail-workbook` 或 docx/xlsx asset 载入专案规则与样式配置。找不到专案规则库时，技能仍可执行通用结构检查，但专案专属格式判断必须标记为「缺少专案规则」，不得从插件内旧个案 reference 偷读预设规则。实际保存 `.docx` / `.xlsx` 时交给 `专案 Office 交付文件编辑器`，不要在本技能中直接写入交付文件。

遇到「系统设计规范 v2.5 / 设计规范 / TSD 格式 / API Detail 格式标准 / 字型规则 / API清单 格式」相关任务时，优先读取专案规则库中的对应 category；技能内 `references/`、`configs/` 仅作历史兼容、fixture 或迁移说明。

### 规则包启动检查

正式 TSD/API Detail 格式检查或修复前，必须先解析 `deliveryFormat` 规则包：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack deliveryFormat `
  --workspace-key "<workspaceKey>"
```

若用户明确给出规则库，改传 `--rules-root "<rulesRoot>"`。脚本输出的 `apiDetailExcelStyle` 与格式规则是专案格式判断的硬约束；`status=blocked` 时，只能执行通用结构检查或标记 `缺少专案规则`，不得宣称通过专案格式标准，也不得用技能内旧样式配置替代外置规则。

## 工作流程

预设流程是先检查、再列问题；只有在使用者确认后才生成修复计划并交给 Office 编辑器，修改后再由本技能验证。

1. 确认输入是 TSD `.docx`、API 规格 `.xlsx`，或包含这两类文件的资料夹。
2. 若输入是 TSD `.docx`，优先执行内建结构检查器：

```bash
python scripts/check_tsd_docx.py "path/to/TSD.xxx.docx" --format json
```

只有在呼叫者希望遇到阻断性合规错误时命令失败，才使用 `--strict-exit`。

3. 若输入是 API 规格 `.xlsx`，先执行只读检查脚本，产出 API worksheet 识别、分区顺序、合并范围、`A:G` 样式、`H:AZ` 空白区污染、底部残留样式与 `Api_List` 跳转检查结果：

```bash
python scripts/check_api_xlsx_format.py "path/to/API_DETAIL.xlsx"
```

此脚本优先读取专案规则库 catalog 中的 `apiDetailExcelStyle` 样式配置；`references/raw/Regression_Example.xlsx`、`references/api-detail-regression-standard.md`、`references/system-design-standard-v2.5-format-rules.md` 与技能内 `configs/` 只保留历史兼容与迁移参考。不要判断接口业务正确性。
4. 仅检查文件/表格层面的结构、必要可见内容、表格存在性、格式、字型规则、繁体中文、页面设定、页尾与视觉风险。
5. 在 TSD 中，将 `API清单` 视为 Word 文件内的表格：
   - 检查表格是否存在于预期章节。
   - 检查表头与必要储存格是否存在。
   - 检查表头水平/垂直置中、资料列垂直置中、资料列水平居左或左右对齐、粗体/斜体漂移。
   - 针对 `API清单` 表格本身检查中文 `微软正黑体`、英文/数字 `Times New Roman` 与繁体中文，不只依赖全文层级检查。
   - 检查交付用词：TSD 可见文字中不得使用 `校验`；依语境改为 `验证`（验证流程/结果）或 `检核`（检核项目/清单）。
   - 不验证 API 业务正确性、API Detail 活页簿、后端来源、栏位语义、范例、必填规则或业务规则。
6. 产出修复前问题清单：
   - `Must fix`: 阻断文件合规或必要结构。
   - `Should fix`: 文件歧义、必要可见内容缺漏、或可能影响审查的格式漂移。
   - `Naming`: 档名、工作表名、标题、章节名称或可见标签问题。
   - `Visual risk`: 需要透过 Word/Excel 渲染或人工视觉检查确认的版面风险。
   - `Covered`: 已通过或已覆盖的检查。
7. 每个问题都要包含位置、现况、建议修改、原因与影响。
8. 使用者确认要修哪些问题前，不要修改文件。确认后：
   - 生成 `office-edit-plan`，列出文件、sheet/章节/row/cell/range、允许操作、禁止操作、验证命令与视觉 QA 要求。
   - 将计划交给 `专案 Office 交付文件编辑器` 执行保存；本技能只接收其 `modifiedFiles`、验证命令、风险与 blocker。
   - XLSX 修复闭环固定为「检查范围 -> office-edit-plan -> Office 编辑器保存 -> 字型槽位收尾（如需要）-> 结构复验 -> artifact-tool inspect/render -> 使用者报告」。
   - XLSX 格式修复不得依 Excel `UsedRange` 全表套用；API Detail 预设只处理 API worksheet 的语义可视范围 `A:G` 到最后内容列。
   - 保留无关内容与既有格式。
9. Office 编辑器修改后，本技能重新执行 `scripts/check_api_xlsx_format.py` 或 DOCX 结构/格式检查；XLSX 需再用 artifact-tool import/inspect/render 抽查代表性 API sheet。
10. 修改后预设执行视觉 QA。只有在已渲染并检视页面/工作表后，才能宣称视觉检查通过；若渲染工具不可用，必须明确列为未完成风险。

## 上游 API 工作簿交接

当本技能在 `专案需求接口设计梳理` 或其他上游 API 设计流程编辑 `NEWDA_API_DETAIL_*.xlsx` 后被调用时，应将工作簿视为语义内容已完成，本技能只负责交付格式判断、修复计划与验收；实际写入仍交给 Office 编辑器。

交接契约：

- 保留上游 API 内容、sheet 意图、字段语义、范例与业务逻辑；除非用户明确要求，不要新增或删除 API 设计内容。
- 使用 API Detail 语义范围作为格式处理范围，不以 Excel `UsedRange` 为准。默认 API worksheet 样式范围仍为 `A:G`；不要因为历史样式污染就把格式扩到 `H:AZ`。
- 当由 `专案需求接口设计梳理` 等上游技能交接局部内容编辑时，以上游交接的 sheet 名、`Api_List` 行号或单元格范围为最高优先级。不要因为局部内容编辑而默认扫描所有 API Detail worksheets 执行字体槽位或样式修复。
- 局部内容编辑后的格式收尾有四条强制约束：一是只对实际新增或替换后的字符/词组使用 `apiDetailExcelStyle` 字型槽位（中文 `微軟正黑體`、英文数字 `Times New Roman`、字号 10）并标红，不得整格、整行或整段标红；二是字体修复只准作用于这些变更字符/词组，其他文字与单元格字体保持既有样式；三是目标 workbook 的所有工作表已用行必须重新自适应高度，含换行文字或合并格的行需按可见内容补足行高；四是行高/换行修复不得把一般内容行改成顶端对齐，必须要求 Office 编辑器保持或恢复水平靠左、垂直居中。
- 信息补充不得重复堆叠：`涉及BackendAPI`、`後端來源`、`Api_List` 仅写调用关系与来源摘要；Redis、DB fallback、排序、异常等细节优先放在 `API 內部業務邏輯` 的对应步骤，避免同一说明在清单和逻辑区重复出现。
- 若上游未提供明确变更范围，先执行只读检查并回报需要确认的范围；不得为了收尾而扩大到全 workbook 或所有 sheets。
- 当 API Detail worksheet 本身需要整页格式收尾时，`office-edit-plan` 可建议 Office 编辑器使用 `scripts/rebuild_api_xlsx_detail_sheets_from_text.ps1` 的“抽取文字并重建”流程：先抽取语义 `A:G` 文字与分区，再创建干净 worksheet，并按配置重新填入。不要在旧 worksheet 上反复修补过期合并格、边框、底色与行高。
- `Api_List` 不参与 API Detail 批量套样式。只有当用户或上游交接指出它属于本次工作簿修复范围时，才规划修复 `Api_List` hyperlink 或索引一致性。当 `Api_List` 本身需要整页格式收尾时，`office-edit-plan` 可建议 Office 编辑器使用 `scripts/rebuild_api_xlsx_api_list_from_text.ps1` 的“抽取文字并重建”流程，不要在旧 sheet 上原地打补丁。
- 严格执行 XLSX 闭环：确认范围 -> office-edit-plan -> Office 编辑器只修范围内格式 -> 只对范围内执行字体槽位 -> 结构复验 -> artifact-tool inspect/render -> 用户报告。
- 最终报告必须包含 `Must fix`、`Should fix`、`Naming`、`Visual risk` 与 `Covered`。刚修复过的工作簿，只要 `Must fix` 或 `Visual risk` 仍非 0，就不得宣称格式闭环完成。

## 检查范围

### TSD DOCX

内建检查器会验证可从 WordprocessingML 稳定读取的部分：

- 档名格式：`TSD.<module>.<number>_<Chinese name>_v<major.minor>_<yyyymmdd>.docx`。
- 封面文字：依专案规则库 `defaults.tsdCoverLabels` 与 `版本 x.y` 检查；缺少专案规则时只检查版本，不猜测专案名称。
- TSD 版本号使用小写 `v`；首页版本需与版本修订表最新版本一致。首次交付的 TSD 只保留初版记录，且版本号同样小写。
- 版本修订表：表头栏位 `版本`、`修改日期`、`修改人`、`PRD版本`、`修改记录`；列日期/版本格式；最新列与封面版本一致；资料列垂直置中、备注对齐与中文范例字型。
- 版本修订表字号：依 `TSD.E.001_匯率表_v1.7_20260511.docx` 基准，资料列可见文字使用 `12 pt`。不得因后续修复被压成 API 清单的 `10 pt`。
- 目录：包含范例要求的五个章节，并需在内容变更后更新，保持目录项目与实际章节一致。
- 必要一级章节，依序为：
  1. `功能目的(Functional Description)`
  2. `功能结构图(Functional Structure Diagram)`
  3. `循序图(Sequence Diagram)`
  4. `参考讯息来源(Reference)`
  5. `API清单`
- 章节内容：功能目的文字、功能结构图图片、循序图表格、参考讯息来源内容、API 清单表格。
- 表格格式：表头水平与垂直置中；表身垂直置中；一般内容水平居左，日期、版本号、姓名等栏位水平置中；循序图标题置中；API 清单需按 API 类别归类并把相同类别放在一起；同时检查循序图资料列对齐，以及 API 清单表头/资料列对齐、粗斜体漂移、表格内字型与繁体中文。
- API 清单字号：依 `TSD.E.001_匯率表_v1.7_20260511.docx` 基准，表头与资料列可见文字使用 `10 pt`。
- API 清单分页：API 清单章节标题与表格不得被拆成上一页少量行、下一页剩余行的跨页画面；修复时应让 `API清单` 标题从新页开始并与表格保持相邻，表格每列设定不允许跨页拆列。若表格长到无法单页容纳，至少需重复表头并避免单列被拆分。
- 字型规则：中文内容使用 `微软正黑体`，其他英文/数字内容使用 `Times New Roman`。
- 语言：所有中文内容必须使用繁体中文；简体字属于阻断性合规错误。
- 术语：可见文字不得使用 `校验`；验证流程、验证结果等语境改为 `验证`，检查项目、检查清单等语境改为 `检核`。
- 页尾版权：`版权所有：昱胜资讯股份有限公司 All Rights Reserved`。
- 页面设定：A4 直向页面大小与范例边界。

### API XLSX

API 规格 Excel 只做文件格式与表格结构检查：

- 活页簿是否可开启；使用者指定或交付范围内的 API worksheet 是否存在且可见。
- API Detail worksheet 是否具备必要分区，且分区顺序为 `API  Name` / 可选 `Header` / `Request` / `Response` / `范例` / `For中台开发人员` / `API 内部业务逻辑`。`Header` 分区不是必填，缺失时不得自动新增。
- 各分区的标题文字、栏位表头、必要可见栏位与必要内容储存格是否存在；只检查文件可见结构，不判断栏位业务语义。
- 可见样式必须优先读取专案规则库 catalog 的 `apiDetailExcelStyle`，按 `regions` 分区检查与修复字型、字级、粗体、底色、框线、对齐、换行、栏宽、列高与合并储存格；不要再用 `Regression_Example.xlsx` 或「既有样式」作为样式值来源。API Detail 可见样式范围只到 `A:G`，不得把框线或底色套到 `H` 栏以后；API Detail sheet 应关闭 worksheet gridlines，内容区外若已有黑色边框需同步删除，必要时以白底/无边框让空白区和背景融为一体。最后一个有效内容列下方的空白区也属于内容区外，需同步清除黑色边框。
- 检查与修复都以语义范围为准，不以 Excel `UsedRange` 作为套用范围。若 `UsedRange` 因历史样式污染扩到 `AZ`，列为 `Visual risk`，修复时仍只对 API Detail 可视范围与明确的清理范围动手。
- 字型只检查可见显示是否符合配置：中文/CJK 使用 `微软正黑体`，英文、数字与半形符号使用 `Times New Roman`；修复时沿用修复原则中的 Excel COM 双字型槽位模式。
- 对齐依配置与序号规则检查：A 栏符合 `^\d+(\.\d+)*$` 的值，以及 `#`、`Number`、`序号` 视为序号并置中；含点号但混有业务文字者，例如 `2.acct.Length==14` 或 `Header.DA-Authorization`，不得误判为序号。
- JSON、备注与业务逻辑等长内容需启用换行并按配置进行列高自适应；每次合并格修复后，API Detail 可视范围 `A:G` 的所有有内容列都需重新自适应列高，避免可见文字被裁切或被窄栏挤成直排。
- 所有中文内容是否为繁体。
- 术语用词：API Excel 可见文字不得使用 `校验`；依语境改为 `验证` 或 `检核`。
- 档名、工作表全局顺序、筛选器、冻结窗格、列印设定、页首/页尾等非分区配置项，只有在使用者明确要求或配置档后续新增规则时才检查。

#### API Detail 分区样式配置规则

当输入为专案 API Detail workbook，或使用者要求「按照技能模板 / 回归样例 / Regression_Example」检查时，先读取专案规则库：

- 样式配置：catalog asset `apiDetailExcelStyle`
- 详细结构与回归规则：catalog category `delivery-format` / `api-detail-workbook`
- 历史结构参考：catalog asset `regressionExample`
- 系统设计规范格式摘要：catalog 中对应规则

入口文件只保留执行护栏；具体分区、栏宽、列高、底色、边框、合并格、命名收敛与 `Api_List` 细则均以专案规则库 catalog 为准。

核心护栏：

- 检查与修复都以语义范围为准，不以 Excel `UsedRange` 作为套用范围。API Detail 可见样式预设只处理 `A:G` 到最后内容列；`H:AZ` 污染列为 `Visual risk` 或明确清理范围，不得反向扩大批量套样式范围。
- 专案规则库 catalog asset `apiDetailExcelStyle` 是可见样式最高优先级；`Regression_Example.xlsx` 只作历史结构参考，不再作为每次修复时的样式取值来源。
- API Detail worksheet 整页格式闭环优先采用 `scripts/rebuild_api_xlsx_detail_sheets_from_text.ps1 -Sheets ...`：先抽取 `A:G` 语义文字与标准分区，再建立干净 sheet 按配置重建。若目标 sheet 有公式、批注、外部超连结、图片/形状/控制项/OLE 内嵌物件，或重要内容位于 `A:G` 之外，列为 `Visual risk` 并等待使用者确认改用客制抽取或窄范围原地修复。
- `Api_List` 不参与 API Detail 批量套样式。整页优化 `Api_List` 时，先读取配置中的 `apiList` 规则并优先使用 `scripts/rebuild_api_xlsx_api_list_from_text.ps1`，不要在旧 sheet 上反复补边框、补底色或改列高。
- 多工作表 API workbook 检查时，将每个 API worksheet 视为独立 `API_Detail` 样式表；`Api_List` / index 类工作表不套用 API Detail 回归样例，除非使用者明确要求。
## 不处理范围

此技能不做业务或接口设计验证：

- 不判断 API 是否设计正确。
- 不比对 TSD `API清单` 与 API sheet / `Api_List` 的业务一致性。
- 不判断 `后端来源` 是否正确。
- 不判断 request/response 栏位语义、范例值、必填规则或业务规则是否正确。
- 不使用 field KB 判断命名或业务含义。
- 需要业务语义、API workbook 深度检查或跨文件接口设计时，改用专门的 API/接口设计技能。

## 修复计划原则

- 预设只产出报告，不自动修复所有问题。
- 可提出安全的文件错字、标题、标签、格式、繁体中文或固定术语修正，但仍需等待使用者确认。
- 固定术语修正包含 `校验` 改为 `验证` 或 `检核`：描述验证流程、验证结果、验证规则时优先用 `验证`；描述检查项目、检查清单、人工核对动作时优先用 `检核`。
- 修复计划采用能解决问题的最小变更。
- 格式检查/修复不得随意新增交付内容：不要为了说明判断依据、命名理由、冻版口径或修复原因，在 Excel/Word 底部追加 `备注`、`注记`、说明列或自由文字段落，除非使用者明确要求把该内容写入交付文件。这类说明应留在检查报告、回复讯息或专门 handoff note 中。
- XLSX 字型修复计划预设要求 Office 编辑器使用 Excel COM 双字型槽位模式，不做逐字/rich-text 拆分。局部业务编辑交接时，必须优先传入明确 `-Sheets` / 范围参数，只处理本次变更的 API Detail worksheets 或 `Api_List` 行。脚本在未传范围时会自动识别 API Detail worksheets、排除 `Api_List`，并只处理 `A:G` 到最后内容列；这种默认模式只适合用户要求检查/修复整本 API workbook 的格式，不适合上游局部内容编辑后的收尾。如需全 workbook，必须显式加 `-AllSheets`。可写入 `office-edit-plan` 的命令范例：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/apply_excel_font_scheme.ps1 -Path "path\to\workbook.xlsx"
```

- 如只修指定 API sheets，可加 `-Sheets "Sheet1","Sheet2"`；只有人工确认要改整本 workbook 时才加 `-AllSheets`。若 workbook 内含 OLE/media，计划必须要求 Office 编辑器用 Excel COM 保存，避免 `openpyxl` 移除嵌入物。
- XLSX 若同时修复对齐与字型，计划顺序为：先修对齐/列高/页面设定，再执行 COM 双字型槽位模式，最后重新开启 workbook 或渲染检查可见字型。
- XLSX 若只需修复 `API 内部业务逻辑` 的 `B:F` 合并格与 `A` 栏步骤栏对齐/底色，可在计划中要求 Office 编辑器执行 `scripts/repair_api_xlsx_internal_logic_merges.ps1`；此脚本预设只处理 API Detail worksheets、排除 `Api_List`，并只动 `API 内部业务逻辑` 的 `A:F` 边框/合并/对齐/底色，不处理 `H:AZ` 或新增 `Api_List` 内容。修复后仍需执行字型槽位脚本与结构/渲染复验。
- XLSX 若需修复 `范例` 区 `B:C` / `D:F` 合并、`A` 栏情境说明对齐与全列自适应高度，可在计划中要求 Office 编辑器执行 `scripts/repair_api_xlsx_example_merges_and_row_heights.ps1`；此脚本预设只处理 API Detail worksheets、排除 `Api_List`，只动 `范例` 区合并/对齐与 `A:G` 有内容列行高，不处理 `H:AZ` 或新增业务情境。修复后仍需执行字型槽位脚本与结构/渲染复验。
- XLSX 若需修复顶部 `API  Name` / `API Description` 高度、`B1:B2` 右边框、非模板内容列自适应高度与 `H:AZ` 空白区可见边框污染，可在计划中要求 Office 编辑器执行 `scripts/repair_api_xlsx_header_scope_and_row_heights.ps1`；此脚本预设只处理 API Detail worksheets、排除 `Api_List`，不改业务内容。
- XLSX 若需对 API Detail worksheet 做整页格式闭环，计划中优先要求 Office 编辑器执行 `scripts/rebuild_api_xlsx_detail_sheets_from_text.ps1 -Sheets ...`；此脚本先抽取目标 sheet 的 `A:G` 语义文字与分区内容，再建立干净新 sheet、按配置重填 `API Name` / `Request` / `Response` / `范例` / `For中台开发人员` / `API 内部业务逻辑`、重建合并格、行高与边框。若检测到公式、外部超连结、批注、形状/图片/控制项/OLE 内嵌物件，预设停止并报告风险，不强行删除。
- XLSX 若需对 `Api_List` 做整页格式闭环、排序、API 名称栏 hyperlink 样式、后端来源同步、行高与底边框统一，计划中优先要求 Office 编辑器执行 `scripts/rebuild_api_xlsx_api_list_from_text.ps1`；此脚本先抽取旧 `Api_List` 的 `A:J` 文字与 `E` 栏内部跳转，再删除旧 sheet、按专案规则库 `apiDetailExcelStyle` 的 `apiList` 配置重建，避免旧 sheet 残留合并、边框、底色或列高污染。
- XLSX 若只需修复目前功能范围内的 `Api_List` API 名称栏 hyperlink 样式、水平靠左/垂直置中、底部黑色边框、目标行 AutoFit，以及 API Detail `Request` / `Response` / `范例` / `API 内部业务逻辑` 区块末行底框，且不需要重建整张 `Api_List`，计划中才要求 Office 编辑器执行 `scripts/repair_api_xlsx_api_list_and_section_borders.ps1 -Sheets ...`；此脚本只处理指定 API sheets 对应的 `Api_List` 行与区块底框，不新增业务行。
- XLSX 修复的最终保存顺序必须以字型槽位收尾：若修复过程中任何一步曾用 `openpyxl` 保存、OpenXML/ZIP 直接替换内容、临时 workbook 覆盖正式档，或其他非 Excel COM 路径写回 `.xlsx`，不得直接宣称字型合规；必须要求 Office 编辑器在全部写回完成后重新执行 COM 双字型槽位脚本，然后再做可见字型/字符级抽查与必要的视觉 QA。
- XLSX 字型检查需分两层回报：可见字型是否合规，以及 XML/fallback/run 是否仍有残留；合并储存格非左上角幽灵格或不可见 fallback 残留只能列为非渲染残留或忽略，不可当成可见字型错误。
- Excel COM 对一个 mixed-font cell 查 `Range.Font.Name` 可能回空值，这代表同格混合字型，不等于失败。需要抽查时用 `Range("A1").Characters(start, length).Font.Name` 分别确认中文与英文字符。
- 逐字/rich-text run 激进修复只作为兜底：当 COM 双字型槽位模式后，实际画面仍有明确字型错误，且使用者同意进行深度富文本修复时才使用。
- XLSX 对齐检查需使用同一套序号识别规则：A 栏 `^\d+(\.\d+)*$` 为序号并置中，其余有内容储存格靠左垂直置中。
- XLSX 行高或 AutoFit 修复必须保留上述对齐结果：除表头、序号或配置明确要求居中的区域外，含内容储存格调整行高后仍应靠左、垂直置中、启用换行；不得为了展示长内容改成顶端对齐。
- 修复既有交付版 API workbook 时，若 workbook 内含 `xl/embeddings/` 或 `xl/media/`，计划必须要求 Office 编辑器优先使用 Excel COM 储存，避免 `openpyxl` 移除 OLE 物件或 EMF 图片。可用 `openpyxl` 读取检查，但不要用它保存此类 workbook。
- Office 编辑器需重新开启每个已修改的 DOCX/XLSX，确认变更后的段落、表格列、储存格或样式。
- Office 编辑器修复完成后，本技能预设执行结构复验与视觉 QA；XLSX 至少要用 artifact-tool import/inspect/render 代表性 API sheet，必要时再转 PDF。未完成渲染与检视前，不得宣称交付版面完全通过。

## 视觉 QA

视觉 QA 用于发现 XML/表格检查无法证明的版面问题，例如表格框线破损、文字被裁切、页码/目录渲染漂移、分页错误、图片或表格不可读。

DOCX 优先渲染路径：

```bash
soffice --headless --convert-to pdf --outdir "<tmp-output-dir>" "<path-to-tsd.docx>"
pdftoppm -png "<tmp-output-dir>/<file>.pdf" "<tmp-output-dir>/<file>"
```

XLSX 视觉检查先使用 artifact-tool 汇入 workbook，对代表性 API sheet 做 `inspect` 与 `render`，确认语义范围、公式/错误扫描与画面非空白；需要交付 PDF 外观时，再使用 LibreOffice 转 PDF，并用 Poppler `pdftoppm` 渲染抽样页面 PNG。至少检视首页、包含主要清单/目录的页面、以及若干代表性 API/Method sheet 页面；必要时用程式检查页面非空白、尺寸合理、文字未明显裁切。只有实际检视输出页面时，才宣称视觉 QA 通过。

备援：

- 可用时载入 `doc` skill 的 DOCX render helper 做补充渲染。
- 若 `soffice` 缺失，告知使用者需安装 LibreOffice，因为它提供 DOCX/XLSX 到 PDF 的渲染能力。
- 若 `pdftoppm` 缺失，告知使用者需安装 Poppler，因为它提供 PDF 到 PNG 页面渲染能力。
- 若渲染工具不可用，明确说明：`Structured validation completed; visual QA was not executed because rendering is unavailable.`
- 未检视渲染页面前，不要宣称视觉 QA 通过。

## 回报格式

面向使用者的报告保持精简。优先提供档案路径、FAIL/WARN/PASS 统计、文件格式合规状态与可执行问题；已覆盖项目只需简要提及。

依序使用这些分类：

1. 必须修复（Must fix）
2. 建议修复（Should fix）
3. Naming
4. 视觉风险（Visual risk）
5. Covered

未单独渲染并检视文件前，不要宣称视觉保真已验证。内建 DOCX 检查器读取 `.docx` 结构与文字，无法证明 Word 栏位渲染后的页码、目录或图表一定正确。

## 资源说明

- `scripts/check_tsd_docx.py`：独立 Python 3 DOCX 结构检查器，只使用标准库。
- `scripts/check_api_xlsx_format.py`：只读 API XLSX 结构/格式复验器，读取样式配置并检查 API sheet 范围、分区、合并、`H:AZ` 污染、底部残留样式与 `Api_List` 跳转。
- `scripts/apply_excel_font_scheme.ps1`：Office 编辑器可按本技能计划调用，使用 Excel COM 套用 API XLSX 双字型槽位；预设只处理 API Detail worksheets 的 `A:G` 语义范围，并输出字符级可见字型抽查结果。
- `scripts/repair_api_xlsx_example_merges_and_row_heights.ps1`：Office 编辑器可按本技能计划调用，使用 Excel COM 修复 `范例` 区 `B:C` / `D:F` 合并格与 `A` 栏情境说明对齐，并依合并后显示宽度重算 `A:G` 有内容列自适应高度。
- `scripts/repair_api_xlsx_header_scope_and_row_heights.ps1`：Office 编辑器可按本技能计划调用，使用 Excel COM 修复顶部 API 标题/描述区、固定模板列高、内容列自适应高度与 `H:AZ` 空白区可见边框污染。
- `scripts/repair_api_xlsx_api_list_and_section_borders.ps1`：Office 编辑器可按本技能计划调用，使用 Excel COM 修复指定 API sheets 对应的 `Api_List` API 名称栏 hyperlink 视觉、对齐、底边框与行高，并补齐 API Detail 各内容区块末行底部黑色边框。
- `scripts/rebuild_api_xlsx_api_list_from_text.ps1`：Office 编辑器可按本技能计划调用，使用 Excel COM 先抽取旧 `Api_List` 的 `A:J` 文字、API 名称内部跳转与原 sheet 位置，再删除并重建 `Api_List`，按配置填回表头/资料、排序、还原 hyperlink、同步 `后端来源`、套用栏宽/底色/字型/边框/行高与 AutoFilter。
- `scripts/rebuild_api_xlsx_detail_sheets_from_text.ps1`：Office 编辑器可按本技能计划调用，使用 Excel COM 先抽取 API Detail worksheet 的 `A:G` 可见文字与标准分区，再用干净新 worksheet 按配置重建 `API Name`、`Request`、`Response`、`范例`、`For中台开发人员`、`API 内部业务逻辑`、合并格、边框、底色、行高与返回连结。
- 专案规则库 catalog asset `apiDetailExcelStyle`：API Detail Excel 分区样式配置。API XLSX 检查与修复时，栏宽、列高、底色、字型、粗体、对齐、边框等可见样式值以此档为最高优先级；若缺少此 asset，脚本会要求传入 `--config` / `-ConfigPath`，不再自动使用插件内旧配置。
- `references/sample-derived-standard.md`：由参考文件推导出的 TSD DOCX 基准规则。
- `references/system-design-standard-v2.5-format-rules.md`：系统设计规范 v2.5 中可稳定执行的 TSD DOCX / API Detail Excel 格式规则。
- `references/raw/Regression_Example.xlsx`：API Detail Excel 历史回归样例，保留作为结构与版型参考，不再作为每次修复时的样式取值来源。
- `references/api-detail-regression-standard.md`：API Detail 结构、区块顺序与配置使用规则。
- API XLSX 目前以 `openpyxl` 进行格式/结构检查；既有交付 workbook 若含 OLE/media，修复保存计划必须要求 Office 编辑器优先使用 Excel COM。
- 相关技能：`专案需求接口设计梳理` 负责专案 API Detail、field KB、业务语义与接口设计决策；当任务超出格式/结构检查时改用该技能。
- 相关技能：`专案 Office 交付文件编辑器` 负责 `.docx` / `.xlsx` 物理写入、保存与复验回报；本技能负责格式判断与验收。
