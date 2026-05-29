---
name: 专案交付中枢：【交付文件】专案原生 VSDX 时序图生成器
description: 生成或修正正式交付用的原生可编辑 Visio VSDX 时序图。按冻版 PRD、TSD、API Detail 产出 native VSDX，并保留 PlantUML/SVG 作为文本草稿、视觉参考或降级输出；重点验证 native shapes、lifeline、alt/ref/opt/group 与可编辑性。关键词：VSDX、Visio、sequence diagram、PlantUML、native validation。
---

# 【交付文件】专案原生 VSDX 时序图生成器

## 上下文策略

保持默认执行轻量化，但正式 VSDX 交付不能轻量到漏规则。读取本文件后，必须先完成「规则包启动检查」，再进行内容设计、spec 编写和 VSDX 构建。

先解析当前 workspace，读取 `<rulesRoot>/catalog.json`。时序图标准、native VSDX template、shape library、PlantUML style 与项目 baseline 都优先从专案规则库的 `sequence-diagram` category、`rulePacks.sequenceDiagram` 与 `assets` 读取。找不到规则库时，只能执行通用草稿流程；正常专案正式 VSDX 必须阻塞并报告“缺少专案规则”，不得从插件内旧个案 reference 偷读默认规则。

### 规则包启动检查

正式 VSDX 交付或修图时，必须先运行规则包解析脚本：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack sequenceDiagram `
  --workspace-key "<workspaceKey>"
```

若用户提供了明确规则库，使用 `--rules-root`：

```powershell
python "<pluginRoot>\references\resolve_project_rule_pack.py" `
  --pack sequenceDiagram `
  --rules-root "<rulesRoot>"
```

脚本输出的 `rules[].resolvedPath` 与 `assets[].resolvedPath` 是本次任务的必读规则包。正常专案时序图必须加载并遵守这些文件，不能只读取 `SKILL.md` 后直接出图。

规则包缺少以下任一项时，不得产出“符合专案规则”的正式 VSDX：

- `system-design-v2.5-sequence-rules`
- `native-vsdx-deep-rules`
- `sequence-diagram-handoff-rules`
- `e001-native-reference-summary`
- asset `nativeVsdxTemplate`
- asset `nativeShapeLibrary`
- asset `sequencePlantUmlStyle`

`catalog.json` 中规则路径字段的事实标准是 `path`；旧 `loadPath` 只作为兼容字段。读取 catalog 时必须同时兼容 `path` / `loadPath`，优先使用 `path`。

以下技能内 reference 只作为历史兼容、fixture 或迁移说明；不得在可解析到外置规则包时替代外置规则：

- `references/native-vsdx-deep-rules.md`：复杂原生 VSDX 布局、Visio ShapeSheet、fragment/list member、User 头像、连接点、主题、历史失败模式等深层规则。
- `references/system-design-standard-v2.5-sequence-rules.md`：系统设计规范 v2.5 中的正式 Visio source、Visio 2013-2016 兼容、参与者、Request/Response、User、`alt`/`opt`/`ref` 与 Common 引用规则。
- `references/standard-examples/E001_native_reference.md`：E.001 原生参考的结构与样式摘要。
- `references/standard-examples/E001_native_reference.vsdx`：历史 VSDX template/master 与既有项目 theme 来源；正常流程优先使用专案规则库 asset。
- `references/sequence-style.puml`：仅在需要编写或刷新 PlantUML 草稿时读取。
- `references/native-shape-library/`：仅在修 native shape/template 或脚本缺少模板信息时读取。
- `scripts/build_native_visio_sequence.ps1` 与 `scripts/validate_native_visio_output.ps1`：构建或验证正式 VSDX 时执行；只有脚本异常或需修脚本时才阅读全文。

外置规则包中命中的 `native-vsdx-deep-rules` 是正式 VSDX 的必读硬约束，不再只是复杂修图时的补充材料。技能内同名 reference 只有在外置规则包缺失且用户明确要求 legacy 兼容时才可读，并且最终说明必须标记为 legacy fallback。

