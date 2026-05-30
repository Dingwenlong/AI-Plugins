# Common Style Rules

Runtime use: load only after `devGuidelineRulesSelected` includes `common-style`.

- Treat API Spec and `codeHandoff` as the business source of truth.
- Treat V6.2 rules as implementation constraints, not as proof that the current repository is already wired.
- Keep implementation changes in business files only; UnitTest and IntegrationTest source belongs to step 05.
- Prefer existing repository helpers, naming, namespaces, and dependency patterns before adding new abstractions.
- Keep comments useful and Traditional Chinese in generated business code.
- Keep SQL command parameters inline unless the repository already has a meaningful helper for type, length, precision, or shared metadata; use `DBNull.Value` at the call site only when SQL NULL is intentional. Do not introduce a helper solely to shorten `new SqlParameter(...)`.
- Do not create `.bak`, timestamped backup, temporary copy, or similar backup files inside the target project repository during code write. Rely on version control, `change-plan.json`, and `implementation-report.md` for traceability; remove accidental project-level backup artifacts before delivery.
- Newly added business source files must keep the repository file header fields: `文件说明`, `新增人员`, `新增时间`, `修改人员`, `修改时间`, and `修改说明`.
- For file headers, `新增人员` must use the current Windows login account normalized as the author. Uppercase the first English letter and keep the rest unchanged, for example `jimmy` becomes `Jimmy`; do not use `AI`, `Codex`, `Regression`, or an arbitrary placeholder.
- `新增时间` uses the current execution date in `yyyy/MM/dd`; leave `修改人员`, `修改时间`, and `修改说明` blank for new files unless there is an actual modification record.
- When modifying an existing business source file, update the file header with an update record using exactly three lines: `修改人员`, `修改时间`, and `修改说明`. `修改人员` follows the same normalized Windows author rule; `修改时间` uses `yyyy/MM/dd`; `修改说明` states the business or code-standard change concisely in Traditional Chinese.
