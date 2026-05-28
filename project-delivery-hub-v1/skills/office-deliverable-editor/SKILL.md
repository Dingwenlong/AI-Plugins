---
name: 【交付文件】专案 Office 交付文件编辑器
description: 专门执行 TSD Word、API Detail Excel、CommonFunc/CommonUtil Excel、Response Code 等交付 Office 文件的物理写入、保存与复验。接收 Design Leader、格式检查器或用户明确给出的 office-edit-plan/file claim，只修改被 claim 的 .docx/.xlsx 文件，回报 modifiedFiles、摘要、验证命令、风险；不裁决业务语义、不判断格式规则、不写 handoff 或共享 .agent 状态。关键词：Word 编辑、Excel 编辑、office-edit-plan、DOCX、XLSX、modifiedFiles、file claim。
---

# 【交付文件】专案 Office 交付文件编辑器

本技能是交付 Office 文件的写入层。它负责把已经裁决好的内容或格式修复计划安全写入 `.docx` / `.xlsx`，并复验保存结果。

## 必读协议

执行前读取插件根目录：

- `references/office-deliverable-edit-protocol.md`

若任务来自设计阶段 leader，也读取：

- `references/design-leader-protocol.md`

## 职责边界

本技能负责：

- 修改 TSD Word 的指定段落、表格、章节文字、固定术语、表格样式与版面属性。
- 修改 API Detail / CommonFunc / CommonUtil / Response Code Excel 的指定 sheet、row、cell、hyperlink、合并格、边框、字体槽位、列高、栏宽、打印/显示设置。
- 使用 caller 指定的脚本或工具复验，例如 `check_tsd_docx.py`、`check_api_xlsx_format.py`、Excel COM 修复脚本、渲染或重新开启检查。
- 回报 `modifiedFiles`、改动摘要、验证命令/结果、阻塞项与风险。

本技能不负责：

- API contract、字段命名、后端来源、CommonFunc/CommonUtil 复用、Response Code 语义、开发就绪判断。
- 格式问题的优先级裁决、Must fix/Should fix/Visual risk 判定。
- 写 `.agent/functions/<functionCode>/handoff/*`、`.agent/functions/<functionCode>/orchestration/*`、`.agent/context/*`、`.agent/status/*`、最终报告或 package metadata。
- 绘制或修改 VSDX。

## 输入要求

优先接收 `office-edit-plan.json` 或明确等价输入。计划必须与 Design Leader / 格式检查器共用同一份契约：

- `schemaVersion`: 当前固定为 `"1.0.0"`
- `functionCode`（若有）
- `owner`: 例如 `api-detail-tsd-sync` 或 `delivery-format-checker`
- `claimId`
- `mode`: `semantic-content`、`format-fix` 或 `content-and-format`
- `targetFiles[]`: 可写目标文件绝对路径、文件类型、`claimScope: "whole-file"`
- `allowedOperations[]`: 每个允许动作的位置、操作、before/after 与 caller-owned reason
- `forbiddenOperations[]`: 禁止操作清单，至少包含未 claim 文件、共享 `.agent` 状态与越权全 workbook 扩散
- `validation[]`: 验证命令或验收口径

若调用者只说“帮我修这个 Word/Excel”，可以在当前对话中形成最小 edit plan；但不能自行发明业务语义或格式标准。

## 工作流程

1. 确认可写文件与 claim 范围；`.docx`、`.xlsx` 一律整文件 claim。
2. 检查文件是否存在、是否疑似锁定、是否属于用户指定工作区或交付目录。
3. 读取计划，只执行 `allowedOperations` 指定的位置和动作。
4. 按文件类型选择安全写入方式：
   - `.docx`：优先用 `python-docx` 精准改文字/表格；涉及版面或目录页码时需渲染或报告视觉风险。
   - `.xlsx`：可只读使用 `openpyxl`；保存含 OLE/media/EMF/控制项/批注/外部链接/复杂富文本的 workbook 时优先 Excel COM。
   - 调用既有 Excel COM 修复脚本时，必须传入 caller 明确给出的 sheet/range；不得默认扩成全 workbook。
5. 不默认产生 `.bak`、`.before_*` 或时间戳备份；确需临时副本时放在工具临时目录并清理。
6. 保存后重新开启每个修改过的文件，执行 caller 指定的检查或渲染。
7. 返回 worker result；在 leader 模式下只返回结果，由 leader 写共享状态。

## 输出格式

回报保持机器可读：

```json
{
  "schemaVersion": "1.0.0",
  "claimId": "office-d001001-api-detail",
  "modifiedFiles": [
    "D:/path/NEWDA_API_DETAIL_Deposit.xlsx"
  ],
  "changeSummary": [
    "Updated the specified Api_List row and adjusted row height."
  ],
  "validationCommands": [
    {
      "command": "python skills/delivery-format-checker/scripts/check_api_xlsx_format.py ...",
      "result": "passed",
      "summary": "Must fix = 0; Visual risk = 0"
    }
  ],
  "blockers": [],
  "risks": []
}
```

在 Design Leader 模式下，本技能只把上述结果交回 leader；由 leader 校验 `claimId`、`modifiedFiles` 与 `file-claims.json` 后写入 `worker-results.json` 或需要时的 `office-edit-results.json`。本技能本身不得写 orchestration、handoff、context 或最终报告。

如验证工具不可用、文件锁定、计划范围不明确、需要业务裁决或会越权修改未 claim 文件，立即停止并回报 blocker。