遇到“系统设计规范 v2.5 / 设计规范 / Visio 2013 / alt/opt/ref 标准 / Common 引用标准”相关任务时，读取外置规则包中全部 `sequence-diagram` required rules，再按输出路径加载 native template、shape library 与 PlantUML style。

## 目的

作为 `专案需求接口设计梳理` 的下手技能使用。父技能负责解析权威 PRD/TSD/API Detail 与 canonical API/字段命名；本技能负责把已冻版或近冻版契约转成专案正式交付用时序图。

正式交付优先级：

- `native-visio` 是正式 VSDX 的唯一正常交付模式。
- PlantUML 是内容草稿与审阅文本，不是正式 VSDX 的生成来源。
- SVG/PNG 是明确要求时才生成的视觉参考或降级产物。
- 不得把整张 SVG 导入 Visio 后包装成正式 VSDX；这只能标记为 `svg-import fallback`。

## 输入

按以下顺序取权威来源：

1. Frozen API Detail：API Name、request/response 字段、examples、`涉及BackendAPI`、business logic。
2. TSD `API清单`、时序/结构说明、业务规则。
3. PRD 页面、流程、入口、默认状态与错误提示。
4. 既有 VSDX/SVG/PlantUML：只作为重构、对齐或修正参考。
5. 专案本地标准：优先 `<rulesRoot>/assets/visio` 中 catalog 指定的 native template 与 baseline；没有时再由用户提供或降级为通用样式。

旧图、旧字段与旧 API 名称不得覆盖冻结版 API Detail。

## 输出契约

默认输出目录：

```text
output/sequence_diagram/{functionCode}/
  {functionCode}_native_visio_spec.json
  {functionCode}_sequence.puml
  {functionCode}_plantuml_落版說明.md
  vsdx/{functionCode}_01.vsdx
```

正式 VSDX 契约：

- 一支 `functionCode` 只交付一个正式 VSDX：`vsdx/{functionCode}_01.vsdx`。
- 一个 VSDX 可以有多个 Visio page tab；tab 按连贯 PRD/TSD 用户流程拆，不按每个 API、成功/失败情境、后台调用、步骤或小页面机械拆。
- 每个正式 tab 必须有可见用户入口，通常是 `User -> APP: 點擊...`。
- 若 PRD/TSD 没给明确拆分，默认一个 tab，并在落版说明记录缺少拆分依据。
- 默认不要创建或刷新 `svg/`、`png/`。用户明确要求图片输出时，才生成并与正式 VSDX 验收分开说明。
- `vsdx/` 内只保留最终 `{functionCode}_01.vsdx`；默认不创建 `.bak`、`.before_*`、时间戳备份或其他交付目录相邻备份。确需安全副本时使用版本控制或工具临时目录，并在交付前清理。

## 核心流程

1. 运行 `scripts/resolve_sequence_rule_pack.py`，加载并确认本次规则包；规则包缺失则阻塞正式 VSDX。
2. 读取规则包列出的 required rule files，尤其是 v2.5 sequence rules、native-vsdx-deep-rules、sequence handoff rules 与 E.001 reference summary。
3. 解析权威 PRD/TSD/API Detail，确认功能入口、业务阶段、主 API、后台来源与错误分支。
4. 先判断是否具备时序图交付条件；缺少关键来源时标记 blocker，不要猜业务。
5. 合并连续的 PRD 页面/确认/提交/结果页为连贯用户流程，并映射到 VSDX page tabs。
6. 只放入主流程实际调用的参与者。
7. 创建或刷新 `{functionCode}_native_visio_spec.json`，作为正式 VSDX 的执行源。
8. 从同一份内容保留一个 PlantUML 文本草稿，供内容审阅。
9. 如存在 CommonFunc/CommonUtil 引用，必须用 `ref over Ent` 和 native ref fragment 表达，并在同一 ref 内放 reference self-call 与底部橙色参考文件说明条；不把 common 方法画成普通 self-call、普通 message 或独立参与者。
10. 除非用户明确只要文本或本机工具缺失，执行 native VSDX 构建脚本。
11. 执行文本验证与 native VSDX 验证。
12. 更新落版说明，列出规则包路径、实际输出、冻结来源、验证结果；若 VSDX 阻塞，写清具体原因。

