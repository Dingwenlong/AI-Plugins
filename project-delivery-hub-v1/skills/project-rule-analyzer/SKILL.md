---
name: project-rule-analyzer
description: 把专案规范文件转换成可被交付链读取的规则库。分析 Word、Excel、Markdown、JSON 规则文件，抽取可复核规则，写入 `.agent/project-rules/<workspaceKey>` 的 JSON/Markdown 产物并更新 catalog；legacy/加密 Word 只记录可读性状态，不凭空生成规则。关键词：project-rules、catalog、规则抽取、sourceHash。
---

# 【资料准备】专案规则分析器

用于把专案规范、设计标准、开发规范、格式样例说明等文件转成后续技能可读取的规则库条目。

默认规则库位置按工作区解析：

1. `--rules-root`
2. `PROJECT_RULES_ROOT` / 专案环境变量
3. `references/local-workspaces.json` 中的 `rulesRoot`
4. `<agentRoot>/project-rules/<workspaceKey>`

## 使用方式

```powershell
python ".\scripts\analyze_project_rules.py" `
  --project-root "D:\Repo\Project\feature_common\P240301Git" `
  --workspace-key "PROJECT" `
  --category api-contract `
  --source "D:\Refs\ProjectRule.docx"
```

默认产物为 `reviewStatus=draft`，需要人工确认。确认后可加 `--approve` 直接写成 active 规则：

```powershell
python ".\scripts\analyze_project_rules.py" `
  --project-root "D:\Repo\Project\feature_common\P240301Git" `
  --workspace-key "PROJECT" `
  --category delivery-format `
  --source "D:\Refs\FormatRules.xlsx" `
  --approve
```

## 输出

- `rules/<category>/<ruleId>.json`
- `rules/<category>/<ruleId>.md`
- `sources/raw/` 下保留来源副本
- `sources/converted/` 下保留抽取状态与可读文本
- `catalog.json` 更新规则索引

每条规则必须记录 `sourceFile`、`sourceHash`、`sourceLocator`、`category`、`priority`、`reviewStatus`。不可读或加密文件只写 source status，不生成 active 规则。

## 接入第 04 步开发规范

开发规范、框架说明、Redis / JWT / Session 说明、编码规范等文件统一使用：

```powershell
python ".\scripts\analyze_project_rules.py" `
  --project-root "D:\Repo\Project\feature_common\P240301Git" `
  --workspace-key "PROJECT" `
  --category code-guidelines `
  --source "D:\Refs\Guidelines\Framework.docx" `
  --approve
```

当 `--category code-guidelines` 且 `--approve` 时，脚本会同时：

- 写入 `rules/code-guidelines/<ruleId>.json` 与 `.md`
- 更新 `<rulesRoot>/catalog.json`
- 确保 `defaults.codeGuidelineCatalog` 指向开发规范 catalog
- 将该规则接入 `rulePacks.apiCodeWriter`
- 更新开发规范 catalog，供第 04 步 `api-code-writer` 产生 `devGuidelineRulesSelected` 与 `devGuidelineLoadHints`

未加 `--approve` 时只产出 `reviewStatus=draft` 的复核稿，不会让第 04 步默认作为 active 开发规范读取。

## 其它规则包的接入（重要：当前非自动）

`--approve` 时脚本**只自动维护 `rulePacks.apiCodeWriter`**（把 `code-guidelines` 规则接入该 pack）。其余规则包的 `requiredRuleIds` 是**跨多个类别精选**的，无法由单条规则的 category 自动派生，因此脚本**不会**自动接入：

- `apiDetailSync` / `apiSpecWriter`：需 `api-contract` + `api-detail-workbook` + `field-kb` + `sequence-diagram` 等多类规则。
- `deliveryFormat`：`delivery-format` + `api-detail-workbook` 等。
- `sequenceDiagram`：`sequence-diagram` 类规则与 native VSDX 规则、相关 asset。
- `sqlFixture`：`sql-fixture` 默认值。
- `unitTestReport`：`test-handoff` 规则 + UT 模板/清单 asset。

因此用本技能新增/批准**非 `code-guidelines`** 类规则后，必须**手动**把新 `ruleId` 加进对应 `rulePacks.<pack>.requiredRuleIds` / `optionalRuleIds`，否则该 pack 的消费技能（如 `delivery-format-checker`、`api-spec-writer`、`native-vsdx-sequence-writer`）不会加载到这条新规则。批准后请复核 `catalog.json` 的 `rulePacks` 是否已覆盖新规则；若需要把自动接入扩展到其它 pack，应先为每个 pack 定义明确的「category → pack」纳入规则，再改脚本。
