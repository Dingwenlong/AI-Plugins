# Payment Field Knowledge Base

## billClosingDate

- PRD meaning: 帳單結帳日，卡費帳單結帳日期，顯示格式 `YYYY/MM/DD`。
- Canonical API field: `billClosingDate`
- Aliases / legacy wording: 帳單結帳日
- Category: Payment
- Evidence: L.005 永豐卡費本人 `GetCreditCardPaymentInit` response; customer IT SPEC v1.1.
- Source decision: `RecentBill.STMTDATE`; TITA includes `ID`, `BillDateYYYYMM`, `FunctionName=Null`.
- Notes: Do not reuse `paymentDueDate`; `paymentDueDate` is 繳款截止日.

## autoDebitFlag

- PRD meaning: 是否已設定自動扣繳；若已設定，畫面需提示「您已設定自動扣繳，請再次確認是否仍要繳費」。
- Canonical API field: `autoDebitFlag`
- Aliases / legacy wording: 自動扣繳提示, 已設定自動扣繳
- Category: Payment
- Evidence: L.005 永豐卡費本人 `GetCreditCardPaymentInit` response; customer IT SPEC v1.1.
- Source decision: `getDDFlag.DDFlag`; `DDFlag=Y` means show the auto-debit reminder.
- Notes: Use `Y/N`; frontend owns the fixed PRD display message unless a later PRD requires backend-returned wording.

## L.005 Card Payment Field Decisions

- 扣款帳號名稱: `debitAccountName`; legacy alias `acctCName`.
- 扣款帳號: `debitAccountNo`; legacy aliases `acctValue`, `debitAcct`.
- 可用餘額: `availableBalance`; legacy alias `availBalance`.
- 本期應繳總額: `currentDueAmount`; legacy alias `currbal`.
- 本期累計已繳: `currentPaidAmount`; legacy alias `lpaysum`.
- 本期最低應繳: `minimumDueAmount`; legacy alias `dueamt`.
- 繳款截止日: `paymentDueDate`; legacy alias `duedate`.
- 轉入帳號: `payeeAccountNo`; legacy aliases `payeeAcct`, `maskedAcct`.
- 轉入帳號長度: `payeeAccountLength`; legacy aliases `payeeAcctLen`, `maskedLength`.
- 繳費金額: `paymentAmount`; legacy alias `transAmt`.
- 驗證類型: `verificationType`; legacy alias `verifyType`.
- 資金用途: `transferPurpose`; legacy alias `purpose`.
- 卡別文字: `cardAccountText`; legacy alias `cardAcctText`.
- 轉入帳號類型: `payeeAccountType`; legacy alias `payeeAcctType`.
- OTP 起始時間: `otpStartTime`; legacy alias `optTimeStart`.
- OTP 有效秒數: `otpTimeoutSeconds`; legacy alias `otpTimeOut`.
- 是否可交易: `canTradeFlag`; legacy alias `transferRltTo`.
- 交易狀態代碼: `transactionStatusCode`; legacy alias `rspCode`.
- 交易訊息: `transactionMessage`; legacy alias `rspMsg`.
- 交易序號: `transactionSeqNo`; legacy alias `mfSeq`.
- 繳費金額顯示文字: `paymentAmountDisplay`.
- 交易時間: `transactionTime`; legacy alias `cardPaymentTime`.
- Removed as unused for L.005 freeze: `transferRltToTo`, `memoUrl`, `header`, `message`, `fee`, `bankBal`, `transferRlt`.

## L.005 / L.005.001 Sinopac Card Payment Field Decisions

- 繳費卡號: `payeeCardNo`; legacy aliases `payeeAccountNo`, `PayeeAcct`.
- 繳費卡號長度: `payeeCardNoLength`; legacy alias `payeeAccountLength`.
- 驗證方式: `verificationMethod`; legacy alias `verificationType`.
- 繳費卡號來源: `payeeCardSourceType`; values `RECENT`, `COMMON`, `AGREED`, `MANUAL`; replaces legacy transfer-style `cardAccountText` / `payeeAccountType`.
- Do not expose `transferPurpose`, `cardAccountText`, `payeeAccountType`, or `otpStartTime` as L.005/L.005.001 request fields. They are backend/session-derived in the frozen new-system contract.

## L.005.001 Other Sinopac Card Payment Field Decisions

