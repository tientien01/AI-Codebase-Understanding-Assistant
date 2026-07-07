from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TreeSitterNodeInfo:
    type: str
    text: str
    start_line: int
    end_line: int


class TreeSitterAdapterBase:
    """Shared helpers for language adapters that normalize tree-sitter nodes into IR."""

    def node_text(self, content: bytes, node: Any) -> str:
        return content[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def node_info(self, content: bytes, node: Any) -> TreeSitterNodeInfo:
        return TreeSitterNodeInfo(
            type=node.type,
            text=self.node_text(content, node),
            start_line=self._row(node.start_point) + 1,
            end_line=self._row(node.end_point) + 1,
        )

    def children_of_type(self, node: Any, *types: str) -> list[Any]:
        wanted = set(types)
        return [child for child in node.children if child.type in wanted]

    def first_child_of_type(self, node: Any, *types: str):
        wanted = set(types)
        return next((child for child in node.children if child.type in wanted), None)

    def walk(self, node: Any):
        yield node
        for child in node.children:
            yield from self.walk(child)

    def _row(self, point) -> int:
        return point[0] if isinstance(point, tuple) else point.row
