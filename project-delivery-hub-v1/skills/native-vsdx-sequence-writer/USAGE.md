# 专案原生 VSDX 时序图生成器使用方式

## 這個技能做什麼

`專案原生VSDX時序圖產生器` 用於依專案凍版 PRD、TSD、API Detail、既有 VSDX/SVG/PlantUML 與本地標準範例，產出或優化正式交付用的原生可編輯 Visio VSDX 時序圖；既有專案標準仍可沿用。当前 native VSDX 標準以專案規則庫或已指定 baseline 為優先基準。

它的重點是「把已確認的接口契約轉成交付用 native VSDX、PNG preview、PlantUML/SVG 參考檔」，不是重新設計 API 業務規格的主要工具。正式 VSDX 不能由整張 SVG 匯入 Visio 代替，也不能只追求截圖相似；成品交給別人在 Visio 裡二次處理時，participant、message、self-call、alt/ref/group 等核心元素要維持原生選取、拖曳、膠合、控制點與文字編輯體驗。

## 適用場景

當 API 契約已基本確認，需要產出、修正或落版時序圖時，可以使用這個技能。

常見需求：

- 依 PRD、TSD、API Detail 產出正式 native VSDX 時序圖。
- 產出 `.puml` / SVG 作為內容與視覺參考。
- 將既有 SVG/VSDX/PlantUML 改成專案 native VSDX 樣式。
- 依標準範例修正 User、APP、Enterprise、IRIS、DB、Redis 等 participant 樣式。
- 補齊 CommonFunc/CommonUtil 的 `ref over Ent` SVG 參考區塊。
- 修正 self-call 文字位置、左對齊、顏色一致性與 native/SVG 目標樣式。
- 修正 `ref` 區塊只保留 SVG 指引文字橙色底，不讓整個 ref 變橙色。
- 修正 `alt` / `else` / `opt` / `group` 分支線、標籤、巢狀框與可讀性問題。
- 依系統設計規範 v2.5 檢查 `alt`/`opt`、`ref`、Request/Response 箭頭文字、User/APP 行為與 Visio 2013-2016 相容交付。
- v2.5 細則按需讀取 `references/system-design-standard-v2.5-sequence-rules.md`；深層原生 VSDX 幾何與 ShapeSheet 規則仍在 `references/native-vsdx-deep-rules.md`。
- 產出 final SVG reference、native VSDX 與 PNG preview。
- 正式交付需保留 Visio source，並在可行時保存/匯出為 Visio 2013-2016 相容格式。
- 提供 Visio/VSDX 落版檢查清單與交付說明。

## 不適用場景

這個技能不適合在 API 契約尚未釐清時單獨使用。

如果需求主要是以下項目，請先使用 `專案需求接口設計梳理`：

- PRD、TSD、API Detail 是否一致。
- API name 或 field name 是否應重命名。
- Request/Response 欄位是否缺漏。
- `Api_List` 或 `後端來源` 是否正確。
- Response Code 與範例情境是否合理。
- 功能是否可進入開發。

如果需求只是檢查 Word/Excel 格式、字型、版面或簡繁體，請使用交付文件格式檢查技能。

## 基本使用方式

在對話中指定技能、功能編號與權威來源文件即可。

### 依 API Detail 產出時序圖

```text
[$專案原生VSDX時序圖產生器](<pluginRoot>\skills\native-vsdx-sequence-writer\SKILL.md)
請依這份 API Detail 產出 E.001 的 project native VSDX 時序圖，包含 PlantUML、SVG reference、VSDX 與 PNG preview。
D:\Workspace\API\NEWDA_API_DETAIL_Deposit_being processed.xlsx
```

### 修正既有 PlantUML

```text
[$專案原生VSDX時序圖產生器](<pluginRoot>\skills\native-vsdx-sequence-writer\SKILL.md)
請修正這份 .puml，讓它符合 專案標準樣式並可渲染。
D:\Workspace\output\sequence_diagram\E001\E001_sequence.puml
```

### 對齊既有 SVG / VSDX

```text
[$專案原生VSDX時序圖產生器](<pluginRoot>\skills\native-vsdx-sequence-writer\SKILL.md)
請比對這份 VSDX 與標準範例，修正 User 樣式、ref 區塊、APP self-call 與右側空白。
D:\Workspace\v1.x Reference\E.001_01.vsdx
```

