# AI Codebase Assistant

AI Codebase Assistant is a local developer workspace for importing a source repository, building a bounded code index, exploring code and dependency views, and asking evidence-backed questions about the indexed repository.

It is designed to keep repository facts deterministic and inspectable. Assistant answers cite indexed source ranges; an optional local Ollama provider can turn selected evidence into natural-language answers, while a deterministic answer remains available when the provider is unavailable or its result cannot be validated.

## What it provides

- Import a public GitHub repository, a local folder, or a ZIP archive.
- Preview file counts, supported languages, ignored paths, warnings, and estimated indexing work before indexing.
- Index supported source files into files, symbols, endpoints, chunks, graph relations, and evidence records.
- Browse source in Code Explorer with stable file and line links.
- Explore repository overview, API endpoints, bounded graph views, and value traces.
- Search indexed source and open exact evidence ranges.
- Ask grounded assistant questions with citations, conversation history, and an optional Ollama provider.
- Review concise non-secret project, assistant, and safety settings.

## Architecture

| Area | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, TanStack Query |
| Backend | Python, FastAPI, Pydantic |
| Local development storage | SQLite |
| Optional answer provider | Ollama on a loopback address |
| Retrieval | Deterministic sparse retrieval with optional local dense retrieval |

The backend and frontend communicate through the versioned `/api/v1` API. Imported source is treated as untrusted data: the application does not execute imported code and excludes sensitive or unsupported files from normal indexing and evidence use.

## Requirements

- Python 3.11 or later
- Node.js 20 or later
- npm
- Optional: [Ollama](https://ollama.com/) and a locally installed chat model for provider-generated answers

## Run locally

### Backend

From the repository root in PowerShell:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If the virtual environment has not been created yet, follow [the development setup guide](docs/17-runbooks/development-setup.md). The backend listens on `http://localhost:8000` by default.

### Frontend

In a second terminal:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`.

## Using the application

1. Open **New Project**.
2. Choose a public GitHub URL, a ZIP file, or a local folder.
3. Enter a project name and select the required source input.
4. Choose **Prepare Preview**, inspect the result, then choose **Start Indexing**.
5. Open the workspace after indexing is complete.
6. Use Code Explorer, Graph View, or API Explorer to inspect the repository.
7. Ask a focused AI Assistant question, such as `Explain the authentication flow starting at main.py`.
8. Open a citation in the Evidence Viewer, then use **Open in Code Explorer** to inspect its source range.

For best assistant results, ask about a concrete file, symbol, endpoint, or flow that exists in the indexed repository.

## Optional Ollama configuration

The application can run with deterministic answers only. To enable local provider-generated answers, configure the backend environment with values appropriate to your machine:

```env
LLM_PROVIDER=ollama
LLM_MODEL=<installed-ollama-model>
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT_SECONDS=180
```

The configured model must be available in the local Ollama service. The UI reports the server-declared provider state. Provider output is accepted only when it has valid citations to the selected evidence; otherwise the application deliberately uses a deterministic fallback instead of inventing unsupported facts.

## Verification

Run frontend checks:

```powershell
Set-Location frontend
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
```

Backend and release-oriented verification commands are documented in [the task and runbook documentation](docs/README.md). Do not run imported repository code as part of indexing or analysis.

## Status and scope

This repository is under active development. The source of truth for implemented behavior, planned work, and production readiness is the [documentation hub](docs/README.md). A working local demo or a passing targeted test does not by itself establish production readiness.
