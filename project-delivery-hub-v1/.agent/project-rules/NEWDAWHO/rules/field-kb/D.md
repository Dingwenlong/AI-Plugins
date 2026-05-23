# D 類字段知識庫

用途：統一 D 類功能（存款、活存、定存相關）新系統 API 欄位命名。此文件以 PRD 中文業務語意為唯一主軸；舊系統、舊 API、DB 欄位、主機欄位只能作為 Source/alias，不作 canonical field。

## 使用原則

- 目標是新系統標準字段，不遷就舊代碼命名。
- 先抽取 PRD 中文語意，再命名英文字段。
- 字段名要能讓開發者不看舊系統也理解業務語意。
- 禁用模糊詞：`type`、`flag`、`list`、`data`、`acct`、`currEName`、`tdAcct`。
- 禁用語意反轉字段：若 PRD 語意是「是否可轉帳」，用 `canTransfer`，不用 `transferRestricted`。
- 縮寫僅保留業界通用縮寫：`twd`、`id`、`api`。帳號用 `accountNumber`，不用 `accountNo`。
- 舊欄位集中放在「Alias / 遷移紀錄」，不得在 canonical 表中重複出現。

## 命名邊界

| PRD 語意邊界 | Canonical rule |
| --- | --- |
| 活存帳號 vs 定存單號 | 活存帳號用 `accountNumber`；定存單號/存單帳號用 `fixedDepositCertificateNumber`。 |
| 扣款/歸戶帳號 vs 定存單號 | 定存查詢中的扣款/歸戶活存帳號用 `linkedAccountNumber`；定位單一定存用 `fixedDepositCertificateNumber`。 |
| 幣別 | 統一用 `currencyCode` / `currencyName`；若需指明帳號、定存、利息幣別，加語意前綴。 |
| 帳號總覽可用餘額 vs 交易後餘額 | 總覽用 `availableBalance`；交易明細用 `balanceAfterTransaction`。 |
| 交易分類 | 交易分類名稱用 `transactionCategoryName`；分類圖示用 `transactionCategoryIcon`；不用 `type` / `typeImg`。 |
| 搜尋關鍵字 vs 搜尋紀錄清單 | 搜尋文字用 `keyword`；搜尋紀錄清單用 `searchHistoryList`。 |
| 操作類型 | 操作型 API 統一用 `action`；不用 `flag`。 |
| 時間欄位 | PRD 若是業務時間，直接命名 `searchTime`、`exchangeRateTime`；不用泛稱 `timestamp`。 |
| 定存狀態 | 用 `fixedDepositStatus` / `fixedDepositStatusName`；不用技術或存單實作詞 `certificateStatus` 作對外語意。 |

## D.001/D.002 API 命名

| Canonical API | 中文功能 | 決策 |
| --- | --- | --- |
| `GetDemandDepositAccounts` | 取臺/外幣活存帳號 | 用 `DemandDeposit` 表達活存語意；不用舊名 `LivedDeposit`。 |
| `GetDemandDepositTransactions` | 取臺/外幣活存交易明細清單 | 用完整 `Transactions`；不用縮寫 `Trans` 或尾綴 `List` 作 API 主名。 |
| `GetDemandDepositSearchHistory` | 取活存搜尋記錄 | 查詢最新 5 筆搜尋紀錄為純讀 API，Request 不帶 `action`。 |
| `MaintainDemandDepositSearchHistory` | 維護活存搜尋記錄 | 新增/刪除搜尋紀錄為寫入 API，使用 `action=ADD/DELETE` + `keyword`。 |

