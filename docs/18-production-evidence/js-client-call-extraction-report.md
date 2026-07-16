# INT-005 JavaScript Client Call Extraction Evidence

Date: 2026-07-15

## Delivered behavior

- JavaScript and TypeScript parsing recognizes direct Axios and Fetch calls, locally configured `axios.create` clients, and imported client aliases with deterministic static routes.
- Quoted routes and template routes are normalized without evaluating repository code. Template expressions become explicit route parameters.
- Configured static base URL paths are joined for calls in the defining module.
- Dynamic route variables that are not statically represented by a literal or template are not emitted or guessed.
- Endpoint matching compares both HTTP method and normalized route shape, and ambiguous candidates remain unlinked.

## Verification

- `backend\.venv\Scripts\python.exe -m pytest ..\tests\intelligence\test_parser_golden.py ..\tests\test_service_boundaries.py -q`: 22 passed, with one third-party OpenTelemetry deprecation warning.
- Static extraction against public WHAT2EAT commit `5474f7da283a60ee4fc95d89ef24953fa5689ce7`: 39 client calls detected across 7 frontend source files. No repository code was imported, built, installed, or executed.
- Focused `git diff --check`: passed.

## Remaining limitations

- Arbitrary wrapper functions and dynamically computed client aliases remain unresolved unless their final HTTP member call is statically visible.
- Router-prefix reconstruction is not included, so some client calls can remain unmatched when backend endpoint facts contain only decorator-local paths.
- Dart, Kotlin, Java, Swift, C#, GraphQL, gRPC, and WebSocket adapters require follow-up tasks that emit the same canonical client-call facts.
