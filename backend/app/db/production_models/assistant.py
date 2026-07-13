"""Evidence, conversation, claim, citation, and agent trace tables."""

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Table, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CHAR

from app.db.production_base import ProductionBase
from app.db.production_models.common import created_at, json_object, nonnegative, prefix_check, range_check, sha256_check, updated_at

m = ProductionBase.metadata

evidence = Table(
    "evidence", m,
    Column("id", Text, primary_key=True), Column("repository_id", Text, nullable=False), Column("index_version_id", Text, nullable=False),
    Column("source_entity_type", Text, nullable=False), Column("source_canonical_key", Text, nullable=False), Column("file_id", Text),
    Column("start_line", Integer), Column("end_line", Integer), Column("content_sha256", CHAR(64), nullable=False), Column("support_type", Text, nullable=False),
    Column("producer_stage", Text, nullable=False), Column("producer_name", Text, nullable=False), Column("producer_version", Text, nullable=False),
    Column("retrieval_source", Text, nullable=False), Column("selection_reason", Text, nullable=False),
    Column("freshness", Text, nullable=False, server_default=text("'fresh'")), Column("safe_preview", Text, nullable=False), json_object("validation_details"),
    created_at(), Column("staled_at", DateTime(timezone=True)),
    ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="RESTRICT", name="fk_evidence_version"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "file_id"], ["files.repository_id", "files.index_version_id", "files.id"], ondelete="RESTRICT", name="fk_evidence_file"),
    UniqueConstraint("repository_id", "index_version_id", "id", name="uq_evidence_owner"), prefix_check("id", "evidence_", "id_prefix"),
    range_check("start_line", "end_line", "source_range", nullable=True), sha256_check("content_sha256", "content_sha256"),
    CheckConstraint("support_type IN ('source_exact','static_resolved','static_ambiguous','heuristic_inferred','llm_inferred','user_supplied')", name="support_type"),
    CheckConstraint("freshness IN ('fresh','stale','invalid')", name="evidence_freshness"),
)
Index("ix_evidence_source", evidence.c.repository_id, evidence.c.index_version_id, evidence.c.source_canonical_key, evidence.c.created_at.desc(), evidence.c.id)

conversations = Table(
    "conversations", m, Column("id", Text, primary_key=True),
    Column("principal_id", Text, ForeignKey("operator_principals.id", ondelete="RESTRICT"), nullable=False),
    Column("repository_id", Text, ForeignKey("repositories.id", ondelete="RESTRICT"), nullable=False), Column("title", Text),
    Column("status", Text, nullable=False, server_default=text("'active'")), created_at(), updated_at(),
    prefix_check("id", "conversation_", "id_prefix"), CheckConstraint("status IN ('active','archived','deleted')", name="status"),
)
Index("ix_conversations_recent", conversations.c.principal_id, conversations.c.repository_id, conversations.c.updated_at.desc(), conversations.c.id.desc())

messages = Table(
    "messages", m, Column("id", Text, primary_key=True),
    Column("conversation_id", Text, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
    Column("repository_id", Text, ForeignKey("repositories.id", ondelete="RESTRICT"), nullable=False), Column("index_version_id", Text),
    Column("role", Text, nullable=False), Column("content", Text, nullable=False), Column("assistant_outcome", Text), Column("request_id", Text), created_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="RESTRICT", name="fk_messages_version"),
    UniqueConstraint("conversation_id", "id", name="uq_messages_conversation"),
    UniqueConstraint("repository_id", "index_version_id", "id", name="uq_messages_owner"), prefix_check("id", "message_", "id_prefix"),
    CheckConstraint("role IN ('operator','assistant','system')", name="message_role"),
    CheckConstraint("assistant_outcome IS NULL OR assistant_outcome IN ('answered','limited','insufficient_evidence','cancelled','failed')", name="assistant_outcome"),
)
Index("ix_messages_order", messages.c.conversation_id, messages.c.created_at, messages.c.id)

claims = Table(
    "claims", m, Column("id", Text, primary_key=True), Column("message_id", Text, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
    Column("repository_id", Text, nullable=False), Column("index_version_id", Text, nullable=False), Column("claim_text", Text, nullable=False),
    Column("support_level", Text, nullable=False), Column("ordinal", Integer, nullable=False), created_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id", "message_id"], ["messages.repository_id", "messages.index_version_id", "messages.id"], ondelete="CASCADE", name="fk_claims_message_owner"),
    UniqueConstraint("repository_id", "index_version_id", "id", name="uq_claims_owner"), UniqueConstraint("message_id", "ordinal", name="uq_claims_ordinal"),
    prefix_check("id", "claim_", "id_prefix"), CheckConstraint("support_level IN ('supported','qualified','unsupported')", name="support_level"), nonnegative("ordinal", "ordinal_nonnegative"),
)

citations = Table(
    "citations", m, Column("id", Text, primary_key=True), Column("claim_id", Text, nullable=False), Column("evidence_id", Text, nullable=False),
    Column("repository_id", Text, nullable=False), Column("index_version_id", Text, nullable=False), Column("display_locator", Text, nullable=False), created_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id", "claim_id"], ["claims.repository_id", "claims.index_version_id", "claims.id"], ondelete="CASCADE", name="fk_citations_claim"),
    ForeignKeyConstraint(["repository_id", "index_version_id", "evidence_id"], ["evidence.repository_id", "evidence.index_version_id", "evidence.id"], ondelete="RESTRICT", name="fk_citations_evidence"),
    UniqueConstraint("claim_id", "evidence_id", name="uq_citations_claim_evidence"), prefix_check("id", "citation_", "id_prefix"),
)

agent_traces = Table(
    "agent_traces", m, Column("id", Text, primary_key=True),
    Column("principal_id", Text, ForeignKey("operator_principals.id", ondelete="RESTRICT"), nullable=False), Column("repository_id", Text, nullable=False),
    Column("index_version_id", Text), Column("conversation_id", Text, ForeignKey("conversations.id", ondelete="SET NULL")),
    Column("request_message_id", Text, ForeignKey("messages.id", ondelete="SET NULL")), Column("response_message_id", Text, ForeignKey("messages.id", ondelete="SET NULL")),
    Column("workflow_version", Text, nullable=False), Column("outcome", Text, nullable=False), json_object("budget_summary"), json_object("provider_summary"),
    Column("started_at", DateTime(timezone=True), nullable=False), Column("finished_at", DateTime(timezone=True)), created_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="RESTRICT", name="fk_agent_traces_version"),
    prefix_check("id", "trace_", "id_prefix"), CheckConstraint("outcome IN ('answered','limited','insufficient_evidence','cancelled','failed')", name="assistant_outcome"),
)

agent_trace_events = Table(
    "agent_trace_events", m, Column("id", Text, primary_key=True), Column("trace_id", Text, ForeignKey("agent_traces.id", ondelete="CASCADE"), nullable=False),
    Column("sequence", Integer, nullable=False), Column("event_type", Text, nullable=False), Column("tool_name", Text), Column("status", Text, nullable=False),
    Column("duration_ms", BigInteger), json_object("payload"), created_at(), UniqueConstraint("trace_id", "sequence", name="uq_agent_trace_events_sequence"),
    prefix_check("id", "traceevent_", "id_prefix"), CheckConstraint("sequence > 0", name="sequence_positive"),
    CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="duration_ms_nonnegative"),
)
Index("ix_trace_events_order", agent_trace_events.c.trace_id, agent_trace_events.c.sequence, agent_trace_events.c.id)
