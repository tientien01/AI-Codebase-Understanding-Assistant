from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3


DDL = """
CREATE TABLE repositories (id TEXT PRIMARY KEY, name TEXT NOT NULL, source_type TEXT NOT NULL, source_uri TEXT, source_label TEXT, source_path TEXT NOT NULL, status TEXT NOT NULL, current_index_version INTEGER, project_fingerprint TEXT, logs_json TEXT, warnings_json TEXT, failed_files INTEGER, current_step TEXT, started_at TEXT, finished_at TEXT);
CREATE TABLE indexing_jobs (id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, status TEXT NOT NULL, current_step TEXT, total_files INTEGER, processed_files INTEGER, skipped_files INTEGER, failed_files INTEGER, total_chunks INTEGER, total_graph_nodes INTEGER, total_graph_edges INTEGER, started_at TEXT, finished_at TEXT, logs_json TEXT, warnings_json TEXT, skipped_files_json TEXT, failed_files_json TEXT, error_code TEXT, error_message TEXT);
CREATE TABLE file_records (id INTEGER PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, path TEXT NOT NULL, absolute_path TEXT NOT NULL, language TEXT NOT NULL, file_type TEXT NOT NULL, size_bytes INTEGER NOT NULL, content_hash TEXT NOT NULL, parse_status TEXT NOT NULL);
CREATE TABLE symbol_records (id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, name TEXT NOT NULL, symbol_type TEXT NOT NULL, file_path TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, metadata_json TEXT, signature TEXT);
CREATE TABLE endpoint_records (id INTEGER PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, method TEXT NOT NULL, path TEXT NOT NULL, handler TEXT NOT NULL, file_path TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, metadata_json TEXT);
CREATE TABLE chunk_records (id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, file_path TEXT NOT NULL, chunk_type TEXT NOT NULL, content TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, symbol_name TEXT, content_hash TEXT);
CREATE TABLE graph_nodes (id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, type TEXT NOT NULL, label TEXT NOT NULL, file_path TEXT, start_line INTEGER, end_line INTEGER, summary TEXT, tags_json TEXT, complexity TEXT, layer TEXT, coverage TEXT, scope_path TEXT, role TEXT, metadata_json TEXT);
CREATE TABLE graph_edges (id INTEGER PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, source TEXT NOT NULL, target TEXT NOT NULL, type TEXT NOT NULL, confidence REAL NOT NULL, evidence_level TEXT, weight REAL, metadata_json TEXT);
CREATE TABLE evidence (evidence_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, index_version INTEGER, source_type TEXT NOT NULL, file_path TEXT NOT NULL, symbol_name TEXT, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, content_preview TEXT NOT NULL, relevance_reason TEXT NOT NULL, confidence_score REAL NOT NULL, retrieval_source TEXT NOT NULL, is_stale INTEGER, metadata_json TEXT);
"""


def build_supported_legacy_fixture(root: Path) -> tuple[Path, Path]:
    managed_root = root / "managed"
    repository_root = managed_root / "repo_legacy"
    source_file = repository_root / "app.py"
    repository_root.mkdir(parents=True)
    content = b"def hello():\n    return 'hello'\n"
    source_file.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    database = root / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(DDL)
        connection.execute("INSERT INTO repositories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("repo_legacy", "Legacy", "upload_folder", None, "Legacy", str(repository_root), "ready", 0, digest, "[]", "[]", 0, "completed", None, None))
        connection.execute("INSERT INTO indexing_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("job_legacy", "repo_legacy", 0, "succeeded", "completed", 1, 1, 0, 0, 1, 2, 1, None, None, "[]", "[]", "[]", "[]", None, None))
        connection.execute("INSERT INTO file_records VALUES (?,?,?,?,?,?,?,?,?,?)", (1, "repo_legacy", 0, "app.py", str(source_file), "python", "source", len(content), digest, "parsed"))
        connection.execute("INSERT INTO symbol_records VALUES (?,?,?,?,?,?,?,?,?,?)", ("legacy_symbol", "repo_legacy", 0, "hello", "function", "app.py", 1, 2, "{}", "hello()"))
        connection.execute("INSERT INTO endpoint_records VALUES (?,?,?,?,?,?,?,?,?,?)", (1, "repo_legacy", 0, "GET", "/hello", "hello", "app.py", 1, 2, "{}"))
        connection.execute("INSERT INTO chunk_records VALUES (?,?,?,?,?,?,?,?,?,?)", ("legacy_chunk", "repo_legacy", 0, "app.py", "symbol", content.decode(), 1, 2, "hello", digest))
        connection.execute("INSERT INTO graph_nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("node_a", "repo_legacy", 0, "function", "hello", "app.py", 1, 2, None, "[]", None, None, "deep_indexed", None, None, "{}"))
        connection.execute("INSERT INTO graph_nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("node_b", "repo_legacy", 0, "module", "app", "app.py", 1, 2, None, "[]", None, None, "deep_indexed", None, None, "{}"))
        connection.execute("INSERT INTO graph_edges VALUES (?,?,?,?,?,?,?,?,?,?)", (1, "repo_legacy", 0, "node_a", "node_b", "DEFINED_IN", 1.0, "deep", 1.0, "{}"))
        connection.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("evidence_legacy", "repo_legacy", 0, "symbol", "app.py", "hello", 1, 2, "def hello()", "exact symbol", 1.0, "exact", 0, "{}"))
    return database, managed_root
