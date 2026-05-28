# 專案需求接口設計梳理 使用方式

## 這個技能做什麼

`專案需求接口設計梳理` 用於協助專案開發人員依 PRD、TSD 與 API Detail Excel 梳理需求、比對接口設計、修正 API 規格與同步文件內容；既有 既有專案規則仍可沿用。

它的重點是「接口設計、業務語義、API 規格一致性與開發前可用性」，不是純格式檢查工具。

## 適用場景

當你需要確認 PRD、TSD、API Detail 是否一致，或需要把接口規格整理到可開發狀態時，可以使用這個技能。

常見需求：

- 比對 PRD、TSD、API Detail Excel 是否覆蓋同一批功能需求。
- 找出缺漏或不合理的 API 名稱、Request/Response 欄位、業務規則、範例情境。
- 依 TSD `API清單` 維護 API Detail 的 `Api_List`。
- 從 API sheet 的 `涉及BackendAPI` 同步 `Api_List` 的 `後端來源`。
- 依欄位知識庫統一 API field naming，避免同一業務含義出現不同欄位名。
- 梳理新增或調整資料庫表、欄位、索引、PK/FK、SP/View、審計欄位、資料保留或敏感資料設計的待確認項。
- 將舊系統、舊欄位、舊 switch 或不清楚命名優化為新系統 canonical name。
- 產出開發修改建議，說明目前問題、建議改法、依據與影響。
- 評估 API 規格完成度，判斷是否可進入開發。
- 檢查專案時序圖 / 循序圖是否符合 PRD/TSD/API Detail 與命名規則。

## 不適用場景

這個技能不主打文件版面與視覺格式檢查。

如果需求主要是以下項目，請改用交付文件格式檢查技能：

- TSD Word 封面、頁尾、頁面設定、字型、表格樣式。
- API Excel 欄寬、列高、框線、底色、列印設定。
- 單純檢查文件是否含簡體字。
- 渲染 Word/Excel 後做純版面 QA。

如果需求主要是產出最終 native VSDX 時序圖，可先用本技能確認 API 契約、canonical naming 與 PRD 頁面/畫面清單，再接續使用 `專案原生 VSDX 時序圖生成器`。PlantUML/SVG 僅作為文本草稿、視覺參考或明確降級輸出。正式循序圖交付採用「一支功能一個 VSDX 文件」；同一 VSDX 內可有多個 Visio tabs，但 tab 依 PRD 頁面/畫面拆分，不按 API、情境、步驟或子流程拆。

## 修完 workbook 後的格式收尾

如果本技能實際修改並保存了 `NEWDA_API_DETAIL_*.xlsx`，例如補 `Api_List`、新增或改名 API sheet、修 Request/Response 欄位、範例、後端來源或 `API 內部業務邏輯`，最後必須接續使用 `專案交付文件格式檢查器` 做格式修整與復驗，不能只回報 API 內容已修完。

固定收尾順序：

1. 完成接口語義裁決，形成 file claim 與 `office-edit-plan`，不在交付目錄預設建立 `.bak`、`.before_*` 或時間戳備份。
2. 完成接口語義與 workbook 內容修復。
3. 交給 `專案交付文件格式檢查器` 執行格式閉環：檢查範圍 -> 修格式 -> 最後執行字型槽位 -> 結構復驗 -> artifact-tool inspect/render。
4. 最終回報需包含 `Must fix / Should fix / Naming / Visual risk / Covered`。

只讀檢查時不寫 workbook，只報告格式風險；只要本技能已寫回 workbook，就至少要修到 `Must fix = 0`、`Visual risk = 0`，並盡量讓 `Should fix = 0`。

## 基本使用方式

在對話中指定技能、功能編號與文件路徑即可。

## 新同事首次使用與路徑配置

需求/API 梳理預設使用工作區 registry：`<agentRoot>/config/design-source-registry.json`。分享插件時不要把個人路徑寫回技能目錄；新同事首次使用時，如果工作區 registry 缺失、為空、JSON 無效、缺少必要目錄，或目錄不存在，技能會先提醒配置路徑，不會猜測文件位置。

首次使用請提供 PRD/TSD/API Spec/Common 路徑，例如：

```text
請配置專案需求梳理路徑：
PRD 目錄：D:\...\2_PRD5.x
TSD/API Spec 目錄：D:\...\2-1系統設計書\v1.x
API Detail workbook 所在目錄：D:\...\2-1系統設計書\v1.x
CommonUtil/CommonFunc 目錄：D:\...\TSD共用相關
customer IT SPEC 目錄（可選）：D:\...\06 IT API Doc
本次功能編號：E.003
API 類別：Exchange
```

使用者給文件路徑時，技能只記錄父目錄；給目錄時直接記錄目錄。配置寫入 `.agent/config/design-source-registry.json` 後，後續可只給功能編號。

`.agent/context` 是 01-05 開發鏈的執行狀態面，不再保存設計來源目錄配置。需求梳理用 `.agent/config/design-source-registry.json` 找來源文件；進入開發後用 `.agent/functions/<functionCode>/inputs` 與 `handoff/development-handoff.json` 交接。