## 活存帳號

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `demandDepositAccounts` | 活存帳號清單 | array | D.001/D.002 取臺/外幣活存帳號 | response list。 |
| `accountNumber` | 活存帳號 | string | 活存帳號、活存交易明細 | 14 碼帳號原值。 |
| `maskedAccountNumber` | 活存帳號遮罩/格式化 | string | 帳號顯示 | 若 PRD 僅要求格式化，不一定遮罩，Notes 要寫清楚。 |
| `accountName` | 帳號中文名稱 | string | 活存帳號清單 item | 例如 DAWHO 活期儲蓄存款。 |
| `accountCategoryCode` | 帳號類別代碼 | string | 活存帳號清單 item | Source 可為主機帳號類別。 |
| `currencyCode` | 幣別代碼/查詢幣別 | string | request filter、帳號清單、交易明細 | ISO-like code，例如 TWD/USD。 |
| `currencyName` | 幣別中文名稱 | string | 帳號清單、幣別顯示 | 例如 新臺幣、美元。 |
| `accountBalance` | 帳戶餘額 | decimal | 活存帳號清單 item | 原幣帳戶餘額。 |
| `twdEquivalentBalance` | 約當臺幣餘額 | decimal | 外幣活存帳號清單 item / 外幣總覽 | 需說明匯率時間規則。 |
| `availableBalance` | 最高可使用金額/可用餘額 | decimal | 活存帳號清單 item | 貼 PRD 顯示文字；不可與交易後餘額混用。 |
| `estimatedAccruedInterest` | 累計利息約 | decimal | 臺幣活存帳號清單 item | 外幣活存不回傳或必填 N。 |
| `canTransfer` | 是否可轉帳/是否允許轉帳 | boolean | 活存帳號清單 item | 若來源是禁止轉出旗標，API 仍回 PRD 正向語意。 |

## 活存交易查詢

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `singleDate` | 使用者輸入單一日期 | string | 活存交易明細 request | 與 `startDate`/`endDate` 二擇一；查 00:00:00~23:59:59。 |
| `startDate` | 使用者輸入起始日期 | string | 活存交易明細 request | 自訂區間起日。 |
| `endDate` | 使用者輸入結束日期 | string | 活存交易明細 request | 自訂區間迄日，不得早於起日。 |
| `queryStartDateTime` | 實際查詢起始時間 | string | 活存交易明細 response | 含 00:00:00。 |
| `queryEndDateTime` | 實際查詢結束時間 | string | 活存交易明細 response | 含 23:59:59。 |
| `transactionCategoryFilters` | 交易分類篩選條件 | array | 活存交易明細 request | item 使用 `transactionCategoryName` + `incomeExpenseType`。 |
| `transactionCategoryName` | 交易分類名稱 | string | 交易分類篩選 item、交易明細 item | 收入/支出同名分類不得只靠名稱判斷。 |
| `incomeExpenseType` | 收支方向 | string enum | 交易分類篩選、交易明細 item | 建議值：`INCOME` / `EXPENSE`。 |
| `keyword` | 關鍵字 | string | 交易明細搜尋、搜尋紀錄 | 最多 15 字元；比對規則寫在 Notes。 |
| `pageNumber` | 頁碼 | int | 列表查詢 request | 第一頁為 1。 |
| `pageSize` | 每頁筆數 | int | 列表查詢 request | 預設值需寫在 Notes。 |

## 活存交易明細

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `transactions` | 交易明細清單 | array | 活存交易明細 response | response list。 |
| `totalTransactionCount` | 交易明細筆數 | int | 活存交易明細 response | 說明是篩選後總筆數或本頁筆數。 |
| `transactionCategoryIcon` | 交易分類圖示 | string | 交易明細 item | 依 `transactionCategoryName` + `incomeExpenseType` 取得。 |
| `transactionMemo` | 摘要備註 | string | 交易明細 item | 主機摘要/備註組合；不可與可編輯交易說明混用。 |
| `transactionDescription` | 交易說明 | string | 交易明細 item | 使用者可編輯/智慧帳本交易說明；非所有資料都有值。 |
| `transactionAmount` | 交易金額 | decimal | 交易明細 item | 收支方向需與正負號或 `incomeExpenseType` 一致。 |
| `balanceAfterTransaction` | 交易後帳戶餘額 | decimal | 交易明細 item | 不同於帳號總覽 `availableBalance`。 |
| `transactionTags` | 交易標籤清單 | array | 交易明細 item | UI 顯示上限寫在 Notes，不硬塞字段名。 |
| `transactionDisplayDate` | 顯示用交易日期 | string | 交易明細 item | 格式 MM/dd。 |
| `transactionDateTime` | 交易日期時間 | string | 交易明細 item | 格式 yyyy/MM/dd HH:mm。 |
| `valueDate` | 計息日 | string | 交易明細 item | 不可與交易日期時間混用。 |
| `accountDisplayName` | 交易明細顯示用帳戶名稱 | string | 交易明細 item | 僅供列表顯示，不作帳號識別。 |
| `transactionExchangeRate` | 交易匯率 | decimal | 外幣活存交易明細 item | TWD 或無匯率時不回傳/前端隱藏。 |
| `transactionDataSource` | 交易資料來源 | string enum | 主機資料/智慧帳本整合 | 建議值：`HOST` / `SMART_BOOK`。 |

