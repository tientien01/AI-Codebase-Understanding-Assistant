# AI-Codebase-Understanding-Assistant

MVP for importing a local repository, indexing source files, viewing codebase overview, asking grounded questions, and opening evidence citations.

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
4. Choose one import mode:

- `Upload Folder`: choose a project folder in the browser.
- `Upload ZIP`: choose a `.zip` archive.
- `Local Path`: use a path readable by the backend process.

For local path testing, use:

```text
../tests/fixtures/fastapi_react_sample
```

5. Click `Import and Index`.
6. Open the workspace.
7. Ask:

```text
How does login flow work?
```

8. Click a citation to open the Evidence / Citation Viewer.

## Current MVP Coverage

- Local repository import.
- Folder upload from the browser.
- ZIP upload.
- Safe file scanning and filtering.
- Python AST parser for classes, functions and FastAPI endpoints.
- Basic JS/TS parser for components/functions and API calls.
- Markdown/config chunking.
- Overview, endpoint list, search, graph subset, chat and evidence API.
- File tree and real file content loading in Code Explorer.
- UI pages following `docs/ui_ux.md`; non-MVP pages show `Đang phát triển`.

## Not Yet Production Grade

- Real LLM provider integration.
- ChromaDB embeddings.
- Persistent database. Current MVP persists index snapshots as JSON under `storage/indexes`.
- GitHub OAuth/import.
- Advanced impact analysis and evaluation dashboard.
