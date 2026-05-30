# Data Access Rules

Runtime use: load only for APIs with DB, SQL, `queryContracts`, DB backend APIs, or SQL executor dependencies.

- Require explicit `queryContracts` or equivalent authoritative SQL evidence before implementing SQL behavior.
- Do not infer table names, joins, ordering, or parameters from similar files when handoff evidence is missing.
- Preserve legacy DB object names only when legacy evidence is authoritative for the current API.
- When the following code only needs the first row or an existence-like single row, push that intent into SQL and the data-access API without changing business semantics. For SQL Server, use `SELECT TOP (1)` and `QueryFirstOrDefaultAsync` / the repository's single-row equivalent instead of fetching a full result set and then calling `FirstOrDefault()` in C#.
- Add an `ORDER BY` with authoritative business evidence whenever the selected first row has business meaning. If no ordering rule exists and the predicate is expected to be unique or any matching row is equivalent, keep the optimization as a defensive row-limit and do not invent ordering.
- Do not rewrite aggregate queries such as `COUNT(0)` merely because the code consumes a single aggregate row; those queries are already single-result by shape.
- Mark `waiting_fixture` or a blocking gap when SQL execution requires schema, seed data, or permissions that are not ready.
- Hand off real Service SQL runtime validation to step 05; mock SQL tests alone do not prove SQL correctness.
