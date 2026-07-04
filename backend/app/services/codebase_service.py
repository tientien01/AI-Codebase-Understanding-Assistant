from __future__ import annotations

import shutil
import zipfile
from copy import deepcopy
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
    GraphResponse,
    ImportantFileDTO,
    IndexStatusResponse,
    ModuleDTO,
    OverviewResponse,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryDTO,
    SearchResponse,
    SearchResultDTO,
)
from app.services.chunking_service import ChunkingService
from app.services.evidence_service import EvidenceService
from app.services.file_rules import IGNORE_DIRS, is_secret_file, is_supported_file
from app.services.graph_service import GraphService
from app.services.index_models import IndexingJobRecord, RepositoryState
from app.services.parser_service import ParserService
from app.services.repository_store import RepositoryStore
from app.services.retrieval_service import RetrievalService
from app.services.scanner_service import ScannerService
from app.services.text_utils import preview, read_text, utc_now


class CodebaseService:
    def __init__(self) -> None:
        self.store = RepositoryStore()
        self.chunking = ChunkingService()
        self.scanner = ScannerService()
        self.parser = ParserService(self.chunking)
        self.graph = GraphService()
        self.retrieval = RetrievalService()
        self.evidence = EvidenceService(self.store)
        self.repositories: dict[str, RepositoryState] = {
            repository.id: repository for repository in self.store.list_repositories()
        }

    def list_repositories(self) -> list[RepositoryDTO]:
        return [self._repository_dto(repository) for repository in self.repositories.values()]

    def delete_repository(self, repository_id: str) -> RepositoryDeleteResponse:
        repository = self._get_repository(repository_id)
        self.store.delete_repository(repository_id)
        self.repositories.pop(repository_id, None)
        self._delete_managed_storage(repository)
        self.evidence.clear_repository(repository_id)
        return RepositoryDeleteResponse(deleted=True, repository_id=repository_id)

    async def upload_zip(self, file: UploadFile, name: str | None) -> RepositoryCreateResponse:
        if not file.filename or not file.filename.endswith(".zip"):
            raise DomainError("INVALID_ARCHIVE", "Only .zip repositories are supported.", 400)

        repository_id = f"repo_{uuid4().hex[:10]}"
        upload_dir = settings.upload_storage_dir
        source_dir = settings.repository_storage_dir / repository_id / "source"
        upload_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)
        zip_path = upload_dir / f"{repository_id}.zip"
        upload_bytes = await file.read()
        max_upload_size = settings.max_upload_size_mb * 1024 * 1024
        if len(upload_bytes) > max_upload_size:
            raise DomainError("FILE_TOO_LARGE", "Uploaded archive is larger than the configured limit.", 413)
        zip_path.write_bytes(upload_bytes)

        try:
            extracted_files = self._safe_extract_zip(zip_path, source_dir)
        except zipfile.BadZipFile as exc:
            raise DomainError("INVALID_ARCHIVE", "Uploaded file is not a valid zip archive.", 400) from exc
        if extracted_files == 0:
            raise DomainError("NO_SUPPORTED_FILES", "Archive contains no supported non-secret files.", 400)

        repository = RepositoryState(
            id=repository_id,
            name=name or Path(file.filename).stem,
            source_type="upload_zip",
            source_uri=str(zip_path),
            source_label=file.filename,
            source_path=source_dir,
        )
        return self._create_repository(repository)

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
            if not self._is_relative_to(target, source_dir.resolve()):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            content = await upload.read()
            if len(content) > settings.max_file_size_mb * 1024 * 1024:
                continue
            target.write_bytes(content)
            saved_files += 1

        if saved_files == 0:
            raise DomainError("INVALID_REPOSITORY", "No supported non-secret files were uploaded.", 400)

        repository = RepositoryState(
            id=repository_id,
            name=name or Path(relative_paths[0]).parts[0],
            source_type="upload_folder",
            source_uri=str(source_dir),
            source_label=name or Path(relative_paths[0]).parts[0],
            source_path=source_dir,
        )
        return self._create_repository(repository)

    def start_indexing(self, repository_id: str, force_reindex: bool = False) -> dict[str, str | int]:
        repository = self._get_repository(repository_id)
        if repository.status == "indexing":
            raise DomainError("INDEXING_ALREADY_RUNNING", "Repository indexing is already running.", 409)
        job = IndexingJobRecord(
            id=f"job_{uuid4().hex[:10]}",
            repository_id=repository.id,
            status="running",
            index_version=repository.current_index_version + 1,
            started_at=utc_now(),
        )
        self.store.save_indexing_job(job)
        working_repository = deepcopy(repository)
        try:
            self._index_repository(working_repository, job)
        except Exception as exc:
            if repository.status != "indexed":
                repository.status = "failed"
                repository.current_step = job.current_step
                repository.failed_files = job.failed_files
                repository.warnings = job.warnings
                repository.logs = job.logs
                repository.finished_at = utc_now()
            else:
                repository.current_step = "index_failed_previous_index_retained"
                repository.warnings = [*repository.warnings, "Latest indexing job failed; previous index was retained."]
            job.status = "failed"
            job.error_code = "INDEXING_FAILED"
            job.error_message = str(exc)
            job.finished_at = utc_now()
            self.store.save_indexing_job(job)
            self._persist_repository(repository)
            raise
        self._replace_repository_index(repository, working_repository)
        self._persist_repository(repository)
        self.store.mark_stale_evidence(repository.id, repository.current_index_version)
        self.evidence.clear_repository(repository.id)
        return {"indexing_job_id": job.id, "repository_id": repository.id, "status": job.status, "index_version": job.index_version}

    def get_index_status(self, repository_id: str) -> IndexStatusResponse:
        repository = self._get_repository(repository_id)
        job = self.store.get_latest_indexing_job(repository.id)
        total = job.total_files if job else len(repository.files)
        processed = job.processed_files if job else (total if repository.status == "indexed" else 0)
        progress = 100 if total == 0 and repository.status == "indexed" else int((processed / max(total, 1)) * 100)
        if repository.status == "indexed":
            progress = 100
        return IndexStatusResponse(
            repository_id=repository.id,
            job_id=job.id if job else None,
            status=job.status if job else repository.status,
            current_step=job.current_step if job else repository.current_step,
            index_version=job.index_version if job else repository.current_index_version,
            total_files=total,
            processed_files=processed,
            skipped_files=job.skipped_files if job else 0,
            failed_files=job.failed_files if job else repository.failed_files,
            progress=progress,
            stats={
                "symbols": len(repository.symbols),
                "endpoints": len(repository.endpoints),
                "chunks": len(repository.chunks),
                "graph_nodes": len(repository.graph_nodes),
                "graph_edges": len(repository.graph_edges),
            },
            started_at=job.started_at if job else repository.started_at,
            finished_at=job.finished_at if job else repository.finished_at,
            logs=(job.logs if job else repository.logs)[-25:],
            warnings=(job.warnings if job else repository.warnings)[-10:],
            error_code=job.error_code if job else None,
            error_message=job.error_message if job else None,
        )

    def get_overview(self, repository_id: str) -> OverviewResponse:
        repository = self._get_indexed_repository(repository_id)
        return OverviewResponse(
            repository_id=repository.id,
            name=repository.name,
            detected_stack=self._detect_stack(repository),
            important_files=self._important_files(repository),
            modules=self._build_modules(repository),
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
            documentation_gaps=self._documentation_gaps(repository),
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
        question_type = self.retrieval.classify_question(message)
        matches = self.retrieval.search_chunks(repository, message, limit=5)
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

        citations = [self.evidence.chunk_to_citation(repository, chunk, "semantic_search") for chunk in matches]
        return ChatResponse(
            conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
            message_id=f"msg_{uuid4().hex[:10]}",
            question_type=question_type,
            answer=self.retrieval.generate_grounded_answer(question_type, message, citations),
            citations=citations,
            evidence_sufficient=True,
        )

    def get_evidence(self, repository_id: str, evidence_id: str) -> EvidenceDTO:
        return self.evidence.get_evidence(repository_id, evidence_id)

    def get_graph(self, repository_id: str) -> GraphResponse:
        repository = self._get_indexed_repository(repository_id)
        return GraphResponse(nodes=repository.graph_nodes, edges=repository.graph_edges)

    def get_file_tree(self, repository_id: str) -> list[FileTreeNodeDTO]:
        repository = self._get_indexed_repository(repository_id)
        root: dict[str, dict | None] = {}
        for file_record in repository.files:
            cursor = root
            parts = file_record.path.split("/")
            for part in parts[:-1]:
                child = cursor.setdefault(part, {})
                if child is None:
                    break
                cursor = child
            cursor.setdefault(parts[-1], None)
        return self._tree_dict_to_dto(root, "")

    def get_file_content(self, repository_id: str, file_path: str) -> FileContentResponse:
        repository = self._get_indexed_repository(repository_id)
        file_record = next((item for item in repository.files if item.path == file_path), None)
        if file_record is None:
            raise DomainError("FILE_NOT_FOUND", "File not found in index.", 404, {"file_path": file_path})
        content = read_text(file_record.absolute_path)
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
                    index_version=repository.current_index_version,
                )
                for symbol in repository.symbols
                if symbol.file_path == file_record.path
            ],
        )

    def search(self, repository_id: str, query: str) -> SearchResponse:
        repository = self._get_indexed_repository(repository_id)
        matches = self.retrieval.search_chunks(repository, query, limit=10)
        results = []
        for chunk in matches:
            citation = self.evidence.chunk_to_citation(repository, chunk, "search")
            results.append(
                SearchResultDTO(
                    evidence_id=citation.evidence_id,
                    file_path=chunk.file_path,
                    title=chunk.symbol_name or Path(chunk.file_path).name,
                    preview=preview(chunk.content),
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    score=round(chunk.score, 2),
                )
            )
        return SearchResponse(results=results)

    def _create_repository(self, repository: RepositoryState) -> RepositoryCreateResponse:
        self.repositories[repository.id] = repository
        self._persist_repository(repository)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    def _delete_managed_storage(self, repository: RepositoryState) -> None:
        repository_root = (settings.repository_storage_dir / repository.id).resolve()
        storage_root = settings.repository_storage_dir.resolve()
        if repository_root.exists() and self._is_relative_to(repository_root, storage_root):
            shutil.rmtree(repository_root)

        if repository.source_type == "upload_zip" and repository.source_uri:
            upload_path = Path(repository.source_uri).resolve()
            upload_root = settings.upload_storage_dir.resolve()
            if upload_path.exists() and upload_path.is_file() and self._is_relative_to(upload_path, upload_root):
                upload_path.unlink()

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True

    def _index_repository(self, repository: RepositoryState, job: IndexingJobRecord) -> None:
        repository.status = "indexing"
        repository.started_at = job.started_at or utc_now()
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
            job.current_step = step
            log_line = f"{utc_now()} {step}"
            repository.logs.append(log_line)
            job.logs.append(log_line)
            if step == "scan_repository_files":
                repository.files = self.scanner.scan_files(repository)
                job.total_files = len(repository.files)
            elif step == "parse_source_code":
                self.parser.parse_files(repository)
                job.processed_files = len(repository.files)
                job.failed_files = repository.failed_files
                job.warnings = list(repository.warnings)
            elif step == "create_chunks":
                self.chunking.create_file_summary_chunks(repository)
                job.total_chunks = len(repository.chunks)
            elif step == "build_code_graph":
                self.graph.build_graph(repository)
                job.total_graph_nodes = len(repository.graph_nodes)
                job.total_graph_edges = len(repository.graph_edges)
            self.store.save_indexing_job(job)

        repository.status = "indexed"
        repository.current_index_version = job.index_version
        repository.current_step = "completed"
        repository.finished_at = utc_now()
        repository.logs.append(f"{repository.finished_at} completed")
        repository.failed_files = job.failed_files
        repository.warnings = job.warnings
        job.status = "completed"
        job.current_step = "completed"
        job.processed_files = len(repository.files)
        job.total_chunks = len(repository.chunks)
        job.total_graph_nodes = len(repository.graph_nodes)
        job.total_graph_edges = len(repository.graph_edges)
        job.finished_at = repository.finished_at
        job.logs.append(f"{repository.finished_at} completed")
        self.store.save_indexing_job(job)

    def _safe_extract_zip(self, zip_path: Path, target_dir: Path) -> int:
        target_root = target_dir.resolve()
        max_uncompressed_size = settings.max_upload_size_mb * 1024 * 1024
        max_file_size = settings.max_file_size_mb * 1024 * 1024
        extracted_files = 0
        with zipfile.ZipFile(zip_path) as archive:
            total_uncompressed = sum(member.file_size for member in archive.infolist())
            if total_uncompressed > max_uncompressed_size:
                raise DomainError("REPOSITORY_TOO_LARGE", "Archive content is larger than the configured limit.", 413)

            for member in archive.infolist():
                self._safe_zip_member_path(member, target_root)

            for member in archive.infolist():
                relative_path = self._safe_zip_member_path(member, target_root)
                if member.is_dir() or relative_path is None:
                    continue
                if member.file_size > max_file_size:
                    continue
                destination = target_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_files += 1
        return extracted_files

    def _safe_zip_member_path(self, member: zipfile.ZipInfo, target_root: Path) -> Path | None:
        normalized = member.filename.replace("\\", "/").strip("/")
        if not normalized:
            return None
        relative_path = Path(normalized)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise DomainError("ARCHIVE_PATH_TRAVERSAL", "Zip archive contains unsafe paths.", 400)
        destination = (target_root / relative_path).resolve()
        if not self._is_relative_to(destination, target_root):
            raise DomainError("ARCHIVE_PATH_TRAVERSAL", "Zip archive contains unsafe paths.", 400)
        if member.is_dir():
            return None
        if any(part in IGNORE_DIRS for part in relative_path.parts):
            return None
        if is_secret_file(relative_path.name):
            return None
        if not is_supported_file(relative_path):
            return None
        return relative_path

    def _clear_index(self, repository: RepositoryState) -> None:
        repository.files = []
        repository.symbols = []
        repository.endpoints = []
        repository.chunks = []
        repository.graph_nodes = []
        repository.graph_edges = []

    def _persist_repository(self, repository: RepositoryState) -> None:
        self.store.save_repository(repository)

    def _replace_repository_index(self, repository: RepositoryState, indexed_repository: RepositoryState) -> None:
        repository.status = indexed_repository.status
        repository.current_index_version = indexed_repository.current_index_version
        repository.files = indexed_repository.files
        repository.symbols = indexed_repository.symbols
        repository.endpoints = indexed_repository.endpoints
        repository.chunks = indexed_repository.chunks
        repository.graph_nodes = indexed_repository.graph_nodes
        repository.graph_edges = indexed_repository.graph_edges
        repository.logs = indexed_repository.logs
        repository.warnings = indexed_repository.warnings
        repository.failed_files = indexed_repository.failed_files
        repository.current_step = indexed_repository.current_step
        repository.started_at = indexed_repository.started_at
        repository.finished_at = indexed_repository.finished_at

    def _repository_dto(self, repository: RepositoryState) -> RepositoryDTO:
        return RepositoryDTO(
            id=repository.id,
            name=repository.name,
            source_type=repository.source_type,
            source_label=repository.source_label,
            source_uri=None,
            status=repository.status,
            current_index_version=repository.current_index_version,
            detected_stack=self._detect_stack(repository),
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
        if any(file.language == "typescript" for file in repository.files):
            stack.add("TypeScript")
        if any(file.language == "javascript" for file in repository.files):
            stack.add("JavaScript")
        if any(Path(file.path).suffix.lower() in {".tsx", ".jsx"} for file in repository.files):
            stack.add("React")
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


codebase_service = CodebaseService()
