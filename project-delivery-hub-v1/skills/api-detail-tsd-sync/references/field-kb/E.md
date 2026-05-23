# E 類欄位命名知識庫

## E / Exchange - GetTransDebitAccount

- `currencyCode`
  - PRD 語意：查詢幣別代碼，供帳號清單依幣別過濾。
  - Evidence：`GetTransDebitAccount` request。
  - Alias/注意：舊 Exchange 語境曾用 `debitCurrency`；共用於定存查詢時採中性命名 `currencyCode`。

- `isOBUCustomer`
  - PRD 語意：是否為 OBU 客戶。
  - Evidence：`GetTransDebitAccount` response。
  - Alias/注意：舊 JSON 範例曾用 `OBUFlag`。

- `debitAccountList`
  - PRD 語意：可用轉出/扣款帳號列表。
  - Evidence：`GetTransDebitAccount` response；TSD.D.001.001_D.002.001 API 清單引用此 Exchange API 取得客戶可用轉出帳號。
  - Alias/注意：舊 JSON 範例曾用 `debitAccList`，已調整為欄位表 canonical name `debitAccountList`。

- `accountId`
  - PRD 語意：帳號。
  - Evidence：`GetTransDebitAccount.debitAccountList` response。
  - Alias/注意：舊 JSON 範例曾用 `debitAcctValue` / `dataValue`。

- `accountName`
  - PRD 語意：帳號中文名稱。
  - Evidence：`GetTransDebitAccount.debitAccountList` response。
  - Alias/注意：舊 JSON 範例曾用 `debitAcctText`。

- `availBalance`
  - PRD 語意：帳戶可用餘額，API 回傳 raw decimal。
  - Evidence：`GetTransDebitAccount.debitAccountList` response。

- `currCName`
  - PRD 語意：幣別中文名稱。
  - Evidence：`GetTransDebitAccount.debitAccountList` response；Exchange API 內部來源為 CommonFunc.GetAccountInfo / J_CURR。

- `currEName`
  - PRD 語意：幣別代碼。
  - Evidence：`GetTransDebitAccount.debitAccountList` response；Exchange API 內部來源為 CommonFunc.GetAccountInfo。

## E / Exchange - GetRateList

- `currEName`
  - PRD 語意：匯率表查詢與匯率列表中的幣別英文代碼。
  - Evidence：`GetRateList` request/response，E.001 匯率表。
  - Alias/注意：E.001 目前以 `TWD` 作為以新臺幣試算基礎；外幣代碼用於列表幣別。

- `currCName`
  - PRD 語意：匯率列表中的幣別中文名稱。
  - Evidence：`GetRateList.rateList` response，E.001 匯率表。

- `rateLastUpdateTime`
  - PRD 語意：匯率時間，取報價系統 ETS 最新時間並顯示為 `yyyy/MM/dd HH:mm:ss`。
  - Evidence：E.001 PRD 匯率表說明；`GetRateList` response。

- `billboardSellRate`
  - PRD 語意：牌告匯率；API 回傳 raw decimal，前端格式化顯示至小數點以下第 4 位。
  - Evidence：E.001 PRD 匯率卡；`GetRateList.rateList` response。

- `dawhoSellRate`
  - PRD 語意：大戶匯率；API 回傳 raw decimal，前端格式化顯示至小數點以下第 4 位。
  - Evidence：E.001 PRD 匯率卡；`GetRateList.rateList` response。

- `extraAmount`
  - PRD 語意：以新臺幣 10 萬元試算牌告匯率與大戶匯率差異可多換的外幣金額；API 回傳 raw decimal，前端依幣別格式化顯示。
  - Evidence：E.001 PRD 多換試算公式；`GetRateList.rateList` response。

- `billboardSellRateTrend`
  - PRD 語意：近一個月新臺幣換外幣的牌告匯率走勢縮圖資料；API 回傳 array[decimal] raw value，前端繪製走勢並處理顯示格式。
  - Evidence：E.001 PRD 匯率卡走勢圖；`GetRateList.rateList` response。

- `recentLowestFlag`
  - PRD 語意：近 7 天最低或近 30 天最低標籤；近 30 天最低優先於近 7 天最低；都不符合則回傳空值。
  - Evidence：E.001 PRD 低點標籤規則；`GetRateList.rateList` response。

- `currENameArray`
  - PRD 語意：客戶拖移後的常用幣別排序清單；若客戶未編輯常用幣別，匯率表依 PRD 預設幣別順序排序。
  - Evidence：CommonUtil `EditCommonCurrency` request，E.001 編輯常用幣別。

