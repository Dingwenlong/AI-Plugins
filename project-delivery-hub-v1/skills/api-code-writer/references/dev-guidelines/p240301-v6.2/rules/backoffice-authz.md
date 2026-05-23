# Backoffice Authorization Rules

Runtime use: load only for mid/backoffice APIs with role, permission, menu, operation-log, or audit behavior.

- Require explicit role, permission, menu, or staff identity evidence before adding authorization behavior.
- Do not treat customer/member JWT or frontstage session rules as proof for backoffice operator identity.
- Preserve audit and operation-log requirements as separate business behavior when the API changes state.
- If the API is ambiguous between frontstage and backoffice, block until the caller/channel is clarified.
- Prefer existing backoffice authorization and audit patterns when present.
