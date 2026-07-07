from __future__ import annotations

import hashlib


def stable_hash(*parts: object, length: int = 16) -> str:
    normalized = "\x1f".join("" if part is None else str(part) for part in parts)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:length]


def stable_file_id(repository_id: str, file_path: str) -> str:
    return f"file_{stable_hash(repository_id, file_path)}"


def stable_symbol_id(repository_id: str, file_path: str, qualified_name: str, symbol_kind: str) -> str:
    return f"symbol_{stable_hash(repository_id, file_path, qualified_name, symbol_kind)}"


def stable_chunk_id(repository_id: str, file_path: str, chunk_type: str, anchor_key: str, content_hash: str) -> str:
    return f"chunk_{stable_hash(repository_id, file_path, chunk_type, anchor_key, content_hash)}"


def stable_node_id(repository_id: str, node_type: str, stable_key: str) -> str:
    return f"{node_type}_{stable_hash(repository_id, node_type, stable_key)}"


def stable_edge_id(repository_id: str, source_id: str, target_id: str, edge_type: str, owning_file_path: str) -> str:
    return f"edge_{stable_hash(repository_id, source_id, target_id, edge_type, owning_file_path)}"


def stable_ast_id(repository_id: str, file_path: str, scope_key: str, ast_path: str, node_kind: str, snippet_hash: str) -> str:
    return f"ast_{stable_hash(repository_id, file_path, scope_key, ast_path, node_kind, snippet_hash)}"