- 近期卡號列表: `recentPayeeCardList`.
- 常用卡號列表: `commonPayeeCardList`.
- 約定卡號列表: `agreedPayeeCardList`.
- 卡號暱稱: `payeeCardNickname`; legacy alias `cardNickname`.
- 繳費卡號: `payeeCardNo`; used in Init lists and Confirm/Submit requests; frontend masks it for display. Legacy display aliases `payeeCardNoDisplay`, `payeeCardNoMask`, `maskedAcct`.
- 最近繳費日期時間: `lastPaymentDateTime`; legacy alias `paymentDateTime`.
- 防詐提醒文字: `antiFraudNotice`.
- 是否可使用非約定轉帳: `nonAgreedTransferAvailableFlag`.
- 是否具備簡訊 OTP 功能: `smsOtpAvailableFlag`.
- 行動裝置是否已綁定: `deviceBoundFlag`; legacy alias `deviceBindingFlag`.
- 網銀會員身分代碼: `onlineBankingMemberStatusCode`; legacy alias `memberStatusCode`.
- Root/JB/USB Debugging / 裝置風險阻擋旗標: `deviceRiskBlockFlag`; legacy alias `crackedDeviceBlockFlag`.
- 單筆繳費限額: `singlePaymentLimitAmount`; legacy alias `singleTransactionLimitAmount`; PRD figure mentions 5 萬 while notes contain account/agreement-specific limits, so workbook keeps this as TODO until rule source is confirmed.
- 留言給自己: `customerMemo`.
- 是否約定繳費卡號: `agreedPayeeCardFlag`; legacy alias `agreedCardFlag`.
- 是否允許繳費: `paymentAllowedFlag`; legacy alias `canTradeFlag`.
- 他人卡費檢核代碼: `paymentValidationCode`; legacy alias `paymentCheckCode`.
- 他人卡費檢核訊息: do not return a backend message field for L.005.001 Confirm; frontend maps `paymentValidationCode` to fixed popup copy. Legacy aliases `paymentValidationMessage`, `paymentCheckMessage`.
- 是否需使用者二次確認: `userConfirmationRequiredFlag`; legacy alias `requireUserConfirmFlag`.
- 繳費對象卡號顯示: do not use a separate `payeeCardNoDisplay` field for L.005.001 Init/Submit; frontend masks `payeeCardNo`.
- 扣款帳號顯示: `debitAccountNoDisplay`; legacy alias `debitAccountDisplay`.
- 扣款帳號餘額顯示: `debitAccountBalanceDisplay`; legacy alias `accountBalanceDisplay`.

## L.005.001 IT SPEC Tightening Decisions

- `nonAgreedTransferAvailableFlag`: source `ws_card_payment.ashx` `NoPact` flag; if `NoPact=N` or `SMS=N`, frontend disables credit-card input.
- `smsOtpAvailableFlag`: source `ws_card_payment.ashx` `SMS` flag.
- `deviceBoundFlag`: source `binding_check.ashx` / `DAWHO.dbo.MB_DEVICE`.
- `onlineBankingMemberStatusCode`: source `MMA.dbo.USER_STATUS.CPRTCD`; member 6/member 8 show the member-status mismatch popup.
- Common/agreed card list query chain: `ws_AcctSet_Overview.ashx` -> `ws_NonPredesignated_Accountlist.ashx` -> `ws_dawhopayeeacct.ashx`; `DataType=2` for agreed card, `DataType=3` for common card.
- Limit tightening: agreed card single-transaction limit is fixed at 2,000,000; non-agreed limits depend on maintainable backend limit source, legacy `mma_limitamt.sitemap`, `TWDUPNOPACT`, and EC0010 remaining quota (`NREG.OTP` / `REG`). Keep workbook TODO until the new backend-maintainable source and account/member mapping are confirmed.

## L.005 / L.005.001 API Naming Decisions

