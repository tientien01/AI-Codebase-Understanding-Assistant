# Parser Output Schema

## Document Purpose

This document defines the normalized output contract for all parsers. All parser implementations must emit records in this shape so chunking, graph building, retrieval, citation generation, and evaluation do not need language-specific logic.

## Global Rules

- Line numbers are 1-based.
- `start_line` and `end_line` are inclusive.
- Every parser result must include `file_path`, `language`, `file_type`, `content_hash`, and `errors`.
- Parser output must not include content from blocked secret files.
- Low-confidence extraction must be marked with a confidence score.
- Parser implementations must not write directly to the database.
- The indexing service is responsible for persisting normalized parser output.

## ParsedFile

```json
{
  "file_path": "backend/app/auth/router.py",
  "language": "python",
  "file_type": "source",
  "content_hash": "sha256...",
  "parser_name": "python_ast_parser",
  "parser_version": "0.1.0",
  "imports": [],
  "symbols": [],
  "endpoints": [],
  "api_calls": [],
  "config_variables": [],
  "document_sections": [],
  "tests": [],
  "relations": [],
  "errors": []
}
```

## ParsedImport

```json
{
  "module": "app.services.auth_service",
  "name": "AuthService",
  "alias": null,
  "import_type": "from_import",
  "start_line": 3,
  "end_line": 3,
  "confidence": 1.0
}
```

Allowed import types:

- `import`
- `from_import`
- `require`
- `dynamic`

## ParsedSymbol

```json
{
  "symbol_type": "function",
  "name": "login",
  "qualified_name": "app.api.auth.routes.login",
  "signature": "async def login(payload: LoginRequest)",
  "start_line": 21,
  "end_line": 45,
  "docstring": "Authenticate user and return token.",
  "decorators": ["router.post('/login')"],
  "parent_symbol": null,
  "metadata": {},
  "confidence": 1.0
}
```

Allowed symbol types:

- `class`
- `function`
- `method`
- `component`
- `constant`
- `model`
- `schema`
- `test`
- `hook`
- `service`

## ParsedEndpoint

```json
{
  "framework": "fastapi",
  "http_method": "POST",
  "route_path": "/login",
  "router_prefix": "/api/auth",
  "full_path": "/api/auth/login",
  "handler_name": "login",
  "qualified_handler_name": "app.api.auth.routes.login",
  "request_model": "LoginRequest",
  "response_model": "TokenResponse",
  "auth_required": false,
  "start_line": 20,
  "end_line": 45,
  "confidence": 0.95
}
```

## ParsedApiCall

```json
{
  "caller": "LoginPage",
  "method": "POST",
  "url": "/api/auth/login",
  "normalized_path": "/api/auth/login",
  "client": "axios",
  "start_line": 32,
  "end_line": 32,
  "confidence": 0.8
}
```

Allowed clients:

- `fetch`
- `axios`
- `httpx`
- `requests`
- `unknown`

## ParsedConfigVariable

```json
{
  "name": "DATABASE_URL",
  "source": ".env.example",
  "value_preview": null,
  "is_secret_like": false,
  "start_line": 4,
  "end_line": 4,
  "confidence": 0.9
}
```

Rules:

- Real `.env` files must not be parsed.
- `.env.example` may expose variable names but not real secret values.
- Config values that look secret-like should not be used as answer content.

## ParsedDocumentSection

```json
{
  "heading": "Setup",
  "level": 2,
  "slug": "setup",
  "start_line": 10,
  "end_line": 32,
  "links": ["backend/app/main.py"],
  "code_fences": ["pip install -r requirements.txt"],
  "confidence": 1.0
}
```

## ParsedTest

```json
{
  "test_name": "test_login_success",
  "qualified_name": "tests.test_auth.test_login_success",
  "framework": "pytest",
  "target_refs": ["app.api.auth.routes.login"],
  "start_line": 8,
  "end_line": 20,
  "confidence": 0.75
}
```

## ParsedRelation

```json
{
  "source_type": "symbol",
  "source_ref": "app.api.auth.routes.login",
  "target_type": "symbol",
  "target_ref": "app.services.auth_service.authenticate_user",
  "relation_type": "calls",
  "start_line": 35,
  "end_line": 35,
  "confidence": 0.7
}
```

Allowed source/target types:

- `repository`
- `module`
- `file`
- `symbol`
- `endpoint`
- `api_call`
- `model`
- `schema`
- `test`
- `document`
- `config`

Allowed relation types:

- `contains`
- `defines`
- `imports`
- `exports`
- `calls`
- `exposes_endpoint`
- `calls_api`
- `uses_model`
- `uses_schema`
- `tested_by`
- `documented_by`
- `configured_by`

## ParserError

```json
{
  "file_path": "frontend/src/App.tsx",
  "error_type": "parse_error",
  "message": "Could not parse TypeScript file with current parser.",
  "line": 12,
  "recoverable": true
}
```

Error types:

- `encoding_error`
- `file_too_large`
- `parse_error`
- `unsupported_language`
- `blocked_secret_file`
- `binary_file`
- `unknown_error`

## Python Parser Requirements

Use `ast`.

Must extract:

- imports and from-imports;
- classes;
- functions;
- async functions;
- methods;
- decorators;
- docstrings;
- FastAPI endpoints;
- SQLAlchemy models;
- Pydantic schemas;
- basic function calls.

Best-effort:

- resolve `APIRouter(prefix=...)`;
- resolve simple router include prefixes;
- resolve `response_model`;
- detect auth dependencies;
- detect pytest test functions.

## JS/TS Parser Requirements

Preferred:

- tree-sitter, Babel, SWC, or TypeScript compiler API.

