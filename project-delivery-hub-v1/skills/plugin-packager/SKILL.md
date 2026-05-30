---
name: plugin-packager
description: 打包、发布并同步 `project-delivery-hub-v1` 插件。仅用于插件维护任务：刷新 `company-jimmy` 本机维护版、`company-dev` 开发测试版或显式配置的 Codex 缓存，套用 `references/package-targets.json` 中的 plugin URI 与 marketplace 规则，并随包携带集中 `.agent`、主流程图、技能/.agent 架构图与工作区结构树；不处理客户 TSD 交付包。关键词：plugin package、company-jimmy、company-dev、agent bundle、cache sync。
---

# 【插件运维】专案交付中枢插件打包器

用于维护 `project-delivery-hub-v1` 的本机维护版、开发测试版与 Codex 缓存同步规则。本技能只处理插件自身打包发布，不处理 TSD 客户交付包。

## 固定规则

- 插件技术 ID 固定为 `project-delivery-hub-v1`。
- 本机/个人维护版 URI 固定为 `plugin://project-delivery-hub-v1@company-jimmy`。
- 打包本插件时，如果用户没有指定目标市场，默认目标固定为 `plugin://project-delivery-hub-v1@company-dev`。
- 权威配置文件为插件根目录下的 `references/package-targets.json`。执行前先读取它，不要凭记忆猜路径。
- `references/package-targets.json` 的 `agentBundle` 定义随包携带的集中 `.agent`；默认从 `references/local-workspaces.json` 的 `NEWDAWHO.agentRoot` 读取，打到插件包根目录 `.agent`。
- 插件根目录必须带 `USAGE.md`，用于给接收插件包的同事安装、初始化项目工作区 `.agent` 与配置 `local-workspaces.json`。
- `company-jimmy` 指向 Jimmy 本机维护市场：`C:\Users\<username>\.agents\plugins\marketplace.json`。
- `company-dev` 指向开发测试打包市场：`C:\Users\<username>\plugin-marketplaces\company-dev\.agents\plugins\marketplace.json`。
- 旧插件 ID 与旧个人 marketplace 组合只视为历史兼容来源，不再作为 active 打包目标；不要在新包里重新写入旧 URI。若 `references/package-targets.json` 仍保留 `personal` target，只能按该配置用于当前安装诊断或显式维护，不作为默认打包目标。
- 打包时必须把 `agentBundle` 指向的 `.agent` 同步进包和缓存；随包 `.agent` 只作为初始化快照，正式运行位置必须是项目工作区根目录，例如 `<workspaceRoot>\.agent`。
- 工作区解析快照只允许存在于 `.agent/config/chain-workspace.json`；不要生成或携带 `.agent/workspaces/<workspaceKey>.json`。
- `.agent` 内的 `.bak`、`__pycache__`、`.tmp`、`.log`、`.pyc` 不得进入打包产物。
- agentBundle 快照只携带可分发骨架，**不得包含**逐功能工作数据与本机运行态目录：`.agent/functions/`、`.agent/status/`、`.agent/tmp/`、`.agent/wedoc-smartsheet-staging/`、`.agent/reference/`。打包脚本已在 agentBundle 镜像排除这些（`$AgentWorkDataDirectoryNames`）；保留 `.agent/project-rules/`（团队规则库）、`.agent/config/`（去除个人/私有档后）与 `.agent/diagrams/`。
- `references/rule-pack-templates/`（`generic/` 通用规则库模板：`catalog.json` + 就绪的 code-guidelines + 占位 `implementation-profile.md` + `README.md`）必须随包，供 `workspace-onboarding` 为新项目脚手架规则库。
- 企业微信智能表格真实配置属于个人/项目私有配置，`.agent/config/wedoc-smartsheet-targets.json` 与 `.agent/config/wedoc-smartsheet-targets.local.json` 不得进入插件源、打包产物或 cache；只允许 `references/wedoc-smartsheet-targets.example.json` 模板随包。
- 个人/本地配置 `references/local-workspaces.json`、`.agent/config/design-source-registry.json`、`.agent/config/feature-tester-map.json`、`.agent/config/chain-workspace.json` 含本机路径/名单，不得带真实值进入插件源、打包产物或 cache；打包脚本已将其纳入排除名单（`$PersonalLocalConfigFileNames`），包内只随对应 `references/*.example.json` 模板。接收方用 `workspace-onboarding` 技能从模板脚手架出本机真实配置（`scripts/init_workspace_config.py`，只新建不覆盖）。
- SQL fixture 数据库连接真实配置属于个人/项目私有配置，`.agent/config/sql-fixture-targets.local.json` 不得进入插件源、打包产物或 cache；技能文档只能保留无密码示例或字段说明。
- 企业微信智能表格新增回执属于项目运行资料，`.agent/wedoc-smartsheet-receipts/` 不得进入插件源、打包产物或 cache。
- 打包扫描若发现真实 `qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/webhook?key=` URL、上述私有配置文件或智能表格回执目录，必须失败并先清理。
- 打包时必须携带 `references/artifact-naming-standard.json`、`references/artifact-naming-standard.md` 与 `skills/plugin-packager/scripts/check_artifact_names.ps1`；命名检查脚本只读报告旧名，不负责迁移。
- 打包技能固定随包携带三张 SVG 架构图，路径为：
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_主流程图.svg`
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_技能与agent架构图.svg`
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_工作区与agent结构树.svg`
- 更新这三张图时，先在集中 `.agent/diagrams` 重新生成确认版，再覆盖打包技能资产目录中的同名 SVG；打包前必须校验文件存在且内容为 SVG。
- 插件发生结构型变动时必须同步这三张图。结构型变动包括：新增/删除/合并技能、调整 01-05 链路、调整梳理/规则/交付/打包分支关系、改变 `.agent` 目录职责、改变 `project-rules` 读取方式、改变工作区/分支代码位置关系、改变打包入口或 marketplace/cache 流向。
- 只有文案修正、脚本 bugfix、局部校验增强且不改变技能关系或 `.agent` 职责时，可以不重画；但仍要保留三张 SVG 随包输出。

## 打包流程

1. 读取 `references/package-targets.json`，确认 `pluginId`、本机 URI、默认打包 URI、可用 target 与目标市场路径；路径不得凭记忆或旧会话推断，路径中的 `<username>` 必须展开为当前 Windows 用户名。
2. 校验 `.codex-plugin/plugin.json` 中的 `name`、`version` 与 `interface.composerIcon` / `interface.logo` 本地资源路径，并确认技能/agent 显示名统一使用 `专案交付中枢：` 前缀；agent 入口必须使用 `interface.display_name`，避免顶层 `name` 被 Codex 再自动套插件名。
3. 若用户未指定目标，选择 `company-dev`；若用户要求刷新本机维护版，选择 `company-jimmy`；若要完整同步，选择 `both`。
4. 校验插件根目录 `USAGE.md` 存在，并写明 `.agent` 正式运行位置是项目工作区 `<workspaceRoot>\.agent`。
5. 若本次包含结构型变动，先同步 `专案交付中枢_主流程图.svg`、`专案交付中枢_技能与agent架构图.svg` 与 `专案交付中枢_工作区与agent结构树.svg`；然后校验打包技能内三张固定 SVG 架构图存在且可读。
6. 按 `agentBundle` 读取集中 `.agent` 并镜像到插件包根目录 `.agent`，同步时排除备份、缓存、临时文件。
7. 校验命名标准文件与只读检查脚本存在；本轮命名规范先行时，只执行报告，不迁移 `.agent` 旧名。
8. 将插件源目录镜像到目标市场的 `plugins/project-delivery-hub-v1`；若目标 marketplace config 不存在，先创建只包含当前插件的本地 marketplace 注册文件；镜像时排除 `.bak`、`__pycache__`、临时日志、缓存文件、智能表格私有配置文件与智能表格回执目录。
9. 同步 Codex 缓存到 `.codex/plugins/cache/<marketplace>/project-delivery-hub-v1/<version>`。
10. 验证 JSON/TOML 可解析，验证新包和缓存中没有旧 active URI；`.agent` 内历史资料不参与旧 active URI 判定。
11. 只报告旧目录或旧缓存仍存在；除非用户明确要求清理，不删除历史来源。

## 推荐命令

默认打包到配置指定的默认 target。当前配置默认是 `company-dev`；若只是检查目标、排除项与 agentBundle 来源，先用 `-DryRun`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<pluginRoot>\skills\plugin-packager\scripts\package_project_delivery_hub.ps1" -DryRun
```

