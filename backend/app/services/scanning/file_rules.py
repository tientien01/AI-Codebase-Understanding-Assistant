from __future__ import annotations

from pathlib import Path

from app.services.language_registry import SOURCE_LANGUAGES, language_definition_for_path

IGNORE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    ".cache",
    ".ai-codebase",
    ".idea",
    ".vscode",
    "target",
}

SECRET_PATTERNS = (
    ".env",
    "secrets.",
    "credentials.",
    ".pem",
    ".key",
)


def is_secret_file(file_name: str) -> bool:
    lower = file_name.lower()
    if lower == ".env.example":
        return False
    return lower == ".env" or any(pattern in lower for pattern in SECRET_PATTERNS)


def is_supported_file(path: Path) -> bool:
    return language_definition_for_path(path) is not None


def detect_language(path: Path) -> str:
    definition = language_definition_for_path(path)
    return definition.language if definition else "unknown"


def detect_file_type(path: Path) -> str:
    if "test" in path.as_posix().lower():
        return "test"
    definition = language_definition_for_path(path)
    if definition and definition.language in SOURCE_LANGUAGES:
        return "source"
    if definition:
        return definition.file_type
    return "config"