## E / Exchange - Rate Notice

- `useCurrEName`
  - PRD 語意：到價通知「我要換」幣別英文代碼，對應畫面 A>B 的左側幣別。
  - Evidence：E.002 `GetRateNoticeList` / `AddRateNotice` / `ModifyRateNotice` / `SaveRateNoticeListChange`。
  - Alias/注意：資料表欄位為 `BaseCurrEName`；API 對外採 PRD 語意命名 `useCurrEName`。

- `useCurrCName`
  - PRD 語意：到價通知「我要換」幣別中文名稱。
  - Evidence：E.002 `GetRateNoticeList` / `SaveRateNoticeListChange`。
  - Alias/注意：資料表欄位為 `BaseCurrCName`。

- `targetCurrEName`
  - PRD 語意：到價通知「換成」幣別英文代碼，對應畫面 A>B 的右側幣別。
  - Evidence：E.002 `GetRateNoticeList` / `AddRateNotice` / `ModifyRateNotice` / `DelRateNotice` / `SaveRateNoticeListChange`。
  - Alias/注意：資料表欄位為 `CurrEName`；舊範例曾用 `currEName`。

- `targetCurrCName`
  - PRD 語意：到價通知「換成」幣別中文名稱。
  - Evidence：E.002 `GetRateNoticeList` / `SaveRateNoticeListChange`。
  - Alias/注意：資料表欄位為 `CurrCName`；舊範例曾用 `currCName`。

- `noticeDirection`
  - PRD 語意：到價通知方向；買外幣為新臺幣>外幣，低於指定匯率通知；賣外幣為外幣>新臺幣，高於指定匯率通知。
  - Evidence：E.002 PRD 新增/編輯到價通知；`AddRateNotice` / `ModifyRateNotice` / `SaveRateNoticeListChange` request。
  - Alias/注意：建議 enum `BUY` / `SELL`。可由 `useCurrEName/targetCurrEName` 推導，但 request 明確帶入可降低 highRate/lowRate 誤用。

- `highRate`
  - PRD 語意：賣外幣時「高於 OO 匯率通知我」的指定匯率。
  - Evidence：E.002 `AddRateNotice` / `ModifyRateNotice` / `SaveRateNoticeListChange`。
  - Alias/注意：`noticeDirection=SELL` 時必填；買外幣情境可為 null。

- `lowRate`
  - PRD 語意：買外幣時「低於 OO 匯率通知我」的指定匯率。
  - Evidence：E.002 `AddRateNotice` / `ModifyRateNotice` / `SaveRateNoticeListChange`。
  - Alias/注意：`noticeDirection=BUY` 時必填；賣外幣情境可為 null。

- `timeStamp`
  - PRD 語意：到價通知設定資料更新時間。
  - Evidence：E.002 `GetRateNoticeList` response。
  - Alias/注意：舊 API Detail 曾拼為 `timesTamp`，應修正為 `timeStamp`。

- `compareDay`
  - PRD 語意：已比價通知日期，用於判斷只通知1次/每日1次的日期狀態。
  - Evidence：E.002 `GetRateNoticeList` response；推播/Email 比價批次邏輯。

- `compareDayPush`
  - PRD 語意：已推播通知日期，用於避免同日重複推播。
  - Evidence：E.002 `GetRateNoticeList` response；推播/Email 比價批次邏輯。

- `frequency`
  - PRD 語意：到價通知頻率，只通知1次或每日1次。
  - Evidence：E.002 `AddRateNotice` / `ModifyRateNotice` / `SaveRateNoticeListChange`。

- `flag008`
  - PRD 語意：幣別可用狀態註記，供匯率到價通知前端判斷 FLAG008 = 1 / 2 的幣別顯示或可用狀態。
  - Evidence：E.002 客戶問題單 2026/05/12；CommonUtil `GetCENCurr` / CommonFunc `GetCENCurrFunc` response。
  - Alias/注意：來源為 `J_CURR.FLAG008`；API 對外採小寫 `flag008`。

- `currEName`
  - PRD 語意：查詢指定幣別英文代碼，用於 `GetDawhoRate` 單幣別匯率查詢。
  - Evidence：E.002 客戶問題單 2026/05/12；CommonUtil `GetDawhoRate` / CommonFunc `GetDawhoRateFunc` request。
  - Alias/注意：E.002 新增/編輯到價通知頁傳入畫面選定幣別，只回傳該幣別匯率；未傳時保留共用 API 回傳全部幣別能力。

## E / Exchange - GetRateTrend

