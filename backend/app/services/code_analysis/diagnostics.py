from __future__ import annotations


def parser_diagnostic(
    file_path: str,
    parser: str,
    stage: str,
    message: str,
    line: int | None = None,
    severity: str = "warning",
) -> dict[str, str | int | None]:
    return {
        "file_path": file_path,
        "language": "python",
        "parser": parser,
        "stage": stage,
        "severity": severity,
        "message": message,
        "line": line,
    }