### 只要 PlantUML

```text
[$專案原生VSDX時序圖產生器](<pluginRoot>\skills\native-vsdx-sequence-writer\SKILL.md)
請只產出 .puml，不需要 SVG/VSDX。
```

## 預設輸出位置

預設會在專案本地輸出到：

```text
output/sequence_diagram/{functionCode}/
  {functionCode}_sequence.puml
  {functionCode}_native_visio_spec.json
  {functionCode}_plantuml_落版說明.md
  vsdx/{functionCode}_01.vsdx
```

一般 專案交付預設包含 native VSDX，不預設渲染 SVG/PNG 參考圖。除非你明確說只要 `.puml`、只要 `.svg`、text-only，或本機缺少 PlantUML/Visio/必要工具，否則技能會嘗試產出 native VSDX 交付包。若只能產出 SVG-import VSDX，必須標成 fallback，不算正式 native VSDX 交付。

正式 VSDX 交付結構固定為：一支功能一個 VSDX 文件，同一個 `{functionCode}` 不因多個 API、情境、步驟或子流程拆成多個正式 VSDX。VSDX 文件內可以有多個 Visio page tab；tab 依 PRD/TSD 的完整使用者流程拆分，不機械地按每個 PRD 頁面/畫面拆。連續的填寫、確認、送出、結果顯示可合併在同一流程 tab 內，用 section divider、`group`、`alt`、`opt`、`loop` 或 `ref` 標示階段。每個正式 tab 都要有可見的 `User -> APP` 進入點；若某個結果或後端處理頁沒有新的使用者入口，應併回前一個流程 tab。

## 預設工作流程

1. 確認功能編號與權威來源文件。
2. 讀取 frozen API Detail、TSD `API清單`、既有 SVG/VSDX/PlantUML 或標準範例。
3. 萃取 API 名稱、描述、Request/Response、Backend source 與業務邏輯。
4. 從 PRD/TSD 識別該功能的使用者流程，合併同一旅程中的連續頁面/畫面，決定單一 VSDX 文件內的 Visio page tabs。
5. 依實際主流程選擇 participant。
6. 建立或更新 `{functionCode}_native_visio_spec.json`，預設 `messageStyle.policy` 使用 `e001-reference`。
7. 產出 PlantUML/SVG reference，並嵌入 project style。
8. 需要 CommonFunc/CommonUtil 時，必須同步加入 PlantUML `ref over Ent` 與 native spec 的 `Other fragment` / 橙色 pointer strip；native ref 內有 reference self-call 時，底部必須有同方法名的橙色參考文件說明條；不得把 common 方法畫成 Enterprise 普通 self-call。
9. 先跑 native layout planner：建 tab 與骨架、放 participant、放子功能 title、放原生片段，依內容預估 fragment/member 高度，先調整片段位置，再把一般 message / return / self-call 箭頭填入；`ref` 在片段階段一次完成六段高度、內部 CommonFunc/CommonUtil reference self-call 與橙色指引，不讓主流程訊息進入 ref。
   - 子功能 title 要按文字長度加寬，避免中文標題折行；標題框仍保留可編輯邊框。
   - 子功能 title 下方第一個業務 fragment 至少下沉兩段參與者連接點；若該 group 內又立即放判斷 `alt`，該 child `alt` 也至少離 parent group 上邊框兩段連接點，避免 title / group / alt 三層擠在同一條水平帶。
   - 下游請求後才做回傳判斷的段落，若視覺標準要求包住請求、返回、ref 與後續組裝，應上移同一個原生 `alt` 包住完整判斷域，不複製訊息、不改業務順序。
10. 一般交付會用 `scripts/build_native_visio_sequence.ps1` 從 layout-planned native spec 產出單一正式 VSDX，並輸出 PNG preview。
11. 用 native VSDX gate 檢查 participant、connector、fragment、ForeignData、檔名、輸出路徑、流程級 tab 拆分、每個 tab 的 User 進入點與真實 Visio 操作體驗。
12. 產出或更新落版說明。

## 時序圖規則重點

### 参与者

