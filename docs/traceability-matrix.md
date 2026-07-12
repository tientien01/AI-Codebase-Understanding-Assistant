# Production Traceability Matrix

Status: Accepted summary; release manifests provide instance-level traceability  
Last verified: 2026-07-12

| Requirement | Design authority | Delivery phase | Required evidence |
| --- | --- | --- | --- |
| Safe repository import | Security + ingestion contract | Phase 7 (`SEC-001`) | Adversarial import suite |
| Durable indexing | Indexing contract + ADR-0001 | Phase 2 (`JOB-*`) | Recovery/idempotency tests |
| Atomic active index | Data/index contract | Phase 2 (`IDX-001..003`) | Failure/activation tests |
| Provenance graph | Parsing/graph contract | Phase 3 (`INT-*`) | Graph validation report |
| Evidence-backed Q&A | Retrieval/evidence contract | Phase 4 (`RET-*`) | Citation/grounding benchmark |
| Bounded Agentic RAG | Assistant contract | Phase 5 (`AGT-*`) | Tool/trace/budget tests |
| Production web UX | Frontend architecture | Phase 6 (`UI-*`) | Component/E2E/accessibility |
| Operable deployment | Reliability/technology | Phase 7 (`OPS-*`) | Deploy/backup/restore drills |
| Release readiness | Governance | Phase 8 (`REL-*`) | Signed L3 release manifest/checklist |

The detailed matrix is generated per release from task metadata and CI artifacts. Missing evidence blocks release.
