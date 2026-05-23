# DAWHO Path Registry Rules

Use these rules when resolving function codes to PRD, TSD, API Detail, Common, Response Code, Customer IT SPEC, or legacy project evidence.

> Extracted from the former heavy `SKILL.md` so the entrypoint can stay lightweight. Load this file only when the matching workflow is active.

## 功能文件路径配置

使用工作区级目录 registry，让用户在设计/API 分析时不必重复提供很长的 PRD/TSD/API SPEC/Common 路径。仅记录目录、功能编号与轻量解析线索，不记录每次命中的完整文件路径。默认不要把这份设计来源 registry 与开发链 `.agent/context` 执行面混用，因为 `.agent/context` 只记录执行状态。

Registry 位置：

- 设计/API 分析默认 registry：当前 `workspaceKey` 对应的 `<agentRoot>/config/design-source-registry.json`，例如 `D:\Devs\<PROJECT>\.agent\config\design-source-registry.json`。
- `agentRoot` 先由 `--agent-root` / `PROJECT_AGENT_ROOT` / `references/local-workspaces.json.agentRoot` 解析；若用户只给项目工作区，则使用 `<workspaceRoot>\.agent`。
- 插件内 `references/api-file-registry.json` 只作为空模板和旧资料迁移参考，不再作为运行时默认 registry，也不要写入个人路径。
- 不再使用 `.agent/context/api-file-registry.json` 保存设计目录配置；`.agent/context` 留给 01-05 的 execution state、API checklist、manifest 与报告状态。
- 若用户为新功能编号提供文件路径，只记录父目录与后续重新查找文件所需的功能元数据。
- 若用户明确说明这些目录只适用于某个专案/工作区，也仍写入该工作区 `.agent/config/design-source-registry.json`，而不是写入插件目录或 `.agent/context`。
- 不要把项目文件路径直接写入本 `SKILL.md`。
- 打包或分享插件时，`.agent` 可作为初始化快照随包带出；新同事正式使用时应把 `.agent` 放到项目工作区，再按本机路径调整 `config/design-source-registry.json`。

Registry 结构：

```json
{
  "version": 2,
  "directories": {
    "prd": "path/to/2_PRD5.x",
    "tsdApiSpec": "path/to/v1.x",
    "common": "path/to/TSD共用相關",
    "customerItSpec": "path/to/06 IT API Doc",
    "legacyProject": "path/to/03 舊大戶代碼相關/既有大戶程式_YYYYMMDD"
  },
  "functions": {
    "D.001 D.002": {
      "aliases": ["D.001", "D.002"],
      "prdCodes": ["D.001", "D.002"],
      "tsdCodes": ["D.001", "D.002"],
      "apiSpecDomain": "Deposit",
      "notes": "optional short note"
    }
  }
}
```

路径解析流程：

1. 每次任务开始时，从用户消息中解析功能编号，例如 `D.001`、`D.002`、`D.001 D.002`、`N.006`。
2. 对需求/接口设计任务，只读取当前工作区 `<agentRoot>/config/design-source-registry.json`。不要自动读取当前工作目录的 `.agent/context/api-file-registry.json`。
3. 对 01-05 开发链任务，也不要把设计目录 registry 写入 `.agent/context`；若下游需要开发输入文件，应由梳理技能物化 `.agent/functions/<functionCode>/inputs` 与 `handoff/development-handoff.json`。
4. 若选定 registry 缺失、为空、JSON 无效、缺少必要 `directories`、指向不存在目录，或无法解析目标功能，则暂停路径解析，先请用户配置路径再继续。
5. 若用户提供 PRD/TSD/API SPEC/Common/customer IT SPEC 文件路径，先验证文件或目录存在；分析前只把父目录与功能元数据写入 `<agentRoot>/config/design-source-registry.json`。
6. 若用户只提供功能编号，先按精确 key 解析，再按 `aliases` 解析，并使用当前场景选定的 registry。
7. 从已登记目录重新发现实际文件：
   - 使用精确功能编号 token 匹配：编号前可出现文件名开头、`.`、`_`、空格、`-` 或标点等分隔符；`D.001` 不得误匹配 `D.001.001`。
   - PRD：对每个 `prdCodes[]`，在 `directories.prd` 中搜索文件名以精确编号 token 开头的 `.docx`；若有多个匹配，优先选择文件名中版本/日期最新者，其次看最后修改时间。
   - TSD：在 `directories.tsdApiSpec` 中搜索文件名包含所有 `tsdCodes[]` 精确编号 token 的 `.docx`；组合编号可用 `_`、空格或标点连接。
   - API SPEC：在 `directories.tsdApiSpec` 中搜索 `NEWDA_API_DETAIL_{apiSpecDomain}*.xlsx`；若有多个匹配，优先文件名含 `being processed` 者，其次看最后修改时间。
   - CommonUtil：在 `directories.common` 中搜索 `NEWDA_API_DETAIL_CommonUtil*.xlsx`，优先最后修改时间最新者。
   - CommonFunc：在 `directories.common` 中搜索 `NEWDA_API_DETAIL_CommonFunc*.xlsx`，优先最后修改时间最新者。
   - Response Codes：在 `directories.tsdApiSpec` 中搜索 `Api_Response_Codes*.xlsx`，优先最后修改时间最新者。
   - Customer IT SPEC: when `directories.customerItSpec` exists, search the business-domain subfolder matching the function-code prefix first, for example `L.*` -> `L 繳費`; then search root-level common files; use `APIDoc 參考 20251231` only as historical fallback. Prefer exact function-code filename matches, then newest version/date in filename, then latest modified time.
   - Legacy project: when `directories.legacyProject` exists, use it as the old DAWHO program/code evidence root for legacy method names, code-behind references, SQL/SP clues, request/response mapping, and old business-flow confirmation. Prefer exact function-code, API name, screen name, or legacy method-name matches; keep old program names as evidence/alias only, not as formal `BackendAPI` names.
8. 若只有一个 registry 条目且必要文件均可解析，直接使用并简要说明已解析的条目。
9. 若多个 registry 条目匹配，请用户选择目标功能组。
10. 若没有 registry 条目匹配，或必要文件无法解析，只询问一次缺失路径。使用这段简短提示：
   - `首次使用或目前路徑配置無效。請提供 {functionCode} 的 PRD 目錄、TSD/API Spec 目錄、API Detail workbook 所在目錄、CommonUtil/CommonFunc 目錄、可選 customer IT SPEC 目錄，以及 API 類別（如 Deposit/Exchange/Payment）；我會只記錄目錄到 <agentRoot>/config/design-source-registry.json。`
11. 对选定 registry 已可解析的路径，不要重复询问，除非用户明确要切换目录/文件。

当合并版 TSD/API 覆盖多个 PRD 编号时，记录合并 key，例如 `D.001 D.002`，并把每个独立 PRD 编号加入 `aliases`。若用户后续只询问 `D.001`，应解析到合并条目。