## 图面硬规则

- 默认参与者顺序：`User -> APP -> Enterprise -> IRIS -> DB -> Redis`。
- `User`、`APP`、`Enterprise` 保持在左侧；`DB`、`Redis` 不得出现在 `Enterprise` 左侧。
- 只有主流程直接调用 DB/Redis 时才画它们；CommonFunc 内部使用 DB/Redis 不代表主图要画。
- 若专案规则未另行指定，DB/Redis 必须是普通 boxed participant，不使用 cylinder/storage 图标。
- `CommonFunc` 必须用 `ref over Ent` / native ref fragment 表达；不要画成 Enterprise 普通 self-call，也不要画成 participant。
- `CommonUtil` 只有在 APP 实际通过 Enterprise 调用该 API 时，才按外部 API 调用表达。
- 可见图面中的内部共用方法使用 `CommonFunc.MethodName` 点号写法，例如 `CommonFunc.GenFntTranSeq`；外部共用接口维持 `CommonUtil/MethodName` 斜线写法，例如 `CommonUtil/GetCENCurr`。
- 图面文字使用台湾繁体中文；用户给的简中内容要转换后再上图。
- API、字段与 source 名称使用冻结版 API Detail / 字段知识库的 canonical 名称。
- 不保留旧字段或旧方法名来说明“已删除”。
- `group` 表示业务阶段，`alt` 表示互斥分支，`opt` 表示单一可选分支，`ref over` 表示可复用 common 引用。
- `alt` 至少两个 branch；只有一个条件分支时使用 `opt`。
- 每个同步 request 都要有 response。
- `User` 只作为触发来源；不要画 `APP -> User` 或 response 到 `User`，页面显示、弹窗、刷新用 APP self-call。
- request/response 箭头要有业务可读标签，不把完整 request/response 字段清单塞进箭头或 self-call。
- APP self-call 用业务动作、显示状态或提示语表达，不堆 raw field list、公式、长斜线字段串。
- PRD/API Detail 要求会员类型、会员身份、网银资格等验证时，在入口附近用 `alt` gate 表达；没有来源依据时不要加泛化验证。

## 原生 VSDX 硬规则

