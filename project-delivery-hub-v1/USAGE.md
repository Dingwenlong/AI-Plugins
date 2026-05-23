# 专案交付中枢使用说明

本文用于把 `project-delivery-hub-v1` 分发给其他同事使用。插件包可以放在 Codex marketplace 目录里，但 `.agent` 是项目工作区资料库，正式运行时必须放在项目工作区根目录。

## 目录定位

分发包建议保持这一层结构：

```text
company-dev\
  .agents\
    plugins\
      marketplace.json
  plugins\
    project-delivery-hub-v1\
      .codex-plugin\
      references\
      skills\
      .agent\                  # 随包快照，只作为初始化来源
      USAGE.md
```

实际项目工作区建议保持这一层结构：

```text
D:\Devs\<PROJECT>\
  .agent\                      # 正式运行位置
  <feature-branch-folder-1>\
  <feature-branch-folder-2>\
```

重点规则：

- 插件安装目录只放插件能力和随包快照。
- `.agent` 的正式运行位置是项目工作区根目录，例如 `D:\Devs\<PROJECT>\.agent`。
- 多个功能分支可以共享同一个项目工作区 `.agent`。
- Codex cache 目录只由 Codex 使用，不要把它当成项目资料库维护。

## 安装插件

1. 将整个 marketplace 包解压到本机目录，例如：

```text
C:\Users\<用户名>\plugin-marketplaces\company-dev
```

2. 在 `C:\Users\<用户名>\.codex\config.toml` 增加或确认：

```toml
[marketplaces.company-dev]
source_type = "local"
source = 'C:\Users\<用户名>\plugin-marketplaces\company-dev'

[plugins."project-delivery-hub-v1@company-dev"]
enabled = true
```

3. 重启 Codex。

4. 可用 URI：

```text
plugin://project-delivery-hub-v1@company-dev
```

## 初始化项目工作区 `.agent`

如果项目工作区还没有 `.agent`，从插件包的随包快照初始化：

```powershell
$pluginAgent = 'C:\Users\<用户名>\plugin-marketplaces\company-dev\plugins\project-delivery-hub-v1\.agent'
$workspaceAgent = 'D:\Devs\<PROJECT>\.agent'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $workspaceAgent) | Out-Null
robocopy $pluginAgent $workspaceAgent /MIR /XD __pycache__ .git /XF *.bak *.tmp *.log *.pyc
```

如果项目工作区已经有 `.agent`，不要直接覆盖；先确认要合并的内容，再把规则库、功能资料或状态文件按需迁入。

## 配置工作区路径

打开插件目录下：

```text
plugins\project-delivery-hub-v1\references\local-workspaces.json
```

把对应专案改成自己的路径，例如：

```json
{
  "schemaVersion": "1.0.0",
  "defaultWorkspace": "PROJECT",
  "workspaces": {
    "PROJECT": {
      "workspaceRoot": "D:\\Devs\\PROJECT",
      "agentRoot": "D:\\Devs\\PROJECT\\.agent",
      "rulesRoot": "D:\\Devs\\PROJECT\\.agent\\project-rules\\PROJECT",
      "defaultCodeRoot": "D:\\Devs\\PROJECT\\feature_common",
      "notes": "Centralized shared .agent for PROJECT feature branches."
    }
  }
}
```

路径含义：

- `workspaceRoot`：项目主工作区，`.agent` 应该放在这里。
- `agentRoot`：共享链路资料库，必须指向 `<workspaceRoot>\.agent`。
- `rulesRoot`：专案规则库，通常是 `<agentRoot>\project-rules\<workspaceKey>`。
- `defaultCodeRoot`：默认代码分支目录，可按功能切换。

PRD / TSD / API Detail / Common 等设计资料目录不要写在插件配置里，统一放到：

```text
<workspaceRoot>\.agent\config\design-source-registry.json
```

这个文件由 `专案需求接口设计梳理` 使用，只记录目录、功能编号、API 类别和轻量索引；`.agent\context` 只记录 01-05 执行状态。

`.agent\config\chain-workspace.json` 是当前工作区解析快照，只记录本次解析到的 `workspaceKey`、`workspaceRoot`、`agentRoot`、`rulesRoot`、`projectRoot` 与配置来源。

## 配置企业微信智能表格同步目标

智能表格 WebHook、请求字段格式和使用者信息属于个人/项目私有配置，不放在插件目录里。每个项目工作区都需要自行配置：

