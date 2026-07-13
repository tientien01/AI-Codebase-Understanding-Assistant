"""PostgreSQL adapter for the current repository/evidence application port."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from sqlalchemy import Engine, and_, case, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401 - register production tables
from app.db.production_session import create_production_engine, create_production_session_factory
from app.schemas.api import EvidenceDTO, GraphEdgeDTO, GraphNodeDTO
from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, IndexingJobRecord, RepositoryState, SymbolRecord


class ProductionRepositoryError(RuntimeError):
    """Safe adapter failure without connection or source-path disclosure."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode()
    return prefix + hashlib.sha256(payload).hexdigest()[:32]


def _sha256(*parts: object) -> str:
    return hashlib.sha256("\x1f".join(str(part) for part in parts).encode()).hexdigest()


def _time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _source_type(value: str) -> str:
    return "public_git" if value == "github_url" else value


def _legacy_source_type(value: str) -> str:
    return "github_url" if value == "public_git" else value


class ProductionRepositoryStore:
    """Maps compatibility domain records onto repository/version-owned tables."""

    def __init__(self, engine: Engine | None = None) -> None:
        self.engine = engine or create_production_engine()
        self.Session = create_production_session_factory(self.engine)
        self.t = ProductionBase.metadata.tables

    def list_repositories(self) -> list[RepositoryState]:
        with self.Session() as session:
            rows = session.execute(
                select(self.t["repositories"], self.t["repository_sources"].c.source_type, self.t["repository_sources"].c.canonical_locator)
                .join(self.t["repository_sources"], self.t["repository_sources"].c.repository_id == self.t["repositories"].c.id)
                .order_by(self.t["repositories"].c.display_name, self.t["repositories"].c.id)
            ).mappings().all()
            return [self._load_repository(session, row) for row in rows]

    def save_repository_metadata(self, repository: RepositoryState) -> None:
        self._validate_managed_source(repository)
        with self.Session.begin() as session:
            self._ensure_repository_identity(session, repository)
            active_id = self._version_id(repository.id, repository.current_index_version) if repository.current_index_version > 0 else None
            compatibility = self._compatibility_metadata(repository)
            if active_id and session.scalar(select(self.t["index_versions"].c.id).where(self.t["index_versions"].c.id == active_id)):
                session.execute(update(self.t["index_versions"]).where(self.t["index_versions"].c.id == active_id).values(coverage=compatibility))

    def save_repository(self, repository: RepositoryState) -> None:
        self._validate_managed_source(repository)
        with self.Session.begin() as session:
            snapshot_id = self._ensure_repository_identity(session, repository)
            if not repository.files and repository.current_index_version <= 0:
                return
            version_id = self._version_id(repository.id, repository.current_index_version)
            existing = session.execute(select(self.t["index_versions"]).where(self.t["index_versions"].c.id == version_id)).mappings().first()
            if existing and existing["lifecycle"] != "building":
                raise ProductionRepositoryError("Immutable production index version already exists")

            repo = self.t["repositories"]
            versions = self.t["index_versions"]
            previous_id = session.scalar(select(repo.c.active_index_version_id).where(repo.c.id == repository.id))
            session.execute(update(repo).where(repo.c.id == repository.id).values(active_index_version_id=None))
            if previous_id:
                session.execute(update(versions).where(versions.c.id == previous_id).values(lifecycle="superseded", superseded_at=func.now()))
            manifest_hash = _sha256("compatibility-manifest", repository.id, repository.current_index_version)
            version_values = dict(
                id=version_id, repository_id=repository.id, version_number=max(1, repository.current_index_version),
                source_snapshot_id=snapshot_id, base_index_version_id=previous_id, build_kind="full", lifecycle="active",
                manifest_schema_version="compatibility/v1", producer_version="dat-003",
                configuration_sha256=_sha256("compatibility-config", repository.id),
                manifest_storage_key=f"repositories/{repository.id}/indexes/{version_id}/manifest.json",
                manifest_sha256=manifest_hash, validation_status="passed", critical_issue_count=0,
                coverage=self._compatibility_metadata(repository), started_at=_time(repository.started_at) or func.now(),
                finished_at=_time(repository.finished_at) or func.now(), activated_at=func.now(),
            )
            if existing:
                session.execute(update(versions).where(versions.c.id == version_id).values(**{key: value for key, value in version_values.items() if key != "id"}))
            else:
                session.execute(insert(versions).values(**version_values))
            file_ids = self._insert_files(session, repository, version_id)
            symbol_ids = self._insert_symbols(session, repository, version_id, file_ids)
            self._insert_endpoints(session, repository, version_id, file_ids, symbol_ids)
            self._insert_chunks(session, repository, version_id, file_ids)
            node_ids = self._insert_nodes(session, repository, version_id, file_ids)
            self._insert_edges(session, repository, version_id, file_ids, node_ids)
            session.execute(update(repo).where(repo.c.id == repository.id).values(active_index_version_id=version_id))
            terminal_state = "succeeded_with_warnings" if repository.status == "indexed_with_warnings" else "succeeded"
            session.execute(
                update(self.t["index_jobs"])
                .where(self.t["index_jobs"].c.repository_id == repository.id)
                .where(self.t["index_jobs"].c.stage_code == "completed")
                .where(self.t["index_jobs"].c.target_index_version_id.is_(None))
                .values(target_index_version_id=version_id, state=terminal_state, finished_at=_time(repository.finished_at) or func.now())
            )

    def delete_repository(self, repository_id: str) -> None:
        with self.Session.begin() as session:
            session.execute(delete(self.t["evidence"]).where(self.t["evidence"].c.repository_id == repository_id))
            session.execute(delete(self.t["index_jobs"]).where(self.t["index_jobs"].c.repository_id == repository_id))
            session.execute(delete(self.t["repositories"]).where(self.t["repositories"].c.id == repository_id))

    def save_evidence(self, evidence: EvidenceDTO) -> None:
        version_id = self._version_id(evidence.repository_id, evidence.index_version)
        files = self.t["files"]
        with self.Session.begin() as session:
            file_id = session.scalar(select(files.c.id).where(files.c.repository_id == evidence.repository_id, files.c.index_version_id == version_id, files.c.relative_path == evidence.file_path))
            if not file_id:
                raise ProductionRepositoryError("Evidence file does not belong to the repository index version")
            values = {
                "id": evidence.evidence_id, "repository_id": evidence.repository_id, "index_version_id": version_id,
                "source_entity_type": evidence.source_type, "source_canonical_key": evidence.symbol_name or f"file:v1:{evidence.file_path}",
                "file_id": file_id, "start_line": evidence.start_line, "end_line": evidence.end_line,
                "content_sha256": _sha256(evidence.content_preview), "support_type": "source_exact",
                "producer_stage": "compatibility", "producer_name": "dat-003", "producer_version": "1",
                "retrieval_source": evidence.retrieval_source, "selection_reason": evidence.relevance_reason,
                "freshness": "stale" if evidence.is_stale else "fresh", "safe_preview": evidence.content_preview,
                "validation_details": evidence.metadata,
            }
            statement = pg_insert(self.t["evidence"]).values(**values)
            session.execute(statement.on_conflict_do_update(index_elements=["id"], set_={key: value for key, value in values.items() if key != "id"}))

    def get_evidence(self, evidence_id: str) -> EvidenceDTO | None:
        evidence = self.t["evidence"]
        files = self.t["files"]
        versions = self.t["index_versions"]
        with self.Session() as session:
            row = session.execute(
                select(evidence, files.c.relative_path, versions.c.version_number)
                .join(files, and_(files.c.repository_id == evidence.c.repository_id, files.c.index_version_id == evidence.c.index_version_id, files.c.id == evidence.c.file_id))
                .join(versions, and_(versions.c.repository_id == evidence.c.repository_id, versions.c.id == evidence.c.index_version_id))
                .where(evidence.c.id == evidence_id)
            ).mappings().first()
            if not row:
                return None
            return EvidenceDTO(
                evidence_id=row["id"], repository_id=row["repository_id"], index_version=int(row["version_number"]),
                source_type=row["source_entity_type"], file_path=row["relative_path"], symbol_name=None,
                start_line=row["start_line"], end_line=row["end_line"], content_preview=row["safe_preview"],
                relevance_reason=row["selection_reason"], confidence_score=1.0, retrieval_source=row["retrieval_source"],
                is_stale=row["freshness"] != "fresh", metadata=row["validation_details"] or {},
            )

    def mark_stale_evidence(self, repository_id: str, current_index_version: int) -> None:
        versions = self.t["index_versions"]
        evidence = self.t["evidence"]
        with self.Session.begin() as session:
            stale_versions = select(versions.c.id).where(versions.c.repository_id == repository_id, versions.c.version_number < current_index_version)
            session.execute(update(evidence).where(evidence.c.repository_id == repository_id, evidence.c.index_version_id.in_(stale_versions)).values(freshness="stale", staled_at=func.now()))

    def save_indexing_job(self, job: IndexingJobRecord) -> None:
        with self.Session.begin() as session:
            snapshot_id = session.scalar(select(self.t["source_snapshots"].c.id).where(self.t["source_snapshots"].c.repository_id == job.repository_id).order_by(self.t["source_snapshots"].c.created_at.desc()))
            if not snapshot_id:
                raise ProductionRepositoryError("Index job repository has no source snapshot")
            idem_id = _stable_id("idem_", job.id)
            idem_values = {"id": idem_id, "principal_id": "principal_local_operator", "operation": "compatibility_index", "idempotency_key": job.id, "normalized_request_hash": _sha256(job.id), "state": "completed", "resource_type": "index_job", "resource_id": job.id, "expires_at": datetime(2100, 1, 1, tzinfo=UTC)}
            idem_stmt = pg_insert(self.t["idempotency_records"]).values(**idem_values)
            session.execute(idem_stmt.on_conflict_do_nothing(index_elements=["id"]))
            target_id = self._version_id(job.repository_id, job.index_version)
            target_exists = session.scalar(select(self.t["index_versions"].c.id).where(self.t["index_versions"].c.id == target_id))
            if job.index_version > 0 and not target_exists:
                session.execute(insert(self.t["index_versions"]).values(
                    id=target_id, repository_id=job.repository_id, version_number=job.index_version,
                    source_snapshot_id=snapshot_id, build_kind="full", lifecycle="building",
                    manifest_schema_version="compatibility/v1", producer_version="dat-003",
                    configuration_sha256=_sha256("compatibility-config", job.repository_id),
                    critical_issue_count=0, coverage={}, started_at=_time(job.started_at) or func.now(),
                ))
                target_exists = target_id
            state = self._job_state(job.status)
            if state in {"succeeded", "succeeded_with_warnings"} and not target_exists:
                state = "running"
            values = {
                "id": job.id, "repository_id": job.repository_id, "source_snapshot_id": snapshot_id,
                "requested_build_kind": "full", "effective_build_kind": "full", "target_index_version_id": target_id if target_exists else None,
                "state": state, "idempotency_record_id": idem_id, "lease_generation": 0, "repository_generation": 0,
                "stage_code": job.current_step, "progress_completed": job.processed_files, "progress_total": job.total_files,
                "progress_unit": "files", "warning_count": len(job.warnings), "error_code": job.error_code,
                "error_message_safe": job.error_message, "started_at": _time(job.started_at) if state != "queued" else None,
                "finished_at": _time(job.finished_at) if state in {"failed", "cancelled", "succeeded", "succeeded_with_warnings"} else None,
            }
            statement = pg_insert(self.t["index_jobs"]).values(**values)
            # Compatibility progress writes must not overwrite the lease authority
            # owned by JobStateStore for a dedicated-worker attempt.
            jobs = self.t["index_jobs"]
            updates = {
                key: value
                for key, value in values.items()
                if key not in {
                    "id",
                    "idempotency_record_id",
                    "lease_generation",
                    "repository_generation",
                }
            }
            leased = jobs.c.current_attempt_id.is_not(None)
            updates["state"] = case((leased, jobs.c.state), else_=state)
            updates["finished_at"] = case(
                (leased, jobs.c.finished_at), else_=values["finished_at"]
            )
            updates["error_code"] = case(
                (leased, jobs.c.error_code), else_=values["error_code"]
            )
            updates["error_message_safe"] = case(
                (leased, jobs.c.error_message_safe),
                else_=values["error_message_safe"],
            )
            session.execute(
                statement.on_conflict_do_update(index_elements=["id"], set_=updates)
            )

    def list_indexing_jobs(self, repository_id: str) -> list[IndexingJobRecord]:
        with self.Session() as session:
            jobs, versions = self.t["index_jobs"], self.t["index_versions"]
            rows = session.execute(select(jobs, versions.c.version_number.label("target_version_number")).outerjoin(versions, and_(versions.c.repository_id == jobs.c.repository_id, versions.c.id == jobs.c.target_index_version_id)).where(jobs.c.repository_id == repository_id).order_by(jobs.c.created_at.desc(), jobs.c.id.desc())).mappings().all()
            return [self._job(row) for row in rows]

    def get_latest_indexing_job(self, repository_id: str) -> IndexingJobRecord | None:
        jobs = self.list_indexing_jobs(repository_id)
        return jobs[0] if jobs else None

    def get_indexing_job(self, repository_id: str, job_id: str) -> IndexingJobRecord | None:
        with self.Session() as session:
            jobs, versions = self.t["index_jobs"], self.t["index_versions"]
            row = session.execute(select(jobs, versions.c.version_number.label("target_version_number")).outerjoin(versions, and_(versions.c.repository_id == jobs.c.repository_id, versions.c.id == jobs.c.target_index_version_id)).where(jobs.c.repository_id == repository_id, jobs.c.id == job_id)).mappings().first()
            return self._job(row) if row else None

    def _ensure_repository_identity(self, session, repository: RepositoryState) -> str:
        principals = self.t["operator_principals"]
        session.execute(pg_insert(principals).values(id="principal_local_operator", display_name="Local operator").on_conflict_do_nothing(index_elements=["id"]))
        repo_values = {"id": repository.id, "owner_principal_id": "principal_local_operator", "display_name": repository.name, "lifecycle": "active", "recovery_state": "ready", "source_freshness": "unverifiable", "operation_generation": 0}
        repo_stmt = pg_insert(self.t["repositories"]).values(**repo_values)
        session.execute(repo_stmt.on_conflict_do_update(index_elements=["id"], set_={"display_name": repository.name, "updated_at": func.now()}))
        source_id = _stable_id("source_", repository.id)
        source_values = {"id": source_id, "repository_id": repository.id, "source_type": _source_type(repository.source_type), "canonical_locator": repository.source_uri if repository.source_type == "github_url" else None, "source_fingerprint": repository.project_fingerprint if repository.project_fingerprint and len(repository.project_fingerprint) == 64 else None}
        source_stmt = pg_insert(self.t["repository_sources"]).values(**source_values)
        session.execute(source_stmt.on_conflict_do_update(index_elements=["id"], set_={key: value for key, value in source_values.items() if key != "id"}))
        snapshot_hash = _sha256(repository.id, *(item.content_hash for item in sorted(repository.files, key=lambda item: item.path)))
        snapshot_id = _stable_id("snapshot_", repository.id, snapshot_hash)
        snapshot_values = {"id": snapshot_id, "repository_id": repository.id, "repository_source_id": source_id, "storage_key": f"repositories/{repository.id}/sources/{snapshot_id}", "snapshot_sha256": snapshot_hash, "policy_version": "dat-003", "inventory_schema_version": "dat-003", "total_files": len(repository.files), "total_bytes": sum(item.size_bytes for item in repository.files)}
        session.execute(pg_insert(self.t["source_snapshots"]).values(**snapshot_values).on_conflict_do_nothing(index_elements=["id"]))
        return snapshot_id

    def _validate_managed_source(self, repository: RepositoryState) -> None:
        storage_root = settings.repository_storage_dir.resolve()
        source_path = repository.source_path.resolve()
        expected = (storage_root / repository.id / "source").resolve()
        if source_path != expected:
            raise ProductionRepositoryError("Repository source is outside its managed production root")

    def _insert_files(self, session, repository: RepositoryState, version_id: str) -> dict[str, str]:
        result = {}
        for item in repository.files:
            file_id = _stable_id("fileobs_", repository.id, version_id, item.path)
            result[item.path] = file_id
            session.execute(insert(self.t["files"]).values(id=file_id, repository_id=repository.id, index_version_id=version_id, canonical_key=f"file:v1:{item.path}", relative_path=item.path, language=item.language, file_type=item.file_type, byte_size=item.size_bytes, content_sha256=item.content_hash, encoding="utf-8", parse_status=item.parse_status, producer_stage="compatibility", producer_name="dat-003", producer_version="1"))
        return result

    def _insert_symbols(self, session, repository, version_id, file_ids):
        result = {}
        for item in repository.symbols:
            symbol_id = _stable_id("symbolobs_", repository.id, version_id, item.id)
            result[item.id] = symbol_id
            session.execute(insert(self.t["symbols"]).values(id=symbol_id, repository_id=repository.id, index_version_id=version_id, canonical_key=item.id, file_id=file_ids[item.file_path], name=item.name, qualified_name=item.name, symbol_kind=item.symbol_type, signature=item.signature, start_line=item.start_line, end_line=item.end_line, producer_stage="compatibility", producer_name="dat-003", producer_version="1", support_type="source_exact", diagnostic_ids=[]))
        return result

    def _insert_endpoints(self, session, repository, version_id, file_ids, symbol_ids):
        for ordinal, item in enumerate(repository.endpoints):
            handler_id = symbol_ids.get(item.handler)
            session.execute(insert(self.t["endpoints"]).values(id=_stable_id("endpointobs_", repository.id, version_id, ordinal, item.method, item.path), repository_id=repository.id, index_version_id=version_id, canonical_key=f"endpoint:v1:http:{item.method.lower()}:{item.path}:{item.handler}", file_id=file_ids[item.file_path], handler_symbol_id=handler_id, protocol="http", method=item.method, normalized_route=item.path, start_line=item.start_line, end_line=item.end_line, producer_stage="compatibility", producer_name="dat-003", producer_version="1", support_type="source_exact", diagnostic_ids=[]))

    def _insert_chunks(self, session, repository, version_id, file_ids):
        for ordinal, item in enumerate(repository.chunks):
            session.execute(insert(self.t["chunks"]).values(id=_stable_id("chunkobs_", repository.id, version_id, item.id), repository_id=repository.id, index_version_id=version_id, canonical_key=item.id, source_entity_type=item.chunk_type, source_canonical_key=item.symbol_name or f"file:v1:{item.file_path}", file_id=file_ids[item.file_path], chunk_kind=item.chunk_type, ordinal=ordinal, start_line=item.start_line, end_line=item.end_line, content_sha256=item.content_hash if len(item.content_hash) == 64 else _sha256(item.content), safe_preview=item.content[:2000], retrieval_metadata={}, producer_stage="compatibility", producer_name="dat-003", producer_version="1"))

    def _insert_nodes(self, session, repository, version_id, file_ids):
        result = {}
        for item in repository.graph_nodes:
            node_id = _stable_id("nodeobs_", repository.id, version_id, item.id)
            result[item.id] = node_id
            metadata = {**item.metadata, "compatibility": {"summary": item.summary, "tags": item.tags, "complexity": item.complexity, "layer": item.layer, "scope_path": item.scope_path, "role": item.role}}
            session.execute(insert(self.t["graph_nodes"]).values(id=node_id, repository_id=repository.id, index_version_id=version_id, canonical_key=item.id, node_type=item.type, label=item.label, file_id=file_ids.get(item.file_path), start_line=item.start_line, end_line=item.end_line, coverage_state=item.coverage, metadata=metadata, producer_stage="compatibility", producer_name="dat-003", producer_version="1", support_type="static_resolved", diagnostic_ids=[]))
        return result

    def _insert_edges(self, session, repository, version_id, file_ids, node_ids):
        for ordinal, item in enumerate(repository.graph_edges):
            if item.source not in node_ids or item.target not in node_ids:
                raise ProductionRepositoryError("Graph edge references a node outside the repository index version")
            session.execute(insert(self.t["graph_edges"]).values(id=_stable_id("edgeobs_", repository.id, version_id, ordinal, item.source, item.target, item.type), repository_id=repository.id, index_version_id=version_id, canonical_key=f"edge:v1:{item.type}:{item.source}:{item.target}:{ordinal}", source_node_id=node_ids[item.source], target_node_id=node_ids[item.target], edge_type=item.type, weight=item.weight, metadata=item.metadata, producer_stage="compatibility", producer_name="dat-003", producer_version="1", support_type="static_resolved", confidence=item.confidence, diagnostic_ids=[]))

    def _load_repository(self, session, row) -> RepositoryState:
        repo_id, version_id = row["id"], row["active_index_version_id"]
        source_path = settings.repository_storage_dir / repo_id / "source"
        if not version_id:
            return RepositoryState(id=repo_id, name=row["display_name"], source_type=_legacy_source_type(row["source_type"]), source_uri=row["canonical_locator"], source_path=source_path)
        version = session.execute(select(self.t["index_versions"]).where(self.t["index_versions"].c.id == version_id)).mappings().one()
        compatibility = (version["coverage"] or {}).get("compatibility", {})
        file_rows = session.execute(select(self.t["files"]).where(self.t["files"].c.repository_id == repo_id, self.t["files"].c.index_version_id == version_id)).mappings().all()
        files = [FileRecord(path=item["relative_path"], absolute_path=source_path / item["relative_path"], language=item["language"], file_type=item["file_type"], size_bytes=item["byte_size"], content_hash=item["content_sha256"], parse_status=item["parse_status"]) for item in file_rows]
        path_by_id = {item["id"]: item["relative_path"] for item in file_rows}
        symbol_rows = session.execute(select(self.t["symbols"]).where(self.t["symbols"].c.repository_id == repo_id, self.t["symbols"].c.index_version_id == version_id)).mappings().all()
        symbols = [SymbolRecord(id=item["canonical_key"], name=item["name"], symbol_type=item["symbol_kind"], file_path=path_by_id[item["file_id"]], start_line=item["start_line"], end_line=item["end_line"], signature=item["signature"] or "") for item in symbol_rows]
        endpoint_rows = session.execute(select(self.t["endpoints"]).where(self.t["endpoints"].c.repository_id == repo_id, self.t["endpoints"].c.index_version_id == version_id)).mappings().all()
        endpoints = [EndpointRecord(method=item["method"], path=item["normalized_route"], handler=item["canonical_key"].rsplit(":", 1)[-1], file_path=path_by_id[item["file_id"]], start_line=item["start_line"], end_line=item["end_line"]) for item in endpoint_rows]
        chunk_rows = session.execute(select(self.t["chunks"]).where(self.t["chunks"].c.repository_id == repo_id, self.t["chunks"].c.index_version_id == version_id).order_by(self.t["chunks"].c.ordinal)).mappings().all()
        chunks = [ChunkRecord(id=item["canonical_key"], file_path=path_by_id[item["file_id"]], chunk_type=item["chunk_kind"], content=item["safe_preview"], start_line=item["start_line"], end_line=item["end_line"], symbol_name=None, content_hash=item["content_sha256"]) for item in chunk_rows]
        node_rows = session.execute(select(self.t["graph_nodes"]).where(self.t["graph_nodes"].c.repository_id == repo_id, self.t["graph_nodes"].c.index_version_id == version_id)).mappings().all()
        node_key_by_id = {item["id"]: item["canonical_key"] for item in node_rows}
        nodes = []
        for item in node_rows:
            extra = (item["metadata"] or {}).get("compatibility", {})
            nodes.append(GraphNodeDTO(id=item["canonical_key"], type=item["node_type"], label=item["label"], file_path=path_by_id.get(item["file_id"]), start_line=item["start_line"], end_line=item["end_line"], summary=extra.get("summary"), tags=extra.get("tags", []), complexity=extra.get("complexity"), layer=extra.get("layer"), coverage=item["coverage_state"], scope_path=extra.get("scope_path"), role=extra.get("role"), metadata={key: value for key, value in (item["metadata"] or {}).items() if key != "compatibility"}))
        edge_rows = session.execute(select(self.t["graph_edges"]).where(self.t["graph_edges"].c.repository_id == repo_id, self.t["graph_edges"].c.index_version_id == version_id)).mappings().all()
        edges = [GraphEdgeDTO(source=node_key_by_id[item["source_node_id"]], target=node_key_by_id[item["target_node_id"]], type=item["edge_type"], confidence=item["confidence"] or 1.0, weight=item["weight"], metadata=item["metadata"] or {}) for item in edge_rows]
        return RepositoryState(id=repo_id, name=row["display_name"], source_type=_legacy_source_type(row["source_type"]), source_uri=row["canonical_locator"], source_path=source_path, source_label=compatibility.get("source_label"), status=compatibility.get("status", "indexed"), current_index_version=int(version["version_number"]), project_fingerprint=compatibility.get("project_fingerprint"), files=files, symbols=symbols, endpoints=endpoints, chunks=chunks, graph_nodes=nodes, graph_edges=edges, logs=compatibility.get("logs", []), warnings=compatibility.get("warnings", []), failed_files=compatibility.get("failed_files", 0), current_step=compatibility.get("current_step", "completed"), started_at=compatibility.get("started_at"), finished_at=compatibility.get("finished_at"))

    def _compatibility_metadata(self, repository):
        return {"compatibility": {"status": repository.status, "source_label": repository.source_label, "project_fingerprint": repository.project_fingerprint, "logs": repository.logs, "warnings": repository.warnings, "failed_files": repository.failed_files, "current_step": repository.current_step, "started_at": repository.started_at, "finished_at": repository.finished_at}}

    def _version_id(self, repository_id: str, version: int) -> str:
        return _stable_id("idx_", repository_id, version)

    def _job_state(self, status: str) -> str:
        return {"completed": "succeeded", "completed_with_warnings": "succeeded_with_warnings", "cancelling": "running", "paused": "running"}.get(status, status if status in {"queued", "running", "failed", "cancelled"} else "failed")

    def _job(self, row) -> IndexingJobRecord:
        status = {"succeeded": "completed", "succeeded_with_warnings": "completed_with_warnings"}.get(row["state"], row["state"])
        return IndexingJobRecord(id=row["id"], repository_id=row["repository_id"], status=status, index_version=int(row.get("target_version_number") or 0), current_step=row["stage_code"], total_files=row["progress_total"] or 0, processed_files=row["progress_completed"] or 0, warnings=["warning"] * row["warning_count"], started_at=row["started_at"].isoformat() if row["started_at"] else None, finished_at=row["finished_at"].isoformat() if row["finished_at"] else None, error_code=row["error_code"], error_message=row["error_message_safe"])
