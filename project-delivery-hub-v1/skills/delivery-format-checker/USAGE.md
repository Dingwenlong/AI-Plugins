# 專案交付文件格式檢查器 使用方式

## 這個技能做什麼

`專案交付文件格式檢查器` 用於檢查專案交付文件的格式與結構合規性，並兼容 既有專案交付標準。目前支援兩類文件：

- TSD Word 文件：`.docx`
- API 規格 Excel 文件：`.xlsx`

它的重點是「文件格式、結構、版面與繁體中文」，不是業務審查工具。

## 適用場景

當你需要確認交付文件是否符合模板、格式是否漂移、是否有簡體字、是否有必要章節或工作表缺漏時，可以使用這個技能。

常見需求：

- 檢查 TSD `.docx` 的封面、目錄、章節、表格、頁尾、頁面設定。
- 檢查 API `.xlsx` 的工作表、表頭、欄位、空白儲存格、字型、對齊、框線、底色、列印設定。
- 以內建 `configs/api-detail-excel-style.json` 檢查 API Detail worksheet 的分區樣式，並以 `Regression_Example.xlsx` 保留結構參考。
- 找出文件中的簡體字並建議轉為繁體。
- 找出不符合交付慣用語的詞，例如將 `校驗` 改為 `驗證` 或 `檢核`。
- 檢查字型是否符合規則：中文用 `微軟正黑體`，其他英文/數字用 `Times New Roman`。
- 將 Word 或 Excel 渲染成 PDF/PNG 後做視覺 QA。
- 在使用者確認後，協助修復格式、文字或樣式問題。

## 不適用場景

這個技能不處理業務邏輯或接口設計問題。

不會檢查：

- API 是否設計正確。
- TSD `API清單` 與 API sheet / `Api_List` 的業務一致性。
- `後端來源` 是否正確。
- Request / Response 欄位語義是否正確。
- 範例值、必填規則、業務規則是否正確。
- field KB 命名或業務含義。

如果要做 API 業務語義、接口設計、跨文件一致性或 field KB 檢查，請改用專門的 API/接口設計技能。

## 基本使用方式

在對話中指定技能與文件路徑即可。

### 檢查單一 TSD DOCX

```text
請使用「專案交付文件格式檢查器」
請檢查這份 TSD：
<path-to>\TSD.N.006_登入記錄查詢_v1.2_20260312.docx
```

### 檢查單一 API XLSX

```text
請使用「專案交付文件格式檢查器」
請檢查這份 API 規格 Excel：
<path-to>\NEWDA_API_DETAIL_Exchange_20260424.xlsx
```

### 檢查資料夾

```text
請使用「專案交付文件格式檢查器」
請檢查這個資料夾內的 TSD .docx 與 API .xlsx：
<path-to>\交付文件
```

## 預設工作流程

1. 確認輸入文件類型與路徑。
2. 先執行格式/結構檢查，不修改原文件。
3. 輸出問題清單與優先級。
4. 等待使用者確認要修哪些問題。
5. 使用者確認後才修改文件。
6. 修改後重新檢查。
7. 可行時進行 Word/Excel 視覺 QA。

## TSD DOCX 檢查內容

TSD Word 文件主要檢查：

- 檔名格式。
- 封面文字與版本。
- 版本修訂表欄位與格式。
- TSD 版本號是否使用小寫 `v`，首頁版本是否與版本修訂表最新列一致；首次交付是否只保留初版記錄。
- 目錄是否包含必要章節，且是否隨內容變更更新。
- 必要章節是否存在且順序正確。
- `功能目的`、`功能結構圖`、`循序圖`、`參考訊息來源`、`API清單` 是否有必要內容。
- 表格格式是否統一：表頭水平/垂直置中，表身垂直置中，日期/版本/姓名等欄位水平置中，循序圖標題置中，API 類別需歸類。
- `API清單` 表格會額外檢查表頭水平/垂直置中、資料列垂直置中、資料列水平居左或左右對齊、粗體/斜體漂移。
- `API清單` 表格會輸出表格級字型與繁體中文結果：中文 `微軟正黑體`、英文/數字 `Times New Roman`、中文內容繁體。
- 系統設計規範 v2.5 的 TSD / API Detail 格式摘要按需讀取 `references/system-design-standard-v2.5-format-rules.md`，不在入口或用法文件中展開整份規範。
- 表格對齊、字型、粗體/斜體等格式。
- 字型規則：中文內容使用 `微軟正黑體`，其他英文/數字內容使用 `Times New Roman`。
- 中文是否全部為繁體。
- 是否含有不建議用語 `校驗`；描述驗證流程/結果時改為 `驗證`，描述檢查項目/清單時改為 `檢核`。
- 頁尾版權文字。
- A4 直向頁面設定與邊界。
- 渲染後是否有版面、分頁、表格或圖片可讀性問題。

