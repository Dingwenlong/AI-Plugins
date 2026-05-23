---
name: 专案交付包收集器
description: 按功能编号收集冻版专案交付物并整理成交付目录。根据已冻版或近冻版的功能设计梳理稿复制 TSD、API Detail、VSDX、报告等文件到 `TSD 交付 YYYYMMDD`；找不到梳理稿或未达开发就绪时停止。关键词：交付包、冻版、功能设计梳理、TSD 交付。
---

# 专案交付包收集器

## 目的

用于根据功能设计梳理稿创建客户交付包。事实来源以梳理稿中的 `已确认交付物` 章节为准；执行时只复制文件，不移动或删除原始文件。

## 安全门槛

复制任何文件前，先完成以下检查：

1. 解析用户要求的功能编号，例如 `L.005`、`L.005.001`，或 `D.001.001 D.002.001` 这类组合编号。
2. 优先在集中 `.agent/functions/<functionCode>/analysis/` 下找到最新匹配的梳理稿；若未配置集中 `.agent` 或未命中，再兼容查找旧 `output/{functionCode}_api_design/`。梳理稿通常命名为 `{functionCode}_功能设计梳理_{yyyyMMdd}.md`。
3. 确认梳理稿包含 `总体判断` 与 `已确认交付物`；`## 1. 总体判断`、`## 4. 已确认交付物` 这类带编号标题也视为有效。
4. 确认梳理稿符合打包条件：
   - 总体判断明确可进入开发，例如 `可进入开发`。
   - 包含正向的冻版或近冻版判断，例如 `冻版`、`接近冻版` 或 `近冻版状态`。
   - 若文中有百分比，完成度通常应为 `>= 90%`。
   - 总体判断中不得出现 `不建议直接进入开发`、`不可进行`、`未达到冻版`、`需补齐后再开发` 或类似阻塞措辞。
5. 任一门槛不通过时，停止并说明原因，不创建半成品交付包。
6. 若梳理稿中已确认的交付物路径不存在，停止并要求修正梳理稿或路径，不静默替换成相似文件。

## 交付目录结构

沿用本地客户交付目录结构：

`TSD 交付客戶版本\TSD 交付 20260516`

默认输出：

```text
TSD 交付客戶版本/
  TSD 交付 {yyyyMMdd}/
    TSD 交付 {tsdVersion} {yyyyMMdd}/
      TSD.*.docx
      NEWDA_API_DETAIL_*.xlsx
      NEWDA_Method_DETAIL_CommonFunc_*.xlsx
      NEWDA_API_DETAIL_CommonUtil_*.xlsx
      Api_Response_Codes_*.xlsx
      vsdx源文件/
        {function}.vsdx
        共用vsdx/
          {CommonFunc/CommonUtil}.vsdx
      共用svg/
        {CommonFunc/CommonUtil}.svg
```

内层目录版本号必须从已确认的 TSD `.docx` 文件名读取，例如 `TSD.D.006_換匯優利定存_v1.0_20260408.docx` 会生成 `TSD 交付 v1.0 {yyyyMMdd}`。若已确认交付物没有 TSD `.docx`、TSD 文件名没有版本号，或同一功能出现多个不一致的 TSD 版本号，必须停止，不得用手动参数或默认值代替。

## 复制范围

只复制已确认的交付物：

- 标记为已确认的 TSD。
- 标记为已确认的 API Detail。
- 标记为已确认的 Response Code。
- CommonFunc / CommonUtil 只有在梳理稿说明当前功能使用或确认引用时才复制；标记为 `未发现`、`未确认引用` 或同等状态的项目跳过。
- 功能自身 VSDX / SVG 只有在梳理稿将其列为当前交付物时才复制。
- 外部或共用 VSDX / SVG 只有在梳理稿列为当前引用交付物时才复制。

不要复制：

- `.bak` 备份文件，除非用户明确要求。
- PRD、IT SPEC、旧代码分析、视觉 QA PDF/PNG、草稿文件或历史参考图，除非梳理稿明确列为已确认交付物。
- 标记为 `历史参考`、`本次未作为冻版图`、`不应视为当前冻版图` 或类似状态的项目。

## 推荐执行方式

先用内置脚本执行 dry-run：

```powershell
$env:PYTHONUTF8='1'
python C:\Users\<username>\plugins\project-delivery-hub-v1\skills\delivery-packager\scripts\package_delivery.py `
  --workspace "D:\Devs\<PROJECT_DOCS>\branches\02系統設計\2-1系統設計書" `
  --workspace-key "NEWDAWHO" `
  --function L.005 `
  --dry-run
```

如果 dry-run 列出的文件正确且没有阻塞错误，再移除 `--dry-run` 正式执行：

```powershell
$env:PYTHONUTF8='1'
python C:\Users\<username>\plugins\project-delivery-hub-v1\skills\delivery-packager\scripts\package_delivery.py `
  --workspace "D:\Devs\<PROJECT_DOCS>\branches\02系統設計\2-1系統設計書" `
  --workspace-key "NEWDAWHO" `
  --function L.005
```

常用参数：

- `--date yyyyMMdd`：覆盖交付包日期；默认使用本地当天日期。
- `--output-root <path>`：覆盖 `TSD 交付客户版本` 输出根目录。
- `--workspace-key <key>` / `--agent-root <path>`：指定集中 `.agent`，用于优先读取 `.agent/functions/<functionCode>/analysis`。
- `--summary <path>`：指定明确的梳理稿。
- `--overwrite`：目标文件已存在时允许替换。
- `--keep-source-dates`：完整保留源文件名，不把文件名末尾日期替换成交付包日期。

## 最终回报

打包后回报：

- 使用的梳理稿。
- 交付包目录路径。
- 按目标目录分组列出的已复制文件。
- 已确认但被跳过的项目及原因。
- 本次是 dry-run 还是正式复制。
