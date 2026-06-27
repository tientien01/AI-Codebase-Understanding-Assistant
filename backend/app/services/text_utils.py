from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")


def preview(content: str, max_length: int = 420) -> str:
    compact = re.sub(r"\s+", " ", content).strip()
    return compact if len(compact) <= max_length else f"{compact[:max_length]}..."


def content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def node_id(node_type: str, value: str) -> str:
    return f"{node_type}_{hashlib.sha1(value.encode('utf-8')).hexdigest()[:10]}"


def normalize_route(route_path: str) -> str:
    normalized = route_path.strip().lower()
    if normalized.startswith("/api"):
        normalized = normalized[4:]
    return normalized.rstrip("/") or "/"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
