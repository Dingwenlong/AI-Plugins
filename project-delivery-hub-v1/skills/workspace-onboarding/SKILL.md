---
name: workspace-onboarding
description: 安装本插件后的一次性引导。把分发包里的 .example 模板脚手架成本机真实配置，初始化项目工作区 .agent，接好 project-rules，让 01-05 交付主链可用。用于新同事 / 新机器 / 新项目首次配置；日常交付不需要它。关键词：安装引导、初始化、onboarding、setup、local-workspaces、.agent/config、配置脚手架。
---

# 【安装引导】工作区与配置初始化引导器

本技能在**首次安装本插件后**用一次，帮你（或新同事）把分发包里的 `.example` 模板落成本机真实配置，并初始化项目工作区 `.agent`。日常交付不需要它。

> 分发包**故意不含**任何真实配置：路径、测试人员名单、企业微信 webhook、SQL 连接串都被脱敏或排除。所以新机器装好后必须先走本引导，否则各技能会因缺配置而阻塞。

## 前置

- 真 Python 3.10+（本插件脚本依赖；`python` 若指向 Windows Store 存根则用真解释器的绝对路径）。
- 按需安装依赖：`python -m pip install jsonschema openpyxl python-docx`。
- 想好你的工作区根目录（放代码分支 / 设计文档 / `.agent` 的位置）。

## 一键脚手架（只新建，绝不覆盖已存在的真实配置）

先 `--dry-run` 预览，确认无误再去掉它正式执行：

```powershell
python "<pluginRoot>\skills\workspace-onboarding\scripts\init_workspace_config.py" `
  --workspace-root "D:\Path\To\MyProject" `
  --workspace-key "MYPROJECT" `
  --rule-pack "generic" `
  --dry-run
```

脚本会从 `references/` 模板生成：

- 插件 `references/local-workspaces.json`（从 `*.example.json`，若缺）；
- `<workspaceRoot>\.agent\config\design-source-registry.json`、`feature-tester-map.json`、`wedoc-smartsheet-targets.json`（从 `*.example.json`，若缺）；
- `<workspaceRoot>\.agent\project-rules\<workspaceKey>\` 规则库：`--rule-pack generic`（默认）复制通用模板（含可直接用的 code-guidelines 与已就绪的 `apiCodeWriter` 包）；`--rule-pack <workspaceKey>` 复制包内 `.agent` 快照里的真实规则包（同团队用）；`--rule-pack none` 跳过。

已存在的真实配置/规则库一律跳过——重复运行安全、幂等。

## 脚手架后必须手工填的值

1. **`references/local-workspaces.json`**：把每个 workspace 的 `workspaceRoot` / `agentRoot` / `rulesRoot` / `defaultCodeRoot` 改成本机绝对路径；按需填 `deliveryOutputRoot`（客户交付包输出根，留空＝默认 `<workspace>/TSD 交付客戶版本`）。`defaultWorkspace` / 键名改成你的 workspaceKey。
2. **`<workspaceRoot>\.agent\config\design-source-registry.json`**：填 PRD / TSD / API Detail / Common / IT SPEC / 旧项目目录，以及各 functionCode 的 aliases / prdCodes / tsdCodes。
3. **`<workspaceRoot>\.agent\config\feature-tester-map.json`**：填 featureId → 测试人员 映射（供第 05 步 UT 报告解析测试人员）。
4. **`<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json`**：仅当用企业微信智能表格异动记录（`wedoc-smartsheet-change-recorder`）时，填真实 webhook / user_id。**私有，不随包分发。**
5. **SQL fixture 连接**（如需第 03 步 `api-sql-fixture-preparer`）：按该技能文档建 `<workspaceRoot>\.agent\config\sql-fixture-targets.local.json`。**私有、无密码勿提交、不随包。**

## 工作区 `.agent` 与 project-rules

- 分发包根目录带一份 `.agent` **初始化快照**；正式运行位置是 `<workspaceRoot>\.agent`（把快照作为起点，真实状态在工作区跑，不要直接在插件目录里跑）。
- `chain-workspace.json` 由 `chain_workspace.py` 自动解析生成，**无需手抄**（`references/chain-workspace.example.json` 仅作字段参考）。
- 规则库（`<rulesRoot>` = `.agent/project-rules/<workspaceKey>`）由上面 `--rule-pack` 脚手架出起点：`generic` 模板已带可直接用的通用 code-guidelines 与就绪的 `apiCodeWriter` 包（第 04 步一上来即有开发规范）。之后**按专案定制**：填 `rules/code-guidelines/.../implementation-profile.md`（框架槽位 / 契约 / 验证命令），并用 `专案规则分析器`（project-rule-analyzer）补 `api-contract` / `field-kb` / `delivery-format` / `sequence-diagram` / `sql-fixture` / `ut-report` 等专案专属类目并接入对应 rule pack；第 04 步 `api-code-writer` 才完整读到。

## 校验就绪

- 规则包解析（确认 workspace / rulesRoot 接好）：

  ```powershell
  python "<pluginRoot>\references\resolve_project_rule_pack.py" --pack apiCodeWriter --workspace-key "MYPROJECT"
  ```

- 设计面产物（若已产出）：

  ```powershell
  python "<pluginRoot>\skills\api-detail-tsd-sync\scripts\validate_design_artifacts.py" --workspace-key "MYPROJECT" --function-code "<functionCode>"
  ```

全部就绪后，即可按 01 → 05 主链正常使用各技能。

## 资源

- `scripts/init_workspace_config.py`
- 模板（`references/`）：`local-workspaces.example.json`、`design-source-registry.example.json`、`feature-tester-map.example.json`、`chain-workspace.example.json`、`wedoc-smartsheet-targets.example.json`