- 正式 VSDX 的落版说明必须列出本次加载的 `rulePack.rulesRoot`、required rule files 与 required assets；若未列出，视为规则加载证据不足。
- 正式 VSDX 必须由 `{functionCode}_native_visio_spec.json` 经 `scripts/build_native_visio_sequence.ps1` 构建。
- 系统设计规范 v2.5 要求正式交付 Visio source；环境支持时需保存/导出为 Visio 2013-2016 兼容格式，无法验证兼容时列为交付风险。
- 使用 Visio UML native masters 与专案 theme；template/master 必须包含 `visio/theme/theme1.xml` 与 document theme relationship。
- 必须使用规则包解析出的专案规则库 asset `nativeVsdxTemplate` / `nativeShapeLibrary` / `sequencePlantUmlStyle`；不可用时必须说明缺少专案模板，不得静默改用旧专案内置样式。
- native spec 必须声明 `messageStyle.policy`，默认 `e001-reference`；只有明确需要全红才使用 `project-red`。
- User 参与者在正式 VSDX 中必须是 E.001 风格任务图标 + boxed `User` 标签，不得残留 PlantUML stick actor。
- DB/Redis 在正式 VSDX 中必须与 APP/Enterprise/IRIS 一样是 boxed participant。
- self-call、message、return message 使用 Visio UML native shapes；self-call 标签留在同一 shape 上，不拆成独立文本框。
- 参与者 lifeline 连接点必须使用 Visio UML 原生默认间距铺成完整、均匀的连接点列；不得用固定 inch 值替代，也不得只在箭头附近新增零散连接点。
- message / return / self-call 箭头头尾必须胶合到既有 lifeline 连接点；不接受仅视觉贴近的端点，找不到可用连接点时构建必须失败。
- ref fragment 只承载 common 引用说明、紧凑 common self-call 与底部橙色参考文件说明条；CommonFunc/CommonUtil 方法不得出现在 ref 外的普通 self-call/message，主流程 request/response 也不要塞进 ref。只要 ref 内有 CommonFunc/CommonUtil reference self-call，就必须有对应同方法名的橙色参考条。
- section title、外层 business group、内层判断 `alt` 需要逐层保留至少两段参与者连接点间距；宽幅 child fragment 不可贴齐 parent fragment 的左右或顶部边界。
- 连续的 sibling `opt` / `alt` / `ref` / `group` 不得互相压线或重叠；至少保留可见垂直间距，只有真正 parent-child 包覆关系才允许图框区域重叠。
- `alt` 必须保留原生 `Alternative fragment` 与原生 `Interaction operand` list member；落版后 operand 的 `PinY`、`Height`、`LocPinY` 需固化为可编辑常量，不得保留跨 member 的 `Sheet.*!Height` / `Sheet.*!PinY` 垂直公式，以免手工拖曳 member 控制点时方向反直觉。
- `alt` 的第一条件与所有 `else` 分支条件都必须显示为 `[条件]` 格式；PlantUML 草稿使用 `else [条件]`，native VSDX 的 `Interaction operand` 文字不得裸露为 `条件` 或 `else 条件`。
- 原生 `Interaction operand` 的 `[条件]` 文字必须贴在 operand 顶部并保留可读间距；延展 `else` 或 `opt` operand 高度时，`TxtPinY` 必须同步到 `Height`，不得让条件说明停在旧高度或落到后续片段附近。
- `alt` 的 success-like `else` 分支（例如 `[帐号检核通过]`、`[查询成功]`、`[有资料]`）若下方接续 nested `opt` / `ref` / `group` / `alt`，外层 `alt` 与最后一个 `Interaction operand` 必须向下完整包覆这些片段，且这些 child fragment 必须成为外层 `alt` 的成员；不得只让画面看似在框内，却在 Visio 原生结构中成为 sibling。
- 延展 native `Interaction operand` 高度时，内部 separator geometry 必须同步更新，输出视觉检查不得出现斜向虚线段或被拉斜的 branch 分隔线。
- 延展 native `alt` / `opt` / `ref` / `group` 外框时，外框 `Geometry` 的最大 X/Y 必须同步到图形实际 `Width` / `Height`；不得只拉大 Shape 尺寸而让可见外框停在旧高度，造成 `else` / child fragment 视觉上顶出外框。
- 延展 native `alt` / `opt` / `ref` / `group` 外框时，左上角标题子图形也必须同步：`PinY` 贴合父 fragment `Height`，`PinX` / `LocPinX` / `Width` 跟随父 fragment `Width`，不得让 `alt` / `opt` / `ref` title 留在旧高度。
- 不把新生成功能图同步复制到 `v1.x Reference/`，除非用户针对本次交付明确要求。

复杂布局、operand/list member、连接点、User 头像替换、主题 fallback、section divider、orange pointer、ShapeSheet 控制点等细节，必须以外置规则包中的 `native-vsdx-deep-rules` 为准；不要只靠入口摘要执行。

## 验证

始终执行文本验证：

- `@startuml` 与 `@enduml` 数量一致。
- 无旧字段、旧 API、旧方法名误带到图面。
- DB/Redis 只在主流程直接调用时出现，且以 boxed participant 声明。
- Common SVG / common diagram 引用存在时，图面 `ref` 必须有底部橙色说明条，且说明条固定显示「`循序图请参考：` + SVG basename 去 `.svg` + 中文说明」，例如 `循序圖請參考：01_CommonFunc.SendToMonitorMail_Push 新版MAIL發送機制（包含推播）`；不得显示 `共用SVG资料夹`、前导 `/` 或 `.svg`，真实 `.svg` 文件名只在落版说明或交付追溯清单中保留。
- CommonFunc/CommonUtil 方法必须落在 `ref` fragment 中；若在主流程普通 message/self-call 上出现 `CommonFunc.`、`CommonFunc/`、`CommonUtil.` 或 `CommonUtil/`，视为验证失败；即使在 `ref` 内，`CommonFunc/MethodName` 与 `CommonUtil.MethodName` 也都是命名格式错误。