## 搜尋紀錄

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `action` | 操作類型 | string enum | 搜尋紀錄維護 request、其他操作型 API request | 搜尋紀錄維護建議值：`ADD` / `DELETE`；查詢搜尋紀錄應拆為純讀 API，不使用 `QUERY` action。 |
| `searchHistoryList` | 搜尋紀錄清單 | array | 搜尋紀錄 response | 最多最近 5 筆。 |
| `searchTime` | 搜尋時間 | string | 搜尋紀錄 item | DB 可仍為 Timestamp，API 用 PRD 語意。 |

## 定存帳號與查詢

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `linkedAccountNumber` | 扣款/歸戶活存帳號 | string | 定存總覽、明細、計息明細、修改名稱 | 定存所屬或扣款的活存帳號。 |
| `maskedLinkedAccountNumber` | 扣款/歸戶活存帳號遮罩/格式化 | string | 定存列表/明細顯示 | 與 `linkedAccountNumber` 成對。 |
| `fixedDepositCertificateNumber` | 定存單號/存單帳號 | string | 定存明細、計息明細、修改名稱 | 定位單一定存必備欄位。 |
| `maskedFixedDepositCertificateNumber` | 定存單號遮罩/格式化 | string | 定存列表/明細顯示 | 與 `fixedDepositCertificateNumber` 成對。 |
| `fixedDepositQueryScope` | 定存查詢範圍 | string enum | 定存查詢 request | 建議值：`ACTIVE` / `HISTORY` / `DETAIL`。 |
| `fixedDepositStatusFilter` | 定存狀態篩選 | string enum | 定存列表/歷史列表 request | request filter。 |
| `sortBy` | 排序欄位 | string enum | 列表查詢 request | 需列出可排序欄位。 |
| `sortOrder` | 排序方向 | string enum | 列表查詢 request | 建議值：`ASC` / `DESC`。 |

## 定存資料、金額與匯率

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `fixedDepositName` | 定存名稱 | string | 定存列表/明細/修改名稱 | 最多 15 個中文字符。 |
| `fixedDepositAmount` | 定存金額/本金 | decimal | 定存存單資料 | 新系統標準為 decimal，不回傳 display string。 |
| `fixedDepositCurrencyCode` | 定存原幣幣別代碼 | string | 定存存單資料 |  |
| `fixedDepositCurrencyName` | 定存原幣幣別中文 | string | 定存存單資料 |  |
| `fixedDepositFundingTypeName` | 存單種類/存款方式顯示名稱 | string | 定存存單資料 | 例如「每月固定存」、「單筆一次存」；不用 `Catg` 縮寫。 |
| `fixedDepositValueDate` | 存單起息日/生效日 | string | 定存存單資料 | 格式 yyyy/MM/dd。 |
| `fixedDepositMaturityDate` | 存單到期日 | string | 定存存單資料 | 格式 yyyy/MM/dd。 |
| `fixedDepositInterestRateTypeName` | 定存利率類型顯示名稱 | string | 定存存單資料 | 例如固定利率、機動利率；不用泛稱 `depositType`。 |
| `fixedDepositOpeningInterestRate` | 定存開單利率 | decimal | 定存存單資料 | 開單年利率。 |
| `fixedDepositOriginalValueDate` | 存單原開單日 | string | 定存存單資料 | 格式 yyyy/MM/dd；不用 `Orig` 縮寫。 |
| `fixedDepositTerm` | 存單期限 | string | 定存存單資料 | 例如 12M。 |
| `fixedDepositRenewalTypeCode` | 續存方式代碼 | string | 定存存單資料 | 例如 P、PI、空值。 |
| `fixedDepositMaxRenewalCount` | 最大轉期次數 | int | 定存存單資料 |  |
| `fixedDepositRenewalCount` | 已轉期次數 | int | 定存存單資料 |  |
| `fixedDepositInterestPaymentMethodName` | 領息方式顯示名稱 | string | 定存存單資料 | 例如「每月固定領」、「到期一次領」。 |
| `fixedDepositRenewalTypeName` | 續存方式顯示名稱 | string | 定存存單資料 | 例如「續存本金」、「續存本金利息」、「不續存」。 |
| `totalFixedDepositAmount` | 定存總額 | decimal | 定存總覽 | 原幣或臺幣需在 Notes 說明。 |
| `totalFixedDepositTwdEquivalentAmount` | 外幣定存約當臺幣總額 | decimal | 外幣定存總覽 | 貼 PRD 外幣總覽語意。 |
| `currencySummaries` | 幣別小計清單 | array | 外幣定存總覽 |  |
| `currencySubtotalAmount` | 幣別原幣小計 | decimal | `currencySummaries` item |  |
| `twdEquivalentAmount` | 約當臺幣小計 | decimal | `currencySummaries` item |  |
| `twdConversionExchangeRate` | 折臺幣匯率 | decimal | 外幣定存約當臺幣換算 |  |
| `twdConversionExchangeRateTime` | 折臺幣匯率時間 | string | 外幣定存約當臺幣換算 | 格式 yyyy/MM/dd HH:mm:ss。 |
| `interestCurrencyCode` | 利息幣別代碼 | string | 定存利息 | 通常同 `fixedDepositCurrencyCode`。 |