```text
<workspaceRoot>\.agent\config\wedoc-smartsheet-targets.json
```

可从插件模板复制：

```text
plugins\project-delivery-hub-v1\references\wedoc-smartsheet-targets.example.json
```

配置要点：

- 每个文档或工作表配置一个 `target key`，例如 `common-change-list`。
- `webhookUrl` 填企业微信智能表格「接收外部数据」生成的工作表 WebHook。
- `userId` 优先填自己的企业微信真实成员 ID。
- 如果暂时只有姓名/别名，且目标智能表格确认接受人员字段姓名/别名模式，可填 `userText`，例如 `丁文龙(Jimmy)`；不要把显示名填进 `userId`。
- `requestFormat.schema` 和 `requestFormat.fieldMap` 按智能表格示例数据填写。
- 多个目标同时存在时，使用技能时可按 `target key` 指定；若只描述语意，技能会按 `key/displayName/description/keywords` 匹配，无法唯一判断时会要求用户选择。

导出插件时会自动排除并扫描阻断以下内容：

- `.agent\config\wedoc-smartsheet-targets.json`
- `.agent\config\wedoc-smartsheet-targets.local.json`
- `.agent\wedoc-smartsheet-receipts\`
- 真实企业微信智能表格 WebHook URL

新增记录成功后，技能会把企业微信返回的 `record_id` 和本次请求内容追加到：

```text
<workspaceRoot>\.agent\wedoc-smartsheet-receipts\<targetKey>.jsonl
```

后续要更新记录时，先用 `--list-receipts` 查回对应 `record_id`，再调用更新记录。回执日志属于项目运行资料，只保留 target key、请求 payload、响应 payload 和 record_id，不记录 WebHook URL，也不随插件包导出。

## 产物命名标准

- 插件级命名标准在 `references/artifact-naming-standard.md` 与 `references/artifact-naming-standard.json`。
- 本版先固定标准，不自动重命名既有 `.agent` 文件。
- 新规则采用阶段语义：`00-` 设计梳理、`01-` 参考索引、`02-` API Spec、`03-` SQL fixture、`04-` 代码写入、`05-` UT 报告，跨技能共享文件使用 `chain-`。
- `.agent/functions/<functionCode>/inputs/` 中复制来的客户源文件保留原文件名；客户正式交付物按专案交付规则优先。
- 只读检查脚本：`skills/plugin-packager/scripts/check_artifact_names.ps1`，用于列出仍符合旧命名的 `.agent` 文件，不会移动、删除或改名。

## 使用顺序

常见链路：

```text
专案规则分析器 -> 需求接口设计梳理 -> 02 API 规格写入器 -> 03 SQL 测试资料准备器 -> 04 API 业务代码写入器 -> 05 单元测试报告生成器
```

补充说明：

- 01 参考资料索引导入器只负责外部 API、DB Schema 等共用参考索引。
- 已经有梳理产物的功能，可以由 02 直接读取 `.agent/functions/<functionCode>/handoff/development-handoff.json`。
- 没有梳理产物的功能，02 会要求先回到需求接口设计梳理，把开发输入包补齐。
- 04 的开发规范、代码规则应来自 `.agent/project-rules/<workspaceKey>`，不是 01。

## 分发与更新注意事项

- 分发给别人时，建议发整个 marketplace 目录，不要只发 `skills`。
- `.agent` 随包只是初始化快照；正式运行、持续更新、状态累积都发生在项目工作区 `.agent`。
- 打包时会自动排除 `.bak`、`__pycache__`、`.tmp`、`.log`、`.pyc`。
- 打包时会携带 `references/artifact-naming-standard.md`、`references/artifact-naming-standard.json` 与命名检查脚本。
- 插件发生结构型变动时，必须同步更新三张 SVG：
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_主流程图.svg`
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_技能与agent架构图.svg`
  - `skills/plugin-packager/assets/diagrams/专案交付中枢_工作区与agent结构树.svg`
- 新项目应复制 `.agent/project-rules/<workspaceKey>` 的结构，再替换为自己的专案规则。

## 快速检查

安装后可检查：

```text
C:\Users\<用户名>\plugin-marketplaces\company-dev\.agents\plugins\marketplace.json
C:\Users\<用户名>\plugin-marketplaces\company-dev\plugins\project-delivery-hub-v1\USAGE.md
D:\Devs\<PROJECT>\.agent
```

如果 Codex 看不到插件，先确认 `config.toml` 中 marketplace 路径与插件启用项是否一致，再重启 Codex。