确认 dry-run 输出后，正式打包到默认 target：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<pluginRoot>\skills\plugin-packager\scripts\package_project_delivery_hub.ps1"
```

完整刷新本机维护版、开发测试版与缓存：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<pluginRoot>\skills\plugin-packager\scripts\package_project_delivery_hub.ps1" -Target both
```

`-DryRun` 只验证配置、必要资产、目标路径与 mirror 计划，不写入 marketplace、cache 或插件根目录的 `.agent` snapshot；正式同步必须去掉 `-DryRun`。

## 脚本与资产索引

- `agents/openai.yaml`
- `scripts/package_project_delivery_hub.ps1`
- `scripts/check_artifact_names.ps1`
- `assets/diagrams/专案交付中枢_主流程图.svg`
- `assets/diagrams/专案交付中枢_技能与agent架构图.svg`
- `assets/diagrams/专案交付中枢_工作区与agent结构树.svg`

## 验收口径

- `C:\Users\<username>\.codex\config.toml` 启用 `project-delivery-hub-v1@company-jimmy`。
- `company-jimmy` 与 `company-dev` marketplace 均能解析 `project-delivery-hub-v1`。
- `company-dev` 包内的 `references/package-targets.json` 标明默认打包目标为 `plugin://project-delivery-hub-v1@company-dev`。
- 新包与新缓存内都包含 `USAGE.md`，且说明 `.agent` 正式运行位置是项目工作区 `<workspaceRoot>\.agent`。
- 新包与新缓存内的 `interface.composerIcon` 与 `interface.logo` 指向插件包内真实图片资源，不引用 Downloads、个人绝对路径或外部 URL。
- 新包与新缓存内都包含 `.agent`，来源为 `references/package-targets.json` 的 `agentBundle`。
- 新包与新缓存内的 `.agent` 不包含 `.bak`、`__pycache__`、`.tmp`、`.log`、`.pyc`。
- 新包与新缓存内不得包含 `.agent/workspaces`；workspace snapshot 统一读取 `.agent/config/chain-workspace.json`。
- 新包与新缓存内都包含 `references/artifact-naming-standard.json`、`references/artifact-naming-standard.md` 与 `skills/plugin-packager/scripts/check_artifact_names.ps1`。
- 新包与新缓存内都包含：
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_主流程图.svg`
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_技能与agent架构图.svg`
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_工作区与agent结构树.svg`
- 若本次包含结构型变动，上述三张图必须已经反映最新技能关系、`.agent` 职责、工作区/分支代码位置与打包/cache 流向。
- 新缓存内没有 `.bak` 与 `__pycache__`。
- 新包与新缓存内的技能 `SKILL.md` frontmatter `name` 使用 kebab 技术 ID（与目录名、文档内 `$技能` 引用一致）；`专案交付中枢：` 前缀只用于 agent 入口 `interface.display_name`（且不保留顶层 `name`）。
- 新包与新缓存内没有 `sql-fixture-targets.local.json`、`wedoc-smartsheet-targets.json`、`wedoc-smartsheet-targets.local.json`、`.agent/wedoc-smartsheet-receipts/` 或真实企业微信智能表格 WebHook URL；也没有带真实值的个人配置 `local-workspaces.json`、`design-source-registry.json`、`feature-tester-map.json`、`chain-workspace.json`；但必须包含全部 `references/*.example.json` 模板（`local-workspaces` / `design-source-registry` / `feature-tester-map` / `chain-workspace` / `wedoc-smartsheet-targets`）、`references/rule-pack-templates/generic/`（含 `catalog.json` 与 code-guidelines 规则）与 `skills/workspace-onboarding/`（含 `scripts/init_workspace_config.py`、`agents/openai.yaml`、`assets/`）。
- 新包与新缓存内的 bundled `.agent`（若有）不含 `functions/`、`status/`、`tmp/`、`wedoc-smartsheet-staging/`、`reference/`；`.agent/project-rules/` 团队规则库可保留（同团队连续性）。
- 新包内不得出现旧插件 ID 与旧个人 marketplace 的 active 组合。

## Multi API Leader Packaging

`multi-api-leader` 是结构性插件能力，打包时必须一起校验：

- `skills/multi-api-leader/SKILL.md`
- `skills/multi-api-leader/agents/openai.yaml`
- `skills/multi-api-leader/scripts/orchestrate_multi_api.py`
- `skills/multi-api-leader/tests/run_regressions.py`
- `schemas/leader-run.schema.json`
- `schemas/api-workgroups.schema.json`
- `schemas/file-claims.schema.json`
- `schemas/final-assessment.schema.json`

如果 orchestration 状态面、file claim、final assessment 或 worker 分工规则有变化，必须同步更新 `USAGE.md`、命名标准、三张架构 SVG 与 package dry-run 校验。

## Design Leader Packaging

`api-detail-tsd-sync` 的 Design Leader Mode、`design-feedback-fix-coordinator` 与 `office-deliverable-editor` 是设计阶段结构性能力，打包时必须一起校验：

- `references/design-leader-protocol.md`
- `references/office-deliverable-edit-protocol.md`
- `skills/api-detail-tsd-sync/SKILL.md`
- `skills/api-detail-tsd-sync/agents/openai.yaml`
- `skills/design-feedback-fix-coordinator/SKILL.md`
- `skills/design-feedback-fix-coordinator/agents/openai.yaml`
- `skills/office-deliverable-editor/SKILL.md`
- `skills/office-deliverable-editor/agents/openai.yaml`
- `references/artifact-naming-standard.json` 中的 `00-design-leader-*` 与 `00-office-edit-*` mappings
- `skills/api-detail-tsd-sync/schemas/design-change-plan.schema.json`
- `skills/api-detail-tsd-sync/schemas/office-edit-plan.schema.json`
- `skills/api-detail-tsd-sync/schemas/file-claims.schema.json`
- `skills/api-detail-tsd-sync/schemas/worker-results.schema.json`
- `skills/api-detail-tsd-sync/schemas/final-design-fix-report.schema.json`
- `skills/api-detail-tsd-sync/schemas/office-edit-results.schema.json`
- `skills/api-detail-tsd-sync/scripts/validate_design_artifacts.py`

如果设计阶段 orchestration 状态面、feedback entrypoint、Office edit plan、file claim 或 handoff 写入规则有变化，必须同步更新 `USAGE.md`、命名标准、三张架构 SVG 与 package dry-run 校验。
