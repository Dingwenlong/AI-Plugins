# API UT 測試項分層與交付規則

本文件是「API 测试代码与单元测试报告生成器」產出測試代碼與 UT 測報時的分層依據。交付文件仍稱為「UT 測報」，但證據來源可以是 UnitTest、IntegrationTest、Service runtime validation、Postman MCP 真实接口调用、code inspection、file/template inspection；不得把所有驗證硬塞進狹義 UnitTest。

## 基底來源

- 預設使用 `assets/UT自测标准_API单元测试CheckList v3 20260509.xlsx` 作為標準化 API UT Check List 基底。
- 主表按 `P0 / P1 / P2 / P3` 優先級執行：
  - `P0`：所有 API 核心必測。
  - `P1`：高風險必測，包括參數、安全、異常與核心業務規則。
  - `P2`：依功能適用，包括 DB、邊界、日誌等。
  - `P3`：依功能適用，包括列印、Mail、檔案、多語等擴展能力。
- 對每支 API，必須再疊加 `API_Spec.json.mockExamples` 的所有范例情景；范例情景不得因為 responseCode 相同而合併或丟棄。
- 分類式 UT 報告中，`UT-01` 固定保留給「功能接口范例单元测试」，由當前功能接口的 API Spec Excel / `mockExamples` 動態展開；標準化 API UT Check List 從 `UT-02` 開始順延。
- v3.5 分類式模板包含 `UT-07 DB / SQL 執行環境驗證`，放在 DB 查詢 / 新增 / 修改 / 刪除分類之前。此分類只適用於有 DB / SQL 依賴的 API；無 DB API 一律標示 `不適用`。
- `EnterpriseAPI 配置連線字串可正常開啟` 屬於環境級前置條件，不放到每支功能的 checklist 內重複判定。此項改由專門的 configured-connection IntegrationTest / Service runtime validation 承接；per-function 報告只保留 API-specific 的 Service SQL 執行、schema/table/column 與 DB 權限 runtime evidence，缺證據時在 `不通過` 下方寫明原因。
- 分類式 UT 報告的總結果需以 `通過 x 項 / 不通過 y 項 / 不適用 z 項` 呈現，不再附加 `如預期結果` 或 `未如預期結果`；只有當前功能收集到的測試全部通過時，才能勾選 `符合需求`。
- 分類式 UT 報告不再輸出 `{UnitTest VS執行總截圖}` 或功能層級總 Summary 截圖；`彙總` 區塊只保留總結果表。總結果表結束後，才依 API 數量逐一展開 detail 區塊。每段包含 API `Heading 1` 標題、該 API 的通過/不通過統計、該 API 對應模擬截圖，以及該 API 自己的清單項。
- 每支 API 的 `測試內容清單` 都要複製標準化 API UT Check List；其中 `UT-01` 只展開該 API 自己的范例情景，`UT-02` 之後的標準檢查項跟隨該 API 一起呈現。
- 模擬截圖不得混入當前功能無關的測試資訊；分類式正式報告只保留單支 API 圖，且單支 API 圖只顯示該 API 的測試。

## 不適合放進狹義 UnitTest 的項目

| 不適合項 | 原因 | 應改用 |
| --- | --- | --- |
| 純 UI 顯示：Title、CSS、欄位順序、表格框線、readonly、焦點、彈窗、捲軸 | 後端單元測試看不到瀏覽器畫面 | 不納入 API UT，或改 UI 自動化 |
| 前端操作：按鈕跳轉、分頁停留、清除按鈕、子畫面返回 | 屬於瀏覽器狀態和前端邏輯 | 不納入 API UT |
| 固定環境性能：開發環境 <2s、上線環境 <3s | 環境波動大，不是單元測試穩定斷言 | 性能測試 / 監控 |
| 真實外部系統送達：真實寄信、推播、列印機、外部 API 實連 | 單元測試不應依賴外部系統可用性 | `UnitTest with mock` 或專門整合測試 |
| 真實 SQL 正確性但不打 DB | mock 只能證明參數與映射，不能證明 SQL syntax、Join、排序真的可跑 | `Service runtime validation` / `IntegrationTest`，預設需使用 EnterpriseAPI 設定連線；LocalDB/fixture 只能作輔助證據 |
| 完整跨系統端到端流程 | 超出單一 API / Service 的單元邊界 | Integration / E2E，不當作 UnitTest |
| 文件視覺排版人工檢查 | 單元測試適合驗證內容和結構，不適合驗證人工視覺效果 | `File inspection` / 人工驗收 |
| 當前 API 根本沒有的功能項 | 不應為了標準項硬造測試 | 報告寫 `接口未涉及` |

## 建議驗證方式

