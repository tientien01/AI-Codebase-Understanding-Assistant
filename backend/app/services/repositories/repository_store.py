from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select, update

from app.db.models import (
    ChunkRecordORM,
    EndpointRecordORM,
    EvidenceORM,
    FileRecordORM,
    GraphEdgeORM,
    GraphNodeORM,
    IndexingJobORM,
    RepositoryORM,
    SymbolRecordORM,
)
from app.db.session import SessionLocal, init_db
from app.schemas.api import EvidenceDTO, GraphEdgeDTO, GraphNodeDTO
from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, IndexingJobRecord, RepositoryState, SymbolRecord


class RepositoryStore:
    def __init__(self) -> None:
        init_db()

    def list_repositories(self) -> list[RepositoryState]:
        with SessionLocal() as session:
            repositories = session.scalars(select(RepositoryORM).order_by(RepositoryORM.name)).all()
            return [self._load_repository_state(session, repository) for repository in repositories]

    def save_repository(self, repository: RepositoryState) -> None:
        with SessionLocal.begin() as session:
            session.merge(
                RepositoryORM(
                    id=repository.id,
                    name=repository.name,
                    source_type=repository.source_type,
                    source_uri=repository.source_uri,
                    source_label=repository.source_label,
                    source_path=str(repository.source_path),
                    status=repository.status,
                    current_index_version=repository.current_index_version,
                    logs_json=json.dumps(repository.logs),
                    warnings_json=json.dumps(repository.warnings),
                    failed_files=repository.failed_files,
                    current_step=repository.current_step,
                    started_at=repository.started_at,
                    finished_at=repository.finished_at,
                )
            )
            self._delete_index_records(session, repository.id)
            session.add_all(
                [
                    FileRecordORM(
                        repository_id=repository.id,
                        index_version=repository.current_index_version,
                        path=file.path,
                        absolute_path=str(file.absolute_path),
                        language=file.language,
                        file_type=file.file_type,
                        size_bytes=file.size_bytes,
                        content_hash=file.content_hash,
                        parse_status=file.parse_status,
                    )
                    for file in repository.files
                ]
            )
            session.add_all(
                [
                    SymbolRecordORM(
                        id=symbol.id,
                        repository_id=repository.id,
                        index_version=repository.current_index_version,
                        name=symbol.name,
                        symbol_type=symbol.symbol_type,
                        file_path=symbol.file_path,
                        start_line=symbol.start_line,
                        end_line=symbol.end_line,
                        signature=symbol.signature,
                    )
                    for symbol in repository.symbols
                ]
            )
            session.add_all(
                [
                    EndpointRecordORM(
                        repository_id=repository.id,
                        index_version=repository.current_index_version,
                        method=endpoint.method,
                        path=endpoint.path,
                        handler=endpoint.handler,
                        file_path=endpoint.file_path,
                        start_line=endpoint.start_line,
                        end_line=endpoint.end_line,
                    )
                    for endpoint in repository.endpoints
                ]
            )
            session.add_all(
                [
                    ChunkRecordORM(
                        id=chunk.id,
                        repository_id=repository.id,
                        index_version=repository.current_index_version,
                        file_path=chunk.file_path,
                        chunk_type=chunk.chunk_type,
                        content=chunk.content,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        symbol_name=chunk.symbol_name,
                        content_hash=chunk.content_hash,
                    )
                    for chunk in repository.chunks
                ]
            )
            session.add_all(
                [
                    GraphNodeORM(
                        id=f"{repository.id}:{node.id}",
                        repository_id=repository.id,
                        index_version=repository.current_index_version,
                        type=node.type,
                        label=node.label,
                        file_path=node.file_path,
                    )
                    for node in repository.graph_nodes
                ]
            )
            session.add_all(
                [
                    GraphEdgeORM(
                        repository_id=repository.id,
                        index_version=repository.current_index_version,
                        source=edge.source,
                        target=edge.target,
                        type=edge.type,
                        confidence=edge.confidence,
                    )
                    for edge in repository.graph_edges
                ]
            )

    def save_indexing_job(self, job: IndexingJobRecord) -> None:
        with SessionLocal.begin() as session:
            session.merge(
                IndexingJobORM(
                    id=job.id,
                    repository_id=job.repository_id,
                    index_version=job.index_version,
                    status=job.status,
                    current_step=job.current_step,
                    total_files=job.total_files,
                    processed_files=job.processed_files,
                    skipped_files=job.skipped_files,
                    failed_files=job.failed_files,
                    total_chunks=job.total_chunks,
                    total_graph_nodes=job.total_graph_nodes,
                    total_graph_edges=job.total_graph_edges,
                    started_at=job.started_at,
                    finished_at=job.finished_at,
                    logs_json=json.dumps(job.logs),
                    warnings_json=json.dumps(job.warnings),
                    skipped_files_json=json.dumps(job.skipped_file_records),
                    failed_files_json=json.dumps(job.failed_file_records),
                    error_code=job.error_code,
                    error_message=job.error_message,
                )
            )

    def get_latest_indexing_job(self, repository_id: str) -> IndexingJobRecord | None:
        with SessionLocal() as session:
            row = session.scalars(
                select(IndexingJobORM)
                .where(IndexingJobORM.repository_id == repository_id)
                .order_by(IndexingJobORM.started_at.desc(), IndexingJobORM.id.desc())
            ).first()
            if row is None:
                return None
            return self._indexing_job_record(row)

    def list_indexing_jobs(self, repository_id: str) -> list[IndexingJobRecord]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(IndexingJobORM)
                .where(IndexingJobORM.repository_id == repository_id)
                .order_by(IndexingJobORM.started_at.desc(), IndexingJobORM.id.desc())
            ).all()
            return [self._indexing_job_record(row) for row in rows]

    def get_indexing_job(self, repository_id: str, job_id: str) -> IndexingJobRecord | None:
        with SessionLocal() as session:
            row = session.get(IndexingJobORM, job_id)
            if row is None or row.repository_id != repository_id:
                return None
            return self._indexing_job_record(row)

    def delete_repository(self, repository_id: str) -> None:
        with SessionLocal.begin() as session:
            self._delete_index_records(session, repository_id)
            for model in (IndexingJobORM, EvidenceORM):
                session.execute(delete(model).where(model.repository_id == repository_id))
            session.execute(delete(RepositoryORM).where(RepositoryORM.id == repository_id))

    def mark_stale_evidence(self, repository_id: str, current_index_version: int) -> None:
        with SessionLocal.begin() as session:
            session.execute(
                update(EvidenceORM)
                .where(EvidenceORM.repository_id == repository_id)
                .where(EvidenceORM.index_version < current_index_version)
                .values(is_stale=1)
            )

    def save_evidence(self, evidence: EvidenceDTO) -> None:
        with SessionLocal.begin() as session:
            session.merge(
                EvidenceORM(
                    evidence_id=evidence.evidence_id,
                    repository_id=evidence.repository_id,
                    index_version=evidence.index_version,
                    source_type=evidence.source_type,
                    file_path=evidence.file_path,
                    symbol_name=evidence.symbol_name,
                    start_line=evidence.start_line,
                    end_line=evidence.end_line,
                    content_preview=evidence.content_preview,
                    relevance_reason=evidence.relevance_reason,
                    confidence_score=evidence.confidence_score,
                    retrieval_source=evidence.retrieval_source,
                    is_stale=1 if evidence.is_stale else 0,
                    metadata_json=json.dumps(evidence.metadata),
                )
            )

    def get_evidence(self, evidence_id: str) -> EvidenceDTO | None:
        with SessionLocal() as session:
            row = session.get(EvidenceORM, evidence_id)
            if row is None:
                return None
            return EvidenceDTO(
                evidence_id=row.evidence_id,
                repository_id=row.repository_id,
                index_version=row.index_version,
                source_type=row.source_type,
                file_path=row.file_path,
                symbol_name=row.symbol_name,
                start_line=row.start_line,
                end_line=row.end_line,
                content_preview=row.content_preview,
                relevance_reason=row.relevance_reason,
                confidence_score=row.confidence_score,
                retrieval_source=row.retrieval_source,
                is_stale=bool(row.is_stale),
                metadata=json.loads(row.metadata_json or "{}"),
            )

    def _delete_index_records(self, session, repository_id: str) -> None:
        for model in (FileRecordORM, SymbolRecordORM, EndpointRecordORM, ChunkRecordORM, GraphNodeORM, GraphEdgeORM):
            session.execute(delete(model).where(model.repository_id == repository_id))

    def _load_repository_state(self, session, repository: RepositoryORM) -> RepositoryState:
        files = session.scalars(select(FileRecordORM).where(FileRecordORM.repository_id == repository.id)).all()
        symbols = session.scalars(select(SymbolRecordORM).where(SymbolRecordORM.repository_id == repository.id)).all()
        endpoints = session.scalars(select(EndpointRecordORM).where(EndpointRecordORM.repository_id == repository.id)).all()
        chunks = session.scalars(select(ChunkRecordORM).where(ChunkRecordORM.repository_id == repository.id)).all()
        graph_nodes = session.scalars(select(GraphNodeORM).where(GraphNodeORM.repository_id == repository.id)).all()
        graph_edges = session.scalars(select(GraphEdgeORM).where(GraphEdgeORM.repository_id == repository.id)).all()
        return RepositoryState(
            id=repository.id,
            name=repository.name,
            source_type=repository.source_type,
            source_uri=repository.source_uri,
            source_label=repository.source_label,
            source_path=Path(repository.source_path),
            status=repository.status,
            current_index_version=repository.current_index_version,
            files=[
                FileRecord(
                    path=file.path,
                    absolute_path=Path(file.absolute_path),
                    language=file.language,
                    file_type=file.file_type,
                    size_bytes=file.size_bytes,
                    content_hash=file.content_hash,
                    parse_status=file.parse_status,
                )
                for file in files
            ],
            symbols=[
                SymbolRecord(
                    id=symbol.id,
                    name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    file_path=symbol.file_path,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    signature=symbol.signature,
                )
                for symbol in symbols
            ],
            endpoints=[
                EndpointRecord(
                    method=endpoint.method,
                    path=endpoint.path,
                    handler=endpoint.handler,
                    file_path=endpoint.file_path,
                    start_line=endpoint.start_line,
                    end_line=endpoint.end_line,
                )
                for endpoint in endpoints
            ],
            chunks=[
                ChunkRecord(
                    id=chunk.id,
                    file_path=chunk.file_path,
                    chunk_type=chunk.chunk_type,
                    content=chunk.content,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    symbol_name=chunk.symbol_name,
                    content_hash=chunk.content_hash,
                )
                for chunk in chunks
            ],
            graph_nodes=[
                GraphNodeDTO(
                    id=node.id.split(":", 1)[1] if node.id.startswith(f"{repository.id}:") else node.id,
                    type=node.type,
                    label=node.label,
                    file_path=node.file_path,
                )
                for node in graph_nodes
            ],
            graph_edges=[GraphEdgeDTO(source=edge.source, target=edge.target, type=edge.type, confidence=edge.confidence) for edge in graph_edges],
            logs=json.loads(repository.logs_json or "[]"),
            warnings=json.loads(repository.warnings_json or "[]"),
            failed_files=repository.failed_files,
            current_step=repository.current_step,
            started_at=repository.started_at,
            finished_at=repository.finished_at,
        )

    def _indexing_job_record(self, row: IndexingJobORM) -> IndexingJobRecord:
        return IndexingJobRecord(
            id=row.id,
            repository_id=row.repository_id,
            index_version=row.index_version,
            status=row.status,
            current_step=row.current_step,
            total_files=row.total_files,
            processed_files=row.processed_files,
            skipped_files=row.skipped_files,
            failed_files=row.failed_files,
            total_chunks=row.total_chunks,
            total_graph_nodes=row.total_graph_nodes,
            total_graph_edges=row.total_graph_edges,
            started_at=row.started_at,
            finished_at=row.finished_at,
            logs=json.loads(row.logs_json or "[]"),
            warnings=json.loads(row.warnings_json or "[]"),
            skipped_file_records=json.loads(row.skipped_files_json or "[]"),
            failed_file_records=json.loads(row.failed_files_json or "[]"),
            error_code=row.error_code,
            error_message=row.error_message,
        )
