# Cache Rules

Runtime use: load only when Redis, cache, TTL, session cache, stale-read, or invalidation behavior appears.

- Decide whether cached data is optimization, session state, or source of truth before implementing it.
- Require TTL, invalidation/refresh, null-caching, and stale-read acceptance rules for new business cache behavior.
- Do not use cache as an authoritative duplicate/existence check unless handoff explicitly says so.
- Do not store sensitive identifiers or secrets in newly invented Redis keys.
- When cache evidence is incomplete, prefer no cache or block rather than generating permanent cache writes.
