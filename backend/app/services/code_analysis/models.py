from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from app.services.code_analysis.graph_candidates import NormalizedGraphArtifact


_SHA256_RE = re.compile(r"(?:sha256:)?([0-9a-f]{64})\Z")
_WINDOWS_DRIVE_RE = re.compile(r"[A-Za-z]:/")


def canonical_file_key(file_path: str) -> str:
    """Return the repository-local canonical key for a validated POSIX path."""
    return f"file:v1:{quote(file_path, safe='/-._~')}"


def canonical_symbol_key(file_key: str, qualified_name: str, symbol_kind: str) -> str:
    encoded_file_key = quote(file_key, safe="")
    encoded_name = quote(qualified_name, safe="-._~")
    return f"symbol:v1:python:{symbol_kind}:{encoded_file_key}:{encoded_name}"


@dataclass(frozen=True)
class ParseRequest:
    """Immutable, file-local input to a language adapter."""

    repository_id: str
    index_version_id: str
    file_path: str
    language: str
    content_hash: str
    source: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.repository_id or not self.index_version_id:
            raise ValueError("repository and index version identities are required")
        if (
            not self.file_path
            or "\\" in self.file_path
            or self.file_path.startswith("/")
            or _WINDOWS_DRIVE_RE.match(self.file_path) is not None
            or any(part in {"", ".", ".."} for part in self.file_path.split("/"))
        ):
            raise ValueError("file path must be a canonical relative POSIX path")
        if not self.language or self.language != self.language.lower():
            raise ValueError("language must be a lowercase canonical name")
        match = _SHA256_RE.fullmatch(self.content_hash)
        if match is None:
            raise ValueError("content hash must be a lowercase SHA-256 identity")
        object.__setattr__(self, "content_hash", f"sha256:{match.group(1)}")

    @property
    def file_key(self) -> str:
        return canonical_file_key(self.file_path)

    @classmethod
    def from_compatibility_state(
        cls,
        *,
        repository_id: str,
        index_version: int,
        file_path: str,
        language: str,
        declared_content_hash: str,
        source: str,
    ) -> "ParseRequest":
        """Bridge MVP records that may predate canonical SHA-256 scan hashes."""
        match = _SHA256_RE.fullmatch(declared_content_hash)
        content_hash = match.group(1) if match else hashlib.sha256(source.encode("utf-8")).hexdigest()
        return cls(
            repository_id=repository_id,
            index_version_id=f"idx_compat_{index_version}",
            file_path=file_path,
            language=language,
            content_hash=content_hash,
            source=source,
        )


@dataclass
class IRNode:
    id: str
    kind: str
    file_path: str
    ast_path: str
    start_line: int
    end_line: int
    text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class IRImport(IRNode):
    module: str = ""
    imported_name: str | None = None
    alias: str | None = None
    level: int = 0


@dataclass
class IRDecorator:
    name: str
    args: list[str] = field(default_factory=list)
    kwargs: dict[str, str] = field(default_factory=dict)
    line: int | None = None


@dataclass
class IRParameter(IRNode):
    name: str = ""


@dataclass
class IRExpression(IRNode):
    name: str | None = None
    value: str | None = None
    children: list["IRExpression"] = field(default_factory=list)


@dataclass
class IRStatement(IRNode):
    expressions: list[IRExpression] = field(default_factory=list)
    targets: list[IRExpression] = field(default_factory=list)
    body: list["IRStatement"] = field(default_factory=list)
    orelse: list["IRStatement"] = field(default_factory=list)
    handlers: list["IRStatement"] = field(default_factory=list)


@dataclass
class IRFunction(IRNode):
    name: str = ""
    qualified_name: str = ""
    parameters: list[IRParameter] = field(default_factory=list)
    body: list[IRStatement] = field(default_factory=list)
    decorators: list[IRDecorator] = field(default_factory=list)
    is_async: bool = False


@dataclass
class IRClass(IRNode):
    name: str = ""
    qualified_name: str = ""
    body: list[IRNode] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)