## API XLSX 檢查內容

API Excel 文件主要檢查：

- 活頁簿是否可開啟。
- 使用者指定或交付範圍內的 API worksheet 是否存在且可見。
- API XLSX 先用 `scripts/check_api_xlsx_format.py` 做只讀檢查，輸出 API sheet 識別、語義範圍、分區、合併、`H:AZ` 污染、底部殘留樣式與 `Api_List` 跳轉結果。
- API Detail worksheet 是否具備必要分區與正確順序；`Header` 分區若存在就檢查，若不存在不自動補。
- 各分區標題、欄位表頭、必要可見欄位與必要內容儲存格。
- 是否依 `configs/api-detail-excel-style.json` 的 `regions` 套用字型、字級、粗體、底色、框線、對齊、換行、欄寬、列高與合併儲存格；可見樣式範圍只到 `A:G`，不得把框線或底色套到 `H` 欄以後。即使 Excel `UsedRange` 因歷史樣式擴到 `AZ`，修復也要按語義範圍處理，不可全表套樣式。內容區外若出現黑色邊框需同步刪除，包含最後一個有效內容列下方的空白區；並關閉 API Detail sheet 的網格線，讓空白區維持白底、無可見邊框。
- 字型可見顯示是否符合規則：中文內容使用 `微軟正黑體`，其他英文/數字使用 `Times New Roman`；修復後需用 Excel COM 字符級抽查可見字型。
- 序號欄是否置中，非序號內容是否保留靠左。
- JSON、備註與業務邏輯等長內容是否換行且未被裁切；每次修復合併格後，`A:G` 所有有內容列都要重新自適應列高。
- 中文是否全部為繁體。
- 是否含有不建議用語 `校驗`，並依語境替換為 `驗證` 或 `檢核`。
- 檔名、全 workbook 工作表順序、篩選器、凍結窗格、列印設定、頁首/頁尾等非分區配置項，只有在明確指定時才檢查。
- 渲染後是否有空白頁、裁切、分頁錯誤或不可讀問題。

### API Detail 分區樣式檢查

本技能內建 API Detail 分區樣式配置：

- `configs/api-detail-excel-style.json`
- 規則說明：`references/api-detail-regression-standard.md`
- 歷史結構參考：`references/raw/Regression_Example.xlsx`

當檢查 既有专案 API Detail workbook 時，API worksheet 會優先讀取配置檔，依 `regions` 分區檢查與修復可見樣式。`Regression_Example.xlsx` 只保留作為結構與區塊順序參考，不再每次打開取樣式值。主要檢查：

