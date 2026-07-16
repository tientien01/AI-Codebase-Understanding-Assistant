from __future__ import annotations

import json
import hashlib
from pathlib import Path

from sqlalchemy import delete, func, select, update

from app.db.models import (
    AgentTraceEventORM,
    AgentTraceORM,
    CitationORM,
    ChunkRecordORM,
    ClaimORM,
    ConversationORM,
    EndpointRecordORM,
    EvidenceORM,
    FileRecordORM,
    GraphEdgeORM,
    GraphNodeORM,
    IndexingJobORM,
    MessageORM,
    RepositoryORM,
    SymbolRecordORM,
)
from app.db.session import SessionLocal, init_db
from app.schemas.api import CitationDTO, EvidenceDTO, GraphEdgeDTO, GraphNodeDTO
from app.services.chat.trace_persistence import (
    AssistantTraceReplay,
    PersistedAssistantTurn,
    PersistedClaim,
    TraceEventRecord,
    TraceEventType,
)
from app.services.chat.conversation_memory import (
    ConversationMessageRecord,
    ConversationSummaryRecord,
    ConversationTranscriptRecord,
)
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
                    project_fingerprint=repository.project_fingerprint,
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
                        metadata_json=json.dumps(endpoint.metadata),
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
                        start_line=node.start_line,
                        end_line=node.end_line,
                        summary=node.summary,
                        tags_json=json.dumps(node.tags),
                        complexity=node.complexity,
                        layer=node.layer,
                        coverage=node.coverage,
                        scope_path=node.scope_path,
                        role=node.role,
                        metadata_json=json.dumps(node.metadata),
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
                        evidence_level=edge.evidence_level,
                        weight=edge.weight,
                        metadata_json=json.dumps(edge.metadata),
                    )
                    for edge in repository.graph_edges
                ]
            )

    def save_repository_metadata(self, repository: RepositoryState) -> None:
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
                    project_fingerprint=repository.project_fingerprint,
                    logs_json=json.dumps(repository.logs),
                    warnings_json=json.dumps(repository.warnings),
                    failed_files=repository.failed_files,
                    current_step=repository.current_step,
                    started_at=repository.started_at,
                    finished_at=repository.finished_at,
                )
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
            trace_ids = select(AgentTraceORM.id).where(AgentTraceORM.repository_id == repository_id)
            message_ids = select(MessageORM.id).where(MessageORM.repository_id == repository_id)
            claim_ids = select(ClaimORM.id).where(ClaimORM.repository_id == repository_id)
            session.execute(delete(AgentTraceEventORM).where(AgentTraceEventORM.trace_id.in_(trace_ids)))
            session.execute(delete(AgentTraceORM).where(AgentTraceORM.repository_id == repository_id))
            session.execute(delete(CitationORM).where(CitationORM.claim_id.in_(claim_ids)))
            session.execute(delete(ClaimORM).where(ClaimORM.message_id.in_(message_ids)))
            session.execute(delete(MessageORM).where(MessageORM.repository_id == repository_id))
            session.execute(delete(ConversationORM).where(ConversationORM.repository_id == repository_id))
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

    def save_assistant_turn(self, turn: PersistedAssistantTurn) -> None:
        """Persist one completed turn in a single local transaction."""

        with SessionLocal.begin() as session:
            repository = session.get(RepositoryORM, turn.repository_id)
            if repository is None or repository.current_index_version != turn.index_version:
                raise ValueError("Assistant turn does not belong to the active repository index")
            conversation = session.get(ConversationORM, turn.conversation_id)
            if conversation is not None and conversation.repository_id != turn.repository_id:
                raise ValueError("Conversation does not belong to the repository")
            if conversation is None:
                session.add(
                    ConversationORM(
                        id=turn.conversation_id,
                        repository_id=turn.repository_id,
                        status="active",
                        title=turn.operator_message[:80],
                    )
                )
            session.add_all(
                [
                    MessageORM(
                        id=turn.request_message_id,
                        conversation_id=turn.conversation_id,
                        repository_id=turn.repository_id,
                        index_version=turn.index_version,
                        role="operator",
                        content=turn.operator_message,
                    ),
                    MessageORM(
                        id=turn.response_message_id,
                        conversation_id=turn.conversation_id,
                        repository_id=turn.repository_id,
                        index_version=turn.index_version,
                        role="assistant",
                        content=turn.assistant_message,
                        assistant_outcome=turn.outcome,
                    ),
                ]
            )

            for ordinal, claim in enumerate(turn.claims):
                session.add(
                    ClaimORM(
                        id=claim.claim_id,
                        message_id=turn.response_message_id,
                        repository_id=turn.repository_id,
                        index_version=turn.index_version,
                        claim_text=claim.text,
                        support_level=claim.support_level,
                        ordinal=ordinal,
                    )
                )
                for evidence_id in claim.citation_ids:
                    evidence = session.get(EvidenceORM, evidence_id)
                    if (
                        evidence is None
                        or evidence.repository_id != turn.repository_id
                        or evidence.index_version != turn.index_version
                    ):
                        raise ValueError("Citation does not belong to the assistant turn")
                    session.add(
                        CitationORM(
                            id=self._citation_id(claim.claim_id, evidence_id),
                            claim_id=claim.claim_id,
                            evidence_id=evidence_id,
                            repository_id=turn.repository_id,
                            index_version=turn.index_version,
                            display_locator=f"{evidence.file_path}:{evidence.start_line}-{evidence.end_line}",
                        )
                    )
            session.add(
                AgentTraceORM(
                    id=turn.trace_id,
                    repository_id=turn.repository_id,
                    index_version=turn.index_version,
                    conversation_id=turn.conversation_id,
                    request_message_id=turn.request_message_id,
                    response_message_id=turn.response_message_id,
                    workflow_version=turn.workflow_version,
                    question_type=turn.question_type,
                    outcome=turn.outcome,
                    configuration_id=turn.configuration_id,
                    budget_json=turn.budget_json,
                    started_at=turn.started_at.isoformat(),
                    finished_at=turn.finished_at.isoformat(),
                )
            )
            session.add_all(
                [
                    AgentTraceEventORM(
                        id=event.event_id,
                        trace_id=turn.trace_id,
                        sequence=event.sequence,
                        event_type=event.event_type.value,
                        tool_name=event.tool_name,
                        status=event.status,
                        duration_ms=event.duration_ms,
                        payload_json=event.payload_json,
                    )
                    for event in turn.events
                ]
            )

    def list_conversations(
        self, repository_id: str, limit: int
    ) -> tuple[ConversationSummaryRecord, ...]:
        with SessionLocal() as session:
            ids = session.scalars(
                select(ConversationORM.id)
                .join(AgentTraceORM, AgentTraceORM.conversation_id == ConversationORM.id)
                .where(ConversationORM.repository_id == repository_id)
                .group_by(ConversationORM.id)
                .order_by(func.max(AgentTraceORM.started_at).desc(), ConversationORM.id.desc())
                .limit(limit)
            ).all()
            return tuple(self._conversation_summary(session, repository_id, item) for item in ids)

    def get_conversation_transcript(
        self, repository_id: str, conversation_id: str, limit: int
    ) -> ConversationTranscriptRecord | None:
        with SessionLocal() as session:
            conversation = session.get(ConversationORM, conversation_id)
            if conversation is None or conversation.repository_id != repository_id:
                return None
            traces = session.scalars(
                select(AgentTraceORM)
                .where(
                    AgentTraceORM.repository_id == repository_id,
                    AgentTraceORM.conversation_id == conversation_id,
                )
                .order_by(AgentTraceORM.started_at.desc(), AgentTraceORM.id.desc())
                .limit(max(1, limit // 2))
            ).all()
            traces.reverse()
            messages: list[ConversationMessageRecord] = []
            for trace in traces:
                request = session.get(MessageORM, trace.request_message_id)
                response = session.get(MessageORM, trace.response_message_id)
                if request is None or response is None:
                    continue
                evidence_rows = session.scalars(
                    select(EvidenceORM)
                    .join(CitationORM, CitationORM.evidence_id == EvidenceORM.evidence_id)
                    .join(ClaimORM, ClaimORM.id == CitationORM.claim_id)
                    .where(ClaimORM.message_id == response.id)
                    .order_by(EvidenceORM.file_path, EvidenceORM.start_line, EvidenceORM.evidence_id)
                ).all()
                citations = tuple(
                    CitationDTO(
                        evidence_id=item.evidence_id,
                        file_path=item.file_path,
                        symbol_name=item.symbol_name,
                        start_line=item.start_line,
                        end_line=item.end_line,
                        index_version=item.index_version,
                        is_stale=bool(item.is_stale),
                    )
                    for item in evidence_rows
                )
                created_at = trace.started_at
                messages.extend(
                    (
                        ConversationMessageRecord(
                            request.id, "user", request.content, request.index_version, created_at
                        ),
                        ConversationMessageRecord(
                            response.id,
                            "assistant",
                            response.content,
                            response.index_version,
                            created_at,
                            citations,
                            response.assistant_outcome == "answered",
                        ),
                    )
                )
            return ConversationTranscriptRecord(
                self._conversation_summary(session, repository_id, conversation_id),
                tuple(messages[:limit]),
            )

    def _conversation_summary(
        self, session, repository_id: str, conversation_id: str
    ) -> ConversationSummaryRecord:
        conversation = session.get(ConversationORM, conversation_id)
        created_at, updated_at = session.execute(
            select(func.min(AgentTraceORM.started_at), func.max(AgentTraceORM.started_at)).where(
                AgentTraceORM.repository_id == repository_id,
                AgentTraceORM.conversation_id == conversation_id,
            )
        ).one()
        message_count = session.scalar(
            select(func.count(MessageORM.id)).where(
                MessageORM.repository_id == repository_id,
                MessageORM.conversation_id == conversation_id,
            )
        ) or 0
        latest_index = session.scalar(
            select(func.max(MessageORM.index_version)).where(
                MessageORM.repository_id == repository_id,
                MessageORM.conversation_id == conversation_id,
            )
        ) or 0
        created_at = created_at or ""
        return ConversationSummaryRecord(
            conversation_id,
            conversation.title if conversation else None,
            conversation.status if conversation else "active",
            int(message_count),
            int(latest_index),
            created_at,
            updated_at or created_at,
        )

    def get_agent_trace(
        self, repository_id: str, trace_id: str
    ) -> AssistantTraceReplay | None:
        with SessionLocal() as session:
            trace = session.get(AgentTraceORM, trace_id)
            if trace is None or trace.repository_id != repository_id:
                return None
            request = session.get(MessageORM, trace.request_message_id)
            response = session.get(MessageORM, trace.response_message_id)
            if request is None or response is None:
                raise ValueError("Stored assistant trace is incomplete")
            claim_rows = session.scalars(
                select(ClaimORM)
                .where(ClaimORM.message_id == trace.response_message_id)
                .order_by(ClaimORM.ordinal, ClaimORM.id)
            ).all()
            citations: dict[str, EvidenceDTO] = {}
            claims: list[PersistedClaim] = []
            for claim in claim_rows:
                citation_rows = session.scalars(
                    select(CitationORM)
                    .where(CitationORM.claim_id == claim.id)
                    .order_by(CitationORM.id)
                ).all()
                evidence_ids = tuple(row.evidence_id for row in citation_rows)
                claims.append(PersistedClaim(claim.id, claim.claim_text, claim.support_level, evidence_ids))
                for evidence_id in evidence_ids:
                    evidence = session.get(EvidenceORM, evidence_id)
                    if evidence is not None:
                        citations[evidence_id] = self._evidence_dto(evidence)
            event_rows = session.scalars(
                select(AgentTraceEventORM)
                .where(AgentTraceEventORM.trace_id == trace_id)
                .order_by(AgentTraceEventORM.sequence, AgentTraceEventORM.id)
            ).all()
            turn = PersistedAssistantTurn(
                trace_id=trace.id,
                conversation_id=trace.conversation_id,
                request_message_id=trace.request_message_id,
                response_message_id=trace.response_message_id,
                repository_id=trace.repository_id,
                index_version=trace.index_version,
                operator_message=request.content,
                assistant_message=response.content,
                outcome=trace.outcome,
                question_type=trace.question_type,
                workflow_version=trace.workflow_version,
                configuration_id=trace.configuration_id,
                budget_json=trace.budget_json,
                claims=tuple(claims),
                citations=tuple(citations[key] for key in sorted(citations)),
                events=tuple(
                    TraceEventRecord(
                        event_id=row.id,
                        sequence=row.sequence,
                        event_type=TraceEventType(row.event_type),
                        status=row.status,
                        payload_json=row.payload_json,
                        tool_name=row.tool_name,
                        duration_ms=row.duration_ms,
                    )
                    for row in event_rows
                ),
                started_at=self._datetime(trace.started_at),
                finished_at=self._datetime(trace.finished_at),
            )
            return AssistantTraceReplay(turn)

    def _delete_index_records(self, session, repository_id: str) -> None:
        for model in (FileRecordORM, SymbolRecordORM, EndpointRecordORM, ChunkRecordORM, GraphNodeORM, GraphEdgeORM):
            session.execute(delete(model).where(model.repository_id == repository_id))

    @staticmethod
    def _citation_id(claim_id: str, evidence_id: str) -> str:
        digest = hashlib.sha256(f"{claim_id}|{evidence_id}".encode()).hexdigest()[:32]
        return f"citation_{digest}"

    @staticmethod
    def _datetime(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)

    @staticmethod
    def _evidence_dto(row: EvidenceORM) -> EvidenceDTO:
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
            project_fingerprint=repository.project_fingerprint,
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
                    metadata=json.loads(endpoint.metadata_json or "{}"),
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
                    start_line=node.start_line,
                    end_line=node.end_line,
                    summary=node.summary,
                    tags=json.loads(node.tags_json or "[]"),
                    complexity=node.complexity,
                    layer=node.layer,
                    coverage=node.coverage or "deep_indexed",
                    scope_path=node.scope_path,
                    role=node.role,
                    metadata=json.loads(node.metadata_json or "{}"),
                )
                for node in graph_nodes
            ],
            graph_edges=[
                GraphEdgeDTO(
                    source=edge.source,
                    target=edge.target,
                    type=edge.type,
                    confidence=edge.confidence,
                    evidence_level=edge.evidence_level or "deep",
                    weight=edge.weight,
                    metadata=json.loads(edge.metadata_json or "{}"),
                )
                for edge in graph_edges
            ],
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
