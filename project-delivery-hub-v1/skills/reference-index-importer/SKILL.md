---
name: 参考资料索引导入器
description: 把外部 API 资料与 DB Schema 导入全局参考索引。第 01 步：维护集中 `.agent/reference/global`，生成 `catalog.json` 与分类索引，供第 02 步 `api-spec-writer` 消费；不搜集开发规范、不维护 `.agent/project-rules`，不梳理单一功能，也不生成功能 handoff。关键词：external API、DB Schema、reference catalog。
---

# 01 参考资料索引导入器

这个第 01 步技能只有一个职责：把外部 API 资料与 DB Schema 导入共享 `.agent/reference/global`，生成可索引的 `catalog.json` 与分类索引。它不负责搜集开发规范、不梳理单一功能、不复制功能开发输入包、不生成 `.agent/functions/<functionCode>/handoff/development-handoff.json`。

第 02 步 [$api-spec-writer](C:/Users/<username>/plugins/project-delivery-hub-v1/skills/api-spec-writer/SKILL.md) 缺少功能 handoff 时，应该先回到 `专案需求接口设计梳理` 生成开发输入包，而不是把 01 当作补救步骤。只有当梳理或 02 明确需要“外部参考资料索引”时，才运行 01。

默认优先解析插件本地 `references/local-workspaces.json`，可按 `workspaceKey` 指向对应集中 `.agent`。参数优先级为 `--agent-root/--workspace-root` > 环境变量 > 插件本地配置 > 旧逻辑 `<project-root>\.agent`。

01 只维护 `.agent/reference/global` 的外部资料索引，不维护专案规则库。开发规范、框架说明、Redis / JWT / Session 说明、编码规范等一律交给 `专案规则分析器` 写入 `<rulesRoot>/rules/code-guidelines/` 与 `<rulesRoot>/catalog.json`，再由第 04 步 `api-code-writer` 的 `apiCodeWriter` 规则包读取。`--rules-root` 仅用于把 workspace snapshot 与后续技能串起来，不会把 reference 文件当成 active project rules。

1. 直接调用 `scripts/import_reference_indexes.py`
2. 传入 `--project-root`
3. 传入外部 API 根目录 `--external-api-dir`
4. 传入 DB Schema 根目录 `--db-schema-dir`
5. 运行后检查 `.agent/reference/global/catalog.json` 与 `indexes/*.json`

## 命令行

```powershell
python ".\scripts\import_reference_indexes.py" `
  --project-root "D:\Repo\Project" `
  --workspace-key "PROJECT" `
  --rules-root "D:\Repo\Project\.agent\project-rules\PROJECT" `
  --external-api-dir "D:\Refs\ExternalApi" `
  --db-schema-dir "D:\Refs\DbSchema"
```

## 输出

- `.agent/reference/global/catalog.json`
- `.agent/reference/global/indexes/external-api-index.json`
- `.agent/reference/global/indexes/db-schema-index.json`
- `.agent/reference/global/raw/external-api/...`
- `.agent/reference/global/raw/db-schema/...`

## 注意事项

- 这个第 01 步技能只负责“导入并建索引”，不负责写 API spec。
- 第 02 步 [$api-spec-writer](C:/Users/<username>/plugins/project-delivery-hub-v1/skills/api-spec-writer/SKILL.md) 读取顺序为功能专属 `inputs/reference` > 全局 `.agent/reference/global` > legacy `.agent/Reference`。
- 01 只维护全局外部参考索引；功能专属 TSD / API Detail / Common / Response Code / DB / Redis 输入包由梳理技能和 `materialize_design_handoff.py` 负责。
- 开发规范不进入 01。需要开发规范时，先运行 `专案规则分析器 --category code-guidelines` 生成 active project rules，再让 04 读取 `apiCodeWriter` 规则包。
- 当前 skill 已自包含 `import_reference_indexes.py`、`reference_support.py`、`runtime.py`，不依赖其他兄弟 skill 的脚本目录。
- 导入时会重建 `.agent/reference/global`，不要把手工文件直接放在该目录下。
- 旧分支 `.agent` 迁移先使用 `scripts/migrate_central_agent.py` dry-run；加 `--apply` 时只复制到集中 `.agent/legacy-imports/`，不删除旧目录。
- 新手可先看 `references/getting-started.md`。
- 从零开始的团队流程看 `references/team-onboarding-workflow.md`。
- 团队端到端模板见 `references/team-end-to-end-template.md`。
