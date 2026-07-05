from __future__ import annotations

from pathlib import Path

from app.services.language_registry import language_definition_for_path
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
    assert is_supported_file(Path("templates/index.html"))
    assert is_supported_file(Path("static/site.css"))
    assert is_supported_file(Path("LoginPage.tsx"))
    assert is_supported_file(Path("main.go"))
    assert is_supported_file(Path("lib.rs"))
    assert is_supported_file(Path("App.java"))
    assert is_supported_file(Path("README.md"))
    assert is_supported_file(Path("Dockerfile"))
    assert not is_supported_file(Path("diagram.png"))


def test_language_detection_for_mvp_stack() -> None:
    assert detect_language(Path("main.py")) == "python"
    assert detect_language(Path("templates/index.html")) == "html"
    assert detect_language(Path("static/site.css")) == "css"
    assert detect_language(Path("authApi.ts")) == "typescript"
    assert detect_language(Path("README.md")) == "markdown"


def test_language_registry_supports_common_source_languages() -> None:
    samples = {
        "main.go": "go",
        "index.html": "html",
        "site.css": "css",
        "lib.rs": "rust",
        "App.java": "java",
        "Service.kt": "kotlin",
        "program.cs": "csharp",
        "main.cpp": "cpp",
        "index.php": "php",
        "app.rb": "ruby",
        "Package.swift": "swift",
    }

    for file_name, language in samples.items():
        definition = language_definition_for_path(Path(file_name))
        assert definition is not None
        assert definition.language == language