## 定存利息、狀態與進度

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `referenceInterest` | 參考利息 | decimal | 定存卡片/明細 | 固定語意：已付 + 未付參考利息。 |
| `paidInterest` | 已付利息 | decimal | 定存卡片/明細 |  |
| `unpaidInterest` | 未付/累計中利息 | decimal | 定存卡片/明細 |  |
| `totalPaidInterest` | 已付利息合計 | decimal | 計息明細總結 |  |
| `outstandingInterest` | 累計中利息 | decimal | 計息明細總結 |  |
| `estimatedTotalInterest` | 累積預估總利息 | decimal | 定存總覽/計息明細 | PRD 若寫「累積預估總利息」，優先用此名。 |
| `fixedDepositStatus` | 定存狀態代碼 | string enum | 定存列表/明細 | 建議值：`ACTIVE` / `SCHEDULED` / `MATURED` / `TERMINATED` / `CANCELLED`。 |
| `fixedDepositStatusName` | 定存狀態顯示名稱 | string | 定存列表/明細 |  |
| `canCancelReservation` | 是否可取消預約定存 | boolean | 定存列表/明細操作 |  |
| `canEditFixedDepositName` | 是否可修改定存名稱 | boolean | 定存列表/明細操作 | 比 `canEditName` 更貼 PRD。 |
| `completedPeriodCount` | 已存期數/已完成期數 | int | 定存進度 |  |
| `totalPeriodCount` | 總期數 | int | 定存進度 |  |
| `progressPercent` | 進度百分比 | decimal | 定存進度 |  |

## 定存利率查詢表

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `fixedDepositRateOptions` | 定存利率方案清單/利率表 | array | D.003 GetFixedDepositRateOptions response | 依所選幣別顯示定存方案；排序與篩選規則需貼 PRD。 |
| `rateTerm` | 利率期限 | string | D.003 GetFixedDepositRateOptions response item | 需能涵蓋 7D、14D、1M、2M、3M、6M、9M、12M、24M、36M。 |
| `rateCurrencyCode` | 利率幣別代碼 | string | D.003 GetFixedDepositRateOptions response item | Source 可為 EC0007.EnqECurr / CommonUtil.GetCENCurr.currEName；對外不用 `currEName`。 |
| `rateType` | 利率類別 | string | D.003 GetFixedDepositRateOptions response item | 不用泛稱 `type`。 |
| `annualInterestRate` | 優惠利率/定存利率 | decimal | D.003 GetFixedDepositRateOptions response item | 若來源為年利率，備註需說明；Source 可為 EC0007.EnqERate。 |
| `ratePlanTag` | 方案標籤 | string | D.003 GetFixedDepositRateOptions response item | 例如換匯優利定存、美人雙幣定存；一般定存可空值；美人雙幣依 DAWHO_fix.sitemap + D.006 DepositCommonUtil.GetExchangeFixLimitAmt 判斷。 |
| `estimatedInterest` | 原幣利息試算 | decimal | D.003 GetFixedDepositRateOptions response item | 依 PRD 顯示規則：TWD/JPY 整數、外幣 2 位小數；實際成交以交易系統為準。 |

## 計息明細

