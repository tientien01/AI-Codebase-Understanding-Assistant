# Storage Design

## Document Purpose

This document defines the local-first storage layout and lifecycle rules for AI Codebase Assistant. It focuses on filesystem storage, upload retention, repository source storage, vector store files, graph exports, logs, evaluation artifacts, cleanup, and safe deletion.

Database table schemas are defined in `03_data_model.md`. System-level persistence architecture is introduced in `02_system_architecture.md`.

## Goal

Storage must support:

- repeatable local demos;
- restart persistence;
- safe import preview;
- safe deletion;
- re-index without mixed stale data;
- citation and evidence persistence;
- future migration to a hosted setup.

## Directory Layout

```text
storage/
  app.db
  repositories/
    {repository_id}/
      source/
      index_versions/
        {index_version}/
          manifest.json
  import_sessions/
    {session_id}/
      source_preview/
      preview.json
  uploads/
    {upload_id}.zip
  chroma/
  graphs/
    {repository_id}.json
  logs/
    app.log
  evaluation/
    runs/
      {run_id}.json
```

## Repository Source Storage

Managed source path:

```text
storage/repositories/{repository_id}/source/
```

Rules:

- Uploaded zip is extracted into this folder after validation.
- Uploaded folder is copied into this folder.
- GitHub repositories are cloned or downloaded into this folder.
- Folder and zip imports are copied into managed storage for stable indexing.
- Source storage should not include blocked secret files when filtering during copy is possible.
- Scanner must still filter blocked files even if source storage contains them.
- Do not store repository source in SQLite.

## Import Session Storage

Temporary import session path:

```text
storage/import_sessions/{session_id}/
```

Purpose:

- Hold uploaded or copied files before the user confirms import.
- Generate preview information.
- Detect duplicates and security warnings.
- Avoid creating permanent repository records until confirmation when the preview flow is used.

Rules:

- Import sessions expire after `IMPORT_SESSION_TTL_MINUTES`.
- Expired sessions should be cleaned up by a cleanup job or on backend startup.
- Import session storage must follow the same path safety and secret filtering rules as repository storage.

## Upload Storage

Path:

```text
storage/uploads/{upload_id}.zip
```

Rules:

- Validate archive before extraction.
- Reject path traversal.
- Reject oversized uploads.
- Optional retention setting controls whether original upload is kept.
- If retention is disabled, delete original upload after successful extraction/import.

## SQLite

SQLite stores:

- repository metadata;
- repository sources;
- import sessions if persisted;
- indexing status;
- parsed records;
- graph records;
- conversations;
- messages;
- evidence;
- evaluation data;
- settings overrides.

Guidelines:

- Use transactions for repository index replacement.
- Use foreign keys where practical.
- Add indexes for common repository-scoped lookups.
- Store raw source files on disk, not in the database.
- Store enough metadata to recreate evidence and citations after restart.

## Vector Store

Default local vector store:

- Chroma or equivalent provider.

Collection:

```text
repo_{repository_id}
```

Vector IDs:

- should equal `chunk_id`.

Metadata:

- repository_id;
- index_version;
- chunk_id;
- file_path;
- chunk_type;
- symbol_name;
- start_line;
- end_line;
- content_hash.

Rules:

- Re-index must delete or replace old vectors for the repository/index version.
- Vector metadata must not include secret content.
- Vector store provider must be replaceable.

## Graph Storage

Primary graph storage should be queryable records in SQLite.

Optional exported graph JSON:

```text
storage/graphs/{repository_id}.json
```

Use exported graph JSON for:

- debugging;
- visualization cache;
- backup;
- human inspection during development.

Do not make JSON export the only source of truth if the API needs graph queries.

## Index Version Artifacts

Optional path:

```text
storage/repositories/{repository_id}/index_versions/{index_version}/manifest.json
```

The manifest may include:

- index_version;
- job_id;
- indexed file count;
- skipped file count;
- failed file count;
- chunk count;
- vector count;
- graph node/edge count;
- content hash summary;
- generated_at.

This is optional but useful for debugging stale index and re-index behavior.

## Logs

Path:

```text
storage/logs/app.log
```

Log records should include:

- timestamp;
- level;
- repository_id;
- job_id;
- conversation_id when useful;
- step;
- error_code;
- safe message.

Never log secrets, raw tokens, private credentials, or real `.env` content.

## Evaluation Artifacts

