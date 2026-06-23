from __future__ import annotations

from pathlib import Path

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
    ".idea",
    ".vscode",
    "target",
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
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
    return path.suffix.lower() in SUPPORTED_EXTENSIONS or path.name in {"Dockerfile", "docker-compose.yml"}


def detect_language(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in {".js", ".jsx"}:
        return "javascript"
    if suffix in {".ts", ".tsx"}:
        return "typescript"
    if suffix == ".md":
        return "markdown"
    if path.name == "Dockerfile":
        return "docker"
    return "config"


def detect_file_type(path: Path) -> str:
    if "test" in path.as_posix().lower():
        return "test"
    language = detect_language(path)
    if language in {"python", "javascript", "typescript"}:
        return "source"
    if language == "markdown":
        return "document"
    return "config"