- 預設順序：`User -> APP -> Enterprise -> IRIS -> DB -> Redis`。
- `User`、`APP`、`Enterprise` 固定在左側。
- DAWHO 最終 SVG/VSDX 的 `User` 必須是標準任務/人物圖示加 bordered `User` label，不可保留 PlantUML 預設 stick actor。
- `DB` 與 `Redis` 必須是一般 boxed participant，不使用 cylinder/storage icon。
- `CommonFunc` 必須使用 `ref over Ent` / native ref fragment，不畫成 Enterprise 普通 self-call，也不畫成獨立 participant。
- `CommonUtil` 只有在 APP 實際呼叫該 outward API 時才畫成主流程 API。
- `ref` 內 reference self-call 的可見命名固定為：內部共用方法 `CommonFunc.MethodName`，外部共用接口 `CommonUtil/MethodName`。例如 `CommonFunc.GenFntTranSeq` 與 `CommonUtil/GetCENCurr`，不要寫成 `CommonFunc/GenFntTranSeq` 或 `CommonUtil.GetCENCurr`。
- native VSDX 的 User / APP / Enterprise / IRIS / DB / Redis 等生命線要沿可見虛線展示完整、均勻的 UML 原生連接點列，連接點間距使用 Visio UML master 的原生預設長度，不用固定 inch 值替代；箭頭頭尾必須膠合到距離最近的既有連接點，不能只做視覺貼近，也不能為每個箭頭端點額外新增零散連接點。
- 章節分隔線只作為分段視覺輔助：頁面必須關閉自動擴頁（`DrawingResizeType=0`、`ResizePage=FALSE`）。雙線條跟隨參與者/內容寬度，不拉到空白頁邊；短流程 tab 要縮小右側空白並讓參與者群組在頁面中適度置中。雙線條鎖住橫向尺寸與水平移動；中央標題框保留可改邊框大小，不因調整標題框而把整張頁面撐大。正式 VSDX 收尾時要把章節雙線條與中央標題框設為上層，避免被 lifeline、message 或 frame 蓋住。
- 頁面最上方大標題放功能名稱，例如 `L.003 自動扣繳申請`；流程或 tab 名稱放在大標題下方作為較小子標題，或放在章節分隔線上。不要把 `L.003 扣繳總覽` 這類流程名稱當作主標題。

### 消息

- User/UI 操作使用 `點擊XXX`。
- APP 呼叫 Enterprise 使用 `Module/APIName` 加中文 API 描述。
- IRIS/DB 呼叫寫實際來源名稱加中文說明。
- Request/Response 箭頭都要有文字；後端相關 Request 需標明 DB table 或 API 英文名與中文含義。
- Enterprise 回 APP 使用實線 response；箭頭線條遵循 native spec 的 `messageStyle.policy` 或 SVG 參考樣式，native VSDX 的 message / return / self-call 字體預設統一黑色 `RGB(0,0,0)`。一般 native VSDX 預設 `e001-reference`，需要全紅時才改 `project-red`。
- User 只作為觸發操作的來源，不畫 `APP -> User`、`APP --> User` 或任何指向 User 的 `Response` 箭頭。
- User 發出指令後必須能看到對應回應；畫面顯示、彈窗、刷新、頁面狀態變更與結果呈現一律由 APP self-call 表示。
- 相鄰 APP self-call 若只是同一畫面結果、提示或狀態更新的不同說法，只保留一條語意最完整的 self-call，不並排畫兩條 folded arrow。
- PlantUML/SVG reference 的 APP self-call 使用紅色箭頭與紅字；native VSDX 預設跟隨 `messageStyle.policy=e001-reference` / E.001 master 線條，但 message / return / self-call 字體統一黑色，不因為是 APP self-call 就固定套紅字，除非該訊息明確有 `textColor` 覆蓋。
- self-call 文字段落預設放在自轉箭頭右側並左對齊，APP 與 Enterprise/backend/internal self-call 都適用；正式交付不要使用置中的 self-call 標籤，除非該局部明確需要 `allowCenteredLabel`。
- message / return message 說明文字要留在同一個 UML 訊息 shape 上，放在箭頭正上方並保持緊湊，native 預設約 `0.04 in` 間距；不可垂直於箭頭、落到箭頭下方，或拆成獨立文字框。
- message / return / self-call 箭頭本體與其他圖形之間至少保留一段連接點間距；一段是參與者 lifeline 預設相鄰兩個連接點的距離，不是固定 inch 值。其他圖形包含 fragment 外框、group/ref/alt 標題區、section divider/title、note 與橙色 SVG 指引條。`Self Message` 上下空間要留 double，也就是 folded arrow 實際占用範圍上方兩段參與者連接點、下方兩段參與者連接點。若箭頭貼到框線、標題帶或相鄰訊息，需移動訊息列或相鄰圖形，不可交付。
- self-call 內的小參數（例如括號內 `currencyCode`）顏色要與同一段中文一致，不保留不同 inherited character color。
- native VSDX 的 message / return / self-call 必須是單一 Visio UML message shape，箭頭兩端要落在 participant lifeline 既有原生連接點列上並完成 GlueTo 膠合；若找不到可用連接點必須退回重排或構建失敗，不可只放在視覺座標上，也不可為單一箭頭新增專屬 connection-point rows。self-call 文字要在 `Self Message` 本體上，並保留可拖曳的文字位置控制點。
- 不在箭頭上堆 Request/Response 欄位清單。

