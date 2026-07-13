from __future__ import annotations

import builtins
import hashlib
import sys
from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import quote

from app.services.code_analysis.models import (
    IRClass,
    IRExpression,
    IRFunction,
    IRModule,
    IRStatement,
    ReferenceArtifact,
    ResolvedReference,
    SourceSpan,
    canonical_file_key,
    canonical_symbol_key,
)


BUILTIN_NAMES = frozenset(dir(builtins))
STDLIB_MODULES = frozenset(getattr(sys, "stdlib_module_names", set()))
FRAMEWORK_MODULES = frozenset({"flask", "fastapi", "django", "sqlalchemy", "celery", "click"})


class PythonReferenceResolver:
    """Resolve Python IR references without filesystem, graph, provider, or DB access."""

    name = "python-static-resolver"
    version = "1"

    def resolve(self, module: IRModule, repository_file_paths: Iterable[str]) -> ReferenceArtifact:
        file_paths = tuple(sorted(set(repository_file_paths)))
        symbols = self._symbol_index(module)
        imports = self._import_aliases(module)
        pending: list[tuple[str | None, str, str, int, int, tuple[str, ...], str | None, str]] = []

        for item in module.imports:
            raw = f"{item.module}.{item.imported_name}".strip(".") if item.imported_name else item.module
            targets, reason = self._resolve_import(module.file_path, item.module, file_paths)
            pending.append((None, "import", raw, item.start_line, item.end_line, targets, reason, "python-import/v1"))

        for function, symbol_kind in self._functions(module):
            source_key = canonical_symbol_key(module.file_key, function.qualified_name, symbol_kind)
            for expression in self._call_expressions(function.body):
                if not expression.name:
                    continue
                targets, reason = self._resolve_call(function, expression.name, symbols, imports)
                pending.append(
                    (
                        source_key,
                        "call",
                        expression.name,
                        expression.start_line,
                        expression.end_line,
                        targets,
                        reason,
                        "python-call/v1",
                    )
                )

        ordered = sorted(pending, key=lambda item: (item[3], item[4], item[1], item[2], item[0] or ""))
        occurrences: defaultdict[tuple[str | None, str, str], int] = defaultdict(int)
        references: list[ResolvedReference] = []
        for source_key, ref_type, raw, start, end, targets, reason, method in ordered:
            identity = (source_key, ref_type, raw)
            ordinal = occurrences[identity]
            occurrences[identity] += 1
            outcome = "resolved" if len(targets) == 1 else "ambiguous" if len(targets) > 1 else "unresolved"
            digest = hashlib.sha256(f"{source_key}|{ref_type}|{raw}|{ordinal}".encode("utf-8")).hexdigest()[:20]
            owner = quote(source_key or module.file_key, safe="")
            references.append(
                ResolvedReference(
                    schema_version="resolved-reference/v1",
                    canonical_key=f"reference:v1:{owner}:{ref_type}:{digest}",
                    repository_id=module.repository_id,
                    index_version_id=module.index_version_id,
                    source_file_key=module.file_key,
                    source_entity_key=source_key,
                    reference_type=ref_type,
                    raw_reference=raw,
                    outcome=outcome,
                    target_keys=tuple(sorted(targets)),
                    resolution_method=method,
                    support_type=(
                        "static_resolved"
                        if outcome == "resolved"
                        else "static_ambiguous"
                        if outcome == "ambiguous"
                        else "source_exact"
                    ),
                    source_spans=(SourceSpan(module.file_key, start, end, module.content_hash),),
                    unresolved_reason=reason if outcome == "unresolved" else None,
                )
            )
        return ReferenceArtifact(
            schema_version="resolved-reference-set/v1",
            repository_id=module.repository_id,
            index_version_id=module.index_version_id,
            producer_name=self.name,
            producer_version=self.version,
            references=tuple(references),
        )

    def _symbol_index(self, module: IRModule) -> dict[str, tuple[str, ...]]:
        index: defaultdict[str, set[str]] = defaultdict(set)
        for function, kind in self._functions(module):
            key = canonical_symbol_key(module.file_key, function.qualified_name, kind)
            index[function.name].add(key)
            index[function.qualified_name].add(key)
        return {name: tuple(sorted(keys)) for name, keys in index.items()}

    def _functions(self, module: IRModule) -> list[tuple[IRFunction, str]]:
        result = [(item, "function") for item in module.functions]
        for item in module.classes:
            result.extend(self._class_functions(item))
        return result

    def _class_functions(self, item: IRClass) -> list[tuple[IRFunction, str]]:
        result: list[tuple[IRFunction, str]] = []
        for child in item.body:
            if isinstance(child, IRFunction):
                result.append((child, "method"))
            elif isinstance(child, IRClass):
                result.extend(self._class_functions(child))
        return result

    def _call_expressions(self, statements: Iterable[IRStatement]) -> list[IRExpression]:
        calls: list[IRExpression] = []
        for statement in statements:
            for expression in [*statement.expressions, *statement.targets]:
                calls.extend(self._calls_from_expression(expression))
            calls.extend(self._call_expressions(statement.body))
            calls.extend(self._call_expressions(statement.orelse))
            calls.extend(self._call_expressions(statement.handlers))
        return calls

    def _calls_from_expression(self, expression: IRExpression) -> list[IRExpression]:
        calls = [expression] if expression.kind == "call" else []
        for child in expression.children:
            calls.extend(self._calls_from_expression(child))
        return calls

    def _import_aliases(self, module: IRModule) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for item in module.imports:
            if item.imported_name:
                aliases[item.alias or item.imported_name] = f"{item.module}.{item.imported_name}".strip(".")
            else:
                aliases[item.alias or item.module.split(".", 1)[0]] = item.module
        return aliases

    def _resolve_call(
        self,
        function: IRFunction,
        raw: str,
        symbols: dict[str, tuple[str, ...]],
        imports: dict[str, str],
    ) -> tuple[tuple[str, ...], str | None]:
        candidates: set[str] = set(symbols.get(raw, ()))
        if raw.startswith("self.") and "." in function.qualified_name:
            owner = function.qualified_name.rsplit(".", 1)[0]
            candidates.update(symbols.get(f"{owner}.{raw.split('.', 1)[1]}", ()))
        if candidates:
            return tuple(sorted(candidates)), None
        root = raw.split(".", 1)[0]
        if root in BUILTIN_NAMES:
            return (), "builtin_target"
        imported = imports.get(root)
        if imported:
            module_root = imported.lstrip(".").split(".", 1)[0]
            if module_root in FRAMEWORK_MODULES:
                return (), "framework_target"
            if module_root in STDLIB_MODULES:
                return (), "stdlib_target"
            return (), "external_target"
        if "." in raw:
            return (), "dynamic_attribute_target"
        return (), "target_not_found"

    def _resolve_import(
        self,
        owning_file_path: str,
        module_name: str,
        file_paths: tuple[str, ...],
    ) -> tuple[tuple[str, ...], str | None]:
        normalized = self._normalize_module_path(owning_file_path, module_name)
        candidates = {f"{normalized}.py", f"{normalized}/__init__.py"}
        matches = tuple(
            sorted(
                canonical_file_key(path)
                for path in file_paths
                if path in candidates or any(path.endswith(f"/{candidate}") for candidate in candidates)
            )
        )
        if matches:
            return matches, None
        root = module_name.lstrip(".").split(".", 1)[0]
        if root in FRAMEWORK_MODULES:
            return (), "framework_module"
        if root in STDLIB_MODULES:
            return (), "stdlib_module"
        return (), "module_not_found"

    def _normalize_module_path(self, owning_file_path: str, module_name: str) -> str:
        leading_dots = len(module_name) - len(module_name.lstrip("."))
        raw_module = module_name.lstrip(".")
        if leading_dots == 0:
            return raw_module.replace(".", "/")
        parent_parts = owning_file_path.rsplit("/", 1)[0].split("/")
        keep_count = max(0, len(parent_parts) - leading_dots + 1)
        parts = parent_parts[:keep_count]
        if raw_module:
            parts.extend(raw_module.split("."))
        return "/".join(part for part in parts if part)
