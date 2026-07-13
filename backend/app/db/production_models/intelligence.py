"""Immutable versioned code-intelligence and graph production tables."""

from sqlalchemy import BigInteger, CheckConstraint, Column, Float, ForeignKeyConstraint, Index, Integer, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import CHAR

from app.db.production_base import ProductionBase
from app.db.production_models.common import created_at, json_array, json_object, json_type_check, nonnegative, paired, prefix_check, producer_columns, range_check, sha256_check, support_columns

m = ProductionBase.metadata


def version_fk(name: str, *, ondelete: str = "CASCADE") -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete=ondelete, name=name)


def version_identity(prefix: str):
    return (
        Column("id", Text, primary_key=True), Column("repository_id", Text, nullable=False),
        Column("index_version_id", Text, nullable=False), Column("canonical_key", Text, nullable=False),
        prefix_check("id", prefix, "id_prefix"),
    )


files = Table(
    "files", m, *version_identity("fileobs_"), Column("relative_path", Text, nullable=False), Column("language", Text, nullable=False),
    Column("file_type", Text, nullable=False), Column("byte_size", BigInteger, nullable=False), Column("content_sha256", CHAR(64), nullable=False),
    Column("encoding", Text, nullable=False), Column("parse_status", Text, nullable=False), *producer_columns(), created_at(),
    version_fk("fk_files_version"), UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_files_canonical_key"),
    UniqueConstraint("repository_id", "index_version_id", "id", name="uq_files_owner"),
    UniqueConstraint("repository_id", "index_version_id", "relative_path", name="uq_files_relative_path"),
    nonnegative("byte_size", "byte_size_nonnegative"), sha256_check("content_sha256", "content_sha256"),
    CheckConstraint("relative_path <> '' AND relative_path !~ '^/' AND relative_path !~ '(^|/)\\.\\.(/|$)' AND position(chr(92) in relative_path) = 0", name="relative_path"),
)
Index("ix_files_path", files.c.repository_id, files.c.index_version_id, files.c.relative_path, files.c.id)