### 原生 Alt / Else

- `alt` 必須使用 Visio UML `Alternative fragment` 原生 master，頁籤文字保留 `alt`。
- `alt` 必須有兩個以上分支，單一條件區塊使用 `opt`。
- 第一條件使用 Alternative fragment 產生出的 `[條件]` / `Interaction operand` 原生位置承載，不另外畫文字框。
- `opt` 必須保留真實 Visio UML 片段操作體驗，頁籤文字保留 `opt`；若 `Optional fragment` master 沒有容器成員與右側控制點，改用可容器化的原生 `Alternative fragment` variant 並把顯示 operator 改成 `opt`。可選條件要放在原生 `[條件]` / `Interaction operand` 位置，不只寫在頁籤或另畫文字框。
- `if` 第一條件頭上方不顯示額外線段；每個後續 `else` operand 都必須由原生 UML `Interaction operand` 承載一條可見的 DAWHO 綠色虛線分隔線，且正式 VSDX 收尾時要置於上層，避免被 lifeline、message 或 frame 蓋住。不要為 `else` 疊加手畫線或 overlay 線；每個 `else` 頭上只保留一條原生 operand 分隔線。章節 section divider 雙線仍維持原本實線雙線，不跟著改成虛線。
- `alt` 的第一條件與所有 `else` 分支條件都必須用中括號顯示；PlantUML 草稿寫 `else [條件]`，native VSDX 的 `Interaction operand` 文字寫 `[條件]`，不可裸露為 `條件` 或 `else 條件`。
- `alt` operand 的視覺順序必須與 spec 分支順序一致：`frames[].condition` 是第一個 if 分支，`separators[]` 依 top 由上到下成為後續 else。收尾腳本只能補 fragment membership，不可把既有 `Interaction operand` 重新插到 list position `0`，避免分支倒置。
- `alt` 的寬高要包住該分支完整內容，包含 nested `ref`、橙色 pointer、response 與 APP self-call；最後一段 `else` operand bottom 要貼齊 `alt` frame bottom。
- `alt` 的非最後一個 `Interaction operand` 在布局計算時要按下一條 operand 分隔線預估高度，不能使用 Visio master 的預設短高度；正式 VSDX 保存前要把每個 operand 的 `PinY`、`Height`、`LocPinY` 固化為當前常量，不能留下跨 member 的 `Sheet.*!Height` / `Sheet.*!PinY` 公式，避免手工拖曳 member 控制點時方向反直覺。
- 判斷分支內容是否溢出時，要用 message 實際占用範圍，不只看 nominal top。`Self Message` 占用 `BeginY` 到 `EndY` 的完整 folded-arrow 高度；if/else 分隔線必須離 self-call folded arrow 實際上下端各至少兩段連接點，並離一般訊息至少一段連接點。
- 巢狀 `alt` 的 operand 只能由自己的 child frame 正規化；外層 `alt` 只可處理左右對齊自身 frame 的 `else` operand，以及貼近自身 header 的第一條件 operand，不可把內層 `else` 條件拉到外層跑道外。
- 巢狀 `alt` 的第一條件 operand 必須位於該 child frame 上邊框之下；如果 bracket operand 在 child frame 上方，即使左右看起來對齊，也只能視為外層分支 separator。
- operand 可以把 `alt` 外框撐大，但預設短 separator operand 不可把既有 `alt` 壓小，避免 branch 內容掉到框外。
- 正式 VSDX 內的 `alt` 要保留原生片段可編輯性：優先使用帶黃色右側控制點的 `Alternative fragment.52` 與 `Interaction operand.53`；拖曳 `alt` 右側上下居中的黃色點可調整片段長度，拖曳直接 if/else operand 左右寬度也要回寫同一個 `alt` 控制點；拖曳 if/else member 控制點時，操作方向必須符合 Visio 原生手感，不可因跨 operand 垂直公式導致往上拉卻向下增高。
- 父層 `alt` / `opt` 的成員關係只可收納完整落在自己框內的 child fragment frame（`alt` / `ref` / `opt` / `loop` / `group`）；不可把後面的 sibling `ref`、section divider、生命線或分支外訊息誤判成子內容，避免拖曳 `opt` / `alt` 時把下一段一起帶亂，或讓父層底線橫穿底部 child `alt`。
- 子片段和父片段要保留可看得出的層級間距。child `group` / `alt` / `ref` 不可與 parent fragment 共用完全相同的左右邊界；寬幅子片段左右至少內縮約一段參與者連接點，且頂部至少離 parent fragment 上邊框/標題區兩段連接點。例如 `查詢定存存單資料` 這類 group 要放在 `[帳號檢核通過]` else 內側，而不是貼齊父 `alt` 邊。
- `[會員身份符合]`、`[帳號檢核通過]`、`[查詢成功]` 這類成功 else 不是單純視覺分隔線；成功分支下的 group/ref/message 必須被外層 `alt` 與最後一個 `Interaction operand` 包住，並成為該 `alt` 的成員。不可把主流程 group 緊貼放在 `alt` 底線外，否則 Visio 會把它當成 sibling 而不是 else 成員。
- 業務 `group` 是語意階段外框時，該階段內的 request/return 判斷 `alt` 必須放在 group 內，不可反過來讓 `alt` 包住 group。D.001.001/D.002.001 計息明細的 `查詢計息資料` 是外層 group，ED0005/ED0009 `[系統異常] / [查詢成功]` 原生 `alt` 必須完整落在它裡面。
- 調整完幾何後要重新建立 Visio container membership；視覺上包住但 `ContainerProperties.GetMemberShapes(...)` 為空，不算正式 native VSDX。

