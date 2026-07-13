from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from inspect import signature
from threading import Event, Lock, Thread
from typing import Callable
from uuid import uuid4

from app.core.errors import DomainError
from app.schemas.api import IndexResponse, IndexStatusResponse, StalenessResponse
from app.services.chunking_service import ChunkingService
from app.services.evidence.evidence_service import EvidenceService
from app.services.enrichment.semantic_enrichment_service import SemanticEnrichmentService
from app.services.graph.graph_service import GraphService
from app.services.index_models import IndexingJobRecord, RepositoryState
from app.services.indexing.job_queue import IndexJobQueuePort, QueueUnavailableError
from app.services.indexing.job_state_store import JobStateStore
from app.services.parsing.parser_service import ParserService
from app.services.parsing.debug_output_service import ParseDebugOutputService
from app.services.repositories.repository_service import RepositoryService
from app.services.repositories.repository_port import RepositoryStorePort
from app.services.scanning.scanner_service import ScannerService
from app.services.text_utils import utc_now


class IndexingCancelled(Exception):
    pass


class IndexingAuthorityLost(Exception):
    """Stop a stale production worker without persisting another side effect."""


class IndexingJobControl:
    def __init__(self, authority_check: Callable[[], None] | None = None) -> None:
        self.pause_requested = Event()
        self.resume_requested = Event()
        self.cancel_requested = Event()
        self.resume_requested.set()
        self.authority_check = authority_check

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
        store: RepositoryStorePort,
        repositories: RepositoryService,
        evidence: EvidenceService,
        scanner: ScannerService,
        parser: ParserService,
        chunking: ChunkingService,
        graph: GraphService,
        job_queue: IndexJobQueuePort | None = None,
        job_state_store: JobStateStore | None = None,
    ) -> None:
        self.store = store
        self.repositories = repositories
        self.evidence = evidence
        self.scanner = scanner
        self.parser = parser
        self.chunking = chunking
        self.graph = graph
        self.job_queue = job_queue
        self.job_state_store = job_state_store
        self.enrichment = SemanticEnrichmentService(chunking)
        self.parse_debug_output = ParseDebugOutputService()
        self._controls: dict[str, IndexingJobControl] = {}
        self._controls_lock = Lock()

    def start_indexing(self, repository_id: str, force_reindex: bool = False) -> IndexResponse:
        repository, job, control, previous_status = self._prepare_indexing_job(repository_id)
        self._execute_indexing(repository, job, control, previous_status, force_reindex=force_reindex)
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def start_indexing_background(self, repository_id: str, force_reindex: bool = False) -> IndexResponse:
        if self.job_queue is not None:
            repository, job, _, _ = self._prepare_indexing_job(
                repository_id, initial_status="queued"
            )
            try:
                self.job_queue.enqueue(job.id)
            except QueueUnavailableError as exc:
                raise DomainError(
                    "INDEX_QUEUE_UNAVAILABLE",
                    "Index job was saved but could not be published.",
                    503,
                    {"job_id": job.id, "retryable": True},
                ) from exc
            return IndexResponse(
                indexing_job_id=job.id,
                repository_id=repository.id,
                status=job.status,
                index_version=job.index_version,
            )

        repository, job, control, previous_status = self._prepare_indexing_job(repository_id)
        Thread(
            target=self._execute_indexing,
            args=(repository, job, control, previous_status, False, force_reindex),
            daemon=True,
        ).start()
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def execute_persisted_job(
        self,
        job_id: str,
        repository_id: str,
        authority_check: Callable[[], None] | None = None,
    ) -> None:
        """Reload and execute an already claimed production job in a worker."""
        repository = self.repositories.get_repository(repository_id)
        job = self.store.get_indexing_job(repository_id, job_id)
        if job is None:
            raise DomainError(
                "INDEXING_JOB_NOT_FOUND",
                "Indexing job not found.",
                404,
                {"job_id": job_id},
            )
        previous_status = "created"
        if repository.current_index_version > 0:
            previous_status = "indexed_with_warnings" if repository.warnings else "indexed"
        control = IndexingJobControl(authority_check)
        with self._controls_lock:
            self._controls[job.id] = control
        self._execute_indexing(
            repository,
            job,
            control,
            previous_status,
            raise_errors=True,
            force_reindex=True,
        )

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
        if self.job_state_store is not None:
            job = self.store.get_indexing_job(repository.id, job_id)
            if job is None:
                raise DomainError("INDEXING_JOB_NOT_FOUND", "Indexing job not found.", 404, {"job_id": job_id})
            state = self.job_state_store.request_cancellation(job_id)
            return IndexResponse(
                indexing_job_id=job.id,
                repository_id=repository.id,
                status="cancelling" if state == "running" else state,
                index_version=job.index_version,
            )
        job = self._get_controllable_job(repository.id, job_id)
        if job.status not in {"running", "paused"}:
            raise DomainError("INDEXING_JOB_NOT_RUNNING", "Only a running or paused indexing job can be cancelled.", 409, {"job_id": job_id})
        control = self._control_for_job(job_id)
        control.cancel()
        job.status = "cancelling"
        job.logs.append(f"{utc_now()} cancelling")
        self.store.save_indexing_job(job)
        return IndexResponse(indexing_job_id=job.id, repository_id=repository.id, status=job.status, index_version=job.index_version)

    def _prepare_indexing_job(
        self, repository_id: str, *, initial_status: str = "running"
    ) -> tuple[RepositoryState, IndexingJobRecord, IndexingJobControl, str]:
        repository = self.repositories.get_repository(repository_id)
        if repository.status == "indexing":
            raise DomainError("INDEXING_ALREADY_RUNNING", "Repository indexing is already running.", 409)
        previous_status = repository.status
        job = IndexingJobRecord(
            id=f"job_{uuid4().hex[:10]}",
            repository_id=repository.id,
            status=initial_status,
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
        if initial_status == "running":
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
        force_reindex: bool = False,
    ) -> None:
        working_repository = deepcopy(repository)
        try:
            self._index_repository(working_repository, job, control, previous_status, force_reindex)
        except IndexingAuthorityLost:
            raise
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
            if control.authority_check is not None:
                control.authority_check()
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

    def _index_repository(
        self,
        repository: RepositoryState,
        job: IndexingJobRecord,
        control: IndexingJobControl,
        previous_status: str,
        force_reindex: bool = False,
    ) -> None:
        previous_repository = deepcopy(repository)
        previous_repository.status = previous_status
        can_incremental = (
            not force_reindex
            and previous_status in {"indexed", "indexed_with_warnings"}
            and previous_repository.current_index_version > 0
            and bool(previous_repository.files)
        )
        repository.status = "indexing"
        repository.started_at = job.started_at or utc_now()
        repository.logs = []
        repository.warnings = []
        repository.failed_files = 0
        if force_reindex or not can_incremental:
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
                incremental_plan = self._incremental_plan(previous_repository, scan_result.files) if can_incremental else None
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
                if incremental_plan is not None:
                    repository.logs.append(
                        f"{utc_now()} incremental_plan changed={len(incremental_plan['changed'])} deleted={len(incremental_plan['deleted'])} unchanged={len(incremental_plan['unchanged'])}"
                    )
                    job.logs.append(repository.logs[-1])
                    self._prepare_incremental_repository(repository, previous_repository, incremental_plan)
            elif step == "parse_source_code":
                def after_file() -> None:
                    job.processed_files += 1
                    self._check_control(repository, job, control)
                    self.store.save_indexing_job(job)

                parse_repository = self._parse_scope(repository)
                if not parse_repository.files:
                    job.processed_files = len(repository.files)
                elif "before_file" in signature(self.parser.parse_files).parameters:
                    self.parser.parse_files(parse_repository, before_file=lambda: self._check_control(repository, job, control), after_file=after_file)
                else:
                    self.parser.parse_files(parse_repository)
                    job.processed_files = len(parse_repository.files)
                if parse_repository is not repository:
                    self._merge_incremental_parse(repository, parse_repository)
                    job.processed_files = len(repository.files)
                job.failed_files = repository.failed_files
                job.warnings = list(repository.warnings)
                job.failed_file_records = list(repository.failed_file_records)
            elif step == "create_chunks":
                self.chunking.create_file_summary_chunks(repository)
                job.total_chunks = len(repository.chunks)
            elif step == "build_code_graph":
                self.graph.build_graph(repository)
                self.enrichment.enrich(repository)
                self.graph.schema.normalize_repository_graph(repository)
                job.total_graph_nodes = len(repository.graph_nodes)
                job.total_graph_edges = len(repository.graph_edges)
                job.total_chunks = len(repository.chunks)
            self.store.save_indexing_job(job)

        has_warnings = bool(job.warnings or job.failed_files)
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

    def _incremental_plan(self, previous: RepositoryState, scanned_files: list) -> dict[str, set[str]]:
        previous_by_path = {file.path: file for file in previous.files}
        scanned_by_path = {file.path: file for file in scanned_files}
        changed = {
            path
            for path, file in scanned_by_path.items()
            if path not in previous_by_path or previous_by_path[path].content_hash != file.content_hash
        }
        deleted = set(previous_by_path) - set(scanned_by_path)
        unchanged = set(scanned_by_path) - changed
        return {"changed": changed, "deleted": deleted, "unchanged": unchanged}

    def _prepare_incremental_repository(
        self,
        repository: RepositoryState,
        previous: RepositoryState,
        plan: dict[str, set[str]],
    ) -> None:
        affected_paths = plan["changed"] | plan["deleted"]
        removed_node_ids = {
            node.id
            for node in previous.graph_nodes
            if node.file_path in affected_paths
            or node.scope_path in affected_paths
            or any(node.id == self._file_node_id(path) for path in affected_paths)
        }
        structural_types = {"folder", "file", "class", "schema", "model", "function", "method", "component", "endpoint"}
        repository.symbols = [symbol for symbol in previous.symbols if symbol.file_path not in affected_paths]
        repository.endpoints = [endpoint for endpoint in previous.endpoints if endpoint.file_path not in affected_paths]
        repository.chunks = [chunk for chunk in previous.chunks if chunk.file_path not in affected_paths]
        repository.graph_nodes = [
            node
            for node in previous.graph_nodes
            if node.id not in removed_node_ids and node.type not in structural_types
        ]
        repository.graph_edges = [
            edge
            for edge in previous.graph_edges
            if edge.source not in removed_node_ids and edge.target not in removed_node_ids
        ]
        repository.parse_diagnostics = [
            item
            for item in previous.parse_diagnostics
            if item.get("file_path") not in affected_paths
        ]
        repository.failed_file_records = [
            item
            for item in previous.failed_file_records
            if item.get("file_path") not in affected_paths
        ]
        repository._incremental_changed_paths = plan["changed"]  # type: ignore[attr-defined]

    def _parse_scope(self, repository: RepositoryState) -> RepositoryState:
        changed_paths = getattr(repository, "_incremental_changed_paths", None)
        if changed_paths is None:
            return repository
        return RepositoryState(
            id=repository.id,
            name=repository.name,
            source_type=repository.source_type,
            source_uri=repository.source_uri,
            source_path=repository.source_path,
            source_label=repository.source_label,
            status=repository.status,
            current_index_version=repository.current_index_version,
            files=[file for file in repository.files if file.path in changed_paths],
        )

    def _merge_incremental_parse(self, repository: RepositoryState, parsed: RepositoryState) -> None:
        repository.symbols.extend(parsed.symbols)
        repository.endpoints.extend(parsed.endpoints)
        repository.chunks.extend(parsed.chunks)
        repository.graph_nodes.extend(parsed.graph_nodes)
        repository.graph_edges.extend(parsed.graph_edges)
        repository.warnings.extend(parsed.warnings)
        repository.failed_files += parsed.failed_files
        repository.failed_file_records.extend(parsed.failed_file_records)
        repository.parse_diagnostics.extend(parsed.parse_diagnostics)

    def _file_node_id(self, file_path: str) -> str:
        from app.services.text_utils import node_id

        return node_id("file", file_path)

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
        if control.authority_check is not None:
            control.authority_check()
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
