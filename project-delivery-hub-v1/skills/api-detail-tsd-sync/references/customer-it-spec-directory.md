# Customer IT SPEC Directory

Root:

`D:\Devs\<PROJECT_DOCS>\branches\01系統分析\1-8客戶提供資料\06 IT API Doc`

Use this folder as the customer-provided IT SPEC source during 既有专案 demand tightening. It complements PRD, TSD, and API Detail; it is especially useful for backend route/source, host or third-party field naming, action/status codes, and notes/terms source confirmation.

## Structure Summary

| Folder | Role | Files | Notes |
|---|---:|---:|---|
| Root files | Common mapping / SSO references | 8 | Includes `SSO_Expose_API_*`, `TX_MAPPING.xlsx`, `T24_CATEGORY.xlsx`, `交易帳號category_0505(最新版).xlsx`, and interest-calculation reference. |
| `APIDoc 參考 20251231` | Historical reference pack | 79 | Use only as fallback or comparison source when current domain folder lacks an exact function-code match. |
| `B 登入前` | Login-before functions | 9 | Current B/C login-related IT SPEC xlsx files. |
| `C 登入後.首頁` | Login-after home | 0 | Empty currently. |
| `D 臺外幣活定存` | Deposit / fixed-deposit | 11 | Covers D.001, D.002, D.003, D.004, D.006, D.007, D.008, D.009 families. |
| `E 匯利率` | Exchange / rates | 7 | Covers E.001 through E.007. |
| `F 轉帳提款` | Transfer / withdrawal | 9 | Has one `archive` subfolder. |
| `G 金融卡` | Debit card | 0 | Empty currently. |
| `H 信用卡` | Credit card | 0 | Empty currently. |
| `I 投資` | Investment | 34 | Has subfolders `基金`, `證券`, `債券`, `海外股票`, `ibrain`. |
| `J 保險` | Insurance | 3 | Covers J.001, J.003, J.003.001. |
| `K 貸款` | Loan | 2 | Covers K.007, K.015. |
| `L 繳費` | Payment | 9 | Covers L.001, L.001.001, L.002, L.003, L.004, L.005, L.005.001, L.006, L.007. |
| `M 客群經營` | Customer operation | 8 | Has M.001 and M.006 subfolders; includes xlsx/docx/pdf. |
| `N 個人化設定` | Personal settings | 10 | Covers N.001, N.001.001, N.001.002, N.005, N.006, N.008, N.009, N.010. |
| `O 共用` | Common samples / shared API docs | 3 | Has `TSD Sample` subfolder. |

Current total file types under root: 168 `.xlsx`, 15 `.docx`, 3 `.pdf`, 2 `.png`, 2 `.pptx`, 2 `.rar`.

## Lookup Rules

1. Derive the business folder from the function-code prefix:
   - `B.*` -> `B 登入前`
   - `C.*` -> `C 登入後.首頁`
   - `D.*` -> `D 臺外幣活定存`
   - `E.*` -> `E 匯利率`
   - `F.*` -> `F 轉帳提款`
   - `G.*` -> `G 金融卡`
   - `H.*` -> `H 信用卡`
   - `I.*` -> `I 投資`
   - `J.*` -> `J 保險`
   - `K.*` -> `K 貸款`
   - `L.*` -> `L 繳費`
   - `M.*` -> `M 客群經營`
   - `N.*` -> `N 個人化設定`
   - `O.*` or common references -> `O 共用` plus root files
2. Search the current business folder first, including its subfolders.
3. Match exact function-code tokens in filenames. `L.005` must not accidentally match only `L.005.001` unless both codes are in scope.
4. Prefer `.xlsx` IT SPEC files for API/backend contract details. Use `.docx`, `.pdf`, `.pptx`, `.png`, and archives as secondary evidence or context.
5. Prefer the newest version/date in the filename, then latest modified time.
6. Search root files for cross-cutting material such as SSO, transaction mapping, T24 category, account category, and formulas.
7. Search `APIDoc 參考 20251231` only after current-domain search fails or when checking historical behavior.

## Payment Folder Snapshot

`L 繳費` currently contains:

- `L.001_DAWHO  IT SPEC_繳費_繳費總覽_吳君儀_v1.1.xlsx`
- `L.001.001_DAWHO  IT SPEC_繳費_繳費紀錄查詢 _吳君儀_v1.1.xlsx`
- `L.002_DAWHO  IT SPEC_繳費_常用帳單設定_吳君儀_v1.1.xlsx`
- `L.003_DAWHO  IT SPEC_繳費_自動扣繳申請_吳君儀_v1.1.xlsx`
- `L.004_DAWHO  IT SPEC_繳費_他行信用卡費-本人_吳君儀_v1.1.xlsx`
- `L.005_DAWHO  IT SPEC_繳費_永豐信用卡費-本人_吳君儀_v1.1_new.xlsx`
- `L.005.001_DAWHO  IT SPEC_永豐信用卡費-他人_吳君儀_v1.1_new.xlsx`
- `L.006_DAWHO  IT SPEC_繳費_水費 _吳君儀_v1.2.xlsx`
- `L.007_DAWHO  IT SPEC_繳費_電信費 _吳君儀_v1.2.xlsx`