### 共用 SVG 参考

共用 SVG 參考使用同一個 `ref over Ent` 區塊，格式類似：

```plantuml
ref over Ent : CommonFunc.GetAccountInfo\n取得帳戶資訊\n　\n　\n循序圖請參考：30_CommonFunc.GetAccountInfo 取帳戶信息
```

注意事項：

- CommonFunc/CommonUtil 名稱、中文說明與 SVG 指引放在同一個 ref；圖面上出現 `CommonFunc.` 或 `CommonUtil/` 時，只能位於 ref 片段內的 reference self-call，且同一 ref 內必須有底部橙色參考文件說明條；`CommonFunc/` 與 `CommonUtil.` 是格式錯誤。
- `ref` 橙色指引條的可見名稱固定使用「`循序圖請參考：` + SVG basename 去 `.svg` + 中文說明」，不可顯示 `共用SVG資料夾`、前導 `/` 或 `.svg`；中文說明優先取 CommonFunc 目錄/檢查 catalog，沒有時才從 SVG `<title>/<desc>` 解析。例：`01_CommonFunc.SendToMonitorMail_Push.svg` 顯示為 `循序圖請參考：01_CommonFunc.SendToMonitorMail_Push 新版MAIL發送機制（包含推播）`。
- 落版說明或交付追溯清單仍可列出實際 `.svg` 檔名，但圖面 `ref` 內不可只放裸檔名。
- 新交付遵守 `Ref僅代表外部引用，無下方[]內容`，不在 ref 內或下方放流程內容；已交付圖不強制回修，除非使用者要求。
- `ref` 是共用引用片段，可放一條 CommonFunc/CommonUtil 原生 reference self-call 箭頭來標示被引用方法，並必須放橙色 SVG 指引；橙色指引需與 `ref` 左右及底部邊框保留內縮，不可貼框；不可混入實際 request、response、return、APP 顯示 self-call 或 Enterprise 主流程處理 self-call，實際流程訊息要放在 ref 框外並保持固定連接點間距。
- 不額外畫一條 CommonFunc participant lifeline。
- final SVG 中只有 `循序圖請參考：...` 指引文字區塊是橙色底。
- ref 框本身保持透明/白底，外框使用 DAWHO 綠色。

