# Common 類欄位命名知識庫

## CommonUtil - GetCENCurr / CommonFunc - GetCENCurrFunc

- `currEName`
  - PRD 語意：幣別代碼/英文幣別名稱，例如 TWD、USD。
  - Evidence：`CommonFunc.GetCENCurrFunc` response；來源 J_CURR.CURRENAME。
  - Alias/注意：只作 CommonFunc 內部方法與來源欄位名稱；CommonUtil 對外 API 與業務/共用業務 API 統一使用 `currencyCode`。

- `currCName`
  - PRD 語意：幣別中文名稱/中文描述，例如 新臺幣、美元。
  - Evidence：`CommonFunc.GetCENCurrFunc` response；來源 J_CURR.CURRCNAME。
  - Alias/注意：只作 CommonFunc 內部方法與來源欄位名稱；CommonUtil 對外 API 與業務/共用業務 API 統一使用 `currencyName`。

- `currId`
  - PRD 語意：幣別資料識別碼。
  - Evidence：`CommonFunc.GetCENCurrFunc` response；來源 J_CURR.CURRID。
  - Alias/注意：只作 CommonFunc 內部方法與來源欄位名稱；CommonUtil 對外 API 使用 `currencyId`。

- `cenCurrList`
  - PRD 語意：幣別資料清單。
  - Evidence：`CommonFunc.GetCENCurrFunc` response。
  - Alias/注意：只作 CommonFunc 內部方法與來源欄位名稱；CommonUtil 對外 API 使用 `currencyList`。

- `flag008`
  - PRD 語意：account008 註記。
  - Evidence：`CommonFunc.GetCENCurrFunc` response；來源 J_CURR.FLAG008。
  - Alias/注意：只作 CommonFunc 內部方法與來源欄位名稱；CommonUtil 對外 API 使用 `account008StatusCode`。

- `currencyId`
  - PRD 語意：幣別資料識別碼。
  - Evidence：`CommonUtil.GetCENCurr` request/response；來源 CommonFunc.GetCENCurrFunc.currId / J_CURR.CURRID。
  - Decision：CommonUtil 對外 API 使用 `currencyId`，不要暴露內部 `currId`。

- `currencyCode`
  - PRD 語意：對外 API 中使用的幣別英文代碼，例如 TWD、USD。
  - Evidence：`CommonUtil.GetCENCurr`、`Deposit.GetFixedDepositDetail`、`Exchange.GetTransDebitAccount`、`CommonUtil.GetCommonCurrency`、`CommonUtil.EditCommonCurrency`、`CommonFunc.GetTransDebitCurrency`。
  - Decision：CommonUtil 對外 API、跨業務 API 與共用業務 API 的 request/response 統一使用 `currencyCode`；來源欄位 `currEName` / `CURRENAME` 只放在備註或 CommonFunc 內部方法。

- `currencyName`
  - PRD 語意：對外 API 中使用的幣別中文名稱。
  - Evidence：`CommonUtil.GetCENCurr`、`Exchange.GetTransDebitAccount` response、`CommonFunc.GetTransDebitCurrency` response、`CommonUtil.GetCurrencyRateDetail` response。
  - Decision：CommonUtil 對外 API、業務/共用業務 response 統一使用 `currencyName`；來源欄位 `currCName` / `CURRCNAME` 只放在備註或 CommonFunc 內部方法。

- `currencyList`
  - PRD 語意：幣別資料清單。
  - Evidence：`CommonUtil.GetCENCurr` response；來源 CommonFunc.GetCENCurrFunc.cenCurrList。
  - Decision：CommonUtil 對外 API 使用 `currencyList`，不要暴露內部 `cenCurrList`。

- `account008StatusCode`
  - PRD 語意：account008 狀態代碼。
  - Evidence：`CommonUtil.GetCENCurr` response；來源 CommonFunc.GetCENCurrFunc.flag008 / J_CURR.FLAG008。
  - Decision：CommonUtil 對外 API 使用 `account008StatusCode`，不要暴露內部 `flag008`；值域 1 / 2 的實際業務含義待確認時，在 API Detail 備註標 TODO。

