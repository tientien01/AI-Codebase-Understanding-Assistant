from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select

from app.db.models import (
    ChunkRecordORM,
    EndpointRecordORM,
    EvidenceORM,
    FileRecordORM,
    GraphEdgeORM,
    GraphNodeORM,
    RepositoryORM,
    SymbolRecordORM,
)
from app.db.session import SessionLocal, init_db
from app.schemas.api import EvidenceDTO, GraphEdgeDTO, GraphNodeDTO
from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, RepositoryState, SymbolRecord


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
                    source_path=str(repository.source_path),
                    status=repository.status,
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
                        source=edge.source,
                        target=edge.target,
                        type=edge.type,
                        confidence=edge.confidence,
                    )
                    for edge in repository.graph_edges
                ]
            )

    def save_evidence(self, evidence: EvidenceDTO) -> None:
        with SessionLocal.begin() as session:
            session.merge(
                EvidenceORM(
                    evidence_id=evidence.evidence_id,
                    repository_id=evidence.repository_id,
                    source_type=evidence.source_type,
                    file_path=evidence.file_path,
                    symbol_name=evidence.symbol_name,
                    start_line=evidence.start_line,
                    end_line=evidence.end_line,
                    content_preview=evidence.content_preview,
                    relevance_reason=evidence.relevance_reason,
                    confidence_score=evidence.confidence_score,
                    retrieval_source=evidence.retrieval_source,
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
                source_type=row.source_type,
                file_path=row.file_path,
                symbol_name=row.symbol_name,
                start_line=row.start_line,
                end_line=row.end_line,
                content_preview=row.content_preview,
                relevance_reason=row.relevance_reason,
                confidence_score=row.confidence_score,
                retrieval_source=row.retrieval_source,
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
            source_path=Path(repository.source_path),
            status=repository.status,
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
