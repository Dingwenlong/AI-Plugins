# Logging And Exception Rules

Runtime use: load only when exception handling, logging, failure disposition, or sensitive-data masking is relevant.

- Preserve existing logger and exception handling patterns.
- Avoid logging secrets, full card numbers, passwords, tokens, or sensitive identity values.
- Keep business failure responses aligned with response-code catalog rules.
- Classify environment or dependency failures separately from code defects in reports.
- Do not hide validation, DB, or external dependency failures behind generic success responses.
