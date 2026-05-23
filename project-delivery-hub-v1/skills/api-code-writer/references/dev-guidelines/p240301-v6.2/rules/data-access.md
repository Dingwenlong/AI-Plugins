# Data Access Rules

Runtime use: load only for APIs with DB, SQL, `queryContracts`, DB backend APIs, or SQL executor dependencies.

- Require explicit `queryContracts` or equivalent authoritative SQL evidence before implementing SQL behavior.
- Do not infer table names, joins, ordering, or parameters from similar files when handoff evidence is missing.
- Preserve legacy DB object names only when legacy evidence is authoritative for the current API.
- Mark `waiting_fixture` or a blocking gap when SQL execution requires schema, seed data, or permissions that are not ready.
- Hand off real Service SQL runtime validation to step 05; mock SQL tests alone do not prove SQL correctness.