- 本人永豐卡費初始資料 API: `OwnSinopacCreditCardPaymentInit`; legacy aliases `GetOwnSinopacCreditCardPaymentInit`, `GetCreditCardPaymentInit`, `CreditCardPaymentInit`.
- 本人永豐卡費確認 API: `OwnSinopacCreditCardPaymentConfirm`; legacy aliases `ConfirmOwnSinopacCreditCardPayment`, `ConfirmCreditCardPayment`, `CreditCardPaymentConfirm`.
- 本人永豐卡費送出 API: `OwnSinopacCreditCardPaymentSubmit`; legacy aliases `SubmitOwnSinopacCreditCardPayment`, `SubmitCreditCardPayment`, `CreditCardPaymentResult`.
- 本人永豐卡費注意事項 API: `OwnSinopacCreditCardPaymentNotice`; legacy/source aliases `GetOwnSinopacCreditCardPaymentNotice`, `Login.GetPostLogin`.
- 他人永豐卡費初始資料 API: `OtherSinopacCreditCardPaymentInit`; legacy aliases `GetOtherSinopacCreditCardPaymentInit`, `GetCreditCardPaymentInit`, `CreditCardPaymentInit`.
- 他人永豐卡費確認 API: `OtherSinopacCreditCardPaymentConfirm`; legacy aliases `ConfirmOtherSinopacCreditCardPayment`, `ConfirmCreditCardPayment`, `CreditCardPaymentConfirm`.
- 他人永豐卡費送出 API: `OtherSinopacCreditCardPaymentSubmit`; legacy aliases `SubmitOtherSinopacCreditCardPayment`, `SubmitCreditCardPayment`, `CreditCardPaymentResult`.
- 他人永豐卡費注意事項 API: `OtherSinopacCreditCardPaymentNotice`; legacy/source aliases `GetOtherSinopacCreditCardPaymentNotice`, `Login.GetPostLogin`.
- Decision: L.005/L.005.001 should not share the generic L.004 `CreditCardPayment` API names. Split Own/Other Sinopac card-payment APIs and place stage words (`Init`, `Confirm`, `Submit`) at the end of the method name. Payment feature API List should not expose `Login` category for card-payment notices. Keep `Login.GetPostLogin` only as a legacy backend/content source note when implementation still reuses it.

## L.005 Own Sinopac Card Payment Result Decisions

- 繳費卡號顯示: do not return `payeeCardNoDisplay` from `OwnSinopacCreditCardPaymentSubmit`; frontend masks the request `payeeCardNo`.
- 扣款帳號顯示: `debitAccountNoDisplay`; returned by `OwnSinopacCreditCardPaymentSubmit` as the complete display text.
- 扣款帳號餘額顯示: `debitAccountBalanceDisplay`; after Submit succeeds, backend queries `ws_dawhodebitacct.ashx` / `EC0001` for the latest available balance and returns the display text.

## L.005.001 Other Sinopac Card Payment Result Decisions

- 繳費卡號顯示: do not return `payeeCardNoDisplay` from `OtherSinopacCreditCardPaymentSubmit`; frontend masks the request `payeeCardNo`.
- 扣款帳號顯示: `debitAccountNoDisplay`; returned by `OtherSinopacCreditCardPaymentSubmit` as the complete display text.
- 扣款帳號餘額顯示: `debitAccountBalanceDisplay`; after Submit succeeds, backend queries `ws_dawhodebitacct.ashx` / `EC0001` for the latest available balance and returns the display text.
- 留言給自己: `customerMemo`; returned from the current Submit request, blank if not provided.

## L.005.001 Other Sinopac Card Payment Confirm Decisions

- Init card-list display: return `payeeCardNo` and let frontend mask it for all recent/common/agreed card lists.
- Confirm popup copy: frontend owns fixed popup wording; backend returns `paymentValidationCode` only.
- `paymentValidationCode` values:
  - `NON_SINOPAC_CARD`: payee card is not a Sinopac credit card.
  - `NON_AGREED_TRANSFER_UNAVAILABLE`: NoPact/SMS qualification is unavailable.
  - `DEVICE_RISK`: Root/JB/USB Debugging or equivalent device-risk check failed.
  - `DEVICE_NOT_BOUND`: mobile device is not bound.
  - `RESET_WITHIN_24H`: online-banking password/OTP reset happened within 24 hours.
  - `DEBIT_CARD`: debit card is not allowed as payee card.
  - `GIFT_CARD`: gift card is not allowed as payee card.
  - `DUPLICATE_24H`: same payee card within 24 hours; frontend shows second-confirmation flow.
  - `LIMIT_EXCEEDED`: payment amount exceeds applicable limit.

## L.004 Other-Bank Card Payment API Mapping

- PRD meaning: 他行信用卡費；選銀行代碼、輸入信用卡號/銷帳編號與繳費金額，確認手續費後送出繳費。
- TSD legacy API names: `CreditCardPaymentInit`, `CreditCardPaymentConfirm`, `CreditCardPaymentResult`.
- Canonical API names: `GetCreditCardPaymentInit`, `ConfirmCreditCardPayment`, `SubmitCreditCardPayment`.
- Supporting Payment APIs from TSD: `GetBarcode`, `GetPayeeAccount`.
- Notice/content source: TSD lists `Login.GetPostLogin`; Payment workbook should expose `GetCreditCardPaymentNotice` only after the TSD API list is corrected to the Payment wrapper/API naming decision above.
- Evidence: L.004 PRD `他行信用卡費`; TSD.L.004 API清單; `NEWDA_API_DETAIL_Payment_20260203_L005_sync.xlsx` API sheets.