- `currencyCodeArray`
  - PRD 語意：幣別代碼排序清單。
  - Evidence：`CommonUtil.EditCommonCurrency` request、`CommonFunc.EditCommonCurrencyFunc` request。
  - Decision：取代舊 `currENameArray`；寫入既有 DB JSON 時仍可映射為來源欄位 `CURRENAME`。

## 命名分層決策

| 層級 | API / Method | 對外欄位命名 | Source / DB 說明 |
| --- | --- | --- | --- |
| 內部幣別字典方法 | `CommonFunc.GetCENCurrFunc` | 保留 `currEName` / `currCName` / `currId` / `cenCurrList` / `flag008` | 直接貼合 `J_CURR.CURRENAME` / `J_CURR.CURRCNAME` / `J_CURR.CURRID` / `J_CURR.FLAG008`。 |
| 對外幣別字典 API | `CommonUtil.GetCENCurr` | 使用 `currencyCode` / `currencyName` / `currencyId` / `currencyList` / `account008StatusCode` | 備註中說明映射至 CommonFunc 與 J_CURR 來源欄位。 |
| 共用業務接口 | `CommonUtil.GetCommonCurrency`、`CommonUtil.EditCommonCurrency`、`CommonUtil.GetCurrencyRateDetail` | 使用 `currencyCode` / `currencyName` / `currencyCodeArray` | 可在備註中說明來源映射至 `CURRENAME` / `CURRCNAME`。 |
| 共用業務方法 | `ExchangeCommonFunc.GetCommonCurrency`、`CommonFunc.EditCommonCurrencyFunc`、`CommonFunc.GetTransDebitCurrency` | 使用 `currencyCode` / `currencyName` / `currencyCodeArray` | DB 儲存結構若仍為 `CURRENAME`，只作來源/落庫說明；常用幣別優先取 Redis，未命中再回源 `CommonCurrencyList`。 |
| 業務 API | Deposit / Exchange / Transfer 等功能 API | 使用 `currencyCode` / `currencyName` | 不使用 `currEName` / `currCName` 作新系統欄位。 |

## Alias / 遷移紀錄

| 舊欄位 | 新 canonical field | 模組/API | 決策 |
| --- | --- | --- | --- |
| `currEName` | `currencyCode` | CommonUtil 對外 API / 業務 / 共用業務 API | `currEName` 僅作 CommonFunc 內部與來源欄位；對外欄位統一使用 `currencyCode`。 |
| `currCName` | `currencyName` | CommonUtil 對外 API / 業務 / 共用業務 API | `currCName` 僅作 CommonFunc 內部與來源欄位；對外欄位統一使用 `currencyName`。 |
| `currId` | `currencyId` | CommonUtil 對外 API | `currId` 僅作 CommonFunc 內部與來源欄位；對外欄位使用 `currencyId`。 |
| `cenCurrList` | `currencyList` | CommonUtil 對外 API | `cenCurrList` 僅作 CommonFunc 內部與來源欄位；對外欄位使用 `currencyList`。 |
| `flag008` | `account008StatusCode` | CommonUtil 對外 API | `flag008` 僅作 CommonFunc 內部與來源欄位；對外欄位使用 `account008StatusCode`。 |
| `currENameArray` | `currencyCodeArray` | CommonUtil/CommonFunc 常用幣別排序 | Request 使用幣別代碼清單語意；落庫時可映射為 `CURRENAME`。 |

## CommonFunc - GetAccountInfo

`GetAccountInfo` 是帳戶總覽共用方法，對外 response 欄位採新系統可讀命名；IRIS/DB 原始欄位僅放在 Source Description / 備註。

