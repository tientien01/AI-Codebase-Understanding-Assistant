# Stateful Local Assistant Delivery Plan

Status: Approved  
Owner: Project maintainer  
Approved: 2026-07-16

Delivery state: AGT-006, AGT-007, RET-004 and RET-005 are verified locally; the versioned dense artifact retains sparse fallback, while UI-024 remains draft and requires separate promotion.

## Outcome

Deliver a replayable, bounded conversational assistant that can run through a local Ollama provider, evaluate dense embeddings before adoption, and disclose whether each answer used Ollama or deterministic fallback without weakening evidence or read-only guarantees.

## Non-negotiable boundaries

- Conversation memory helps resolve follow-up intent but never becomes repository evidence.
- Every technical answer remains supported by current validated evidence and citation checks.
- Ollama is optional; outage, timeout or invalid output preserves deterministic behavior.
- Dense embeddings do not replace sparse retrieval until a frozen same-input benchmark passes reviewed quality and resource gates.
- Model, embedding and index identities remain versioned. Changing embedding model/dimension/preprocessing requires a compatible rebuild.
- Imported source remains untrusted data. The assistant never edits source, executes repository instructions or invokes terminal tools.

## Delivery sequence

1. **AGT-006 — Stateful conversation foundation**
   - Stable conversation identity, repository-owned list/replay APIs and frontend refresh/reopen behavior.
   - Bounded deterministic multi-turn memory separated from source evidence.
   - Verified 2026-07-16; evidence: `docs/18-production-evidence/assistant-stateful-conversation-report.md`.
2. **AGT-007 — Ollama grounded chat provider**
   - Explicit Ollama adapter, local readiness/health, bounded timeout and deterministic fallback.
3. **RET-004 — Ollama dense embedding benchmark**
   - Same-input sparse/dense/hybrid evaluation covering quality, latency, indexing time and memory. No production replacement.
4. **RET-005 — Versioned dense embedding index**
   - Verified 2026-07-17; immutable compatibility-bound artifact and explicit dense semantic adapter preserve sparse fallback.
5. **UI-024 — Assistant provider and readiness UX**
   - Truthful per-answer/provider/index state: deterministic, Ollama, hybrid or fallback; loading/degraded/stale states.

Only one task may be `ready` or `in_progress` at a time. Later tasks remain `draft` until predecessor evidence and any required technology decision are accepted.

## Cross-task acceptance

```text
conversation replay + bounded memory
→ validated sparse/dense retrieval
→ exact selected source evidence
→ optional Ollama grounded generation
→ citation validation
→ persisted answer/provider outcome
→ truthful frontend replay/readiness
```

The sequence is complete only when provider outage, stale conversation/index, insufficient evidence, long conversation, changed embedding configuration and refresh/replay cases have deterministic tests and production evidence.

## Rollback strategy

Each slice is independently reversible: disable memory projection while retaining messages; disable Ollama while retaining deterministic answers; decline dense adoption while retaining sparse retrieval; hide provider UI only when the underlying capability is also absent. No task may require rolling back conversation or evidence records to disable an optional provider.
