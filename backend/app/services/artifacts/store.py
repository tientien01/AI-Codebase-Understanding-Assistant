"""Safe immutable filesystem implementation of the artifact storage port."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable, Protocol


SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_%=+.-]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class ArtifactStoreError(RuntimeError):
    """Stable artifact failure that never contains the configured host root."""


class UnsafeArtifactKeyError(ArtifactStoreError):
    pass


class ArtifactNotFoundError(ArtifactStoreError):
    pass


class ArtifactIntegrityError(ArtifactStoreError):
    pass


class ArtifactConflictError(ArtifactStoreError):
    pass


@dataclass(frozen=True)
class StoredArtifact:
    key: str
    sha256: str
    byte_size: int


class ArtifactStorePort(Protocol):
    def write(
        self,
        key: str,
        chunks: Iterable[bytes],
        *,
        expected_sha256: str,
        expected_size: int,
    ) -> StoredArtifact: ...

    def verify(
        self, key: str, *, expected_sha256: str, expected_size: int
    ) -> StoredArtifact: ...

    def read_bytes(
        self, key: str, *, expected_sha256: str, expected_size: int
    ) -> bytes: ...


def validate_logical_key(key: str) -> str:
    if not key or "\\" in key or "\x00" in key or key.startswith("/"):
        raise UnsafeArtifactKeyError("Artifact key must be a relative POSIX key")
    parts = key.split("/")
    for part in parts:
        stem = part.split(".", 1)[0].upper()
        if (
            part in {"", ".", ".."}
            or not SAFE_SEGMENT.fullmatch(part)
            or part.endswith(".")
            or stem in WINDOWS_RESERVED
        ):
            raise UnsafeArtifactKeyError("Artifact key contains an unsafe segment")
    return key


def version_root_key(repository_id: str, index_version_id: str) -> str:
    if not re.fullmatch(r"repo_[A-Za-z0-9][A-Za-z0-9_-]{0,127}", repository_id):
        raise UnsafeArtifactKeyError("Invalid repository artifact owner")
    if not re.fullmatch(r"idx_[A-Za-z0-9][A-Za-z0-9_-]{0,127}", index_version_id):
        raise UnsafeArtifactKeyError("Invalid index-version artifact owner")
    return f"repositories/{repository_id}/indexes/{index_version_id}"


def artifact_key(
    repository_id: str,
    index_version_id: str,
    artifact_type: str,
    filename: str,
) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", artifact_type):
        raise UnsafeArtifactKeyError("Invalid artifact type")
    key = f"{version_root_key(repository_id, index_version_id)}/artifacts/{artifact_type}/{filename}"
    validate_logical_key(key)
    if filename == "manifest.json":
        raise UnsafeArtifactKeyError("Manifest name is reserved at the version root")
    return key


def manifest_key(repository_id: str, index_version_id: str) -> str:
    return f"{version_root_key(repository_id, index_version_id)}/manifest.json"


class FilesystemArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def write(
        self,
        key: str,
        chunks: Iterable[bytes],
        *,
        expected_sha256: str,
        expected_size: int,
    ) -> StoredArtifact:
        self._validate_expected(expected_sha256, expected_size)
        destination = self._path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_beneath_root(destination)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".artifact-", dir=destination.parent, delete=False
            ) as handle:
                temporary = Path(handle.name)
                digest = hashlib.sha256()
                byte_size = 0
                for chunk in chunks:
                    if not isinstance(chunk, bytes):
                        raise TypeError("artifact chunks must be bytes")
                    handle.write(chunk)
                    digest.update(chunk)
                    byte_size += len(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            actual_sha256 = digest.hexdigest()
            if actual_sha256 != expected_sha256 or byte_size != expected_size:
                raise ArtifactIntegrityError(
                    f"Artifact bytes do not match declared metadata for key {key}"
                )
            try:
                os.link(temporary, destination)
            except FileExistsError:
                try:
                    return self.verify(
                        key,
                        expected_sha256=expected_sha256,
                        expected_size=expected_size,
                    )
                except ArtifactIntegrityError:
                    raise ArtifactConflictError(
                        f"Immutable artifact already exists with different bytes for key {key}"
                    ) from None
            except OSError:
                raise ArtifactStoreError(
                    f"Artifact could not be finalized for key {key}"
                ) from None
            return StoredArtifact(key, actual_sha256, byte_size)
        except ArtifactIntegrityError:
            raise
        except ArtifactStoreError:
            raise
        except (OSError, TypeError):
            raise ArtifactStoreError(f"Artifact write failed for key {key}") from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def verify(
        self, key: str, *, expected_sha256: str, expected_size: int
    ) -> StoredArtifact:
        self._validate_expected(expected_sha256, expected_size)
        path = self._path(key)
        digest = hashlib.sha256()
        byte_size = 0
        try:
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
                    byte_size += len(chunk)
        except FileNotFoundError:
            raise ArtifactNotFoundError(f"Artifact is missing for key {key}") from None
        except OSError:
            raise ArtifactStoreError(f"Artifact read failed for key {key}") from None
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256 or byte_size != expected_size:
            raise ArtifactIntegrityError(f"Artifact is corrupt for key {key}")
        return StoredArtifact(key, actual_sha256, byte_size)

    def read_bytes(
        self, key: str, *, expected_sha256: str, expected_size: int
    ) -> bytes:
        self._validate_expected(expected_sha256, expected_size)
        path = self._path(key)
        digest = hashlib.sha256()
        payload = bytearray()
        try:
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
                    payload.extend(chunk)
        except FileNotFoundError:
            raise ArtifactNotFoundError(f"Artifact is missing for key {key}") from None
        except OSError:
            raise ArtifactStoreError(f"Artifact read failed for key {key}") from None
        if len(payload) != expected_size or digest.hexdigest() != expected_sha256:
            raise ArtifactIntegrityError(f"Artifact is corrupt for key {key}")
        return bytes(payload)

    def _path(self, key: str) -> Path:
        validate_logical_key(key)
        path = self.root.joinpath(*key.split("/"))
        self._ensure_beneath_root(path)
        return path

    def _ensure_beneath_root(self, path: Path) -> None:
        try:
            path.resolve(strict=False).relative_to(self.root)
        except ValueError:
            raise UnsafeArtifactKeyError("Artifact key resolves outside its root") from None

    def _validate_expected(self, sha256: str, byte_size: int) -> None:
        if not SHA256.fullmatch(sha256):
            raise ValueError("expected_sha256 must be lowercase SHA-256")
        if byte_size < 0:
            raise ValueError("expected_size must be non-negative")