## L.004 Other-Bank Card Payment Field Decisions

- 常用他行信用卡費帳單列表: `otherBankCreditCardBillList`; source alias `GetCommonBillList`.
- 帳單暱稱: `billNickname`.
- 銀行代碼: `paymentBankCode` in business APIs; `bankCode` inside bank-list items.
- 銀行名稱: `paymentBankName` in business APIs; `bankName` inside bank-list items.
- 繳費項目 Id: `paymentBillId`; IT SPEC source `bill_id`, used by U100/U103/C101/T102.
- 信用卡號/銷帳編號: `paymentTargetNo`; result display field `paymentTargetNoDisplay`.
- 可繳他行信用卡銀行清單: `otherBankList`.
- 繳費對象輸入提示文字: `targetInputHint`; PRD evidence from 附件一各銀行提示文字.
- 同意條款內容: `paymentTermsContent`; request confirmation flag `termsAgreedFlag`.
- 單筆繳費限額: `maxPaymentAmount`; PRD L.004 input-page validation says 10 萬.
- 手續費提示文字: `feeNoticeText`.
- 手續費金額/幣別: `paymentFeeAmount`, `paymentFeeCurrency`; frontend formats display text.
- 財金 Session ID: `fiscSessionId`; IT SPEC C101 response `fisc_session_id`, T102 request `fisc_session_id`.
- 繳費代號: `paymentNo`.
- 手續費顯示文字: `paymentFeeAmountDisplay`.
- 永豐 Session ID: `sinopacSessionId`; IT SPEC T102 response `session_id`.
- 是否已設定為常用帳單: `commonBillRegisteredFlag`; controls whether result page shows `加入常用帳單`.
- Decision: L.004 should not reuse L.005/L.005.001 card-number semantics such as `payeeCardNoMask` when the PRD calls the field `信用卡號/銷帳編號`; use `paymentTargetNo` instead.
- IT SPEC mapping: U100 `/billhubintra/v1/user/billsetting` gives `otherbank_card_info.bill_id/bank_name/prompt_text`; U103 `/billhubintra/v1/user/commonqry` gives common bills `comm_name/bill_name/comm_info.notice_info.notice_no`; C101 `/billhubintra/v1/common/check` gives `hc_info.fee_id` and `fisc_session_id`; T102 `/billhubintra/v1/common/pay` returns `status/stan/session_id/txn_info.notice_no/txn_info.txn_amount`.
- GetBarcode response mapping: use `cardCustomerId`, `barcodeResultCode`, `barcodeResultMessage`, `convenienceStoreBarcodeNo`, `barcodePaymentAmount`, `barcodeImageBase64`; legacy/source aliases are `pid`, `reCode`, `reDesc`, `rebarcode`, `reAmt`, `barcode`.
- GetPayeeAccount response mapping: use `otherCardFlag`, `payeeAccountQueryStatusCode`, `payeeAccountQueryMessage`, `ownSinopacCardAvailableFlag`, `agreedTransferAccountAvailableFlag`, `nonAgreedTransferAccountAvailableFlag`, and `payeeAccountList`.
- GetPayeeAccount list item fields: use `payeeAccountText`, `payeeAccountNo`, `bankCode`, `currentPaidAmount`, `currentDueAmount`, `minimumDueAmount`, `payeeAccountTypeCode`, `agreementMethodDisplayText`; legacy/source aliases are `cardText`, `cardValue`, `bankId`, `PayedAmt` / `payedAmt`, `payAll`, `payMin`, `dataType`, `displayText`.
- Decision: GetBarcode / GetPayeeAccount may keep old downstream names only in Source Description or business-logic notes; API 對外 response fields should not expose `re*`, `pid`, `OtherCard`, `subInfo`, or ambiguous `*Len` legacy names.

## L.003 Auto Debit Field Decisions

- API naming decision:
  - 取得自動扣繳扣款工具: `GetAutoDebitInstruments`; legacy alias `GetCustAcctInfo`.
  - 取得自動扣繳申請項目: `GetAutoDebitBillers`; legacy alias `GetBillType`.
  - 取得自動扣繳設定清單: `GetAutoDebitSettingList`; legacy alias `GetDeductSettingList`.
  - 維護自動扣繳設定: `MaintainAutoDebitSetting`; legacy alias `ChangeDeductSetting`.
