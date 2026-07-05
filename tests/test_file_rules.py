from __future__ import annotations

from pathlib import Path

from app.services.scanning.file_rules import detect_language, is_secret_file, is_supported_file


def test_secret_file_rules_skip_real_credentials() -> None:
    assert is_secret_file(".env")
    assert is_secret_file(".env.local")
    assert is_secret_file("secrets.json")
    assert is_secret_file("credentials.yml")
    assert is_secret_file("private.key")
    assert is_secret_file("certificate.pem")


def test_secret_file_rules_allow_example_env() -> None:
    assert not is_secret_file(".env.example")


def test_supported_files_cover_mvp_source_and_docs() -> None:
    assert is_supported_file(Path("app.py"))
    assert is_supported_file(Path("LoginPage.tsx"))
    assert is_supported_file(Path("README.md"))
    assert is_supported_file(Path("Dockerfile"))
    assert not is_supported_file(Path("diagram.png"))


def test_language_detection_for_mvp_stack() -> None:
    assert detect_language(Path("main.py")) == "python"
    assert detect_language(Path("authApi.ts")) == "typescript"
    assert detect_language(Path("README.md")) == "markdown"
