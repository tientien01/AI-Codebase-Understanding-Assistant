from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LanguageDefinition:
    language: str
    display_name: str
    extensions: tuple[str, ...] = ()
    file_names: tuple[str, ...] = ()
    file_type: str = "source"
    tree_sitter_language: str | None = None


LANGUAGE_DEFINITIONS: tuple[LanguageDefinition, ...] = (
    LanguageDefinition("python", "Python", (".py",), tree_sitter_language="python"),
    LanguageDefinition("javascript", "JavaScript", (".js", ".jsx"), tree_sitter_language="javascript"),
    LanguageDefinition("typescript", "TypeScript", (".ts", ".tsx"), tree_sitter_language="typescript"),
    LanguageDefinition("go", "Go", (".go",), tree_sitter_language="go"),
    LanguageDefinition("rust", "Rust", (".rs",), tree_sitter_language="rust"),
    LanguageDefinition("java", "Java", (".java",), tree_sitter_language="java"),
    LanguageDefinition("kotlin", "Kotlin", (".kt", ".kts"), tree_sitter_language="kotlin"),
    LanguageDefinition("c", "C", (".c", ".h"), tree_sitter_language="c"),
    LanguageDefinition("cpp", "C++", (".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"), tree_sitter_language="cpp"),
    LanguageDefinition("csharp", "C#", (".cs",), tree_sitter_language="c_sharp"),
    LanguageDefinition("php", "PHP", (".php",), tree_sitter_language="php"),
    LanguageDefinition("ruby", "Ruby", (".rb",), tree_sitter_language="ruby"),
    LanguageDefinition("swift", "Swift", (".swift",), tree_sitter_language="swift"),
    LanguageDefinition("markdown", "Markdown docs", (".md",), file_type="document"),
    LanguageDefinition("docker", "Docker", file_names=("Dockerfile",), file_type="config"),
    LanguageDefinition(
        "config",
        "Config",
        (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"),
        file_names=("docker-compose.yml",),
        file_type="config",
    ),
)

LANGUAGES_BY_EXTENSION = {
    extension: definition
    for definition in LANGUAGE_DEFINITIONS
    for extension in definition.extensions
}
LANGUAGES_BY_FILE_NAME = {
    file_name: definition
    for definition in LANGUAGE_DEFINITIONS
    for file_name in definition.file_names
}
SOURCE_LANGUAGES = {
    definition.language
    for definition in LANGUAGE_DEFINITIONS
    if definition.file_type == "source"
}


def language_definition_for_path(path: Path) -> LanguageDefinition | None:
    return LANGUAGES_BY_FILE_NAME.get(path.name) or LANGUAGES_BY_EXTENSION.get(path.suffix.lower())


def supported_extensions() -> set[str]:
    return set(LANGUAGES_BY_EXTENSION)


def supported_file_names() -> set[str]:
    return set(LANGUAGES_BY_FILE_NAME)

