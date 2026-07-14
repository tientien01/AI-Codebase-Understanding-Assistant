from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IndexedFileSignal:
    path: str
    language: str
    content: str

    @property
    def normalized_path(self) -> str:
        return self.path.replace("\\", "/").lower()


@dataclass(frozen=True)
class RoleRule:
    role: str
    kind: str
    layer: str
    path_tokens: tuple[str, ...] = ()
    name_suffixes: tuple[str, ...] = ()
    source_markers: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    base_score: int = 0


@dataclass
class ComponentCandidate:
    role: str
    kind: str
    layer: str
    domain: str
    files: list[str] = field(default_factory=list)
    evidence: list[tuple[str, str]] = field(default_factory=list)
    score: int = 0


@dataclass(frozen=True)
class TechnologySignal:
    key: str
    label: str
    category: str
    markers: tuple[str, ...]
    relation_label: str
