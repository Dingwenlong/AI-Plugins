# Database Design Standard v3 - Source Unreadable

Source: `數據庫設計規範 v3 20220908.docx`.

This rule is a blocker, not a database design rule. The supplied source is an old Office OLE container with `DRMEncryptedDataSpace` and `EncryptedPackage`; LibreOffice headless and Word COM read-only conversion could not extract reliable body text.

## When To Load

Load this file only when the current DAWHO/New DAWHO design task requires database design guidance, such as:

- creating or changing a database table;
- designing or renaming columns;
- deciding primary keys, foreign keys, unique keys, or indexes;
- designing stored procedures or views;
- defining audit fields, retention, or sensitive-data handling.

Do not load it for ordinary API naming, Request/Response field naming, workbook formatting, or DB/SP source tracing where no new database design decision is being made.

## Required Behavior

- Do not invent table-naming, column, key, index, stored procedure, view, audit, data-retention, or sensitive-data rules from memory.
- Mark the database-design standard as `source_unreadable` in the design analysis when these rules are needed.
- Continue using PRD/TSD/API Detail/legacy DB evidence for factual tracing, but do not claim compliance with `數據庫設計規範 v3` until a readable Markdown/JSON or unprotected Word source is supplied.
- If a new table or new column must be designed before the source is readable, list the missing facts explicitly: table purpose, authoritative source, field semantics, data type, nullability, PK/FK/unique key, index intent, update frequency, expected data volume, retention period, and sensitive-data classification.

## Replacement Rule

When a readable source is available, replace this blocker with topic rules under:

- `rules/table-naming.md`
- `rules/column-naming.md`
- `rules/primary-foreign-key.md`
- `rules/index-design.md`
- `rules/stored-procedure-view.md`
- `rules/audit-fields.md`
- `rules/data-type-nullability.md`
- `rules/retention-security.md`