- `API Detail` 整頁格式閉環：若整張接口設計 sheet 格式漂移嚴重，預設採用重建式流程。先抽取 `A:G` 可見文字與 `Header` / `Request` / `Response` / `範例` / `For中台開發人員` / `API 內部業務邏輯` 分區，再建立乾淨新 sheet 按配置重填、合併、套樣式、重算行高。若目標 sheet 有公式、批註、外部超連結、圖片/形狀/控制項/OLE 內嵌物件，或重要內容在 `A:G` 外，需先回報風險，不直接刪除重建。
- 區塊順序：`API Name`、`Request`、`Response`、`範例`、`For中台開發人員`、`API 內部業務邏輯`。
- 分區樣式：`API Name/API Description`、可選 `Header`、`Request`、`Response`、`範例`、`For中台開發人員`、`API 內部業務邏輯`。
- 欄寬與列高：欄寬使用配置檔交付整數，固定列高使用配置檔內的 Excel 原始高度直接寫回，例如頂部 `API Name/API Description` 標題 `15.95`、API method/description 內容列 `20.1`、區塊標題 `15.95`、表頭 `15`、`For中台開發人員` `17.1`；合併格修復後，只有模板標題/表頭之外的 `A:G` 有內容列使用自動換行與 Excel COM 依顯示寬度自適應列高。
- 背景色：包含藍底標題、表頭淺色、`API Description` 灰底、`For中台開發人員` 黃底與情境內容白底；`API 內部業務邏輯` 內容列 `A` 欄步驟欄需與本區塊 `# / 邏輯說明` 表頭列底色一致。
- 邊框：普通表格、合併標題、情境列與業務邏輯列都依配置檔的 border preset 套用，不只檢查是否「有邊框」。
- 修邊框時不得覆蓋配置底色：表頭淡綠色固定使用配置檔 `tableHeaderLight`，視覺範例色為 `FFC6E0B4`；Excel COM 寫入需使用配置中的 `ThemeColor=10` / `TintAndShade=0.5999938962981048`，不得硬編亮綠色；內部業務邏輯左側步驟欄也要保留與 `# / 邏輯說明` 表頭列一致的淡綠色。
- 內容邊界：`Request` / `Response` 內容列要閉合到 `G` 欄右邊線，`範例` / `API 內部業務邏輯` 要閉合到 `F` 欄右邊線；最後內容列下方的殘留框線要清掉。
- 區塊底框：`Request` / `Response` 最後一條可見內容列需閉合 `A:G` 底部黑色細邊框；`範例` / `API 內部業務邏輯` 最後一條可見內容列需閉合 `A:F` 底部黑色細邊框，避免畫面底線斷開。
- 合併標題列：`Request` / `Response` 的 `A:G`，以及 `範例` / `For中台開發人員` / `API 內部業務邏輯` 的 `A:F`，合併後仍要補齊上、下、左、右四邊外框，不能只剩底線或左上角邊框。
- 頂部 API 標題區：`A1:B1` 固定高度 `15.95`，`A2:B2` 固定高度 `20.1`；`B1` 與 `B2` 必須保留右邊框，`C1 返回API_List` 保持 hyperlink 樣式且不得有底色或表格框線。
- `Api_List` 目標 API 行：API 名稱欄需維持淡藍 `#0563C1`、單底線、`Times New Roman` 的 internal hyperlink；API 名稱欄需水平靠左、上下垂直置中、啟用換行，且底部黑色細邊框不能斷線。目標行 `A:J` 需換行並經 Excel COM AutoFit 復驗。
- `Api_List` 整頁樣式：下次優化 `Api_List` 時需直接讀取 `configs/api-detail-excel-style.json` 的 `apiList` 配置。該配置已摘錄目前 Payment workbook `Api_List` 的 `A:J` 欄寬、表頭淡黃底、10 號字、資料列對齊/框線、`API 名稱` hyperlink、`後端來源`、排序與 AutoFit 規則。若是整頁格式閉環，預設不在舊 sheet 上反覆補格式，而是先完整抽取 `A:J` 文字與 API 名稱內部跳轉，再刪除舊 `Api_List`、新建 sheet、按配置重新填回與套樣式。
- `範例` 的四個標準情境：`正向情境`、`連接數據庫或下游服務失敗`、`查詢成功後,返回的數據為null`、`未輸入必填請求參數`。
- `範例` 區塊合併格：header 與每個情境列都必須保持 `B:C` 與 `D:F`。若 Response JSON 被壓在單一 `D` 欄、`E:F` 留下空白小格直線，或 Request 區 `B:C` 被拆開，需修回合併格；合併前若 `C` 或 `E:F` 有文字，先匯整到合併格左上角，不丟字。
- `範例` 情境內容列的 `A` 欄情境說明需靠左、上下垂直置中並啟用換行。
- `For中台開發人員` 合併格：`A:F`。
- `API 內部業務邏輯` 連續 populated rows 合併格：`B:F`；遇到第一列真正空白分隔列即停止，不合併下方附表或試算表。若右側 `C:F` 出現空白小格與多條直線，需修成 `B:F` 合併格，合併前若 `C:F` 有文字需先匯整到 `B`。
- `API 內部業務邏輯` 內容列的 `A` 欄步驟欄需靠左、上下垂直置中並啟用換行，底色需與 `# / 邏輯說明` 表頭列一致。
- JSON 是否 pretty-print、換行、列高足夠且 PDF 不裁切。