- `UnitTest`：覆蓋 API 范例情景、DTO 校驗、Service 業務分支、錯誤碼、邊界值、mock 外部依賴失敗。
- `Controller integration`：覆蓋 route、HTTP method、model binding、授權、統一回包；若 mock Service，只能證明 Controller 層。
- `Service runtime validation`：覆蓋完整 Service 邏輯鏈，尤其是 DB 查詢、Join、排序、欄位映射、交易結果。DB / SQL API 預設必須額外使用 EnterpriseAPI 專案設定的連線字串，透過正式 `SqlDbFactory` / `SqlExecutor` 路徑執行；LocalDB 或 fixture 測試只作為可控資料輔助驗證，不可取代設定連線證據。
- `IntegrationTest`：覆蓋 Controller + Service + fixture 的關鍵鏈路；用於證明接線和運行邊界。
- `Code inspection`：覆蓋 route attribute、權限標註、log、敏感資料遮罩、固定配置等靜態證據。
- `API runtime call`：由 agent 使用 Postman MCP 實際呼叫 API，保存遮蔽敏感資訊後的 request/response JSON 與 status PNG，覆蓋真實 HTTP 入參、回包、狀態碼與接口可達性。此證據必須稱為「Postman MCP / 真实接口调用」，不得稱為 UnitTest。
- `File inspection` / `Template inspection`：覆蓋匯出檔、mail template、檔案內容，不做真實發送。

## Mock 使用邊界

- 不要求所有測試都禁止 mock。傳參驗證、DTO validation、Controller model binding、Controller contract、外部系統隔離等項目，可以依測試目的使用 mock。
- 若測試項目要證明 Service 內部業務規則、DB / SQL、欄位映射、交易結果、快取刷新或其他往下執行的邏輯，必須執行真實 Service 方法；不得 mock Service 本身後宣稱已驗證 Service 業務邏輯。
- mock `ISqlExecutor`、Redis、外部 gateway 可以用來驗證分支、參數、錯誤處理與映射，但不能單獨作為 SQL syntax、Join、排序、DB 權限、schema/table/column 或正式 runtime 行為正確的證據。
- DB / SQL API 至少需要一層 Service runtime validation / IntegrationTest；若交付要求使用 EnterpriseAPI 設定連線，該證據必須讀取 EnterpriseAPI `appsettings.json` 並經正式 `SqlDbFactory` / `SqlExecutor` 路徑執行。
- 正式報告表述要寫清證據層級：mock-based UnitTest 是「規格範例、輸出契約、分支與映射」證據；Service runtime validation 才是「Service 往下執行、SQL / DB runtime」證據。
- Postman MCP 真实接口调用可以補充部署/本機 API 可達性與 HTTP 回包證據，但不能替代應有的 UnitTest、IntegrationTest 或 Service runtime validation。缺少 Postman MCP 工具或缺少 request/response/status 截圖時，該分支應阻塞或待補。

## 執行策略

1. 讀取標準化 API UT Check List，按 P0/P1/P2/P3 優先級作為基底。
2. 讀取 `.agent/context/<functionCode>/apis/<apiId>/*_API_Spec.json`。
3. 強制納入 `mockExamples` 的每個范例情景，不能只挑成功樣本；正式報告中展開為 `UT-01-01`、`UT-01-02` 等。
4. 讀取 `codeHandoff.queryContracts`、`runtimeDependencies`、`serviceRuntimeValidationRequired`、`unresolved`。
5. 按 API 實際功能篩選適用項：無 DB、無 mail、無 upload、無 export 的項目寫 `接口未涉及`。
6. 生成測試代碼時，每個范例至少斷言 `isSuccess`、`responseCode`、`responseMessage`、`data` 和關鍵欄位映射。
7. 若 API 涉及 DB / SQL，必須同時生成 mock-based UnitTest、LocalDB/fixture 輔助驗證，以及 EnterpriseAPI 設定連線的 Service runtime validation；其中 EnterpriseAPI 設定連線下的 Service SQL 執行是預設交付證據，不是可選項。單純「連線字串可開啟」不列入每支功能的 checklist。
8. 若 EnterpriseAPI 設定連線因登入、權限、schema、seed、網路或測試環境未就緒而無法通過，報告不得寫成完整通過；需保留 mock / fixture 證據，並明確標示設定連線 runtime validation 未通過或待環境補齊。
9. `上線前環境驗證條件需保留確認紀錄` 屬於上線審批前置檢查，不由 UnitTest 自動判定通過；在 UT 測報中標示 `不適用`，由 UAT / 準生產驗證或發布清單承接。
10. 產出 UT 報告時，用人寫測報的口吻描述「驗證了什麼業務行為」，不要把內部方法名、JSON key、工具過程堆到正式報告裡。

## 報告表述規則

- mock-based UnitTest 可描述為「依規格范例驗證輸出契約與映射邏輯」。
- LocalDB / fixture 測試可描述為「以測試資料庫驗證 Service 查詢、排序、Join 與欄位轉換」。
- EnterpriseAPI 設定連線測試可描述為「以 EnterpriseAPI 設定連線驗證正式 SQL 可執行」。
- 若缺 DB schema、seed、測試連線或資料庫權限，保留 mock 單測與 fixture 證據，但需寫明 EnterpriseAPI 設定連線 runtime evidence 尚未通過或需環境補齊。
- `接口未涉及` 用於當前 API 沒有該功能；不得為了讓報告看起來完整而生成假測試。
- 若當前 API 沒有可解析 `mockExamples`，`UT-01` 保留一條說明性項並標記需要補齊范例或 evidence blocked，不得偽造成通過。