| 舊欄位 | 新 canonical field | PRD/業務語意 | 來源說明 |
| --- | --- | --- | --- |
| `accList` | `accountList` | 帳號清單 | EC0001 body 逐筆組成 |
| `acctValue` | `accountNumber` | 帳號；外幣時為外幣主帳號 | TWD: `EC0001.EnqEAcctId`; foreign: `EC0001.EnqEMainAcctId` |
| `acctCName` | `accountName` | 帳號名稱 | `EC0001.EnqEAcctTitle1` / DB account name |
| `acctText` | `accountDisplayName` | 帳號顯示名稱 | 預設同 `accountName` |
| `subAcct` | `subAccountNumber` | 外幣子帳號 | foreign: `EC0001.EnqEAcctId`; TWD/none: empty |
| `curr` | `currencyCode` | 幣別代碼 | `EC0001.EnqEAcctCurr` |
| `curText` | `currencyName` | 幣別中文名稱 | `J_CURR.CURRCNAME` |
| `availBalance` | `workingBalance` | 帳戶餘額 | `EC0001.EnqEAcctWkBal` |
| `acctCategory` | `accountCategoryCode` | 帳戶種類代碼 | `EC0001.EnqEAcctCatg` |
| `digitalFg` | `digitalAccountFlag` | 數位帳號註記 | `EC0001.EnqEDigitalFg` |
| `foreignStop` | `foreignExchangeStopFlag` | 暫停外匯交易註記 | `EC0001.EnqEMemo15` |
| `foreignAlert` | `foreignExchangeAlertFlag` | 外匯疑似化整為零註記 | `EC0001.EnqEMemo14` |
| `enqECustSms1` | `mobilePhone` | 聯絡電話 | `EC0001.EnqECustSms1` |
| `enqECustEmail` | `email` | 電子郵件 | `EC0001.EnqECustEmail` |
| `genQuotaMark` | `generalQuotaFlag` | 綜合額度註記 | CommonFunc 組裝 |
| `genAcctMark` | `generalAccountFlag` | 綜存戶註記 | `EC0001.EnqELinkAioAc` / account type rule |
| `acctStat` | `inactiveAccountFlag` | 久未往來戶註記 | `EC0001.EnqEInactiveFlag` |
| `nonTrxferFlg` | `nonTransferFlag` | 禁止轉出註記 | `ACCT_NOTRANSFER` + EC0001 status rule |
| `goalbr` | `performanceBranchCode` | 績效行代碼 | `EC0001.EnqEAcctKpiBr` |
| `accType` | `accountTypeCode` | 帳號類型代碼 | `GetAccTypebyCategory()` |
| `fixBalance` | `timeDepositBalance` | AIO 定存單金額 | `EC0001.EnqEAioTdBalTot` |
| `maxAvail` | `availableAmount` | 最高可使用額 | `EC0001.EnqEAcctAvlAmt` |
| `blkAmt` | `lockedAmount` | 只扣金額 | `EC0001.EnqEAcctBlkAmt` |
| `outStdLmt` | `overdraftLimitAmount` | 透支額度 | `EC0001.EnqEAcctLmAmt` |
| `allowPledge` | `pledgeAllowedFlag` | 質借註記 | `EC0001.EnqEAllowPledge` |
| `ipIGFg` | `smartPiggyBankFlag` | 智能撲滿註記 | `EC0001.EnqEIpigFg` |
| `pockeyFg` | `pocketMoneyFlag` | 私房錢綁定註記 | `EC0001.EnqEPockeyFg` |
| `evtFg` | `debitStopFlag` | 止扣註記 | `EC0001.EnqEEvtType` |
| `eQuotaTotD` | `nonAgreedDailyLimitAmount` | 非約轉日限額 | `EC0001.EnqEQuotaTotD` |
| `applyCCYProject` | `foreignCurrencyProjectFlag` | 外幣階梯活期存款專案註記 | `EC0001.EnqEProject` |
| `applyCCYProjectMDATE` | `foreignCurrencyProjectMaturityDate` | 外幣階梯活期存款專案到期日 | `EC0001.EnqEProjectMdate` |
| `applyCCYStairateFG` | `foreignCurrencyStairRateFlag` | 外幣階梯活期存款階梯存款註記 | `EC0001.EnqEStairateFg` |
| `isOBUCustome` | `isObuCustomer` | 是否 OBU 身分 | 修正舊欄位拼字 |