多 sheet workbook 會把每張 API worksheet 視為獨立 `API_Detail` 樣式表檢查；`Api_List` 這類索引表不套用該回歸樣例。

## 問題分類

檢查報告會使用以下分類：

- `Must fix`：阻斷文件合規或必要結構的問題，例如簡體字、必要章節缺漏、必要表格缺漏。
- `Should fix`：建議修正的文件問題，例如格式漂移、必要可見內容疑似缺漏。
- `Naming`：檔名、工作表名、標題、章節名稱或可見標籤問題。
- `Visual risk`：需要渲染或人工視覺檢查確認的版面風險。
- `Covered`：已通過或已覆蓋的檢查項目。

## 修復方式

如果只要求「檢查」，技能會保持報告模式，不修改文件。

如果需要修復，可以在收到報告後指定要修哪些項目，例如：

```text
請修復 Must fix 裡的簡體字問題，其他先不要動。
```

或：

```text
請修復簡體字與頁面方向設定，Api_List 的空白欄位先保留。
```

修復原則：

- 只修使用者確認的項目。
- 使用最小必要變更。
- 保留無關內容與既有格式。
- 術語修正可將 `校驗` 改成 `驗證` 或 `檢核`：流程/結果/規則偏向 `驗證`，項目/清單/人工核對偏向 `檢核`。
- API XLSX 修復固定走閉環：檢查範圍 -> 備份/複製 -> 修格式 -> 最後執行字型槽位 -> 結構復驗 -> artifact-tool inspect/render -> 回報。
- 字型槽位腳本預設只修 API Detail worksheets 的 `A:G` 語義範圍，並排除 `Api_List`；要修整本 workbook 時必須明確要求 `-AllSheets`。
- 只修 `API 內部業務邏輯` 右側空白小格/直線與 `A` 欄步驟欄對齊/底色時，可用 `scripts/repair_api_xlsx_internal_logic_merges.ps1`；它預設只處理 API Detail worksheets，將邏輯說明列修成 `B:F` 合併格，並將步驟欄修成靠左、垂直置中、與 `# / 邏輯說明` 表頭列一致的淡綠色，不處理 `H:AZ`、不碰 `Api_List` 內容。
- 只修 `範例` 區 Response/Request 合併、`A` 欄情境說明對齊與列高時，可用 `scripts/repair_api_xlsx_example_merges_and_row_heights.ps1`；它預設只處理 API Detail worksheets，將情境列修成 `B:C` / `D:F` 合併格，將情境說明修成靠左且垂直置中，並重算 `A:G` 所有有內容列自適應高度。
- 只修頂部 API 標題區高度、`B1:B2` 右邊框、內容列自適應與 `H:AZ` 空白區可見框線時，可用 `scripts/repair_api_xlsx_header_scope_and_row_heights.ps1`；它不改 `Api_List`，也不新增業務內容。
- 整頁重建接口設計 sheet 時，優先用 `scripts/rebuild_api_xlsx_detail_sheets_from_text.ps1 -Sheets ...`：它會先讀取舊 API sheet 的 `A:G` 可見文字與標準分區，再建立乾淨新 sheet，按配置重填 `API Name`、`Request`、`Response`、`範例`、`For中台開發人員`、`API 內部業務邏輯`、返回連結、合併格、欄寬、字型、底色、邊框與行高。若偵測到公式、外部超連結、批註或內嵌物件，會先停止並回報風險。
- 整頁優化 `Api_List` 時，優先用 `scripts/rebuild_api_xlsx_api_list_from_text.ps1`：它會先讀取舊 `Api_List` 的 `A:J` 文字、API 名稱欄內部跳轉與原 sheet 位置，再刪除舊 sheet，按配置新建 `Api_List`、填回資料、依 PRD 編號排序、同步 `後端來源`、還原 hyperlink、套用欄寬/字型/底色/框線/行高與 AutoFilter。若偵測到公式、外部超連結、批註或形狀等不可安全搬遷內容，需先回報風險並確認。
- 只修目前功能範圍內的 `Api_List` API 名稱欄樣式/對齊/底線與 API Detail 各區塊末行底框、且不需要重建整張 `Api_List` 時，才用 `scripts/repair_api_xlsx_api_list_and_section_borders.ps1 -Sheets ...`；它只動指定 API sheets 對應的 `Api_List` 行，不新增 API row。
- 既有交付版 Excel 若含嵌入物件或圖片，修復保存時優先使用 Excel COM，避免 `openpyxl` 移除 OLE/media。
- 修改後重新檢查。

