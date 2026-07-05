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