### 比對 PRD / TSD / API Detail

```text
[$專案需求接口設計梳理](<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md)
請幫我檢查 D.001 D.002 的 PRD、TSD、API Detail 是否一致，列出開發前需要修正的接口問題。
PRD：D:\Workspace\PRD\D.001 活存查詢.docx
TSD：D:\Workspace\TSD\TSD_D.001_D.002.docx
API Detail：D:\Workspace\API\NEWDA_API_DETAIL_Deposit_being processed.xlsx
```

### 只給功能編號

```text
[$專案需求接口設計梳理](<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md)
請檢查 D.001 D.002 是否可進入開發。
```

若該功能已登記在 `.agent/config/design-source-registry.json`，技能會自動解析 PRD、TSD、API SPEC 與 Common 文件。需求梳理不會讀取 `.agent/context/api-file-registry.json`；`.agent/context` 只留給後續 01-05 執行狀態。

### 同步 Api_List

```text
[$專案需求接口設計梳理](<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md)
請依 TSD 5. API清單 更新這份 API Detail 的 Api_List，並同步每個 API sheet 的 涉及BackendAPI 到 後端來源。
D:\Workspace\API\NEWDA_API_DETAIL_Deposit_being processed.xlsx
```

### 優化接口命名

```text
[$專案需求接口設計梳理](<pluginRoot>\skills\api-detail-tsd-sync\SKILL.md)
請檢查這份 API Detail 裡是否有舊系統欄位名或命名不清楚的 API，提出 canonical field name 與 API name 修改建議。
```

## 預設工作流程

1. 確認功能編號、PRD、TSD、API Detail、Common 與 Response Code 文件來源。
2. 若只提供功能編號，需求梳理預設只從 `.agent/config/design-source-registry.json` 解析文件位置；若 registry 缺失或路徑無效，先請使用者配置。
3. 讀取 TSD `API清單` 作為接口清單權威來源。
4. 對照 API Detail `Api_List` 與各 API sheet。
5. 依 PRD/TSD 業務語義檢查 API 名稱、欄位、範例、Response Code、Backend source 與業務規則。
6. 依 field knowledge base 檢查欄位命名一致性。
7. 若任務涉及新增/調整資料庫表、欄位、索引、PK/FK、SP/View、審計欄位、資料保留或敏感資料設計，才讀取 `references/database-design-standard-v3/catalog.json`；依 catalog 的 `loadPath` 按需讀取細則。
8. 若要交接循序圖，先整理該 functionCode 的 PRD 頁面/畫面清單，作為 VSDX 內 tabs 的切分依據。
9. 輸出差異、風險與開發修改建議。
10. 若使用者要求修復，才對 Excel/文件做最小必要修改。
11. 修改後重新開啟檔案驗證關鍵列、欄位與 `後端來源`。
12. 若本次保存了 `NEWDA_API_DETAIL_*.xlsx`，接續使用 `專案交付文件格式檢查器` 完成格式修整、字型槽位、結構復驗與渲染抽查後再回報。

## 主要檢查內容

### PRD / TSD / API 覆蓋

- PRD 功能是否在 TSD 與 API Detail 中有對應 API。
- TSD `API清單` 是否列出正確 API。
- API Detail 是否存在對應 API sheet。
- `Api_List` 是否缺少功能編號、API 類別、API 名稱或 `後端來源`。
- CommonUtil / CommonFunc 是否被放在正確層級。

### 系統設計規範 v2.5 同步規則

入口只保留摘要；細則按需讀取 `references/system-design-standard-v2.5-api-contract-rules.md`。

- API 查詢命名使用 `Get`，不沿用舊 `Query`。
- 交易式 API 依填寫/確認/結果階段使用 `{FunctionName}Init`、`{FunctionName}Confirm`、`{FunctionName}Result`。
- API/DB 名稱使用 PascalCase；API 欄位與 payload 變數使用 camelCase。
- 舊大戶命名僅可作為參考，不可直接照搬為新系統 API、Redis、設定或欄位名稱。
- `password` 概念若必須出現，API 命名使用 `passwd`；掩碼/隱碼預設由前端處理，API payload 不放顯示用遮罩字串。
- Header 來源、必填 Y/N、真實資料型別、Response Code 情境、`responseData` 無資料 `{}` 都要在 API Detail 中說清楚。
- Redis、Appsetting、DB 命名規範只作為本技能的設計梳理與開發就緒度證據，不自動擴展到程式碼寫入技能。

### 數據庫設計規範 v3 漸進式披露

資料庫設計規範不會預設載入；只有任務真的涉及表設計、欄位設計、PK/FK、唯一鍵、索引、SP/View、審計欄位、資料保留或敏感資料欄位時，才讀取 `references/database-design-standard-v3/catalog.json`。

目前提供的 `數據庫設計規範 v3 20220908.docx` 是舊 Office OLE / DRM 加密容器，LibreOffice 與 Word COM 只讀轉換都無法可靠抽取正文。因此現階段 catalog 只提供 `source_unreadable` 阻塞規則，不會偽造 table naming、column naming 或 index design 細則。

