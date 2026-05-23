---
name: 专案规则分析器
description: 把专案规范文件转换成可被交付链读取的规则库。分析 Word、Excel、Markdown、JSON 规则文件，抽取可复核规则，写入 `.agent/project-rules/<workspaceKey>` 的 JSON/Markdown 产物并更新 catalog；legacy/加密 Word 只记录可读性状态，不凭空生成规则。关键词：project-rules、catalog、规则抽取、sourceHash。
---

# 专案规则分析器

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