### 上游 API workbook 交接

當本技能是從 `專案需求接口設計梳理` 接續執行時，代表上游已經完成 API 語義、欄位、範例或 `Api_List` 等內容修復。本技能只負責交付格式閉環：

- 保留上游已修好的 API 內容，不自行新增、刪除或改寫接口語義。
- 以 API Detail 語義範圍修格式，不因 Excel `UsedRange` 被污染就擴大套用到 `H:AZ`。
- `Api_List` 不參與 API Detail 批量套樣式；只有連結、索引一致性、API 名稱欄對齊/底框/行高被點名或檢查器報出時才修。
- 完成後回報 `Must fix / Should fix / Naming / Visual risk / Covered`；若剛做過修復，`Must fix` 或 `Visual risk` 仍未清零時不得宣稱格式閉環完成。

## 視覺 QA 說明

視覺 QA 用來確認 Word/Excel 實際渲染後是否正常，例如：

- 是否產生空白頁。
- 表格是否被裁切。
- 文字是否超出欄位。
- 圖片是否不可讀。
- 頁碼、目錄或分頁是否異常。

只有在實際渲染並檢視頁面後，才會回報視覺 QA 已完成。若本機缺少 LibreOffice 或 Poppler 等工具，會明確說明視覺 QA 未執行。

## 常用指令範例

以下腳本示例假設目前所在目錄是本技能資料夾；若在其他目錄執行，請將 `scripts/...` 換成對應的實際路徑。

只檢查不修改：

```text
請檢查這份文件，只列問題，不要修改。
```

檢查並做視覺 QA：

```text
請檢查格式與結構，並在可行時渲染做視覺 QA。
```

只修 Must fix：

```text
請只修復 Must fix 問題，其他問題先不要動。
```

只檢查繁體中文：

```text
請只檢查這份文件是否含有簡體字。
```

只檢查術語：

```text
請只檢查這份文件是否含有「校驗」，並建議改成「驗證」或「檢核」。
```

只檢查字型：

```text
請只檢查這份文件的字型是否符合中文微軟正黑體、其他 Times New Roman。
```

檢查資料夾內所有交付文件：

```text
請檢查這個資料夾裡所有 TSD .docx 和 API .xlsx，分文件輸出問題清單。
```

直接執行 API XLSX 結構/格式復驗：

```powershell
python scripts/check_api_xlsx_format.py "<path-to>\NEWDA_API_DETAIL.xlsx"
```

只對 API Detail worksheets 套用字型槽位：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/apply_excel_font_scheme.ps1 -Path "<path-to>\NEWDA_API_DETAIL.xlsx"
```

只有明確需要整本 workbook 時才使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/apply_excel_font_scheme.ps1 -Path "<path-to>\NEWDA_API_DETAIL.xlsx" -AllSheets
```

## 建議輸入資訊

為了讓檢查更準確，建議提供：

- 文件完整路徑。
- 是只檢查，還是允許後續修復。
- 是否需要視覺 QA。
- 若有固定模板，提供模板文件或說明。
- 是否只關注某一類問題，例如繁體中文、表格格式、列印設定。

## 注意事項

- 此技能不會自動修復全部問題。
- 未經確認不會修改文件。
- API Excel 的格式/結構檢查不等於 API 業務審查。
- 不要用 Excel `UsedRange` 作為 API Detail 修復範圍；若 `UsedRange` 被樣式污染擴大，只能列為風險或清理對象，不能反過來擴大修復範圍。
- `備註` 等欄位是否允許空白，若模板沒有明確規定，會列為確認項而不是直接判定錯誤。
- 視覺 QA 依賴本機渲染工具；沒有渲染工具時，只能完成結構檢查。