若任務需要設計新表或新欄位，輸出必須明確列出缺口：表用途、權威來源、欄位語義、資料型別、必填/可空、PK/FK/唯一鍵、索引意圖、更新頻率、預計資料量、保留期限、審計欄位與敏感資料分類。缺少依據時標記 `待確認` / `unresolved`，不可自行補成最終表設計。

拿到可讀 Markdown/JSON 或未受保護 Word 後，可用 `scripts/convert_database_design_standard.py` 重新抽取 source，再替換 catalog 裡的阻塞規則為正式主題規則。

### API 命名與欄位語義

- API method name 是否反映 PRD 業務能力。
- Request / Response 欄位是否符合 PRD 語義。
- 欄位中文說明是否貼近 PRD，而不是複製舊系統或其他功能文字。
- 是否存在舊系統縮寫、舊頁面 switch、模糊欄位名或錯誤 domain 命名。
- JSON 範例是否與欄位表一致。

### 範例情境與 Response Code

- `範例` 是否覆蓋成功、無資料、下游失敗、輸入檢核、權限或業務限制等必要情境。
- 非成功情境的 `responseCode` 是否存在於 Response Code workbook。
- Response message 是否對應實際業務狀態。
- 不會把所有 API 強制改成固定四種範例情境；會依 PRD/TSD/API 行為判斷。

### API 內部業務邏輯

- 必須寫清楚涉及的 BackendAPI 或 DB。
- 查詢要有 `WHERE`、Select 欄位、必要排序/分組與資料轉換/融合/過濾；不得把 `SELECT *` 當作正式設計。
- 新增、修改、刪除要寫明條件、欄位和值。
- `responseData` 要說明返回欄位來源與含義。
- 舊代碼邏輯理清 Excel 是重要證據來源；未確認的 DB/SP/BackendAPI 需保留 `todo` 或 `待確認`，不要猜。

### 開發前完成度

當你問「完成程度」、「完成度」、「是否可開發」、「能不能進開發」時，技能會給出：

- 約略百分比。
- `可進入開發` 或 `需補齊後再開發`。
- 已完成/對齊項目。
- 剩餘風險/開發前強化項目。
- 最終判斷。

## 修復方式

如果只要求「檢查」或「梳理」，技能會保持報告模式，不修改文件。

如果需要修復，可以指定範圍，例如：

```text
請只修 Api_List 的缺漏列與 後端來源，API sheet 內容先不要動。
```

或：

```text
請依你剛才的建議修正 Request/Response 欄位名、JSON 範例和 field KB。
```

修復原則：

- 只修使用者確認的範圍。
- 優先修改使用者指定的 workbook，不任意切換備份檔。
- 保留無關 sheet、樣式與既有資料。
- 字體與格式只限本次修改的 sheet、Api_List 行或單元格；不要因局部內容修改而掃全 workbook / 所有 sheets 改字體。
- 欄位命名以 PRD 中文業務含義為準。
- 修改 field name 時，同步欄位表、JSON 範例、業務邏輯文字、相關報告與 field KB。
- 修改後重新開啟檔案驗證。

## 常用指令範例

只列問題不修改：

```text
請只檢查 PRD/TSD/API Detail 的接口一致性，列出問題，不要修改文件。
```

同步後端來源：

```text
請把每個 API sheet 的 涉及BackendAPI 同步到 Api_List 的 後端來源。
```

檢查欄位命名：

```text
請依 Deposit field KB 檢查這份 API Detail 的 request/response field name 是否一致。
```

評估完成度：

```text
請評估這個功能目前 API 規格完成度，能不能進開發。
```

準備時序圖前置分析：

```text
請先確認這些 API 的 canonical name、欄位、主流程與 PRD 頁面/畫面清單，整理給 PlantUML/VSDX 時序圖使用。正式交付要一支功能一個 VSDX，依 PRD 頁面拆 tabs。
```

## 建議輸入資訊

為了讓分析更準確，建議提供：

- 功能編號，例如 `D.001 D.002`、`N.006`。
- PRD `.docx` 路徑。
- TSD `.docx` 路徑。
- API Detail `.xlsx` 路徑。
- PRD 頁面/畫面清單；若未提供，技能會從 PRD/TSD 推導，推導不足時交給循序圖技能預設單一 tab 並標註。
- CommonUtil / CommonFunc workbook 路徑或所在資料夾。
- Response Code workbook 路徑或所在資料夾。
- 是只檢查，還是允許修復。
- 是否需要更新 field KB。

## 注意事項

- TSD `API清單` 是接口清單權威來源。
- API sheet 的 `API Name` 與 `涉及BackendAPI` 是同步 `Api_List` 的主要來源。
- 不會把 CommonFunc 內部 helper 當成 feature workbook 的 API row，除非使用者明確要求。
- 不會為了相容舊系統而保留舊欄位名；除非使用者明確要求 backward compatibility。
- 若 workbook 被 Excel 鎖定，會說明阻塞或產生替代輸出檔。
- 純格式、字型、列印設定與視覺 QA 請使用交付文件格式檢查技能。
