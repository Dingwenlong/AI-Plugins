# Frontstage Session Rules

Runtime use: load only for frontstage member/customer APIs with identity, JWT, session, Redis, or personal-data behavior.

- Require a clear source of truth for member identity before generating runtime context code.
- Accept identity only from verified JWT claims, session-scoped Redis data, or existing authenticated context wiring.
- Do not combine arbitrary headers, global Redis keys, and local fallbacks to invent a current user.
- Treat V6.2 session/JWT descriptions as target-state guidance unless the repository has matching wiring evidence.
- If `auth_sn`, member hash, `CustId`, or `KeyId` origins are unclear, block with `spec_handoff_gap` or `devGuidelineGaps`.