正式 VSDX 存在时，始终执行 native 验证：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <pluginRoot>\skills\native-vsdx-sequence-writer\scripts\validate_native_visio_output.ps1 -VsdxPath path\to\file.vsdx
```

验收重点：

- `{functionCode}_native_visio_spec.json` 与 `vsdx/{functionCode}_01.vsdx` 都在 `output/sequence_diagram/{functionCode}/` 下。
- 一个 function 只有一个正式 VSDX，page tabs 按 coherent user flow 拆分。
- VSDX 不是单一 SVG import group；没有 `ForeignData`、`visio/media`、`visio/embeddings`。
- VSDX 与 template/master 含专案 project theme。
- User、DB、Redis 参与者样式符合 E.001 native baseline。
- 参与者 lifeline 连接点间距为 UML 原生默认长度，连接点列完整且不聚集；message / return / self-call 端点全部胶合到既有连接点。
- CommonFunc/CommonUtil 只允许作为 native `ref` fragment 内的紧凑 reference self-call，并必须配套同方法名的底部橙色参考文件说明条；不得以 Enterprise 普通 self-call 形式出现在主流程线上。
- `CommonFuncSlashNotation=0`、`CommonUtilDotNotation=0`、`RefDisplayNamesMissingPointerPrefix=0`：native `ref` 内 reference self-call 的可见命名需固定为 `CommonFunc.MethodName` / `CommonUtil/MethodName`；橙色参考条固定使用 `循序图请参考：` + SVG basename + 中文说明，例如 `循序圖請參考：04_CommonFunc.GenFntTranSeq 取得交易序號`。
- message/self-call/return label 不重叠、不贴框、不脱离 native shape。
- fragment、alt operand、ref、group 成员关系与视觉包覆正确。
- `EmptyGroupFragments=0`：业务 `group` 不得是只有标题、没有内容的空框；若只是分段标题应使用 section divider，若是语意阶段外框就必须完整包住其 child `alt` / `ref` / message。
- success-like `else` 下方的 nested `opt` / `ref` / `group` / `alt` 不得穿出 owning `alt` / final operand 底边；若顶边轻微贴住或重叠底线但底部在框外，仍视为验证失败。
- sibling fragment 不得可见重叠；例如连续两个 `opt` 需要留出清楚间距，不得让上一个 `opt` 底线压到下一个 `opt` 顶线。
- 导出的视觉探针不得包含斜向 dashed path；若出现，通常代表 native `Interaction operand` 被拉高后 separator geometry 未同步，需修正后再交付。
- `FragmentFrameGeometryMismatch=0`：所有 native `alt` / `opt` / `ref` / `group` 的可见外框 geometry 必须贴合实际图形宽高，避免 Visio 选取框够高但正式外框仍停在旧高度。
- `FragmentTitleMisaligned=0`：所有 native fragment 的左上角 title tab 必须跟随外框尺寸，尤其是被加高的外层 `alt`，不得出现 title 停在旧位置。
- `ConditionOperandsWithoutBrackets=0`：所有 native `alt` / `else` 的 `Interaction operand` 条件都必须是 `[条件]` 格式。
- `ConditionOperandTextMisaligned=0`：所有 native `Interaction operand` 的 `[条件]` 文字必须位于 operand 顶部；外层 `else` 被加高后不得留下旧 `TxtPinY`。
- `AltOperandVerticalFormulaLock=0`：`Interaction operand` 的垂直尺寸不得依赖其他 operand 的 ShapeSheet 高度/位置公式，用户拖拽 if/else member 控制点时必须保持 Visio 原生手感。
- 落版说明列实际 VSDX 输出与验证结果；正常交付不得写成“若后续要做 VSDX”。

若工具或 Visio COM 不可用，仍产出 PlantUML 文本草稿，并把 native VSDX 明确列为未完成项和 blocker，不要静默跳过。
