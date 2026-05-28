# 01 Reference Index Importer 新手教程

这个第 01 步 skill 用来把外部参考资料导入项目的 `.agent/reference/global`，并生成给第 02 步 `api-spec-writer` 使用的索引文件。它不是主链路的第一步；真正的主链路起点是 `专案需求接口设计梳理`，先生成 `.agent/functions/<functionCode>/analysis + inputs + handoff`，后面 02 才有可消费的开发输入。

## 什么时候用

- 第一次初始化 `.agent/reference/global`
- 外部 API / DB Schema 有更新，要重建索引
- 第 02 步 `api-spec-writer` 需要参考 `.agent/reference/global`，但当前没有 `catalog.json` 或 `indexes/*.json`

## 你要准备什么

1. 一个外部 API 根目录
2. 一个 DB Schema 根目录

开发规范、JWT / Redis / Session 说明、框架说明文档不要交给 01。它们应先由 `专案规则分析器` 以 `--category code-guidelines` 写入 `.agent/project-rules/<workspaceKey>`，再由第 04 步读取 `apiCodeWriter` 规则包。

## 最简单的用法

先进入 skill 目录，再执行脚本：

```powershell
Set-Location "<pluginRoot>\\skills\\reference-index-importer"

python ".\\scripts\\import_reference_indexes.py" `
  --project-root "D:\Repo\Project" `
  --external-api-dir "D:\Refs\ExternalApi" `
  --db-schema-dir "D:\Refs\DbSchema"
```

## 跑完会产出什么

会重建下面这些内容：

- `.agent/reference/global/catalog.json`
- `.agent/reference/global/indexes/external-api-index.json`
- `.agent/reference/global/indexes/db-schema-index.json`
- `.agent/reference/global/raw/...`

## 怎么判断成功

命令结束后会打印类似结果：

```text
referenceRoot: D:/Repo/Project/.agent/reference/global
externalApiImported: 82
dbSchemaImported: 3
```

只要看到 `referenceRoot` 和各分类导入数量，就表示索引已经建出来了。

## 使用上的注意点

- 这个动作会重建 `.agent/reference/global`
- 不要把手工文件直接放在 `.agent/reference/global` 下面
- 第 02 步 `api-spec-writer` 不负责导入参考资料；若确实缺外部 API / DB Schema 索引，再跑这个第 01 步 skill
- 推荐链路是 `专案需求接口设计梳理 -> 可选 01 -> 02 -> 03 Optional -> 专案规则分析器(code-guidelines) -> 04 -> 05 Optional`
- 当前 skill 已自包含，不依赖其他兄弟 skill 的脚本路径
- 如果 `.agent/reference/global` 被防毒或 Explorer 占用，重建时可能会删不掉旧目录；这时先关闭占用再重跑