## 驗證內容

技能會至少做文字層驗證：

- `@startuml` 與 `@enduml` 數量一致。
- 沒有分析時已標記的舊欄位名、舊 API 名或過期文字。
- `DB` / `Redis` 沒有使用 `database`、`collections`、`queue` 等非標準 participant keyword。
- Common SVG reference 存在時，`ref` 圖面顯示名必須含 `循序圖請參考：`，不得含 `共用SVG資料夾`、`.svg`，且 basename 後需有中文說明；實際 `.svg` 檔名需能在落版說明或交付追溯清單對上。
- 最終交付路徑與檔名符合 `output/sequence_diagram/{functionCode}/` 規則。

預設不渲染 SVG/PNG 參考圖。若使用者明確要求 SVG 或圖片輸出，才額外檢查：

- User 是否為 專案標準樣式。
- DB/Redis 是否是 boxed participant。
- ref 是否只有 pointer 區塊為橙色。
- self-call 是否遵循目標樣式政策、貼近 folded arrow、位於箭頭右側且段落左對齊；native `e001-reference` 不應殘留紅字或 theme 字色，小參數顏色需與中文一致並統一黑色。
- `alt` / `else` / `opt` / `group` 分支線是否符合規則；native VSDX 的每個 `else` operand separator 必須有一條可見 DAWHO 綠色虛線，包含最後一個 else，section divider 雙線仍為實線。
- 巢狀 `group` / `alt` / `ref` 是否相對父片段有明顯內縮；不可讓子片段左右邊界與父 `alt`/`group` 完全重合，尤其是接在 `else` 分隔線下方的業務 group。
- section title、外層 business group、內層判斷 `alt` 是否逐層下沉；若任兩層只差一段連接點，需退回加大到至少兩段連接點。
- `else` operand 分隔線與 section divider 是否位於上層，沒有被 lifeline、message 或 frame 遮擋。
- message / return / self-call 箭頭與 fragment/frame/header/section/note/orange pointer 是否至少相隔一段連接點；Self Message 上下是否保留 double 連接點間距；不可貼框、貼標題帶、壓到橙色指引條或貼近相鄰訊息。
- native `alt` 是否完整包住 branch 內容、是否露出黃色右側控制點、直接 if/else operand width 是否以 `SETATREF(<alt>!Controls.Row_1)` 或 `LISTSHEETREF()!Controls.ROW_1` 回寫、operand 垂直尺寸是否沒有跨 member 的 `Sheet.*!Height` / `Sheet.*!PinY` 公式、`if` 頭上是否無多餘線段、最後一段 `else` bottom 是否貼齊 `alt` bottom、container membership 是否非空。
- native `alt` / `else` 的所有 `Interaction operand` 條件是否都為 `[條件]` 格式；若 validator 回報 `ConditionOperandsWithoutBrackets > 0`，需退回修正。
- request/return 判斷 `alt` 是否位於所屬業務 `group` 內；若 `查詢計息資料` 之類的 group 被 ED0005/ED0009 判斷 `alt` 反向包住，需退回修正。
- 成功 else 下方是否有 group/ref/message 緊貼在 `alt` 底線外；若有，代表成功分支內容沒有被最後一個 operand 包住，需退回修正。
- native `alt` 的 message / return / self-call 是否完整落在自己的 if/else operand 內；不得有 self-call folded arrow 或任一訊息跨過 `Interaction operand` separator。
- native `ref` 框內是否只包含 CommonFunc/CommonUtil 參考 self-call 與橙色 SVG 指引，不能包含實際 request/response/main-flow self-message 箭頭。
- native `ref` 內有 CommonFunc/CommonUtil 參考 self-call 時，是否存在同方法名、格式為 `循序圖請參考：basename 中文說明` 的底部橙色參考文件條；缺少時驗證必須失敗。
- native 主流程普通 message / self-call 上不得出現 CommonFunc/CommonUtil 方法名；若出現，代表共用方法沒有改成 ref 片段，驗證必須失敗。
- 巢狀 `alt` 的 `else` 條件是否仍在自己的 child frame 內，沒有被外層 operand 正規化拉出跑道。
- participant 是否為 native UML lifeline master；message / return / self-call 是否為 native UML message master 且端點已膠合到既有原生連接點列上；self-call 是否有文字位置控制點；不能只用手動畫線和文字框模擬，也不能為了 connector glue 新增單箭頭專屬 connection-point rows。
- 所有生命線是否保留完整且均勻的 UML 原生連接點列；選取 User / APP / Enterprise / IRIS / DB / Redis lifeline 時應能看到沿生命線分布的灰色吸附點，且訊息 / self-call 箭頭端點應吸附到最近的既有連接點，不應出現稀疏缺點或多個幾乎重疊的連接點。
- 頁面是否固定尺寸：`DrawingResizeType` 必須為 `0`、`ResizePage` 必須為 `FALSE`；章節雙線條要鎖定橫向尺寸/水平移動，中央標題框則要保留邊框可調整能力，不能因拖曳標題框邊框而放大 Visio 頁面。
- 正式 VSDX 是否維持一支功能一個文件；文件內 tab 是否依完整使用者流程拆分，每個 tab 是否有 User 進入點，而不是依 API、成功/失敗情境、步驟、子流程或每個小 PRD 頁面硬拆。
- VSDX 是否可開啟、是否是 native 結構、message 端點是否全部膠合到既有原生連接點列上，且沒有 embedded raster/ForeignData 風險。
- PNG preview 是否能快速視覺 QA。