- 扣款帳號名稱: `debitAccountName`; legacy alias `AcctCName`; evidence `Payment.GetAutoDebitInstruments`.
- 扣款帳號: `debitAccountNo`; legacy alias `AcctValue`; evidence `Payment.GetAutoDebitInstruments`.
- 可用餘額: `availableBalance`; legacy alias `AvailBalance`; evidence `Payment.GetAutoDebitInstruments`.
- 是否有可用永豐信用卡: `hasCreditCardFlag`; evidence `Payment.GetAutoDebitInstruments`, IT SPEC L.003 可用永豐主卡來源；正式 API Detail 後端來源不暴露舊程式方法或 code-behind 檔名。
- 可扣款信用卡列表: `creditCardList`; only include `CardTypeDesc=主卡`; evidence IT SPEC L.003.
- 卡圖代碼: `cardFaceCode`; legacy/source alias `CardFace`.
- 信用卡名稱: `cardName`; legacy/source alias `Name`.
- 信用卡號原值: `cardNo`; legacy/source alias `CARD_NO`; return the raw value needed by the contract and let frontend mask it.
- 卡別名稱: `cardTypeName`; source alias `CardTypeDesc`.
- 自動扣繳設定清單: `autoDebitSettingList`; legacy aliases `deductSettingList`, `withholdingList`.
- 代扣繳ID: `autoPayId`; legacy/backend alias `autopay_id`; IT SPEC shows this is a biller/autopay service ID, not a unique per-setting row ID.
- 事業單位ID: `companyId`; legacy/backend alias `company_Id`.
- 帳單類型代碼: `billTypeCode`; legacy alias `billType`; values distinguish water fee and telecom fee before UI rendering.
- 代扣繳名稱/事業單位名稱: `billerName`; workbook alias `withholdingName`, legacy/backend alias `company_name`.
- 帳單識別欄位名稱: `billIdentifierFieldName`; derived from `billTypeCode`; values such as `水號` and `用戶號碼`.
- 帳單識別號碼: `billIdentifierNo`; legacy aliases `waterNo`, `subscriberNo`, workbook alias `waterId`; backend alias `user_no`; frontend chooses display label from `billIdentifierFieldName` and owns masking.
- 營運處代號: `branchCode`; legacy/backend alias `branch`.
- 扣繳方式代碼: `debitMethodCode`; legacy alias `debitMethod`; backend alias `pay_way`; values distinguish Sinopac account and Sinopac credit card.
- 扣款帳號/卡號原值: `debitInstrumentNo`; workbook alias `withholdingNameAccount`, legacy/backend alias `creditcard_or_acct`.
- 扣繳狀態代碼: `autoDebitStatusCode`; legacy alias `deductStatusCode`; backend alias `status`.
- 扣繳狀態顯示: `autoDebitStatusName`; legacy alias `deductStatusName`; backend alias `status_name`.
- 申請日期: `applicationDate`; legacy alias `applyDate`; backend alias `apply_date`.
- 聯絡電話: `contactPhone`; workbook alias `tel`, legacy/backend alias `phone`.
- 電子信箱: `email`; legacy/backend alias `email`.
- 查詢筆數: `totalCount`; legacy/backend alias `user_info.count`.
- 維護操作類型代碼: `maintainActionCode`; legacy alias `action`; IT SPEC U109 values `0=新增`, `1=更新`, `2=刪除`.
- 維護結果狀態代碼: `maintainStatusCode`; legacy alias `maintainStatus`; backend alias `status`.
- BillHub 原始回應代碼: `backendReturnCode`; backend alias `return_code`; kept for reconciliation and troubleshooting.
- BillHub 原始回應訊息: `backendReturnDesc`; backend alias `return_desc`; kept for reconciliation and troubleshooting.
- Masking decision: keep `debitAccountNo`, `cardNo`, and `debitInstrumentNo` as complete raw values in the API contract; do not add `*Mask` / `*Display` fields for L.003 unless a later PRD explicitly requires backend-returned display strings.
- Evidence: L.003 PRD 自動扣繳總覽/申請/編輯；TSD API 清單 `GetAutoDebitInstruments` / `GetAutoDebitBillers` / `GetAutoDebitSettingList` / `MaintainAutoDebitSetting`; IT SPEC L.003 U108 `autopayqry` and U109 `autopaymaintain`.
