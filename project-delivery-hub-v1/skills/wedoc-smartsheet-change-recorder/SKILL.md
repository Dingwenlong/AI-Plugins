---
name: 专案交付中枢：【运营同步】企业微信智能表格异动记录器
description: 将 Common/API/配置异动记录写入企业微信文档智能表格 WebHook。用于按 `records-json` 生成 add_records 或 update_records payload，可只读参考本地异动清单 Excel 的表头与示例写法，并按项目 .agent 私有配置选择 target key、校验 WebHook、json 请求格式与 user_id，防止未配置或误用他人配置。
---

# 【运营同步】企业微信智能表格异动记录器

用于把结构化 `records-json` 转换为企业微信文档智能表格 WebHook payload，并提交新增或更新记录。本地异动清单 Excel 只作为表头、字段写法和历史记录风格的证据；脚本不会从 Excel 自动抽取待提交记录。

## 必要配置

真实配置必须放在项目工作区：

```text
<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json
```

不要把真实 WebHook、user_id 或私有请求格式写入插件目录。复制插件模板 `references/wedoc-smartsheet-targets.example.json` 后按项目修改。

每个同步目标必须配置一个 `target key`，供后续按对话语意选择：

- `displayName`: 给用户看的目标名称。
- `description`: 目标用途说明。
- `keywords`: 用于语意匹配的关键词，例如 `Common異動清單`、`CommonFunc`。
- `webhookUrl`: 企业微信文档智能表格「接收外部数据」工作表 WebHook。
- `userId`: 当前使用者企业微信真实 user_id，优先使用。
- `userText`: 当前使用者姓名/别名，例如 `丁文龙(Jimmy)`；仅在没有真实 user_id、且目标智能表格确认接受姓名/别名模式时使用。
- `requestFormat.schema`: 智能表格示例数据中的字段 schema。
- `requestFormat.fieldMap`: 标准字段到字段 ID 的映射，必须包含 `note`、`content`、`date`、`user`、`type`、`api`。

## 工作流

1. 若用户提供 Excel，先只读查看第一行表头和已有数据，确认字段写法；不要把 Excel 当成脚本的记录来源。
2. 将本次要新增/更新的记录整理成 `records-json`。若用户只给 Excel，必须先由人工或表格工具抽取成 JSON，再调用脚本。
3. 读取 `<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json`。
4. 选择 target：
   - 用户明确说 key 时，使用 `--target-key`。
   - 用户描述目标时，使用 `--target-hint` 依据 `key/displayName/description/keywords` 匹配。
   - 只有一个 target 时可自动使用。
   - 多个 target 无法唯一判断时，列出 key 和 displayName，请用户选择；不要猜测发送。
5. 校验 target：
   - WebHook 必须是企业微信智能表格 WebHook，且不能是占位值。
   - `userId` 或 `userText` 必须至少有一个存在且不能是占位值。
   - `requestFormat.schema` 与 `requestFormat.fieldMap` 必须完整。
6. 按既有清单风格整理记录：
   - `備註` 写变更类型，例如 `變更公共方法`、`新追加公共方法`、`增加配置項`。
   - `調整內容` 用编号逐条写清楚，保留换行。
   - `調整日期` 转为北京时间当天 00:00:00 的毫秒时间戳字符串。
   - `調整人(人员)` 优先使用 userid 模式：`[{"user_id": "<userId>"}]`。
   - 若配置的是 `userText`，使用姓名/别名模式：`["丁文龙(Jimmy)"]`，不要把显示名塞进 `user_id`。
   - `所屬類型` 写 `CommonUtil` / `CommonFunc` / `appsetting` 等。
   - `調整接口` 写接口或配置名称。
7. 调用 WebHook 后检查 `errcode`：
   - `0` 表示成功，记录返回的 `record_id`，并追加写入 `<workspaceRoot>\.agent\wedoc-smartsheet-receipts\<targetKey>.jsonl`。
   - 非 0 时回报错误码和 errmsg，不重复新增。
8. 后续要更新记录时，先用 `--list-receipts` 查回当初新增时的 `record_id`，再调用 `update_records`。

## 脚本

