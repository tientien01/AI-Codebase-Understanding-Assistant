# AI-Codebase-Understanding-Assistant

MVP for importing a repository, indexing source files, viewing codebase overview, asking grounded questions, and opening evidence citations.

## Run Backend

```bash
cd backend
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

## Run Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## Test The MVP

1. Start backend and frontend.
2. Open the frontend.
3. Click `New Project`.
4. Choose `Upload Folder` or `Upload ZIP`.
5. For folder testing, use `tests/fixtures/fastapi_react_sample`.
6. Click `Start Indexing`. The frontend creates an import session, confirms it, and starts indexing.
7. Open the workspace.
8. Ask `How does login flow work?`.
9. Click a citation to open the Evidence / Citation Viewer.

## Current MVP Coverage

- Import sessions for folder and ZIP upload, preview API, confirm, and cancel.
- Folder upload from the browser.
- ZIP upload.
- Safe file scanning and filtering.
- Python AST parser for classes, functions, and FastAPI endpoints.
- Basic JS/TS parser for components/functions and API calls.
- Markdown/config chunking.
- Overview, endpoint list, search, graph subset, chat, and evidence API.
- Evidence validation and search ask-with-evidence API.
- File tree and real file content loading in Code Explorer.
- UI pages following `docs/08_frontend_workspace_ux.md`; non-MVP pages show an in-development state.

## Not Yet Production Grade

- Real LLM provider integration.
- ChromaDB embeddings.
- Full database migration management. Current MVP uses SQLite metadata storage under `storage/app.db`.
- GitHub OAuth/import.
- Advanced impact analysis and evaluation dashboard.
