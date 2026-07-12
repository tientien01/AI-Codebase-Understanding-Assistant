# Engineering Standards

- Thin routes; application use cases coordinate domain services; adapters own infrastructure.
- Typed boundary models; no long-lived raw dictionaries crossing domains.
- Parser, resolver, graph assembly, validation, and publish remain separate.
- Feature-oriented frontend modules replace the monolithic controller incrementally.
- Dependencies require accepted technology status, lockfile update, license/security review, tests, operational documentation, and rollback.
- CI runs formatting, lint, type checks, unit/integration/contract tests, frontend build/E2E, migration drift, docs links, security scans, and AI regression gates as appropriate.

Standard commands should converge on cross-platform tasks equivalent to: setup, dev, dev-infra, migrate, test, integration, e2e, benchmark, lint, typecheck, build, production-check.

`specifications/detailed-coding-standards.md` remains the detailed convention set for backend structure, Python/FastAPI/services/database/providers, frontend, errors, logging, naming, comments, tests, production indexing, and service boundaries.
