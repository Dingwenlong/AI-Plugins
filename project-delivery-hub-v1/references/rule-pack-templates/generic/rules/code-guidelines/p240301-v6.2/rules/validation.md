# Validation Rules

Runtime use: load only when request fields, required flags, custom validation, or validation-response mapping is relevant.

- Prefer DTO attributes for basic single-field validation when the repository supports that layer.
- Keep Service validation for business semantics, runtime context, DB/cache state, and cross-field rules.
- Do not duplicate DTO attribute validation in Service code.
- If spec requires exact response code/message for validation failures, require mapping evidence before implementation.
- Mark a shared validation infrastructure gap when the repository cannot map attribute errors to spec response codes.