## 修復方式

如果只要求「檢查」，技能會列出問題與建議，不會改檔。

如果需要修復，可以指定範圍，例如：

```text
請修正 User 樣式、DB/Redis participant、ref 區塊橙色底與 APP self-call，其他內容先不要動。
```

或：

```text
請重新輸出完整交付包，包含 .puml、SVG、VSDX、PNG preview 和落版說明。
```

修復原則：

- 以 frozen API Detail 為權威來源。
- 保留正確的主流程與業務語義。
- 不把舊圖中過期 API/欄位名帶到新圖。
- 優先輸出專案本地 `output/sequence_diagram/{functionCode}/`。
- 只有使用者要求時才額外複製到 `v1.x Reference/`。
- 若 native VSDX 產出或驗證失敗，會明確說明缺少哪個工具或哪一步失敗；不會把 SVG-import VSDX 包裝成正式交付。

## 常用指令範例

產出完整交付包：

```text
請產出完整 專案時序圖交付包：PlantUML、SVG、VSDX、PNG preview、落版說明。
```

只修 PlantUML 可渲染性：

```text
請檢查這份 .puml 是否可在 PlantUML editor 渲染，修正語法錯誤。
```

只修 專案視覺樣式：

```text
請依標準範例修正 SVG/VSDX 樣式，尤其是 User、ref、APP self-call、alt 分支線。
```

檢查 Common SVG reference：

```text
請確認所有 CommonFunc/CommonUtil 的 ref over Ent 都引用正確共用 SVG 檔名。
```

只產出文字交付：

```text
請只產出 .puml 和落版說明，不要渲染 SVG/VSDX。
```

## 建議輸入資訊

為了讓時序圖更準確，建議提供：

- 功能編號。
- frozen API Detail `.xlsx`。
- TSD `.docx`。
- 既有 `.puml`、`.svg`、`.vsdx` 或截圖。
- `v1.x Reference` 或共用 SVG 資料夾位置。
- 是否需要完整交付包，或只要 `.puml` / `.svg` / `.vsdx`。
- PRD/TSD 中的頁面/畫面與使用者流程；若未提供，技能會先從 PRD/TSD 推導，無法確認時預設單一 tab 並在落版說明標註。
- 是否要複製最終檔到 `v1.x Reference/`。

## 注意事項

- 舊 SVG/VSDX 是參考，不會覆蓋 frozen API Detail。
- API contract 未定時，應先用接口設計梳理技能確認命名與欄位。
- 一般交付預設包含 VSDX，不需要另外再說一次。
- 一支功能只交付一個正式 VSDX；同一 VSDX 裡可有多個 tab，但 tab 以完整使用者流程為主，連續頁面/步驟可合併，且每個 tab 都要有 User 進入點。
- 若本機缺少 PlantUML、Java、Visio COM 或轉檔工具，會回報可完成與未完成的部分。
- 不會把 Request/Response 欄位清單塞滿箭頭標籤；圖面優先保持業務可讀。
- 預設不產出 final `svg/` 與 `png/` 參考圖；只有使用者明確要求圖片輸出時才額外產生並檢查。