- `useCurrEName`
  - PRD 語意：匯率走勢頁「我要用」幣別英文代碼。
  - Evidence：`GetRateTrend` request，E.003 匯率走勢查詢。
  - Alias/注意：買外幣預設為 `TWD`；賣外幣時為客戶選擇之外幣。

- `targetCurrEName`
  - PRD 語意：匯率走勢頁「換成」幣別英文代碼。
  - Evidence：`GetRateTrend` request，E.003 匯率走勢查詢。
  - Alias/注意：買外幣時為客戶選擇之外幣；賣外幣固定為 `TWD`。

- `queryRangeType`
  - PRD 語意：匯率走勢頁資料區間，區分今天、近 7 日、近 30 日、近 3 個月、近 6 個月。
  - Evidence：`GetRateTrend` request，E.003 匯率走勢查詢。
  - Alias/注意：不支援 6 個月以上；`TODAY` 每 15 分鐘一點；其他區間取營業日 15:30 收盤價格。

- `exchangeDirection`
  - PRD 語意：匯率走勢頁籤方向，區分我要買外幣與我要賣外幣。
  - Evidence：`GetRateTrend` request，E.003 匯率走勢查詢。
  - Alias/注意：只支援 TWD <-> 外幣；`BUY_FOREIGN` 取牌告賣匯作為走勢主線；`SELL_FOREIGN` 取牌告買匯作為走勢主線。

- `avgCostRate`
  - PRD 語意：我的成本／平均成本線，依資料區間內換匯交易金額加權計算。
  - Evidence：`GetRateTrend` response；E.003 PRD「我的平均匯率計算公式」。
  - Alias/注意：取代舊命名 `avgExRate` / `avgExchangeRate` / `myCost`，避免同一 PRD 語意多名；IRIS 與智慧收支帳本重複交易保留 IRIS 一筆；E.003 由 `GetRateTrend` 回傳，不需另呼叫 `GetRateMyCost`。

- `avgBillboardRate`
  - PRD 語意：資料區間內該組合幣別的歷史牌告平均匯價。
  - Evidence：`GetRateTrend` response；E.003 PRD「平均匯價線」。
  - Alias/注意：取代舊命名 `avgRate`；對 `rateTrendList.trendRate` 做簡單平均。

- `dataLastUpdateTime`
  - PRD 語意：匯率走勢頁資料時間。
  - Evidence：`GetRateTrend` response；E.003 PRD「資料時間」。
  - Alias/注意：`TODAY` 取最近一筆牌告報價時間；非今天區間取區間最後一個營業日 15:30；假日/非營業時間以前一可用營業日或最近報價點為準。

- `hasAvgCost`
  - PRD 語意：是否有我的成本資料，用於決定是否顯示我的成本線。
  - Evidence：`GetRateTrend` response；E.003 PRD 客戶無換匯紀錄情境。
  - Alias/注意：取代舊命名 `hasMyCost`；前端自行依 false 判斷無紀錄文案。

- `rateTrendList`
  - PRD 語意：匯率走勢圖資料點清單。
  - Evidence：`GetRateTrend` response；E.003 PRD 匯率走勢共同需求。
  - Alias/注意：每筆包含 `pointTime`、`billboardBuyRate`、`billboardSellRate`、`trendRate`、`rateType`；舊 `displayRate` 改為更明確的 `trendRate`。

- `pointTime`
  - PRD 語意：匯率走勢圖單一資料點時間。
  - Evidence：`GetRateTrend.rateTrendList` response；E.003 PRD 日期格式規則。
  - Alias/注意：`TODAY` 為 `HH:mm`；其他區間為 `YYYY/MM/DD`。

- `trendRate`
  - PRD 語意：匯率走勢圖主線匯率。
  - Evidence：`GetRateTrend.rateTrendList` response；E.003 PRD 買/賣匯價顯示規則。
  - Alias/注意：`BUY_FOREIGN` 取牌告賣匯；`SELL_FOREIGN` 取牌告買匯。

- `billboardBuyRate`
  - PRD 語意：走勢資料點的牌告買匯匯率。
  - Evidence：`GetRateTrend.rateTrendList` response；E.003 PRD 買/賣匯價顯示規則。

- `billboardSellRate`
  - PRD 語意：走勢資料點的牌告賣匯匯率。
  - Evidence：`GetRateTrend.rateTrendList` response；E.003 PRD 買/賣匯價顯示規則。

- `rateType`
  - PRD 語意：走勢主線使用的牌告匯率類型。
  - Evidence：`GetRateTrend.rateTrendList` response。
  - Alias/注意：`SELL_RATE` 代表牌告賣匯；`BUY_RATE` 代表牌告買匯。
