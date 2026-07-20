# UI-024 Assistant Provider Readiness UI Report

Status: Completed locally on 2026-07-17

Chat responses now declare generation mode, provider state and retrieval mode. The
frontend renders those declarations per current answer and never derives provider use
from configured settings. Accepted Ollama output, another accepted provider,
deterministic output, deterministic fallback, sparse retrieval and hybrid retrieval
have distinct labels. Existing loading, error, insufficient-evidence and stale-index
notices remain unchanged. Historic replay without outcome metadata stays unlabeled.

Verification: 26 provider-focused backend tests, 65 assistant tests, frontend lint,
115 frontend tests across 17 files, TypeScript production compilation and Vite build
all pass. No dependency, database or migration change was made.
