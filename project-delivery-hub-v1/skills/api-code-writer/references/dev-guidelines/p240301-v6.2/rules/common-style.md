# Common Style Rules

Runtime use: load only after `devGuidelineRulesSelected` includes `common-style`.

- Treat API Spec and `codeHandoff` as the business source of truth.
- Treat V6.2 rules as implementation constraints, not as proof that the current repository is already wired.
- Keep implementation changes in business files only; UnitTest and IntegrationTest source belongs to step 05.
- Prefer existing repository helpers, naming, namespaces, and dependency patterns before adding new abstractions.
- Keep comments useful and Traditional Chinese in generated business code.
