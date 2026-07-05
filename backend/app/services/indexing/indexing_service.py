from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.core.errors import DomainError
from app.schemas.api import IndexResponse, IndexStatusResponse, StalenessResponse
from app.services.chunking_service import ChunkingService
from app.services.evidence.evidence_service import EvidenceService
from app.services.graph.graph_service import GraphService
from app.services.index_models import IndexingJobRecord, RepositoryState
from app.services.parsing.parser_service import ParserService
from app.services.repositories.repository_service import RepositoryService
from app.services.repositories.repository_store import RepositoryStore
from app.services.scanning.scanner_service import ScannerService
from app.services.text_utils import utc_now


class IndexingService:
    def __init__(
        self,
        store: RepositoryStore,
        repositories: RepositoryService,
        evidence: EvidenceService,
        scanner: ScannerService,
        parser: ParserService,
        chunking: ChunkingService,
        graph: GraphService,
    ) -> None:
        self.store = store
        self.repositories = repositories
        self.evidence = evidence
        self.scanner = scanner
        self.parser = parser
        self.chunking = chunking
        self.graph = graph

    def start_indexing(self, repository_id: str, force_reindex: bool = False) -> IndexResponse:
        repository = self.repositories.get_repository(repository_id)
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
            if repository.status not in {"indexed", "indexed_with_warnings"}:
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
            self.repositories.persist_repository(repository)
            raise
        self.repositories.replace_repository_index(repository, working_repository)
        self.repositories.persist_repository(repository)
        self.store.mark_stale_evidence(repository.id, repository.current_index_version)
        self.evidence.clear_repository(repository.id)
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def get_index_status(self, repository_id: str) -> IndexStatusResponse:
        repository = self.repositories.get_repository(repository_id)
        job = self.store.get_latest_indexing_job(repository.id)
        total = job.total_files if job else len(repository.files)
        processed = job.processed_files if job else (total if repository.status in {"indexed", "indexed_with_warnings"} else 0)
        progress = 100 if total == 0 and repository.status in {"indexed", "indexed_with_warnings"} else int((processed / max(total, 1)) * 100)
        if repository.status in {"indexed", "indexed_with_warnings"}:
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

    def get_staleness(self, repository_id: str) -> StalenessResponse:
        repository = self.repositories.get_repository(repository_id)
        if not repository.finished_at:
            return StalenessResponse(
                repository_id=repository.id,
                is_stale=False,
                current_index_version=repository.current_index_version,
                last_indexed_at=None,
                stale_reason=None,
                recommended_action="index" if repository.status == "created" else None,
            )

        try:
            indexed_at = datetime.fromisoformat(repository.finished_at)
        except ValueError:
            indexed_at = datetime.min.replace(tzinfo=timezone.utc)

        changed_files = 0
        if repository.source_path.exists():
            for path in repository.source_path.rglob("*"):
                if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) > indexed_at:
                    changed_files += 1

        is_stale = changed_files > 0
        return StalenessResponse(
            repository_id=repository.id,
            is_stale=is_stale,
            current_index_version=repository.current_index_version,
            last_indexed_at=repository.finished_at,
            stale_reason="source_files_modified_after_index" if is_stale else None,
            changed_files_count=changed_files,
            recommended_action="reindex" if is_stale else None,
        )

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
                scan_result = self.scanner.scan_files_with_diagnostics(repository)
                repository.files = scan_result.files
                repository.skipped_file_records = [
                    {
                        "file_path": skipped.file_path,
                        "reason": skipped.reason,
                        "matched_pattern": skipped.matched_pattern,
                    }
                    for skipped in scan_result.skipped_files
                ]
                job.total_files = len(repository.files)
                job.skipped_files = len(scan_result.skipped_files)
                job.skipped_file_records = list(repository.skipped_file_records)
                if not repository.files:
                    raise DomainError("NO_INDEXABLE_FILES", "Repository contains no indexable files.", 400)
            elif step == "parse_source_code":
                self.parser.parse_files(repository)
                job.processed_files = len(repository.files)
                job.failed_files = repository.failed_files
                job.warnings = list(repository.warnings)
                job.failed_file_records = list(repository.failed_file_records)
            elif step == "create_chunks":
                self.chunking.create_file_summary_chunks(repository)
                job.total_chunks = len(repository.chunks)
            elif step == "build_code_graph":
                self.graph.build_graph(repository)
                job.total_graph_nodes = len(repository.graph_nodes)
                job.total_graph_edges = len(repository.graph_edges)
            self.store.save_indexing_job(job)

        has_warnings = bool(job.warnings or job.failed_files or job.skipped_files)
        repository.status = "indexed_with_warnings" if has_warnings else "indexed"
        repository.current_index_version = job.index_version
        repository.current_step = "completed"
        repository.finished_at = utc_now()
        repository.logs.append(f"{repository.finished_at} completed")
        repository.failed_files = job.failed_files
        repository.warnings = job.warnings
        job.status = "completed_with_warnings" if has_warnings else "completed"
        job.current_step = "completed"
        job.processed_files = len(repository.files)
        job.total_chunks = len(repository.chunks)
        job.total_graph_nodes = len(repository.graph_nodes)
        job.total_graph_edges = len(repository.graph_edges)
        job.finished_at = repository.finished_at
        job.logs.append(f"{repository.finished_at} completed")
        self.store.save_indexing_job(job)

    def _clear_index(self, repository: RepositoryState) -> None:
        repository.files = []
        repository.symbols = []
        repository.endpoints = []
        repository.chunks = []
        repository.graph_nodes = []
        repository.graph_edges = []
