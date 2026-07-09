from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from inspect import signature
from threading import Event, Lock, Thread
from uuid import uuid4

from app.core.errors import DomainError
from app.schemas.api import IndexResponse, IndexStatusResponse, StalenessResponse
from app.services.chunking_service import ChunkingService
from app.services.evidence.evidence_service import EvidenceService
from app.services.graph.graph_service import GraphService
from app.services.index_models import IndexingJobRecord, RepositoryState
from app.services.parsing.parser_service import ParserService
from app.services.parsing.debug_output_service import ParseDebugOutputService
from app.services.repositories.repository_service import RepositoryService
from app.services.repositories.repository_store import RepositoryStore
from app.services.scanning.scanner_service import ScannerService
from app.services.text_utils import utc_now


class IndexingCancelled(Exception):
    pass


class IndexingJobControl:
    def __init__(self) -> None:
        self.pause_requested = Event()
        self.resume_requested = Event()
        self.cancel_requested = Event()
        self.resume_requested.set()

    def pause(self) -> None:
        self.pause_requested.set()
        self.resume_requested.clear()

    def resume(self) -> None:
        self.pause_requested.clear()
        self.resume_requested.set()

    def cancel(self) -> None:
        self.cancel_requested.set()
        self.resume_requested.set()


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
        self.parse_debug_output = ParseDebugOutputService()
        self._controls: dict[str, IndexingJobControl] = {}
        self._controls_lock = Lock()

    def start_indexing(self, repository_id: str, force_reindex: bool = False) -> IndexResponse:
        repository, job, control, previous_status = self._prepare_indexing_job(repository_id)
        self._execute_indexing(repository, job, control, previous_status)
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def start_indexing_background(self, repository_id: str, force_reindex: bool = False) -> IndexResponse:
        repository, job, control, previous_status = self._prepare_indexing_job(repository_id)
        Thread(
            target=self._execute_indexing,
            args=(repository, job, control, previous_status, False),
            daemon=True,
        ).start()
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def pause_indexing_job(self, repository_id: str, job_id: str) -> IndexResponse:
        repository = self.repositories.get_repository(repository_id)
        job = self._get_controllable_job(repository.id, job_id)
        if job.status != "running":
            raise DomainError("INDEXING_JOB_NOT_RUNNING", "Only a running indexing job can be paused.", 409, {"job_id": job_id})
        control = self._control_for_job(job_id)
        control.pause()
        job.status = "paused"
        job.logs.append(f"{utc_now()} paused")
        self.store.save_indexing_job(job)
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def resume_indexing_job(self, repository_id: str, job_id: str) -> IndexResponse:
        repository = self.repositories.get_repository(repository_id)
        job = self._get_controllable_job(repository.id, job_id)
        if job.status != "paused":
            raise DomainError("INDEXING_JOB_NOT_PAUSED", "Only a paused indexing job can be resumed.", 409, {"job_id": job_id})
        control = self._control_for_job(job_id)
        control.resume()
        job.status = "running"
        job.logs.append(f"{utc_now()} resumed")
        self.store.save_indexing_job(job)
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def cancel_indexing_job(self, repository_id: str, job_id: str) -> IndexResponse:
        repository = self.repositories.get_repository(repository_id)
        job = self._get_controllable_job(repository.id, job_id)
        if job.status not in {"running", "paused"}:
            raise DomainError("INDEXING_JOB_NOT_RUNNING", "Only a running or paused indexing job can be cancelled.", 409, {"job_id": job_id})
        control = self._control_for_job(job_id)
        control.cancel()
        job.status = "cancelling"
        job.logs.append(f"{utc_now()} cancelling")
        self.store.save_indexing_job(job)
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def _prepare_indexing_job(self, repository_id: str) -> tuple[RepositoryState, IndexingJobRecord, IndexingJobControl, str]:
        repository = self.repositories.get_repository(repository_id)
        if repository.status == "indexing":
            raise DomainError("INDEXING_ALREADY_RUNNING", "Repository indexing is already running.", 409)
        previous_status = repository.status
        job = IndexingJobRecord(
            id=f"job_{uuid4().hex[:10]}",
            repository_id=repository.id,
            status="running",
            index_version=repository.current_index_version + 1,
            started_at=utc_now(),
        )
        repository.status = "indexing"
        repository.current_step = "queued"
        repository.started_at = job.started_at
        repository.finished_at = None
        repository.logs = [f"{job.started_at} queued"]
        self.store.save_indexing_job(job)
        self.repositories.persist_repository_metadata(repository)
        control = IndexingJobControl()
        with self._controls_lock:
            self._controls[job.id] = control
        return repository, job, control, previous_status

    def _execute_indexing(
        self,
        repository: RepositoryState,
        job: IndexingJobRecord,
        control: IndexingJobControl,
        previous_status: str,
        raise_errors: bool = True,
    ) -> None:
        working_repository = deepcopy(repository)
        try:
            self._index_repository(working_repository, job, control)
        except IndexingCancelled:
            if previous_status in {"indexed", "indexed_with_warnings"}:
                repository.status = previous_status
                repository.current_step = "cancelled_previous_index_retained"
                repository.warnings = [*repository.warnings, "Latest indexing job was cancelled; previous index was retained."]
            else:
                repository.status = "created"
                repository.current_step = "cancelled"
            repository.finished_at = utc_now()
            job.status = "cancelled"
            job.current_step = "cancelled"
            job.finished_at = repository.finished_at
            job.logs.append(f"{repository.finished_at} cancelled")
            self.store.save_indexing_job(job)
            self.repositories.persist_repository_metadata(repository)
        except Exception as exc:
            if previous_status not in {"indexed", "indexed_with_warnings"}:
                repository.status = "failed"
                repository.current_step = job.current_step
                repository.failed_files = job.failed_files
                repository.warnings = job.warnings
                repository.logs = job.logs
                repository.finished_at = utc_now()
            else:
                repository.status = previous_status
                repository.current_step = "index_failed_previous_index_retained"
                repository.warnings = [*repository.warnings, "Latest indexing job failed; previous index was retained."]
            job.status = "failed"
            job.error_code = "INDEXING_FAILED"
            job.error_message = str(exc)
            job.finished_at = utc_now()
            self.store.save_indexing_job(job)
            self.repositories.persist_repository_metadata(repository)
            if raise_errors:
                raise
        else:
            self.repositories.replace_repository_index(repository, working_repository)
            self.repositories.persist_repository(repository)
            self.store.mark_stale_evidence(repository.id, repository.current_index_version)
            self.evidence.clear_repository(repository.id)
        finally:
            with self._controls_lock:
                self._controls.pop(job.id, None)

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

    def _index_repository(self, repository: RepositoryState, job: IndexingJobRecord, control: IndexingJobControl) -> None:
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
            self._check_control(repository, job, control)
            repository.current_step = step
            job.current_step = step
            log_line = f"{utc_now()} {step}"
            repository.logs.append(log_line)
            job.logs.append(log_line)
            if step == "scan_repository_files":
                scan_result = self.scanner.scan_files_with_diagnostics(repository)
                repository.files = scan_result.files
                repository.project_fingerprint = self._project_fingerprint(repository)
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
                def after_file() -> None:
                    job.processed_files += 1
                    self._check_control(repository, job, control)
                    self.store.save_indexing_job(job)

                if "before_file" in signature(self.parser.parse_files).parameters:
                    self.parser.parse_files(repository, before_file=lambda: self._check_control(repository, job, control), after_file=after_file)
                else:
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
        self._write_parse_debug_output(repository)
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

    def _write_parse_debug_output(self, repository: RepositoryState) -> None:
        try:
            artifact_path = self.parse_debug_output.write(repository)
        except OSError as exc:
            repository.warnings.append(f"Could not write parse debug output: {exc}")
            return
        repository.logs.append(f"{utc_now()} parse_debug_output_written {artifact_path}")

    def _project_fingerprint(self, repository: RepositoryState) -> str | None:
        if not repository.files:
            return None
        digest = hashlib.sha256()
        for file in sorted(repository.files, key=lambda item: item.path):
            digest.update(file.path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(file.size_bytes).encode("ascii"))
            digest.update(b"\0")
            digest.update(file.content_hash.encode("ascii"))
            digest.update(b"\n")
        return digest.hexdigest()

    def _check_control(self, repository: RepositoryState, job: IndexingJobRecord, control: IndexingJobControl) -> None:
        if control.cancel_requested.is_set():
            raise IndexingCancelled()
        if not control.pause_requested.is_set():
            return
        job.status = "paused"
        repository.current_step = job.current_step
        self.store.save_indexing_job(job)
        control.resume_requested.wait()
        if control.cancel_requested.is_set():
            raise IndexingCancelled()
        job.status = "running"
        self.store.save_indexing_job(job)

    def _get_controllable_job(self, repository_id: str, job_id: str) -> IndexingJobRecord:
        job = self.store.get_indexing_job(repository_id, job_id)
        if job is None:
            raise DomainError("INDEXING_JOB_NOT_FOUND", "Indexing job not found.", 404, {"job_id": job_id})
        self._control_for_job(job_id)
        return job

    def _control_for_job(self, job_id: str) -> IndexingJobControl:
        with self._controls_lock:
            control = self._controls.get(job_id)
        if control is None:
            raise DomainError("INDEXING_JOB_NOT_CONTROLLABLE", "This indexing job is no longer running.", 409, {"job_id": job_id})
        return control