D.001.001/D.002.001 目前凍版口徑：`GetFixedDepositInterestDetail` 只回前端計息明細頁實際展示欄位，摘要金額由前一頁 `GetFixedDepositDetail` 提供；本金、年利率、給息起迄日、計息天數、毛息、計息帳號等欄位僅作來源/內部對照，不放入該 API 對外 response。

| Canonical field | PRD 中文語意 | Type | Context / APIs | Notes |
| --- | --- | --- | --- | --- |
| `hasInterestDetails` | 是否有計息明細 | boolean | 計息明細 response | 無資料時 false。 |
| `payableInterestCount` | 應付計息筆數 | int | 計息明細 response |  |
| `paidInterestCount` | 已付計息筆數 | int | 計息明細 response |  |
| `payableInterestDetails` | 應付計息清單 | array | 計息明細 response | 可為空陣列。 |
| `paidInterestDetails` | 已付計息清單 | array | 計息明細 response | 可為空陣列。 |
| `payableInterestCurrencyCode` | 應付利息幣別 | string | `payableInterestDetails` item |  |
| `paidInterestCurrencyCode` | 已付利息幣別 | string | `paidInterestDetails` item |  |
| `payablePrincipalAmount` | 應付計息本金 | decimal | `payableInterestDetails` item | Source 可為 ED0005.TmnCrValBalance。 |
| `paidPrincipalAmount` | 已付計息本金 | decimal | `paidInterestDetails` item | Source 可為 ED0009.TmnCrValBalance。 |
| `payableAnnualInterestRate` | 應付計息年利率 | decimal | `payableInterestDetails` item |  |
| `paidAnnualInterestRate` | 已付計息年利率 | decimal | `paidInterestDetails` item |  |
| `payableInterestDate` | 應付計息日期 | string | `payableInterestDetails` item | 格式 yyyy/MM/dd。 |
| `paidInterestDate` | 已付計息日期 | string | `paidInterestDetails` item | 格式 yyyy/MM/dd。 |
| `payableInterestPeriodStartDate` | 應付給息起日 | string | `payableInterestDetails` item | 格式 yyyy/MM/dd。 |
| `paidInterestPeriodStartDate` | 已付給息起日 | string | `paidInterestDetails` item | 格式 yyyy/MM/dd。 |
| `payableInterestPeriodEndDate` | 應付給息迄日 | string | `payableInterestDetails` item | 格式 yyyy/MM/dd。 |
| `paidInterestPeriodEndDate` | 已付給息迄日 | string | `paidInterestDetails` item | 格式 yyyy/MM/dd。 |
| `payableInterestDays` | 應付計息天數 | int | `payableInterestDetails` item |  |
| `paidInterestDays` | 已付計息天數 | int | `paidInterestDetails` item |  |
| `payableInterestSubtotal` | 應付利息小計 | decimal | `payableInterestDetails` item | 不等同毛息時需在 Notes 說明差異。 |
| `paidInterestSubtotal` | 已付利息小計 | decimal | `paidInterestDetails` item | 不等同毛息時需在 Notes 說明差異。 |
| `payableGrossInterest` | 應付利息毛息 | decimal | `payableInterestDetails` item |  |
| `paidGrossInterest` | 已付利息毛息 | decimal | `paidInterestDetails` item |  |
| `payableInterestAccountNumber` | 應付計息帳號 | string | `payableInterestDetails` item | 若僅為來源帳號，仍使用 accountNumber 語意，不用 Account 縮寫。 |
| `paidInterestAccountNumber` | 已付計息帳號 | string | `paidInterestDetails` item | 若僅為來源帳號，仍使用 accountNumber 語意，不用 Account 縮寫。 |

## Alias / 遷移紀錄