使用 `scripts/send_wedoc_change_records.py` 生成或提交 payload。以下路径请按实际插件安装目录替换。

新增记录。`--records-json` 是待提交记录来源，`--excel` 只是可选证据路径：

```powershell
python "<pluginRoot>\skills\wedoc-smartsheet-change-recorder\scripts\send_wedoc_change_records.py" `
  --config "<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json" `
  --target-key "common-change-list" `
  --excel "<workspaceRoot>\Common異動清單.xlsx" `
  --records-json ".\records.json" `
  --date "2026/5/23"
```

只生成 payload 不提交：

```powershell
python "<pluginRoot>\skills\wedoc-smartsheet-change-recorder\scripts\send_wedoc_change_records.py" `
  --config "<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json" `
  --target-key "common-change-list" `
  --records-json ".\records.json" `
  --dry-run
```

查询新增记录回执：

```powershell
python "<pluginRoot>\skills\wedoc-smartsheet-change-recorder\scripts\send_wedoc_change_records.py" `
  --config "<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json" `
  --target-key "common-change-list" `
  --list-receipts
```

按语意选择目标：

```powershell
python "<pluginRoot>\skills\wedoc-smartsheet-change-recorder\scripts\send_wedoc_change_records.py" `
  --target-hint "Common 異動清單" `
  --records-json ".\records.json" `
  --dry-run
```

列出可用目标：

```powershell
python "<pluginRoot>\skills\wedoc-smartsheet-change-recorder\scripts\send_wedoc_change_records.py" `
  --config "<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json" `
  --list-targets
```

更新既有记录人员字段：

```powershell
python "<pluginRoot>\skills\wedoc-smartsheet-change-recorder\scripts\send_wedoc_change_records.py" `
  --config "<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json" `
  --target-key "common-change-list" `
  --update-user-record-ids "BDh0ht,TmIZR7"
```

指定回执日志路径：

```powershell
python "<pluginRoot>\skills\wedoc-smartsheet-change-recorder\scripts\send_wedoc_change_records.py" `
  --config "<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json" `
  --target-key "common-change-list" `
  --records-json ".\records.json" `
  --receipt-log "<workspaceRoot>\.agent\wedoc-smartsheet-receipts\common-change-list.jsonl"
```

`records.json` 格式：

```json
[
  {
    "note": "變更公共方法",
    "content": "1.調整內容...",
    "type": "CommonUtil",
    "api": "GetCommonCurrency"
  }
]
```

## records-json 与 Excel 边界

- `--records-json` 必须是 JSON array，元素使用标准键 `note/content/type/api`，也可使用既有中文列名 `備註/調整內容/所屬類型/調整接口`。
- `--excel` 只检查文件存在并作为证据记录在操作说明中；脚本不会读取、解析或提交 Excel 行。
- 新增记录时没有 `--records-json` 必须阻塞，即使提供了 `--excel`。
- dry-run 会输出 payload 且不调用 WebHook、不写回执；正式新增成功后才写 `<workspaceRoot>\.agent\wedoc-smartsheet-receipts\<targetKey>.jsonl`。

## 资源

- `agents/openai.yaml`
- `scripts/send_wedoc_change_records.py`
- `tests/run_regressions.py`

## 注意

- 不要把一次性 WebHook URL 固化到技能文件、脚本或插件目录。
- 新增记录成功后必须记录回执日志；`--dry-run` 只看 payload，不写回执。
- 回执日志保存 `record_id`、请求 payload、响应 payload 与 target key；不保存 WebHook URL。
- 回执日志是项目运行资料，不随插件包分发。
- 新增记录和更新记录都使用 `POST` 到工作表 WebHook 地址。
- WebHook 不支持写入公式、自动编号、查找引用、关联、创建人、创建时间、最后编辑人、最后编辑时间、群聊、文件字段。
- 成员字段优先使用 userid 模式；若只有姓名/别名且目标智能表格确认可接受，配置 `userText`，脚本会写成字符串数组。
- 若已新增成功后发现人员字段不对，优先用 `update_records` 原地修正，不要重复新增。
- 频率限制：每个工作表累计添加或更新记录不超过 3000 条/分钟；每个智能表格文档所有 WebHook 累计不超过 10000 条/分钟。