Path:

```text
storage/evaluation/runs/{run_id}.json
```

Use this for optional exported evaluation results. The database remains the source of truth for evaluation runs and results.

## Delete Repository

Delete must remove:

- repository row;
- file/symbol/endpoint/API call/chunk records;
- graph records;
- vector collection or repository vectors;
- managed source folder;
- graph JSON export;
- index version artifacts;
- upload artifacts if not retained.

Conversation/evidence retention is configurable. Default local behavior can delete all related records.

## Re-index

Re-index must:

- preserve repository identity;
- create a new indexing job;
- assign a new `index_version`;
- clear or supersede stale parsed/index records;
- clear old vectors or mark old vectors inactive;
- rebuild records;
- update `last_indexed_at`;
- avoid presenting mixed old/new index data as complete.

If re-index fails:

- mark job failed;
- mark repository failed or keep previous indexed version with a clear warning, depending on chosen policy;
- keep job logs;
- do not present partial new records as a successful index.

## Cleanup Rules

Cleanup should handle:

- expired import sessions;
- failed upload artifacts;
- orphan graph JSON files;
- vector collections for deleted repositories;
- stale temporary files from interrupted imports.

Cleanup must never delete paths outside configured storage roots.

## Notes for AI Coding Agents

- Always resolve and validate paths before reading or writing.
- Never trust uploaded relative paths.
- Keep storage paths configurable through environment variables.
- Do not use graph JSON as the only source of graph truth.
- Do not implement deletion without tests for path safety.

## Production Index Artifact Layout

Production indexing must store enough artifacts to debug, validate, compare, and safely activate index versions.

Recommended layout:

```text
storage/repositories/{repository_id}/
├── source/
├── index_versions/
│   └── {version}/
│       ├── manifest.json
│       ├── artifacts/
│       │   ├── preflight.json
│       │   ├── scan-result.json
│       │   ├── resolution-result.json
│       │   ├── graph-candidates.json
│       │   ├── assembled-graph.json
│       │   ├── graph-normalization-report.json
│       │   ├── architecture.json
│       │   ├── tours.json
│       │   ├── chunks-manifest.json
│       │   ├── validation-report.json
│       │   └── fingerprints.json
│       ├── parser-results/
│       │   ├── file-001.json
│       │   └── file-002.json
│       ├── graph/
│       │   └── knowledge-graph.json
│       ├── reports/
│       │   └── index-quality.json
│       └── debug/
│           ├── semantic-batches.json
│           └── enrichment/
└── active_index_version
```

Use database records as the source of truth for product queries. Use artifacts for reproducibility, diagnostics, export, and comparison.

### Retention Classes

Permanent:

- manifest;
- scan result;
- validation report;
- fingerprints;
- current graph export;
- parser provenance summary.

Debug retention:

- per-file parser output;
- graph candidates;
- batch outputs;
- prompt inputs and normalized LLM outputs when local debug mode allows them;
- merge logs.

Temporary:

- extracted upload scratch;
- retry payloads;
- failed provider payloads;
- partial vector build scratch.

Debug and temporary artifacts must have cleanup policies.

### Index Manifest

Each version must have `manifest.json`:

```json
{
  "repository_id": "repo_123",
  "index_version": 4,
  "status": "ready_with_warnings",
  "base_index_version": 3,
  "source_revision": "abc123",
  "pipeline_versions": {},
  "capability_readiness": {},
  "coverage_summary": {},
  "validation_summary": {},
  "artifact_hashes": {},
  "started_at": "...",
  "finished_at": "...",
  "activated_at": "..."
}
```

### Atomic Publish Storage Rules

Build the new index under its own version directory. Do not overwrite the active version while building.

Activation order:

1. Write all mandatory artifacts.
2. Persist derived database records for the new version.
3. Commit keyword/vector indexes for the new version.
4. Write validation report and manifest.
5. Mark the new version ready.
6. Switch repository active index version in one database transaction.

If activation fails, the old active index remains available.

### Exportable Graph Artifact

`knowledge-graph.json` should be an export of the normalized graph, not the only graph store.

It should include:

- schema version;
- repository id;
- index version;
- generated timestamp;
- nodes with canonical keys;
- edges with canonical source/target keys;
- provenance summaries;
- validation summary;
- capability readiness summary.

This artifact supports demos, debugging, and optional docs-as-code workflows.
