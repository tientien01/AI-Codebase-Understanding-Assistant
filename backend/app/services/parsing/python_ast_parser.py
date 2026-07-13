"""Deprecated import compatibility for the pre-INT-001 Python parser name."""

from app.services.parsing.canonical_python_parser import CanonicalPythonParser


class PythonAstParser(CanonicalPythonParser):
    """Compatibility alias; canonical parsing is owned by PythonAdapter."""