symbols = Table(
    "symbols", m, *version_identity("symbolobs_"), Column("file_id", Text, nullable=False), Column("name", Text, nullable=False),
    Column("qualified_name", Text, nullable=False), Column("symbol_kind", Text, nullable=False), Column("signature", Text),
    Column("start_line", Integer, nullable=False), Column("end_line", Integer, nullable=False), *producer_columns(), *support_columns(), created_at(),
    version_fk("fk_symbols_version"), ForeignKeyConstraint(["repository_id", "index_version_id", "file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="CASCADE", name="fk_symbols_file"),
    UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_symbols_canonical_key"), range_check("start_line", "end_line", "source_range"),
    UniqueConstraint("repository_id", "index_version_id", "id", name="uq_symbols_owner"),
)
Index("ix_symbols_name", symbols.c.repository_id, symbols.c.index_version_id, symbols.c.name, symbols.c.canonical_key, symbols.c.id)

endpoints = Table(
    "endpoints", m, *version_identity("endpointobs_"), Column("file_id", Text, nullable=False), Column("handler_symbol_id", Text),
    Column("protocol", Text, nullable=False), Column("method", Text, nullable=False), Column("normalized_route", Text, nullable=False),
    Column("start_line", Integer, nullable=False), Column("end_line", Integer, nullable=False), *producer_columns(), *support_columns(), created_at(),
    version_fk("fk_endpoints_version"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="CASCADE", name="fk_endpoints_file"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "handler_symbol_id"], ["symbols.repository_id", "symbols.index_version_id", "symbols.id"], ondelete="SET NULL", name="fk_endpoints_handler"),
    UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_endpoints_canonical_key"),
    UniqueConstraint("repository_id", "index_version_id", "protocol", "method", "normalized_route", "handler_symbol_id", name="uq_endpoints_route_handler"),
    range_check("start_line", "end_line", "source_range"),
)
Index("ix_endpoints_route", endpoints.c.repository_id, endpoints.c.index_version_id, endpoints.c.protocol, endpoints.c.method, endpoints.c.normalized_route, endpoints.c.id)

references = Table(
    "references", m, *version_identity("reference_"), Column("source_file_id", Text, nullable=False), Column("source_symbol_id", Text),
    Column("source_canonical_key", Text, nullable=False), Column("target_entity_type", Text), Column("target_canonical_key", Text),
    Column("reference_type", Text, nullable=False), Column("outcome", Text, nullable=False), Column("start_line", Integer, nullable=False), Column("end_line", Integer, nullable=False),
    json_array("candidate_keys"), *producer_columns(), *support_columns(), created_at(), version_fk("fk_references_version"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "source_file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="CASCADE", name="fk_references_file"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "source_symbol_id"], ["symbols.repository_id", "symbols.index_version_id", "symbols.id"], ondelete="SET NULL", name="fk_references_symbol"),
    UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_references_canonical_key"),
    CheckConstraint("outcome IN ('resolved','ambiguous','unresolved')", name="reference_outcome"), range_check("start_line", "end_line", "source_range"),
    json_type_check("candidate_keys", "array", "candidate_keys_array"),
    CheckConstraint("(outcome = 'resolved' AND target_canonical_key IS NOT NULL) OR (outcome = 'unresolved' AND target_canonical_key IS NULL) OR (outcome = 'ambiguous' AND target_canonical_key IS NULL AND jsonb_array_length(candidate_keys) >= 2)", name="outcome_target"),
)
Index("ix_references_source", references.c.repository_id, references.c.index_version_id, references.c.source_canonical_key, references.c.reference_type, references.c.id)
Index("ix_references_target", references.c.repository_id, references.c.index_version_id, references.c.target_canonical_key, references.c.reference_type, references.c.id)

chunks = Table(
    "chunks", m, *version_identity("chunkobs_"), Column("source_entity_type", Text, nullable=False), Column("source_canonical_key", Text, nullable=False),
    Column("file_id", Text, nullable=False), Column("chunk_kind", Text, nullable=False), Column("ordinal", Integer, nullable=False),
    Column("start_line", Integer, nullable=False), Column("end_line", Integer, nullable=False), Column("content_sha256", CHAR(64), nullable=False),
    Column("safe_preview", Text, nullable=False), Column("artifact_id", Text), Column("artifact_offset", BigInteger), Column("artifact_length", BigInteger),
    json_object("retrieval_metadata"), *producer_columns(), created_at(), version_fk("fk_chunks_version"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="CASCADE", name="fk_chunks_file"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "artifact_id"], ["index_artifacts.repository_id", "index_artifacts.index_version_id", "index_artifacts.id"], ondelete="SET NULL", name="fk_chunks_artifact"),
    UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_chunks_canonical_key"),
    nonnegative("ordinal", "ordinal_nonnegative"), range_check("start_line", "end_line", "source_range"), sha256_check("content_sha256", "content_sha256"),
    CheckConstraint("(artifact_id IS NULL AND artifact_offset IS NULL AND artifact_length IS NULL) OR (artifact_id IS NOT NULL AND artifact_offset >= 0 AND artifact_length >= 0)", name="artifact_location"),
)
Index("ix_chunks_source", chunks.c.repository_id, chunks.c.index_version_id, chunks.c.source_canonical_key, chunks.c.ordinal, chunks.c.id)

graph_candidates = Table(
    "graph_candidates", m, *version_identity("candidate_"), Column("candidate_kind", Text, nullable=False), Column("source_canonical_key", Text),
    Column("target_canonical_key", Text), Column("relation_type", Text), Column("origin", Text, nullable=False), Column("file_id", Text),
    Column("start_line", Integer), Column("end_line", Integer), Column("status", Text, nullable=False), Column("normalization_reason", Text),
    *producer_columns(), *support_columns(), created_at(), version_fk("fk_graph_candidates_version"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="SET NULL", name="fk_graph_candidates_file"),
    UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_graph_candidates_canonical_key"),
    CheckConstraint("candidate_kind IN ('node','edge')", name="candidate_kind"), CheckConstraint("status IN ('pending','accepted','changed','dropped')", name="status"),
    range_check("start_line", "end_line", "source_range", nullable=True),
    CheckConstraint("(candidate_kind = 'edge' AND source_canonical_key IS NOT NULL AND target_canonical_key IS NOT NULL AND relation_type IS NOT NULL) OR (candidate_kind = 'node' AND target_canonical_key IS NULL)", name="candidate_shape"),
)

graph_nodes = Table(
    "graph_nodes", m, *version_identity("nodeobs_"), Column("node_type", Text, nullable=False), Column("label", Text, nullable=False),
    Column("file_id", Text), Column("entity_canonical_key", Text), Column("start_line", Integer), Column("end_line", Integer),
    Column("coverage_state", Text, nullable=False), json_object("metadata"), *producer_columns(), *support_columns(), created_at(), version_fk("fk_graph_nodes_version"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="SET NULL", name="fk_graph_nodes_file"),
    UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_graph_nodes_canonical_key"),
    UniqueConstraint("repository_id", "index_version_id", "id", name="uq_graph_nodes_owner"), range_check("start_line", "end_line", "source_range", nullable=True),
)

graph_edges = Table(
    "graph_edges", m, *version_identity("edgeobs_"), Column("source_node_id", Text, nullable=False), Column("target_node_id", Text, nullable=False),
    Column("edge_type", Text, nullable=False), Column("file_id", Text), Column("start_line", Integer), Column("end_line", Integer), Column("weight", Float),
    json_object("metadata"), *producer_columns(), *support_columns(), created_at(), version_fk("fk_graph_edges_version"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "source_node_id"], ["graph_nodes.repository_id", "graph_nodes.index_version_id", "graph_nodes.id"], ondelete="CASCADE", name="fk_graph_edges_source"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "target_node_id"], ["graph_nodes.repository_id", "graph_nodes.index_version_id", "graph_nodes.id"], ondelete="CASCADE", name="fk_graph_edges_target"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="SET NULL", name="fk_graph_edges_file"),
    UniqueConstraint("repository_id", "index_version_id", "canonical_key", name="uq_graph_edges_canonical_key"), range_check("start_line", "end_line", "source_range", nullable=True),
)
Index("ix_graph_edges_forward", graph_edges.c.repository_id, graph_edges.c.index_version_id, graph_edges.c.source_node_id, graph_edges.c.edge_type, graph_edges.c.target_node_id, graph_edges.c.id)
Index("ix_graph_edges_reverse", graph_edges.c.repository_id, graph_edges.c.index_version_id, graph_edges.c.target_node_id, graph_edges.c.edge_type, graph_edges.c.source_node_id, graph_edges.c.id)