| 舊欄位 | 新 canonical field | 模組/API | 決策 |
| --- | --- | --- | --- |
| `accountNo` | `accountNumber` | D.001/D.002 | 新系統不用 `No` 縮寫。 |
| `currEName` | `currencyCode` | D 類全域 | 新系統不用舊系統 EName 命名。 |
| `currCName` | `currencyName` | D 類全域 | 新系統不用舊系統 CName 命名。 |
| `tdAccountNo` 表示活存帳號 | `accountNumber` | D.001/D.002 | 活存帳號不可使用定存命名。 |
| `tdAccountNo` 表示定存單號 | `fixedDepositCertificateNumber` | D.001.001/D.002.001 | 貼 PRD 定存單號/存單帳號語意。 |
| `queryAccountNo` | `linkedAccountNumber` | D.001.001/D.002.001 | 表示定存關聯的扣款/歸戶活存帳號。 |
| `type` | `transactionCategoryName` | D.001/D.002 | PRD 中文為交易分類名稱。 |
| `typeImg` | `transactionCategoryIcon` | D.001/D.002 | PRD 中文為交易分類圖示。 |
| `memo` | `transactionMemo` | D.001/D.002 | PRD 中文為摘要備註。 |
| `description` | `transactionDescription` | D.001/D.002 | PRD 中文為交易說明。 |
| `txnAmount` | `transactionAmount` | D.001/D.002 | 新系統不用 txn 縮寫。 |
| `availBalance` | `balanceAfterTransaction` | D.001/D.002 | PRD 語意為交易後帳戶餘額。 |
| `displayDate` | `transactionDisplayDate` | D.001/D.002 | PRD 語意為顯示用交易日期。 |
| `txnDateTime` | `transactionDateTime` | D.001/D.002 | 新系統不用 txn 縮寫。 |
| `account` | `accountDisplayName` | D.001/D.002 | 僅供列表顯示，不是帳號識別。 |
| `fxRate` | `transactionExchangeRate` | D.001/D.002 | PRD 語意為交易匯率。 |
| `dataSource` | `transactionDataSource` | D.001/D.002 | 指交易資料來源。 |
| `flag` | `action` | D.001/D.002 | 操作型 API 統一用 `action`；搜尋紀錄 action 值為 `QUERY` / `ADD` / `DELETE`。 |
| `historyList` | `searchHistoryList` | D.001/D.002 | PRD 語意為搜尋紀錄清單。 |
| `searchRecord` | `keyword` | D.001/D.002 | PRD 語意為搜尋關鍵字；DB 欄位仍是 `HistoricalSearch.SearchRecord`。 |
| `timestamp` | `searchTime` | D.001/D.002 | PRD 語意為搜尋時間。 |
| `GetLivedDepositAccount` | `GetDemandDepositAccounts` | D.001/D.002 API | `Lived` 不是業務語意；新 API 名用活存標準詞 `DemandDeposit`。 |
| `GetLivedDepositTransList` | `GetDemandDepositTransactions` | D.001/D.002 API | 不使用 `Trans` 縮寫與 `List` 尾綴作 API 主名。 |
| `DepositSearchHistory` | `GetDemandDepositSearchHistory` / `MaintainDemandDepositSearchHistory` | D.001/D.002 API | 舊 API 同時承擔查詢/新增/刪除；新系統拆成純讀查詢 API 與 ADD/DELETE 維護 API。 |
| `ManageDemandDepositSearchHistory` | `GetDemandDepositSearchHistory` / `MaintainDemandDepositSearchHistory` | D.001/D.002 API | 中間命名曾用 `Manage` 合併 QUERY/ADD/DELETE；凍版口徑改為查詢與維護分離。 |
| `PatchFixedDepositName` | `PatchFixedDepositTitle` | D.001.001/D.002.001 | 對齊 TSD API 清單；若 API 重新設計，可命名為修改定存名稱對應 API。 |
| `GetDepositInterestDetail` | `GetFixedDepositInterestDetail` | D.001.001/D.002.001 | 新系統 API 名稱需明確表達「定存」計息明細，避免與一般存款利息混淆。 |
| `depositAmount` | `fixedDepositAmount` | D.001.001/D.002.001 | PRD 中文為定存金額。 |
| `totalAmt` | `totalFixedDepositAmount` | D.001.001/D.002.001 | PRD 中文為定存總額。 |
| `totalTwdEquivalentAmount` | `totalFixedDepositTwdEquivalentAmount` | D.002.001 | PRD 中文為外幣定存約當臺幣總額。 |
| `exchangeRate` | `twdConversionExchangeRate` | D.002.001 | PRD 語意為外幣定存折臺幣匯率。 |
| `exchangeRateTime` | `twdConversionExchangeRateTime` | D.002.001 | PRD 語意為外幣定存折臺幣匯率時間。 |
| `certificateStatus` | `fixedDepositStatus` | D.001.001/D.002.001 | PRD 中文為定存狀態，不用存單技術詞。 |
| `canEditName` | `canEditFixedDepositName` | D.001.001/D.002.001 | 貼 PRD 修改定存名稱。 |
| `depositCatgType` | `fixedDepositFundingTypeName` | D.001.001/D.002.001 | PRD 顯示為存單種類/存款方式；不用 `Catg` 縮寫。 |
| `depositValueDate` | `fixedDepositValueDate` | D.001.001/D.002.001 | PRD 中文為存單起息日/生效日。 |
| `depositMaturityDate` | `fixedDepositMaturityDate` | D.001.001/D.002.001 | PRD 中文為存單到期日。 |
| `depositType` | `fixedDepositInterestRateTypeName` | D.001.001/D.002.001 | PRD 中文為定存利率類型，不用泛稱 type。 |
| `depositRateOpen` | `fixedDepositOpeningInterestRate` | D.001.001/D.002.001 | PRD 中文為定存開單利率，不用 Open 縮寫式尾碼。 |
| `depositOrigValueDate` | `fixedDepositOriginalValueDate` | D.001.001/D.002.001 | PRD 中文為存單原開單日，不用 Orig 縮寫。 |
| `depositTerm` | `fixedDepositTerm` | D.001.001/D.002.001 | PRD 中文為存單期限。 |
| `depositRollType` | `fixedDepositRenewalTypeCode` | D.001.001/D.002.001 | PRD 中文為續存方式；代碼欄位明確用 Code。 |
| `depositRollMax` | `fixedDepositMaxRenewalCount` | D.001.001/D.002.001 | PRD 中文為轉期次數上限。 |
| `depositRollTimes` | `fixedDepositRenewalCount` | D.001.001/D.002.001 | PRD 中文為已轉次數。 |
| `depositReceiveInterestType` | `fixedDepositInterestPaymentMethodName` | D.001.001/D.002.001 | PRD 中文為領息方式；對外回中文顯示名稱時用 Name。 |
| `depositRollTypeName` | `fixedDepositRenewalTypeName` | D.001.001/D.002.001 | PRD 中文為續存方式顯示名稱。 |
| `paidPeriodCount` | `completedPeriodCount` | D.001.001/D.002.001 | PRD 中文為已存期數/已完成期數。 |
| `cumulativeTotalInterest` | `estimatedTotalInterest` | D.001.001/D.002.001 | PRD 中文為累積預估總利息。 |
| `payableInfo` | `payableInterestDetails` | D.001.001/D.002.001 | PRD 中文為應付計息清單。 |
| `paidInfo` | `paidInterestDetails` | D.001.001/D.002.001 | PRD 中文為已付計息清單。 |
| `payableValBalance` | `payablePrincipalAmount` | D.001.001/D.002.001 | PRD 中文為應付計息本金，不保留 ValBalance 舊主機命名。 |
| `paidValBalance` | `paidPrincipalAmount` | D.001.001/D.002.001 | PRD 中文為已付計息本金，不保留 ValBalance 舊主機命名。 |
| `payableIntRate` | `payableAnnualInterestRate` | D.001.001/D.002.001 | PRD 中文為年利率，新系統不用 Int 縮寫。 |
| `paidIntRate` | `paidAnnualInterestRate` | D.001.001/D.002.001 | PRD 中文為年利率，新系統不用 Int 縮寫。 |
| `payableIntDate` | `payableInterestDate` | D.001.001/D.002.001 | PRD 中文為計息日期，新系統不用 Int 縮寫。 |
| `paidIntDate` | `paidInterestDate` | D.001.001/D.002.001 | PRD 中文為計息日期，新系統不用 Int 縮寫。 |
| `payablePeriodFirstDate` | `payableInterestPeriodStartDate` | D.001.001/D.002.001 | PRD 中文為給息起日，使用 StartDate 語意。 |
| `paidPeriodFirstDate` | `paidInterestPeriodStartDate` | D.001.001/D.002.001 | PRD 中文為給息起日，使用 StartDate 語意。 |
| `payablePeriodLastDate` | `payableInterestPeriodEndDate` | D.001.001/D.002.001 | PRD 中文為給息迄日，使用 EndDate 語意。 |
| `paidPeriodLastDate` | `paidInterestPeriodEndDate` | D.001.001/D.002.001 | PRD 中文為給息迄日，使用 EndDate 語意。 |
| `payableNoOfDays` | `payableInterestDays` | D.001.001/D.002.001 | PRD 中文為計息天數，不保留 NoOfDays 舊命名。 |
| `paidNoOfDays` | `paidInterestDays` | D.001.001/D.002.001 | PRD 中文為計息天數，不保留 NoOfDays 舊命名。 |
| `payableIntAmt` | `payableInterestSubtotal` | D.001.001/D.002.001 | PRD 中文為利息小計，新系統不用 Int/Amt 縮寫。 |
| `paidIntAmt` | `paidInterestSubtotal` | D.001.001/D.002.001 | PRD 中文為利息小計，新系統不用 Int/Amt 縮寫。 |
| `payabletotalInterest` / `payableTotalInterest` | `payableGrossInterest` | D.001.001/D.002.001 | PRD 中文為應付利息毛息。 |
| `paidtotalInterest` / `paidTotalInterest` | `paidGrossInterest` | D.001.001/D.002.001 | PRD 中文為已付利息毛息。 |
| `payableAccount` | `payableInterestAccountNumber` | D.001.001/D.002.001 | PRD 中文為計息帳號，不用泛稱 Account。 |
| `paidAccount` | `paidInterestAccountNumber` | D.001.001/D.002.001 | PRD 中文為計息帳號，不用泛稱 Account。 |
| `rateList` | `fixedDepositRateOptions` | D.003 | 對外 response 使用定存利率方案清單語意，不用泛稱 list。 |
| `code` / `fixedDepositRateCode` | 不對外回傳 | D.003 | 20260507 問題單確認前端未使用利率編號；EC0007.EnqERateCode 僅作內部來源/判斷。 |
| `term` / `fixedDepositTerm` | `rateTerm` | D.003 | 本 API row item 採用利率期限語意，避免與存單期限混淆。 |
| `currEName` / `rateCurrEName` | `currencyCode` request / `rateCurrencyCode` response | D.003 | `currEName` 僅保留為 CommonUtil/來源欄位；D.003 對外用幣別代碼語意。 |
| `type` / `fixedDepositRateType` | `rateType` | D.003 | 利率方案 item 內使用更短且有前綴的利率類別。 |
| `rate` | `annualInterestRate` | D.003 | 明確表達年利率。 |
| `tag` / `flag` | `ratePlanTag` | D.003 | 方案標籤不得出現欄位表與範例不一致。 |
| `calcInterest` | `estimatedInterest` | D.003 | 利息試算屬於每筆方案 item。 |
| `GetFixedDepositRateList` | `GetFixedDepositRateOptions` | D.003 | API 名稱改為更貼近 PRD 的定存利率方案清單語意。 |

