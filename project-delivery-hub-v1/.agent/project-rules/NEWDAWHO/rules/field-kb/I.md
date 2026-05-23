# I 類欄位命名知識庫

用途：統一 Insurance 類功能的新系統 API 欄位命名。此文件以 PRD 中文業務語意為主軸；舊系統、SP、DB 欄位只能作為 Source/alias，不作 canonical field。

## Insurance - GetMyPolicy / J.003 保險庫存查詢

- `policyTypeFilter`
  - PRD 語意：保險庫存首頁的保單類型篩選，包含全部、投資型、非投資型、產險。
  - Evidence：J.003 PRD「篩選」；`GetMyPolicy` request，值為 `All` / `Life` / `Invest` / `Property`。
  - Alias/注意：舊 workbook 曾使用 `prodType`；J.003 frozen 版已改為 `policyTypeFilter`，`prodType` 僅作遷移 alias。

- `policyList`
  - PRD 語意：我的保單小卡列表，依篩選類型回傳並以保單生效日近到遠排序。
  - Evidence：J.003 PRD「我的保單小卡」；`GetMyPolicy` response。
  - Alias/注意：舊 workbook 曾使用 `insuranceList`；J.003 frozen 版已改為 `policyList`。

- `policyNumber`
  - PRD 語意：保單號碼，API 回傳值可能包含銷售管道註記符號。
  - Evidence：J.003 PRD「保單號碼」；`GetMyPolicy` response。
  - Alias/注意：`policyNo2` 來自 INSAG source，作 Source/alias；J.003 frozen 版對外欄位已改為 `policyNumber`。

- `insuranceCompanyName`
  - PRD 語意：保險公司名稱。
  - Evidence：`GetMyPolicy` response；舊 `companyCode` 範例為「台灣人壽」。
  - Alias/注意：若回傳值是中文名稱，不建議使用 `companyCode`；若未來同時回傳代碼與名稱，代碼另命名 `insuranceCompanyCode`。

- `productName`
  - PRD 語意：商品名稱。
  - Evidence：J.003 PRD「商品名稱」；`GetMyPolicy` response。
  - Alias/注意：`planTitle` 可作保險來源欄位 alias；J.003 frozen 版對外欄位已改為 `productName`。

- `maskedInsuredId`
  - PRD 語意：被保險人身分證字號遮罩。
  - Evidence：`GetMyPolicy` response；來源為 `INSAG.relation_id`。
  - Alias/注意：舊 workbook 曾使用 `relationId`；J.003 frozen 版已改為 `maskedInsuredId`，並明確只回傳遮罩後資料。

- `policyEffectiveDate`
  - PRD 語意：保單生效日，列表排序依此日期由近到遠。
  - Evidence：J.003 PRD「保單生效日」；`GetMyPolicy` response。
  - Alias/注意：`poIssueDate` 可保留為 Source/alias；J.003 frozen 版對外欄位已改為 `policyEffectiveDate`。

- `policyEndDate`
  - PRD 語意：保險期間迄/保單到期日。
  - Evidence：`GetMyPolicy` response；產險來源為 `INSAG_297.Insurdate_End_date`。

- `policyCurrencyName`
  - PRD 語意：保單幣別中文名稱。
  - Evidence：J.003 PRD「幣別顯示邏輯」；`GetMyPolicy` response。
  - Alias/注意：若前端只顯示英文碼，可仍保留中文名稱供轉換/追蹤；英文碼用 `policyCurrencyCode`。

- `policyCurrencyCode`
  - PRD 語意：保單幣別英文代碼，例如 TWD/USD/CNY。
  - Evidence：J.003 PRD「臺幣以 TWD 顯示、美金以 USD 顯示、人民幣以 CNY 顯示」；`GetMyPolicy` response，來源 `CommonFunc.GetCurrEName`。
  - Alias/注意：`currencyCpoEn` 作 Source/alias；J.003 frozen 版對外欄位已改為 `policyCurrencyCode`。

- `paymentPeriod`
  - PRD 語意：主約繳費年期/繳別。
  - Evidence：`GetMyPolicy` response；舊欄位為 `collectionYear`。

- `insuredAmount`
  - PRD 語意：主約保額，若無資料以 `-` 顯示。
  - Evidence：J.003 PRD「主約保額」；`GetMyPolicy` response；舊欄位為 `faceAmt`。

- `paidPremiumAmount`
  - PRD 語意：累計已繳保費，若無資料以 `-` 顯示。
  - Evidence：J.003 PRD「已繳保費」；`GetMyPolicy` response；舊欄位為 `allPremAmtCpo`。

- `nextPremiumAmount`
  - PRD 語意：下次繳費提醒的應繳金額，僅符合繳費提醒條件時使用。
  - Evidence：J.003 PRD「繳費提醒」；`GetMyPolicy` response；舊欄位為 `totalPremCpo`。

- `nextPaymentDate`
  - PRD 語意：下次繳費提醒的應繳日期。
  - Evidence：J.003 PRD「下次繳費 YYYY/MM/DD」；`GetMyPolicy` response；舊欄位為 `paidToDate`。

- `policyType`
  - PRD 語意：保單類型，區分投資型、非投資型、產險，用於篩選與前端卡片類型判斷。
  - Evidence：J.003 PRD「投資型 / 非投資型 / 產險」；`GetMyPolicy` response。
  - Alias/注意：若 request 已改 `policyTypeFilter`，response 不應再共用同名 `prodType`；J.003 frozen 版 response 已改為 `policyType`。
