from __future__ import annotations

import ast
import hashlib
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import DomainError
from app.schemas.api import (
    ChatResponse,
    CitationDTO,
    EndpointDTO,
    EvidenceDTO,
    FileContentResponse,
    FileTreeNodeDTO,
    GraphEdgeDTO,
    GraphNodeDTO,
    GraphResponse,
    ImportantFileDTO,
    IndexStatusResponse,
    ModuleDTO,
    OverviewResponse,
    RepositoryCreateResponse,
    RepositoryDTO,
    SearchResponse,
    SearchResultDTO,
)
from app.services.file_rules import IGNORE_DIRS, detect_file_type, detect_language, is_secret_file, is_supported_file
from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.repository_store import RepositoryStore


class CodebaseService:
    def __init__(self) -> None:
        self.store = RepositoryStore()
        self.repositories: dict[str, RepositoryState] = {
            repository.id: repository for repository in self.store.list_repositories()
        }
        self.evidence: dict[str, EvidenceDTO] = {}

    def list_repositories(self) -> list[RepositoryDTO]:
        return [self._repository_dto(repository) for repository in self.repositories.values()]

    def import_local(self, name: str, local_path: str) -> RepositoryCreateResponse:
        source_path = Path(local_path).expanduser().resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise DomainError("REPOSITORY_NOT_FOUND", "Local repository path does not exist.", 404, {"local_path": local_path})

        repository = RepositoryState(
            id=f"repo_{uuid4().hex[:10]}",
            name=name,
            source_type="local_path",
            source_uri=str(source_path),
            source_path=source_path,
        )
        self.repositories[repository.id] = repository
        self._persist_repository(repository)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    async def upload_zip(self, file: UploadFile, name: str | None) -> RepositoryCreateResponse:
        if not file.filename or not file.filename.endswith(".zip"):
            raise DomainError("INVALID_ARCHIVE", "Only .zip repositories are supported.", 400)

        repository_id = f"repo_{uuid4().hex[:10]}"
        upload_dir = settings.upload_storage_dir
        source_dir = settings.repository_storage_dir / repository_id / "source"
        upload_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)
        zip_path = upload_dir / f"{repository_id}.zip"
        zip_path.write_bytes(await file.read())

        try:
            self._safe_extract_zip(zip_path, source_dir)
        except zipfile.BadZipFile as exc:
            raise DomainError("INVALID_ARCHIVE", "Uploaded file is not a valid zip archive.", 400) from exc

        repository = RepositoryState(
            id=repository_id,
            name=name or Path(file.filename).stem,
            source_type="upload_zip",
            source_uri=str(zip_path),
            source_path=source_dir,
        )
        self.repositories[repository.id] = repository
        self._persist_repository(repository)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    async def upload_folder(self, files: list[UploadFile], relative_paths: list[str], name: str | None) -> RepositoryCreateResponse:
        if not files:
            raise DomainError("INVALID_REPOSITORY", "No files were uploaded.", 400)
        if len(files) != len(relative_paths):
            raise DomainError("INVALID_REPOSITORY", "Uploaded files and relative paths do not match.", 400)

        repository_id = f"repo_{uuid4().hex[:10]}"
        source_dir = settings.repository_storage_dir / repository_id / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        saved_files = 0
        for upload, relative_path in zip(files, relative_paths, strict=True):
            safe_path = self._safe_upload_relative_path(relative_path or upload.filename or "")
            if safe_path is None:
                continue
            target = (source_dir / safe_path).resolve()
            if not str(target).startswith(str(source_dir.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(await upload.read())
            saved_files += 1

        if saved_files == 0:
            raise DomainError("INVALID_REPOSITORY", "No supported non-secret files were uploaded.", 400)

        repository = RepositoryState(
            id=repository_id,
            name=name or Path(relative_paths[0]).parts[0],
            source_type="upload_folder",
            source_uri=str(source_dir),
            source_path=source_dir,
        )
        self.repositories[repository.id] = repository
        self._persist_repository(repository)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    def start_indexing(self, repository_id: str, force_reindex: bool = False) -> dict[str, str]:
        repository = self._get_repository(repository_id)
        if repository.status == "indexing":
            raise DomainError("INDEXING_ALREADY_RUNNING", "Repository indexing is already running.", 409)
        if force_reindex:
            self._clear_index(repository)
        self._index_repository(repository)
        self._persist_repository(repository)
        return {"indexing_job_id": f"job_{uuid4().hex[:10]}", "repository_id": repository.id, "status": "completed"}

    def get_index_status(self, repository_id: str) -> IndexStatusResponse:
        repository = self._get_repository(repository_id)
        total = len(repository.files)
        processed = total if repository.status == "indexed" else 0
        progress = 100 if repository.status == "indexed" else 0
        return IndexStatusResponse(
            repository_id=repository.id,
            status=repository.status,
            current_step=repository.current_step,
            total_files=total,
            processed_files=processed,
            failed_files=repository.failed_files,
            progress=progress,
            started_at=repository.started_at,
            finished_at=repository.finished_at,
            logs=repository.logs[-25:],
            warnings=repository.warnings[-10:],
        )

    def get_overview(self, repository_id: str) -> OverviewResponse:
        repository = self._get_indexed_repository(repository_id)
        modules = self._build_modules(repository)
        important_files = self._important_files(repository)
        detected_stack = self._detect_stack(repository)
        documentation_gaps = self._documentation_gaps(repository)

        return OverviewResponse(
            repository_id=repository.id,
            name=repository.name,
            detected_stack=detected_stack,
            important_files=important_files,
            modules=modules,
            endpoints=[
                EndpointDTO(
                    method=endpoint.method,
                    path=endpoint.path,
                    handler=endpoint.handler,
                    file_path=endpoint.file_path,
                    start_line=endpoint.start_line,
                    end_line=endpoint.end_line,
                )
                for endpoint in repository.endpoints
            ],
            documentation_gaps=documentation_gaps,
            stats={
                "files": len(repository.files),
                "functions": len([symbol for symbol in repository.symbols if symbol.symbol_type in {"function", "method"}]),
                "classes": len([symbol for symbol in repository.symbols if symbol.symbol_type == "class"]),
                "endpoints": len(repository.endpoints),
                "chunks": len(repository.chunks),
                "graph_nodes": len(repository.graph_nodes),
            },
        )

    def chat(self, repository_id: str, message: str, conversation_id: str | None = None) -> ChatResponse:
        repository = self._get_indexed_repository(repository_id)
        question_type = self._classify_question(message)
        matches = self._search_chunks(repository, message, limit=5)
        if not matches:
            return ChatResponse(
                conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
                message_id=f"msg_{uuid4().hex[:10]}",
                question_type=question_type,
                answer="Chua du bang chung de tra loi chac chan. He thong khong tim thay file, symbol hoac relation phu hop trong index hien tai.",
                citations=[],
                evidence_sufficient=False,
                missing_evidence=["Expected code or document evidence", "Expected citation metadata"],
            )

        citations = [self._chunk_to_citation(repository, chunk, "semantic_search") for chunk in matches]
        answer = self._generate_grounded_answer(question_type, message, citations)
        return ChatResponse(
            conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
            message_id=f"msg_{uuid4().hex[:10]}",
            question_type=question_type,
            answer=answer,
            citations=citations,
            evidence_sufficient=True,
        )

    def get_evidence(self, repository_id: str, evidence_id: str) -> EvidenceDTO:
        evidence = self.evidence.get(evidence_id)
        if evidence is None:
            evidence = self.store.get_evidence(evidence_id)
        if evidence is None or evidence.repository_id != repository_id:
            raise DomainError("EVIDENCE_NOT_FOUND", "Evidence not found.", 404, {"evidence_id": evidence_id})
        self.evidence[evidence.evidence_id] = evidence
        return evidence

    def get_graph(self, repository_id: str) -> GraphResponse:
        repository = self._get_indexed_repository(repository_id)
        return GraphResponse(nodes=repository.graph_nodes, edges=repository.graph_edges)

    def get_file_tree(self, repository_id: str) -> list[FileTreeNodeDTO]:
        repository = self._get_indexed_repository(repository_id)
        root: dict[str, dict] = {}
        for file_record in repository.files:
            cursor = root
            parts = file_record.path.split("/")
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor.setdefault(parts[-1], None)
        return self._tree_dict_to_dto(root, "")

    def get_file_content(self, repository_id: str, file_path: str) -> FileContentResponse:
        repository = self._get_indexed_repository(repository_id)
        file_record = next((item for item in repository.files if item.path == file_path), None)
        if file_record is None:
            raise DomainError("FILE_NOT_FOUND", "File not found in index.", 404, {"file_path": file_path})
        content = self._read_text(file_record.absolute_path)
        return FileContentResponse(
            file_path=file_record.path,
            language=file_record.language,
            content=content,
            lines=content.splitlines(),
            symbols=[
                CitationDTO(
                    evidence_id=f"symbol_{symbol.id}",
                    file_path=symbol.file_path,
                    symbol_name=symbol.name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                )
                for symbol in repository.symbols
                if symbol.file_path == file_record.path
            ],
        )

    def search(self, repository_id: str, query: str) -> SearchResponse:
        repository = self._get_indexed_repository(repository_id)
        matches = self._search_chunks(repository, query, limit=10)
        results = []
        for chunk in matches:
            citation = self._chunk_to_citation(repository, chunk, "search")
            results.append(
                SearchResultDTO(
                    evidence_id=citation.evidence_id,
                    file_path=chunk.file_path,
                    title=chunk.symbol_name or Path(chunk.file_path).name,
                    preview=self._preview(chunk.content),
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    score=round(chunk.score, 2),
                )
            )
        return SearchResponse(results=results)

    def _index_repository(self, repository: RepositoryState) -> None:
        repository.status = "indexing"
        repository.started_at = self._now()
        repository.logs = []
        repository.warnings = []
        repository.failed_files = 0
        self._clear_index(repository)

        steps = [
            "scan_repository_files",
            "apply_ignore_rules",
            "parse_source_code",
            "create_chunks",
            "build_code_graph",
            "finalize",
        ]
        for step in steps:
            repository.current_step = step
            repository.logs.append(f"{self._now()} {step}")
            if step == "scan_repository_files":
                repository.files = self._scan_files(repository)
            elif step == "parse_source_code":
                self._parse_files(repository)
            elif step == "create_chunks":
                self._create_file_summary_chunks(repository)
            elif step == "build_code_graph":
                self._build_graph(repository)

        repository.status = "indexed"
        repository.current_step = "completed"
        repository.finished_at = self._now()
        repository.logs.append(f"{repository.finished_at} completed")

    def _scan_files(self, repository: RepositoryState) -> list[FileRecord]:
        files: list[FileRecord] = []
        max_size = settings.max_file_size_mb * 1024 * 1024
        for path in repository.source_path.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORE_DIRS for part in path.relative_to(repository.source_path).parts):
                continue
            if is_secret_file(path.name):
                continue
            if not is_supported_file(path):
                continue
            size = path.stat().st_size
            relative_path = path.relative_to(repository.source_path).as_posix()
            if size > max_size:
                repository.warnings.append(f"Skipped large file: {relative_path}")
                continue
            try:
                content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                repository.failed_files += 1
                repository.warnings.append(f"Could not read file: {relative_path}")
                continue
            files.append(
                FileRecord(
                    path=relative_path,
                    absolute_path=path,
                    language=detect_language(path),
                    file_type=detect_file_type(path),
                    size_bytes=size,
                    content_hash=content_hash,
                )
            )
        return files

    def _parse_files(self, repository: RepositoryState) -> None:
        for file_record in repository.files:
            try:
                text = self._read_text(file_record.absolute_path)
            except UnicodeDecodeError:
                repository.failed_files += 1
                file_record.parse_status = "failed"
                repository.warnings.append(f"Encoding error: {file_record.path}")
                continue

            if file_record.language == "python":
                self._parse_python(repository, file_record, text)
            elif file_record.language in {"javascript", "typescript"}:
                self._parse_js_ts(repository, file_record, text)
            elif file_record.language == "markdown":
                self._parse_markdown(repository, file_record, text)
            else:
                self._add_chunk(repository, file_record.path, "config_section", text, 1, max(1, len(text.splitlines())))

    def _parse_python(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            repository.failed_files += 1
            repository.warnings.append(f"Python parse error: {file_record.path}:{exc.lineno}")
            self._add_chunk(repository, file_record.path, "file_summary", text, 1, max(1, len(text.splitlines())))
            return

        lines = text.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbol_type = "class" if isinstance(node, ast.ClassDef) else "function"
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", node.lineno)
                signature = self._python_signature(node)
                repository.symbols.append(
                    SymbolRecord(
                        id=f"symbol_{uuid4().hex[:10]}",
                        name=node.name,
                        symbol_type=symbol_type,
                        file_path=file_record.path,
                        start_line=start_line,
                        end_line=end_line,
                        signature=signature,
                    )
                )
                chunk_type = "class" if symbol_type == "class" else "function"
                self._add_chunk(repository, file_record.path, chunk_type, "\n".join(lines[start_line - 1 : end_line]), start_line, end_line, node.name)

                endpoint = self._extract_fastapi_endpoint(node, file_record.path)
                if endpoint:
                    repository.endpoints.append(endpoint)
                    self._add_chunk(
                        repository,
                        file_record.path,
                        "endpoint",
                        "\n".join(lines[start_line - 1 : end_line]),
                        start_line,
                        end_line,
                        node.name,
                    )

    def _parse_js_ts(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        lines = text.splitlines()
        function_pattern = re.compile(r"(?:function\s+([A-Z_a-z][\w]*)|const\s+([A-Z_a-z][\w]*)\s*=\s*(?:async\s*)?\(?[^=]*\)?\s*=>)")
        api_pattern = re.compile(r"(axios\.(get|post|put|delete|patch)|fetch)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
        for index, line in enumerate(lines, start=1):
            function_match = function_pattern.search(line)
            if function_match:
                name = function_match.group(1) or function_match.group(2)
                symbol_type = "component" if name[:1].isupper() else "function"
                repository.symbols.append(
                    SymbolRecord(
                        id=f"symbol_{uuid4().hex[:10]}",
                        name=name,
                        symbol_type=symbol_type,
                        file_path=file_record.path,
                        start_line=index,
                        end_line=min(len(lines), index + 12),
                    )
                )
                self._add_chunk(repository, file_record.path, symbol_type, "\n".join(lines[index - 1 : index + 12]), index, min(len(lines), index + 12), name)

            api_match = api_pattern.search(line)
            if api_match:
                method = api_match.group(2).upper() if api_match.group(2) else "GET"
                route_path = api_match.group(3)
                self._add_chunk(repository, file_record.path, "api_call", line, index, index, f"{method} {route_path}")
                repository.graph_nodes.append(GraphNodeDTO(id=f"api_call_{uuid4().hex[:8]}", type="api_call", label=f"{method} {route_path}", file_path=file_record.path))

    def _parse_markdown(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        lines = text.splitlines()
        headings = [(index, line.strip("# ").strip()) for index, line in enumerate(lines, start=1) if line.startswith("#")]
        if not headings:
            self._add_chunk(repository, file_record.path, "doc_section", text, 1, max(1, len(lines)))
            return
        for position, (start, heading) in enumerate(headings):
            end = headings[position + 1][0] - 1 if position + 1 < len(headings) else len(lines)
            self._add_chunk(repository, file_record.path, "doc_section", "\n".join(lines[start - 1 : end]), start, end, heading)

    def _create_file_summary_chunks(self, repository: RepositoryState) -> None:
        existing = {(chunk.file_path, chunk.chunk_type) for chunk in repository.chunks}
        for file_record in repository.files:
            if (file_record.path, "file_summary") in existing:
                continue
            summary = f"{file_record.path} ({file_record.language}, {file_record.file_type})"
            self._add_chunk(repository, file_record.path, "file_summary", summary, 1, 1)

    def _build_graph(self, repository: RepositoryState) -> None:
        nodes: dict[str, GraphNodeDTO] = {}
        edges: list[GraphEdgeDTO] = []
        for file_record in repository.files:
            file_id = self._node_id("file", file_record.path)
            nodes[file_id] = GraphNodeDTO(id=file_id, type="file", label=Path(file_record.path).name, file_path=file_record.path)

        for symbol in repository.symbols:
            symbol_id = self._node_id("symbol", f"{symbol.file_path}:{symbol.name}")
            file_id = self._node_id("file", symbol.file_path)
            nodes[symbol_id] = GraphNodeDTO(id=symbol_id, type=symbol.symbol_type, label=symbol.name, file_path=symbol.file_path)
            edges.append(GraphEdgeDTO(source=file_id, target=symbol_id, type="defines", confidence=0.95))

        for endpoint in repository.endpoints:
            endpoint_id = self._node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            handler_id = self._node_id("symbol", f"{endpoint.file_path}:{endpoint.handler}")
            nodes[endpoint_id] = GraphNodeDTO(id=endpoint_id, type="endpoint", label=f"{endpoint.method} {endpoint.path}", file_path=endpoint.file_path)
            edges.append(GraphEdgeDTO(source=endpoint_id, target=handler_id, type="exposes_endpoint", confidence=0.9))

        endpoint_by_path = {self._normalize_route(endpoint.path): endpoint for endpoint in repository.endpoints}
        for node in list(repository.graph_nodes):
            if node.type != "api_call":
                continue
            route = node.label.split(" ", 1)[-1]
            normalized_route = self._normalize_route(route)
            endpoint = endpoint_by_path.get(normalized_route)
            if endpoint is None:
                endpoint = next(
                    (
                        candidate
                        for candidate in repository.endpoints
                        if normalized_route.endswith(self._normalize_route(candidate.path))
                    ),
                    None,
                )
            if not endpoint:
                continue
            endpoint_id = self._node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            edges.append(GraphEdgeDTO(source=node.id, target=endpoint_id, type="calls_api", confidence=0.72))

        repository.graph_nodes = list(nodes.values()) + repository.graph_nodes
        repository.graph_edges = edges

    def _search_chunks(self, repository: RepositoryState, query: str, limit: int) -> list[ChunkRecord]:
        terms = [term.lower() for term in re.findall(r"[\w/.-]+", query) if len(term) > 1]
        scored: list[ChunkRecord] = []
        for chunk in repository.chunks:
            haystack = f"{chunk.file_path} {chunk.symbol_name or ''} {chunk.content}".lower()
            score = sum(1.0 for term in terms if term in haystack)
            if "login" in query.lower() and ("login" in haystack or "auth" in haystack):
                score += 3
            if any(token in query.lower() for token in ["overview", "kien truc", "architecture"]) and chunk.chunk_type in {"doc_section", "file_summary"}:
                score += 1
            if score > 0:
                clone = ChunkRecord(**{**chunk.__dict__, "score": min(0.99, score / max(len(terms), 1))})
                scored.append(clone)
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def _generate_grounded_answer(self, question_type: str, message: str, citations: list[CitationDTO]) -> str:
        first = citations[0]
        if question_type == "flow_tracing":
            return (
                f"Luong xu ly co evidence chinh tai {first.file_path}:{first.start_line}-{first.end_line}. "
                "He thong tim cac endpoint, symbol va file lien quan trong index, sau do sap xep evidence theo do khop voi cau hoi. "
                "Cac buoc chi nen xem la grounded trong pham vi citation duoc tra ve."
            )
        if question_type == "debugging":
            return (
                f"Bat dau debug tu {first.file_path}:{first.start_line}-{first.end_line}, sau do kiem tra cac citation con lai. "
                "Neu loi lien quan config, he thong chi dung file config duoc index va khong doc .env that."
            )
        if question_type == "architecture_overview":
            return (
                "Kien truc duoc tom tat tu file source, README/docs va metadata parser. "
                f"Evidence manh nhat hien tai la {first.file_path}:{first.start_line}-{first.end_line}."
            )
        return (
            f"He thong tim thay evidence lien quan cho cau hoi '{message}'. "
            f"Ket luan chinh duoc neo vao {first.file_path}:{first.start_line}-{first.end_line} va cac citation kem theo."
        )

    def _chunk_to_citation(self, repository: RepositoryState, chunk: ChunkRecord, retrieval_source: str) -> CitationDTO:
        evidence_id = f"ev_{uuid4().hex[:10]}"
        evidence = EvidenceDTO(
            evidence_id=evidence_id,
            repository_id=repository.id,
            source_type="code" if chunk.chunk_type not in {"doc_section", "config_section"} else "document",
            file_path=chunk.file_path,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            content_preview=self._preview(chunk.content),
            relevance_reason=f"Matched by {retrieval_source} for {chunk.chunk_type}",
            confidence_score=round(max(0.5, chunk.score), 2),
            retrieval_source=retrieval_source,
            metadata={"chunk_type": chunk.chunk_type},
        )
        self.evidence[evidence_id] = evidence
        self.store.save_evidence(evidence)
        return CitationDTO(
            evidence_id=evidence_id,
            file_path=chunk.file_path,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
        )

    def _add_chunk(
        self,
        repository: RepositoryState,
        file_path: str,
        chunk_type: str,
        content: str,
        start_line: int,
        end_line: int,
        symbol_name: str | None = None,
    ) -> None:
        normalized = content.strip()
        if not normalized:
            return
        repository.chunks.append(
            ChunkRecord(
                id=f"chunk_{uuid4().hex[:10]}",
                file_path=file_path,
                chunk_type=chunk_type,
                content=normalized,
                start_line=start_line,
                end_line=end_line,
                symbol_name=symbol_name,
                content_hash=hashlib.sha256(f"{file_path}:{start_line}:{end_line}:{normalized}".encode("utf-8")).hexdigest(),
            )
        )

    def _safe_extract_zip(self, zip_path: Path, target_dir: Path) -> None:
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                destination = (target_dir / member.filename).resolve()
                if not str(destination).startswith(str(target_dir.resolve())):
                    raise DomainError("INVALID_ARCHIVE", "Zip archive contains unsafe paths.", 400)
            archive.extractall(target_dir)

    def _clear_index(self, repository: RepositoryState) -> None:
        repository.files = []
        repository.symbols = []
        repository.endpoints = []
        repository.chunks = []
        repository.graph_nodes = []
        repository.graph_edges = []

    def _persist_repository(self, repository: RepositoryState) -> None:
        self.store.save_repository(repository)

    def _repository_dto(self, repository: RepositoryState) -> RepositoryDTO:
        return RepositoryDTO(
            id=repository.id,
            name=repository.name,
            source_type=repository.source_type,
            source_uri=repository.source_uri,
            status=repository.status,
            total_files=len(repository.files),
            indexed_files=len(repository.files) if repository.status == "indexed" else 0,
            symbols=len(repository.symbols),
            endpoints=len(repository.endpoints),
            chunks=len(repository.chunks),
            graph_nodes=len(repository.graph_nodes),
            last_indexed_at=repository.finished_at,
        )

    def _get_repository(self, repository_id: str) -> RepositoryState:
        repository = self.repositories.get(repository_id)
        if repository is None:
            raise DomainError("REPOSITORY_NOT_FOUND", "Repository not found.", 404, {"repository_id": repository_id})
        return repository

    def _get_indexed_repository(self, repository_id: str) -> RepositoryState:
        repository = self._get_repository(repository_id)
        if repository.status != "indexed":
            raise DomainError("REPOSITORY_NOT_INDEXED", "Repository has not been indexed yet.", 409, {"repository_id": repository_id})
        return repository

    def _important_files(self, repository: RepositoryState) -> list[ImportantFileDTO]:
        important: list[ImportantFileDTO] = []
        for file_record in repository.files:
            name = Path(file_record.path).name.lower()
            if name in {"main.py", "app.py"}:
                important.append(ImportantFileDTO(file_path=file_record.path, reason="Backend entrypoint candidate"))
            elif name.startswith("readme"):
                important.append(ImportantFileDTO(file_path=file_record.path, reason="Project documentation"))
            elif "router" in file_record.path.lower() or "routes" in file_record.path.lower():
                important.append(ImportantFileDTO(file_path=file_record.path, reason="API routing file"))
        return important[:8]

    def _build_modules(self, repository: RepositoryState) -> list[ModuleDTO]:
        counts: dict[str, int] = {}
        for file_record in repository.files:
            parts = file_record.path.split("/")
            module_name = parts[-2] if len(parts) > 1 else "root"
            counts[module_name] = counts.get(module_name, 0) + 1
        return [ModuleDTO(name=name, summary=f"{count} indexed files in this module.", file_count=count) for name, count in sorted(counts.items())[:8]]

    def _detect_stack(self, repository: RepositoryState) -> list[str]:
        stack: set[str] = set()
        if any(file.language == "python" for file in repository.files):
            stack.add("Python")
        if any(file.language in {"javascript", "typescript"} for file in repository.files):
            stack.add("React/JS")
        if repository.endpoints:
            stack.add("FastAPI")
        if any(file.language == "markdown" for file in repository.files):
            stack.add("Markdown docs")
        return sorted(stack)

    def _documentation_gaps(self, repository: RepositoryState) -> list[str]:
        has_readme = any(Path(file.path).name.lower().startswith("readme") for file in repository.files)
        gaps = []
        if not has_readme:
            gaps.append("Repository has no README indexed.")
        if not any("test" in file.path.lower() for file in repository.files):
            gaps.append("No test files were detected.")
        if not repository.endpoints:
            gaps.append("No FastAPI endpoint was detected.")
        return gaps or ["No major documentation gap detected by MVP rules."]

    def _classify_question(self, question: str) -> str:
        normalized = question.lower()
        if any(token in normalized for token in ["kien truc", "architecture", "overview", "tong the"]):
            return "architecture_overview"
        if any(token in normalized for token in ["luong", "flow", "hoat dong"]):
            return "flow_tracing"
        if any(token in normalized for token in ["api", "endpoint", "post", "get"]):
            return "api_question"
        if any(token in normalized for token in ["database", "model", "table", "migration"]):
            return "database_question"
        if any(token in normalized for token in ["error", "loi", "401", "500", "exception"]):
            return "debugging"
        if any(token in normalized for token in ["doc file nao", "moi join", "onboarding"]):
            return "onboarding"
        if any(token in normalized for token in ["impact", "anh huong", "neu sua"]):
            return "impact_analysis"
        return "code_question"

    def _extract_fastapi_endpoint(self, node: ast.AST, file_path: str) -> EndpointRecord | None:
        decorators = getattr(node, "decorator_list", [])
        for decorator in decorators:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            route_path = str(decorator.args[0].value)
            return EndpointRecord(
                method=decorator.func.attr.upper(),
                path=route_path,
                handler=getattr(node, "name", "handler"),
                file_path=file_path,
                start_line=getattr(node, "lineno", 1),
                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            )
        return None

    def _python_signature(self, node: ast.AST) -> str:
        if isinstance(node, ast.ClassDef):
            return f"class {node.name}"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            return f"{prefix} {node.name}({', '.join(args)})"
        return ""

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                return path.read_text(encoding="latin-1")

    def _node_id(self, node_type: str, value: str) -> str:
        return f"{node_type}_{hashlib.sha1(value.encode('utf-8')).hexdigest()[:10]}"

    def _normalize_route(self, route_path: str) -> str:
        normalized = route_path.strip().lower()
        if normalized.startswith("/api"):
            normalized = normalized[4:]
        return normalized.rstrip("/") or "/"

    def _safe_upload_relative_path(self, raw_path: str) -> Path | None:
        normalized = raw_path.replace("\\", "/").strip("/")
        if not normalized:
            return None
        path = Path(normalized)
        if path.is_absolute() or ".." in path.parts:
            return None
        if any(part in IGNORE_DIRS for part in path.parts):
            return None
        if is_secret_file(path.name):
            return None
        if not is_supported_file(path):
            return None
        return path

    def _tree_dict_to_dto(self, tree: dict[str, dict | None], prefix: str) -> list[FileTreeNodeDTO]:
        nodes: list[FileTreeNodeDTO] = []
        for name, child in sorted(tree.items()):
            node_path = f"{prefix}/{name}".strip("/")
            if child is None:
                nodes.append(FileTreeNodeDTO(name=name, path=node_path, type="file"))
            else:
                nodes.append(FileTreeNodeDTO(name=name, path=node_path, type="directory", children=self._tree_dict_to_dto(child, node_path)))
        return nodes

    def _preview(self, content: str, max_length: int = 420) -> str:
        compact = re.sub(r"\s+", " ", content).strip()
        return compact if len(compact) <= max_length else f"{compact[:max_length]}..."

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


codebase_service = CodebaseService()
