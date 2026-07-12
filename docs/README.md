# Production Documentation Hub

This documentation defines the production target, records the current implementation gap, and controls the work that closes that gap.

## Start here

1. Read `project-status.md` for the verified current phase, blockers, and next task.
2. Read `00-governance/release-levels.md` for the meaning of demo, portfolio, and production readiness.
3. Read the relevant product/architecture overview and its linked normative contract.
4. Read `15-plans/master-roadmap.md` and the current phase plan.
5. Implement only a `ready` or `in_progress` task under `16-agent-tasks/`.

The shortest architecture introduction is `02-system-architecture/architecture-at-a-glance.md`.

## Reading paths

| Goal | Start here |
| --- | --- |
| See current status and next work | `project-status.md` |
| Set up and verify development | `17-runbooks/development-setup.md`, `14-implementation-baseline/verification-report.md` |
| Understand the product | `01-product/README.md` |
| Review system design | `02-system-architecture/README.md` |
| Review the approved stack | `03-technology/README.md` |
| Review database and artifacts | `04-domain-and-data/README.md` |
| Implement a domain | `05-domain-contracts/README.md` |
| Review API/security/operations | `06-api-and-integrations/README.md`, `07-security/README.md`, `08-reliability-and-operations/README.md` |
| Review UX | `09-frontend-and-ux/README.md` |
| Review RAG and Agentic AI | `10-ai-rag-and-evaluation/README.md` |
| Understand current source | `14-implementation-baseline/README.md` |
| See delivery order | `15-plans/README.md` |
| Execute code work | `16-agent-tasks/README.md` |
| Decide release readiness | `18-production-evidence/README.md` |
| Study other repositories | `19-research/README.md` |

## Document classes

- **Normative:** accepted architecture, contracts, ADRs, security and operational requirements.
- **Baseline:** verified description of current source; never the production target by itself.
- **Plan:** approved migration from baseline to target.
- **Task:** the only document that authorizes an implementation change.
- **Evidence:** proof that requirements and gates have passed.
- **Research/archive:** informative only; cannot authorize code.

## Detail policy

Overview files explain boundaries and reading order. Detailed specifications live under `specifications/`, `page-contracts/`, or the owning domain directory and are linked from its README. An agent must read the detailed specification named by its task; summaries are not sufficient implementation contracts.

## Status vocabulary

Documents use `draft`, `proposed`, `accepted`, `deprecated`, or `historical`. Tasks use `draft`, `ready`, `in_progress`, `blocked`, or `completed`. Implementation/evidence claims use `implemented` and `verified` only when supported by source/tests or release evidence.

## Production rule

Completing feature tasks is insufficient. A release is production-ready only when `00-governance/definition-of-production-ready.md` and `18-production-evidence/release-checklist.md` pass.