@dataclass
class IREndpoint:
    method: str
    path: str
    handler: str
    handler_qualified_name: str
    file_path: str
    start_line: int
    end_line: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class IRModule:
    schema_version: str
    repository_id: str
    index_version_id: str
    file_key: str
    content_hash: str
    adapter_name: str
    adapter_version: str
    id: str
    file_path: str
    language: str
    imports: list[IRImport] = field(default_factory=list)
    classes: list[IRClass] = field(default_factory=list)
    functions: list[IRFunction] = field(default_factory=list)
    statements: list[IRStatement] = field(default_factory=list)
    endpoints: list[IREndpoint] = field(default_factory=list)
    diagnostics: list[dict[str, str | int | None]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Produce a JSON-compatible deterministic ParsedFile envelope."""
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class SourceSpan:
    file_key: str
    start_line: int
    end_line: int
    content_hash: str

    def __post_init__(self) -> None:
        if not self.file_key.startswith("file:v1:"):
            raise ValueError("source span requires a canonical file key")
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("source span must be a valid inclusive range")
        match = _SHA256_RE.fullmatch(self.content_hash)
        if match is None:
            raise ValueError("source span requires a lowercase SHA-256 identity")
        object.__setattr__(self, "content_hash", f"sha256:{match.group(1)}")


@dataclass(frozen=True)
class ResolvedReference:
    schema_version: str
    canonical_key: str
    repository_id: str
    index_version_id: str
    source_file_key: str
    source_entity_key: str | None
    reference_type: str
    raw_reference: str
    outcome: str
    target_keys: tuple[str, ...]
    resolution_method: str
    support_type: str
    source_spans: tuple[SourceSpan, ...]
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != "resolved-reference/v1":
            raise ValueError("unsupported resolved-reference schema")
        if not self.canonical_key.startswith("reference:v1:"):
            raise ValueError("reference requires a canonical key")
        if not self.source_file_key.startswith("file:v1:"):
            raise ValueError("reference requires a canonical source file key")
        if self.source_entity_key is not None and not self.source_entity_key.startswith("symbol:v1:"):
            raise ValueError("reference source entity must be a canonical symbol key")
        if self.reference_type not in {"import", "call"} or not self.raw_reference:
            raise ValueError("reference type and raw value are required")
        if self.support_type not in {"source_exact", "static_resolved", "static_ambiguous"}:
            raise ValueError("invalid static reference support type")
        if self.outcome not in {"resolved", "ambiguous", "unresolved"}:
            raise ValueError("invalid reference outcome")
        if tuple(sorted(set(self.target_keys))) != self.target_keys:
            raise ValueError("reference target keys must be unique and sorted")
        if self.outcome == "resolved" and (len(self.target_keys) != 1 or self.unresolved_reason is not None):
            raise ValueError("resolved reference requires exactly one target")
        if self.outcome == "ambiguous" and (len(self.target_keys) < 2 or self.unresolved_reason is not None):
            raise ValueError("ambiguous reference requires at least two targets")
        if self.outcome == "unresolved" and (self.target_keys or not self.unresolved_reason):
            raise ValueError("unresolved reference requires a reason and no targets")
        if not self.source_spans:
            raise ValueError("reference requires source provenance")
        if any(span.file_key != self.source_file_key for span in self.source_spans):
            raise ValueError("reference spans must belong to the source file")


@dataclass(frozen=True)
class ReferenceArtifact:
    schema_version: str
    repository_id: str
    index_version_id: str
    producer_name: str
    producer_version: str
    references: tuple[ResolvedReference, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "resolved-reference-set/v1":
            raise ValueError("unsupported reference artifact schema")
        keys = [item.canonical_key for item in self.references]
        if len(keys) != len(set(keys)):
            raise ValueError("reference artifact keys must be unique")
        if any(
            item.repository_id != self.repository_id or item.index_version_id != self.index_version_id
            for item in self.references
        ):
            raise ValueError("reference artifact ownership must be uniform")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class CFGNode:
    id: str
    kind: str
    label: str
    file_path: str
    function_qualified_name: str
    start_line: int
    end_line: int


@dataclass
class CFGEdge:
    source: str
    target: str
    type: str
    confidence: float = 0.9


@dataclass
class CFGGraph:
    function_id: str
    nodes: list[CFGNode] = field(default_factory=list)
    edges: list[CFGEdge] = field(default_factory=list)


@dataclass
class DFGNode:
    id: str
    kind: str
    name: str
    file_path: str
    function_qualified_name: str
    line: int


@dataclass
class DFGEdge:
    source: str
    target: str
    type: str
    confidence: float = 0.85


@dataclass
class DFGGraph:
    function_id: str
    nodes: list[DFGNode] = field(default_factory=list)
    edges: list[DFGEdge] = field(default_factory=list)


@dataclass
class CPGResult:
    module: IRModule
    cfg_graphs: list[CFGGraph] = field(default_factory=list)
    dfg_graphs: list[DFGGraph] = field(default_factory=list)
    references: ReferenceArtifact | None = None
    normalized_graph: NormalizedGraphArtifact | None = None
