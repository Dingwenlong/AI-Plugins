---
name: reference-index-importer
description: 把外部 API 资料与 DB Schema 导入全局参考索引。可选『参考资料索引导入器』（资料准备旁路，非主链编号步骤）：维护集中 `.agent/reference/global`，生成 `catalog.json` 与分类索引，供 01、02、03 消费；不搜集开发规范、不维护 `.agent/project-rules`，不梳理单一功能，也不生成功能 handoff。关键词：external API、DB Schema、reference catalog。
---

# 【资料准备】参考资料索引导入器

这个可选『参考资料索引导入器』（资料准备旁路，非主链编号步骤）只有一个职责：把外部 API 资料与 DB Schema 导入共享 `.agent/reference/global`，生成可索引的 `catalog.json` 与分类索引，同时喂给 01、02、03（03 靠这里的表目录定位目标表；01 设计梳理可用它校验后端来源/命名/字段，详见 `api-detail-tsd-sync`）。它不负责搜集开发规范、不梳理单一功能、不复制功能开发输入包、不生成 `.agent/functions/<functionCode>/handoff/development-handoff.json`。

梳理（01）仍是推荐前置；本旁路只在确需外部 API / DB Schema 索引时才补做。第 02 步 [$api-spec-writer](<pluginRoot>/skills/api-spec-writer/SKILL.md) 缺少功能 handoff 时，也允许用明确的 `docx_ref` / `execution-batch` 直接继续（见 api-spec-writer 现文），不必把本旁路当补救步骤。

默认优先解析插件本地 `references/local-workspaces.json`，可按 `workspaceKey` 指向对应集中 `.agent`。参数优先级为 `--agent-root/--workspace-root` > 环境变量 > 插件本地配置 > 旧逻辑 `<project-root>\.agent`。

本旁路只维护 `.agent/reference/global` 的外部资料索引，不维护专案规则库。开发规范、框架说明、Redis / JWT / Session 说明、编码规范等一律交给 `专案规则分析器` 写入 `<rulesRoot>/rules/code-guidelines/` 与 `<rulesRoot>/catalog.json`，再由第 04 步 `api-code-writer` 的 `apiCodeWriter` 规则包读取。`--rules-root` 仅用于把 workspace snapshot 与后续技能串起来，不会把 reference 文件当成 active project rules。

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

- 这个可选『参考资料索引导入器』（资料准备旁路）只负责“导入并建索引”，不负责写 API spec。
- 第 02 步 [$api-spec-writer](<pluginRoot>/skills/api-spec-writer/SKILL.md) 读取顺序为功能专属 `inputs/reference` > 全局 `.agent/reference/global` > legacy `.agent/Reference`。
- 本旁路只维护全局外部参考索引；功能专属 TSD / API Detail / Common / Response Code / DB / Redis 输入包由梳理技能和 `materialize_design_handoff.py` 负责。
- 开发规范不进入本旁路。需要开发规范时，先运行 `专案规则分析器 --category code-guidelines` 生成 active project rules，再让 04 读取 `apiCodeWriter` 规则包。
- 当前 skill 已自包含 `import_reference_indexes.py`、`reference_support.py`、`runtime.py`，不依赖其他兄弟 skill 的脚本目录。
- 导入时会重建 `.agent/reference/global`，不要把手工文件直接放在该目录下。
- 旧分支 `.agent` 迁移先使用 `scripts/migrate_central_agent.py` dry-run；加 `--apply` 时只复制到集中 `.agent/legacy-imports/`，不删除旧目录。
- 新手可先看 `references/getting-started.md`。
- 从零开始的团队流程看 `references/team-onboarding-workflow.md`。
- 团队端到端模板见 `references/team-end-to-end-template.md`。

## DB Schema Excel 的「清单 + 编号 sheet」模式（重要）

部分外部 DB Schema Excel **不是**「一个 sheet 一张表、sheet 名即表名」的结构，而是：

- **第一个 sheet 是清单/目录**（常见名 `Table List` / `清单` / `list`），用表头行（如 `project`(编号)、`data sheet`(表名)、`describe`(描述)、`Category`、`Infinity Functionality`、`Table Status`）建立 **编号 → 真实表名 → 描述/分类** 的权威映射。
- **其余 sheet 按编号命名**（`15`、`16`、`17`…）；sheet 名只是编号，真正的表名写在该 sheet 内部（通常第 1 行 `data sheet` 储存格）。

例：`MMA to Infinity DBX Traceability Mapping.xlsx` 共 241 个 sheet，首个 `Table List` 列出 `15 → ACCT_ACTIVITY`、`16 → ACCT_NOTRANSFER`…，其余 240 个编号 sheet 各放一张表的字段定义。

对这类文件，`scripts/import_reference_indexes.py` 现在会**自动识别并把第一个清单 sheet 解析成权威表目录**：

- 在 db-schema 索引记录中输出 `tableCatalog`（每条 `编号 sheet ↔ 真实表名 ↔ 描述/分类`），并把真实表名（**含不含底线的表名**，如 `APIWHITELIST`、`LISTRATE`）与编号一并加入 `tableNames` / `sheetMatchKeys`，使下游能用**真实表名**（而非 `15` 这种编号）检索到对应 sheet；否则第 03 步 `api-sql-fixture-preparer` 会找不到目标表。
- 这弥补了默认 token 扫描的盲区：旧逻辑只抓储存格里**带底线的大写 token**，会漏掉**不含底线的表名**与表的**描述/分类**——这些只能从清单 sheet 补全。
- 触发线索（`workbook_looks_like_catalog`）：首个 sheet 名为 `Table List`/`清单`/`list` 等，或其余 sheet 大量是纯数字/编号。普通「一个 sheet 一张表、sheet 名即表名」的工作簿不会触发，行为不变。
- 若清单 sheet 缺失或解析不出表目录，`tableCatalog` 为空、回退到原 token 扫描；正式流程应在索引报告中标记该文件「表目录不完整」并提示下游可能找不到目标表、需人工补充。
