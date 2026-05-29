---
name: 专案交付中枢：【开发落地】代码规范审查器
description: 只读审查既有 C# 业务代码是否符合当前 04 api-code-writer 技能本体约束与专案外置 apiCodeWriter 规则包。用于 04 规范变更后定位旧代码不符合规范的位置，输出 code-style-review JSON/Markdown 报告；不修改代码、不生成测试源码、不回写 codeStatus。关键词：代码规范审查、旧代码、style review、code-style-review、04、apiCodeWriter、定位不符合规范。
---

# 【开发落地】代码规范审查器

用于在 04 代码产出规范变更后，回头检查旧代码是否还符合当前规范。这个技能是只读定位工具，不是修复器。

## 职责边界

- 读取当前 `skills/api-code-writer/SKILL.md` 作为 04 技能本体约束来源，不复制旧规则。
- 解析专案 `apiCodeWriter` 规则包，读取外置 `common-style`、`data-access` 等规则来源。
- 默认从 `.agent/context/<functionCode>/apis/*/change-plan.json` 收集 Controller / Interface / Service / Entity / codeTargetFiles，只扫相关业务源码。
- 输出 `.agent/context/<functionCode>/code-style-review.json` 与 `.md`；指定 `--api-id` 时也输出到对应 API 目录。
- 不修改业务代码，不改 `manifest.json`、`api-checklist.json`、`execution-state.json` 或 `codeStatus`。
- 不检查 UnitTest / IntegrationTest，除非用户显式传入 `--file`。

## 推荐命令

```powershell
python ".\skills\code-style-reviewer\scripts\review_code_style.py" `
  --project-root "<projectRoot>" `
  --agent-root "<agentRoot>" `
  --workspace-key "<workspaceKey>" `
  --function-code "<functionCode>"
```

缩小到单支 API：

```powershell
python ".\skills\code-style-reviewer\scripts\review_code_style.py" `
  --project-root "<projectRoot>" `
  --agent-root "<agentRoot>" `
  --workspace-key "<workspaceKey>" `
  --function-code "<functionCode>" `
  --api-id "<apiId>"
```

审查指定文件：

```powershell
python ".\skills\code-style-reviewer\scripts\review_code_style.py" `
  --project-root "<projectRoot>" `
  --agent-root "<agentRoot>" `
  --workspace-key "<workspaceKey>" `
  --function-code "<functionCode>" `
  --scope files `
  --file "<repo-relative-csharp-file>"
```

`<projectRoot>` 是实际代码分支目录，`<agentRoot>` 是共享 `.agent` 根目录；不要把旧会话中的本机路径当作默认值。

## 输出

- `code-style-review.json`
- `code-style-review.md`

每条 finding 至少包含：

- `severity`
- `category`
- `ruleId`
- `source`
- `file`
- `line`
- `message`
- `evidence`
- `expected`
- `actual`
- `fixHint`
- `confidence`

`needs_review` 表示脚本只定位候选，不假装已完成业务语义判断。

## 可定位规则

- block-scoped namespace 候选。
- 可简化 `new()` 候选。
- collection expression 候选。
- 防呆 `if` / defensive branch 缺少 `[業務]` / `[意圖]` 标签。
- 访问外部状态或服务的 `await` 缺少即时 `[意圖]` 标签。
- DI 字段命名不是 `_camelCase` 或仍使用传统构造函数候选。
- `QueryAsync(...).FirstOrDefault()` 未收敛为 `TOP (1)` / 单笔查询 API 候选。
- SQL 参数 helper 候选。
- 文件头 `新增人员` 不符合项目 author 规则。
- 既有源码缺少三行修改记录候选。
- 项目仓库内 `.bak`、`.tmp`、`.orig`、`.before_*` 等备份或临时副本。

## 验收

- `apiCodeWriter` 规则包必须 `status=ready`。
- 报告必须记录 `api-code-writer/SKILL.md`、规则包 catalog 与加载到的外置规则文件 path / sha256。
- 脚本只读业务仓库；唯一写入位置是 `.agent/context/<functionCode>/` 报告文件。

## 资源

- `agents/openai.yaml`
- `scripts/review_code_style.py`
- `tests/run_regressions.py`