## 已確認規則

- 定存名稱最多 15 個中文字符。
- 金額欄位新系統標準優先使用 decimal，不回傳 display string；顯示格式由前端或格式化層處理。
- `referenceInterest` 固定表示「已付 + 未付參考利息」。
- 操作型 API 統一用 `action`；舊欄位 `flag` 僅作 alias / 遷移來源。
- D.001.001/D.002.001 計息明細 API 名稱固定為 `GetFixedDepositInterestDetail`；舊名 `GetDepositInterestDetail` 僅作遷移別名。
- D.001.001/D.002.001 `GetFixedDepositInterestDetail` 不再回傳摘要欄位 `referenceInterest`、`outstandingInterest`、`estimatedTotalInterest`，也不回傳前端未展示的本金/利率/毛息/計息帳號等內部欄位；摘要資訊由前一頁 `GetFixedDepositDetail` 提供。
- D.003 利率查詢表的 API 類別為 Deposit，API 名稱為 GetFixedDepositRateOptions；業務 API 查詢幣別使用 `currencyCode`，CommonUtil.GetCENCurr 的 `currEName` 僅作共用幣別資料 API 的來源/相容欄位。
- D.003 `ratePlanTag`：換匯優利定存標籤依 EC0007 回傳方案；美人雙幣定存標籤需先讀取 `DAWHO_fix.sitemap` 判斷活動，細部活動/額度規則參考 D.006 `DepositCommonUtil.GetExchangeFixLimitAmt`。
- D.003 幣別資料透過 CommonUtil.GetCENCurr 取得；其底層 CommonFunc.GetCENCurrFunc 先查 Redis Key=`J_CURR`，無資料再查 `[MMA].[dbo].[J_CURR]` 並回寫 Redis。

## 待確認事項

- 若新系統 API 要直接落地到現有前端或中台 DTO，需另行建立 compatibility mapping；不得污染 canonical field。