Fallback:

- controlled regex with confidence scores.

Must extract:

- imports;
- exports;
- functions;
- const arrow functions;
- React component heuristics;
- fetch calls;
- axios calls.

Best-effort:

- normalize API base URL constants;
- detect service wrapper functions;
- connect frontend API calls to backend endpoints;
- detect test files and test cases.

## Markdown Parser Requirements

Extract:

- heading hierarchy;
- section line ranges;
- code fences;
- links to files;
- setup commands.

## Config Parser Requirements

Extract:

- JSON/YAML/TOML keys;
- Dockerfile instructions;
- docker-compose services;
- `.env.example` variable names only.

## Confidence Rules

- AST exact extraction: `0.90 - 1.00`.
- Parser library extraction: `0.85 - 1.00`.
- Clear regex extraction: `0.70 - 0.85`.
- Heuristic/dynamic extraction: `0.40 - 0.65`.
- Below `0.40`: do not use as primary evidence.

## Notes for AI Coding Agents

- Keep schema stable because chunking, graph building, API Explorer, impact analysis, and evidence validation depend on it.
- Add new parser fields through `metadata` first unless the field is clearly needed across multiple services.
- Do not let parser-specific output leak into downstream services without normalization.

## Production Parser, Resolver, And Graph Candidate Contract

The production implementation must keep three layers separate:

```text
Parser output
-> Resolver output
-> Graph candidate output
```

Parser output is raw structural evidence from one file. Resolver output maps raw references to canonical entities across files. Graph candidate output proposes nodes and edges with provenance before graph normalization.

### Parser Responsibilities

Parsers must:

- process only files listed in the canonical scan inventory;
- produce deterministic output for the same file content and parser version;
- include line ranges where possible;
- include extraction method and confidence;
- never write directly to the database;
- never infer cross-file relations when a resolver should do it;
- never read skipped or secret-like files.

Parser output should include:

- `file_key`
- `parser_name`
- `parser_version`
- `language`
- `symbols`
- `imports`
- `exports`
- `endpoints`
- `api_calls`
- `config_variables`
- `document_sections`
- `tests`
- `raw_relations`
- `diagnostics`

### Canonical Parser Item Fields

Every parser item should include:

```json
{
  "id": "parser_item_123",
  "file_key": "file:backend/app/auth/router.py",
  "kind": "function",
  "name": "login",
  "start_line": 20,
  "end_line": 45,
  "extraction_method": "ast",
  "confidence": 0.98,
  "parser_version": "python-3.1",
  "metadata": {}
}
```

Extraction methods:

- `ast`
- `tree_sitter`
- `compiler_api`
- `language_server`
- `regex`
- `heuristic`
- `llm_assisted`

LLM-assisted parser output must always pass schema validation and must be marked with lower provenance strength than deterministic output.

### Resolver Output

Resolvers convert raw parser facts into canonical relationships.

Output artifact:

```text
resolution-result.json
```

Resolved reference schema:

```json
{
  "id": "ref_123",
  "reference_type": "import",
  "source_file_key": "file:backend/app/api/auth.py",
  "source_symbol_key": null,
  "raw_reference": "app.services.auth_service.AuthService",
  "resolved_file_key": "file:backend/app/services/auth_service.py",
  "resolved_symbol_key": "class:backend/app/services/auth_service.py:AuthService",
  "resolution_method": "python_absolute_import",
  "confidence": 1.0,
  "provenance": [
    "parser-results/file_backend_app_api_auth_py.json#import_3"
  ],
  "metadata": {}
}
```

Resolver methods should be deterministic whenever possible:

- python absolute import;
- python relative import;
- TypeScript path alias;
- package export map;
- FastAPI route decorator;
- React service wrapper;
- pytest naming convention;
- config key lookup;
- SQLAlchemy model reference.

Resolvers must not use LLMs for relationships that can be resolved by static analysis.

### Graph Candidate Output

Graph candidates are not final graph records. They are normalized and merged later.

Node candidate:

```json
{
  "candidate_id": "cand_node_1",
  "candidate_type": "node",
  "canonical_key": "function:backend/app/auth/service.py:login",
  "node_type": "function",
  "label": "login",
  "file_key": "file:backend/app/auth/service.py",
  "start_line": 18,
  "end_line": 44,
  "origin": "parser_exact",
  "confidence": 0.98,
  "evidence_refs": ["parser_item_123"],
  "created_by_component": "python_parser",
  "component_version": "3.1",
  "metadata": {}
}
```

Edge candidate:

```json
{
  "candidate_id": "cand_edge_1",
  "candidate_type": "edge",
  "source_key": "endpoint:POST:/api/auth/login",
  "target_key": "function:backend/app/auth/service.py:login",
  "edge_type": "handled_by",
  "origin": "resolver_exact",
  "confidence": 0.96,
  "evidence_refs": ["ref_123", "parser_item_456"],
  "created_by_component": "fastapi_resolver",
  "component_version": "2.0",
  "metadata": {}
}
```

### Provenance Strength

Use this order when merging conflicting data:

1. `user_confirmed`
2. `parser_exact`
3. `resolver_exact`
4. `framework_rule`
5. `heuristic`
6. `llm_inferred`

The final graph may include heuristic or LLM-inferred relations, but the UI and agent must label them as inferred rather than evidence-based.

### Required Validation

Before parser/resolver output is consumed:

- every item must reference a known `file_key`;
- every line range must be valid for the file line count when available;
- every confidence must be between `0` and `1`;
- every canonical key must follow the project key convention;
- every unresolved reference must be kept with a diagnostic rather than silently dropped.
