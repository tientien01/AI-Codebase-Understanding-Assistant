"""Deterministic one-shot mapper from the supported nine-table SQLite schema."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
from typing import Any

from sqlalchemy import Engine, func, insert, select, update

from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401 - register production tables


LEGACY_TABLES = (
    "repositories", "indexing_jobs", "file_records", "symbol_records",
    "endpoint_records", "chunk_records", "graph_nodes", "graph_edges", "evidence",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class LegacyUpgradeError(ValueError):
    """Raised before the target transaction commits any migrated row."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return prefix + hashlib.sha256(payload).hexdigest()[:32]


def _sha256(*parts: object) -> str:
    return hashlib.sha256("\x1f".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def _json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise LegacyUpgradeError("Legacy JSON field is invalid") from exc
    if not isinstance(parsed, type(fallback)):
        raise LegacyUpgradeError("Legacy JSON field has an unsupported shape")
    return parsed


def _relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or "\x00" in normalized:
        raise LegacyUpgradeError("Legacy file path is not a safe relative path")
    return path.as_posix()


def _managed_path(value: str, managed_root: Path) -> Path:
    candidate = Path(value).resolve(strict=True)
    try:
        candidate.relative_to(managed_root)
    except ValueError as exc:
        raise LegacyUpgradeError("Legacy source path is outside the managed source root") from exc
    return candidate


def _load_source(source_database: Path) -> dict[str, list[dict[str, Any]]]:
    if not source_database.is_file():
        raise LegacyUpgradeError("Legacy SQLite database does not exist")
    with sqlite3.connect(f"file:{source_database.as_posix()}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if set(LEGACY_TABLES) - names:
            raise LegacyUpgradeError("Legacy SQLite schema is not the supported nine-table shape")
        return {
            name: [dict(row) for row in connection.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
            for name in LEGACY_TABLES
        }


def migrate_supported_legacy_sqlite(source_database: Path, target_engine: Engine, managed_source_root: Path) -> dict[str, int]:
    """Validate and copy the supported legacy shape in one target transaction."""

    managed_root = managed_source_root.resolve(strict=True)
    if not managed_root.is_dir():
        raise LegacyUpgradeError("Managed source root must be a directory")
    rows = _load_source(source_database.resolve(strict=True))
    tables = ProductionBase.metadata.tables

    repositories = {row["id"]: row for row in rows["repositories"]}
    if not repositories:
        raise LegacyUpgradeError("Legacy source contains no repository")

    repo_ids: dict[str, str] = {}
    repo_roots: dict[str, Path] = {}
    version_ids: dict[tuple[str, int], str] = {}
    file_ids: dict[tuple[str, int, str], str] = {}
    node_ids: dict[tuple[str, int, str], str] = {}
    prepared: dict[str, list[dict[str, Any]]] = {name: [] for name in tables}
    prepared["operator_principals"].append({"id": "principal_legacy", "display_name": "Legacy operator"})

    observations = rows["file_records"] + rows["symbol_records"] + rows["endpoint_records"] + rows["chunk_records"] + rows["graph_nodes"] + rows["graph_edges"] + rows["evidence"]
    versions_by_repo: dict[str, set[int]] = {repo: set() for repo in repositories}
    for row in observations + rows["indexing_jobs"]:
        repo = row["repository_id"]
        if repo not in repositories:
            raise LegacyUpgradeError("Legacy row references an unknown repository")
        versions_by_repo[repo].add(int(row.get("index_version", 0)))

    for legacy_id, row in sorted(repositories.items()):
        repo_id = legacy_id if legacy_id.startswith("repo_") else _stable_id("repo_", legacy_id)
        repo_ids[legacy_id] = repo_id
        repo_root = _managed_path(row["source_path"], managed_root)
        repo_roots[legacy_id] = repo_root
        source_id = _stable_id("source_", repo_id)
        snapshot_id = _stable_id("snapshot_", repo_id)
        source_files = [item for item in rows["file_records"] if item["repository_id"] == legacy_id]
        for item in source_files:
            absolute = _managed_path(item["absolute_path"], repo_root)
            if not absolute.is_file():
                raise LegacyUpgradeError("Legacy file observation is missing from managed source")
            if not SHA256_RE.fullmatch(item["content_hash"]):
                raise LegacyUpgradeError("Legacy file checksum is invalid")
        versions = sorted(versions_by_repo[legacy_id] or {int(row.get("current_index_version", 0))})
        active_legacy_version = int(row.get("current_index_version", versions[-1]))
        if active_legacy_version not in versions:
            active_legacy_version = versions[-1]
        active_id = _stable_id("idx_", repo_id, active_legacy_version)
        prepared["repositories"].append({
            "id": repo_id, "owner_principal_id": "principal_legacy", "display_name": row["name"],
            "lifecycle": "active", "recovery_state": "ready", "active_index_version_id": None,
            "source_freshness": "unverifiable", "operation_generation": 0,
        })
        prepared["repository_sources"].append({
            "id": source_id, "repository_id": repo_id,
            "source_type": row["source_type"] if row["source_type"] in {"upload_zip", "upload_folder", "public_git"} else "upload_folder",
            "canonical_locator": row.get("source_uri") if row["source_type"] == "public_git" else None,
            "source_fingerprint": row.get("project_fingerprint") if SHA256_RE.fullmatch(row.get("project_fingerprint") or "") else None,
        })
        snapshot_hash = _sha256(repo_id, *(item["content_hash"] for item in sorted(source_files, key=lambda item: item["path"])))
        prepared["source_snapshots"].append({
            "id": snapshot_id, "repository_id": repo_id, "repository_source_id": source_id,
            "storage_key": f"repositories/{repo_id}/snapshots/{snapshot_id}", "snapshot_sha256": snapshot_hash,
            "policy_version": "legacy-v1", "inventory_schema_version": "legacy-v1",
            "total_files": len(source_files), "total_bytes": sum(int(item["size_bytes"]) for item in source_files),
        })
        for legacy_version in versions:
            version_id = _stable_id("idx_", repo_id, legacy_version)
            version_ids[(legacy_id, legacy_version)] = version_id
            lifecycle = "active" if version_id == active_id else "superseded"
            manifest_hash = _sha256("manifest", repo_id, legacy_version)
            prepared["index_versions"].append({
                "id": version_id, "repository_id": repo_id, "version_number": max(1, legacy_version + 1),
                "source_snapshot_id": snapshot_id, "build_kind": "full", "lifecycle": lifecycle,
                "manifest_schema_version": "legacy-v1", "producer_version": "legacy-mapper-v1",
                "configuration_sha256": _sha256("configuration", repo_id, legacy_version),
                "manifest_storage_key": f"repositories/{repo_id}/versions/{version_id}/manifest.json",
                "manifest_sha256": manifest_hash, "validation_status": "passed", "critical_issue_count": 0,
                "coverage": {}, "started_at": EPOCH, "finished_at": EPOCH,
                "activated_at": EPOCH if lifecycle == "active" else None,
            })
        prepared["repositories"][-1]["active_index_version_id"] = active_id

    for row in rows["file_records"]:
        path = _relative_path(row["path"])
        key = (row["repository_id"], int(row["index_version"]), path)
        if key in file_ids:
            raise LegacyUpgradeError("Legacy file paths are not unique within a version")
        file_id = _stable_id("fileobs_", *key)
        file_ids[key] = file_id
        prepared["files"].append({
            "id": file_id, "repository_id": repo_ids[key[0]], "index_version_id": version_ids[key[:2]], "canonical_key": path,
            "relative_path": path, "language": row["language"], "file_type": row["file_type"], "byte_size": int(row["size_bytes"]),
            "content_sha256": row["content_hash"], "encoding": "utf-8", "parse_status": row["parse_status"],
            "producer_stage": "legacy_upgrade", "producer_name": "sqlite_mapper", "producer_version": "1",
        })

    def file_id_for(row: dict[str, Any], field: str = "file_path") -> str:
        key = (row["repository_id"], int(row["index_version"]), _relative_path(row[field]))
        try:
            return file_ids[key]
        except KeyError as exc:
            raise LegacyUpgradeError("Legacy observation references an unknown file") from exc

    for row in rows["symbol_records"]:
        prepared["symbols"].append({
            "id": row["id"] if row["id"].startswith("symbolobs_") else _stable_id("symbolobs_", row["repository_id"], row["index_version"], row["id"]),
            "repository_id": repo_ids[row["repository_id"]], "index_version_id": version_ids[(row["repository_id"], int(row["index_version"]))],
            "canonical_key": row["id"], "file_id": file_id_for(row), "name": row["name"], "qualified_name": row["name"],
            "symbol_kind": row["symbol_type"], "signature": row.get("signature"), "start_line": int(row["start_line"]), "end_line": int(row["end_line"]),
            "producer_stage": "legacy_upgrade", "producer_name": "sqlite_mapper", "producer_version": "1", "support_type": "source_exact", "diagnostic_ids": [],
        })
    for row in rows["endpoint_records"]:
        prepared["endpoints"].append({
            "id": _stable_id("endpointobs_", row["repository_id"], row["index_version"], row["id"]), "repository_id": repo_ids[row["repository_id"]],
            "index_version_id": version_ids[(row["repository_id"], int(row["index_version"]))], "canonical_key": f"{row['method']}:{row['path']}:{row['handler']}",
            "file_id": file_id_for(row), "protocol": "http", "method": row["method"], "normalized_route": row["path"],
            "start_line": int(row["start_line"]), "end_line": int(row["end_line"]), "producer_stage": "legacy_upgrade",
            "producer_name": "sqlite_mapper", "producer_version": "1", "support_type": "source_exact", "diagnostic_ids": [],
        })
    for row in rows["chunk_records"]:
        prepared["chunks"].append({
            "id": row["id"] if row["id"].startswith("chunkobs_") else _stable_id("chunkobs_", row["repository_id"], row["index_version"], row["id"]),
            "repository_id": repo_ids[row["repository_id"]], "index_version_id": version_ids[(row["repository_id"], int(row["index_version"]))],
            "canonical_key": row["id"], "source_entity_type": row["chunk_type"], "source_canonical_key": row.get("symbol_name") or _relative_path(row["file_path"]),
            "file_id": file_id_for(row), "chunk_kind": row["chunk_type"], "ordinal": 0, "start_line": int(row["start_line"]), "end_line": int(row["end_line"]),
            "content_sha256": row["content_hash"] if SHA256_RE.fullmatch(row.get("content_hash") or "") else _sha256(row["content"]),
            "safe_preview": row["content"][:500], "retrieval_metadata": {}, "producer_stage": "legacy_upgrade", "producer_name": "sqlite_mapper", "producer_version": "1",
        })
    for row in rows["graph_nodes"]:
        key = (row["repository_id"], int(row["index_version"]), row["id"])
        node_id = row["id"] if row["id"].startswith("nodeobs_") else _stable_id("nodeobs_", *key)
        node_ids[key] = node_id
        prepared["graph_nodes"].append({
            "id": node_id, "repository_id": repo_ids[key[0]], "index_version_id": version_ids[key[:2]], "canonical_key": row["id"],
            "node_type": row["type"], "label": row["label"], "file_id": file_id_for(row) if row.get("file_path") else None,
            "start_line": row.get("start_line"), "end_line": row.get("end_line"), "coverage_state": row.get("coverage") or "deep_indexed",
            "metadata": _json(row.get("metadata_json"), {}), "producer_stage": "legacy_upgrade", "producer_name": "sqlite_mapper", "producer_version": "1",
            "support_type": "static_resolved", "diagnostic_ids": [],
        })
    for row in rows["graph_edges"]:
        base = (row["repository_id"], int(row["index_version"]))
        try:
            source_id, target_id = node_ids[(*base, row["source"])], node_ids[(*base, row["target"])]
        except KeyError as exc:
            raise LegacyUpgradeError("Legacy graph edge is dangling") from exc
        prepared["graph_edges"].append({
            "id": _stable_id("edgeobs_", *base, row["id"]), "repository_id": repo_ids[base[0]], "index_version_id": version_ids[base],
            "canonical_key": str(row["id"]), "source_node_id": source_id, "target_node_id": target_id, "edge_type": row["type"],
            "weight": row.get("weight"), "metadata": _json(row.get("metadata_json"), {}), "producer_stage": "legacy_upgrade",
            "producer_name": "sqlite_mapper", "producer_version": "1", "support_type": "static_resolved", "confidence": float(row["confidence"]), "diagnostic_ids": [],
        })
    for row in rows["evidence"]:
        file_id = file_id_for(row)
        prepared["evidence"].append({
            "id": row["evidence_id"] if row["evidence_id"].startswith("evidence_") else _stable_id("evidence_", row["evidence_id"]),
            "repository_id": repo_ids[row["repository_id"]], "index_version_id": version_ids[(row["repository_id"], int(row["index_version"]))],
            "source_entity_type": row["source_type"], "source_canonical_key": row.get("symbol_name") or _relative_path(row["file_path"]), "file_id": file_id,
            "start_line": int(row["start_line"]), "end_line": int(row["end_line"]), "content_sha256": _sha256(row["content_preview"]),
            "support_type": "source_exact", "producer_stage": "legacy_upgrade", "producer_name": "sqlite_mapper", "producer_version": "1",
            "retrieval_source": row["retrieval_source"], "selection_reason": row["relevance_reason"],
            "freshness": "stale" if int(row["is_stale"]) else "fresh", "safe_preview": row["content_preview"], "validation_details": _json(row.get("metadata_json"), {}),
        })

    # Jobs are preserved after identities exist; a deterministic idempotency scope is created for each.
    active_jobs: set[str] = set()
    for row in rows["indexing_jobs"]:
        repo_id = repo_ids[row["repository_id"]]
        state = row["status"] if row["status"] in {"queued", "running", "succeeded", "succeeded_with_warnings", "failed", "cancelled"} else "failed"
        if state in {"queued", "running"} and repo_id in active_jobs:
            raise LegacyUpgradeError("Legacy source has multiple active jobs for one repository")
        active_jobs.add(repo_id) if state in {"queued", "running"} else None
        job_id = row["id"] if row["id"].startswith("job_") else _stable_id("job_", row["id"])
        idem_id = _stable_id("idem_", job_id)
        prepared["idempotency_records"].append({
            "id": idem_id, "principal_id": "principal_legacy", "operation": "legacy_index_job", "idempotency_key": job_id,
            "normalized_request_hash": _sha256(job_id), "state": "completed", "resource_type": "index_job", "resource_id": job_id, "expires_at": EPOCH,
        })
        version_id = version_ids[(row["repository_id"], int(row["index_version"]))]
        prepared["index_jobs"].append({
            "id": job_id, "repository_id": repo_id, "source_snapshot_id": prepared["source_snapshots"][[x["repository_id"] for x in prepared["source_snapshots"]].index(repo_id)]["id"],
            "requested_build_kind": "full", "effective_build_kind": "full", "target_index_version_id": version_id,
            "state": state, "idempotency_record_id": idem_id, "lease_generation": 0, "repository_generation": 0,
            "stage_code": row["current_step"], "progress_completed": int(row["processed_files"]), "progress_total": int(row["total_files"]), "progress_unit": "files",
            "warning_count": len(_json(row.get("warnings_json"), [])), "error_code": row.get("error_code"), "error_message_safe": row.get("error_message"),
            "queued_at": EPOCH, "started_at": EPOCH if state != "queued" else None, "finished_at": EPOCH if state in {"succeeded", "succeeded_with_warnings", "failed", "cancelled"} else None,
        })

    insertion_order = [table.name for table in ProductionBase.metadata.sorted_tables]
    with target_engine.begin() as connection:
        if connection.scalar(select(func.count()).select_from(tables["repositories"])):
            raise LegacyUpgradeError("Target production schema is not empty")
        for name in insertion_order:
            if prepared[name]:
                connection.execute(insert(tables[name]), prepared[name])

    return {name: len(values) for name, values in prepared.items() if values}
