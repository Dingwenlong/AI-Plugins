# Test Handoff Rules

Runtime use: handoff only. Step 04 must not create UnitTest, IntegrationTest, or Service runtime validation source.

- Preserve every `mockExamples` scenario in `testScenarioPlan`.
- Hand off `unitTestTargetFiles`, `integrationTestTargetFiles`, and Service runtime validation needs to step 05.
- For DB APIs, separate mock-based scenario/mapping UnitTests from real Service SQL runtime validation.
- Controller IntegrationTests that mock Service prove route/auth/serialization only, not Service business logic.
- Missing fixture, DB, schema, or configured-connection evidence must remain visible as a step-05 gap.
