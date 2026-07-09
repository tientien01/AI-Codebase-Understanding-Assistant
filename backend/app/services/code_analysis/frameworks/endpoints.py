from __future__ import annotations

import ast
from dataclasses import dataclass

from app.services.code_analysis.models import IRDecorator, IREndpoint, IRFunction, IRModule


HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


@dataclass(frozen=True)
class EndpointCandidate:
    endpoint: IREndpoint
    framework: str
    confidence: float
    extraction_method: str


class EndpointDetector:
    framework = "generic"

    def detect(self, module: IRModule) -> list[EndpointCandidate]:
        raise NotImplementedError


class GenericRouteDecoratorDetector(EndpointDetector):
    framework = "unknown"

    def detect(self, module: IRModule) -> list[EndpointCandidate]:
        candidates: list[EndpointCandidate] = []
        for function in _module_functions(module):
            for decorator in function.decorators:
                endpoint = self._endpoint_from_decorator(function, decorator)
                if endpoint:
                    candidates.append(
                        EndpointCandidate(
                            endpoint=endpoint,
                            framework=self.framework,
                            confidence=0.55,
                            extraction_method="generic_route_decorator",
                        )
                    )
        return candidates

    def _endpoint_from_decorator(self, function: IRFunction, decorator: IRDecorator) -> IREndpoint | None:
        decorator_name = decorator.name.lower()
        decorator_tail = decorator_name.rsplit(".", 1)[-1]
        path = _first_string_arg(decorator)
        if not path:
            return None
        if decorator_tail == "route":
            methods = _methods_from_decorator(decorator) or ["GET"]
        elif decorator_tail in HTTP_METHODS:
            methods = [decorator_tail.upper()]
        else:
            return None
        return _endpoint(function, methods[0], path)


class FlaskEndpointDetector(GenericRouteDecoratorDetector):
    framework = "flask"

    def detect(self, module: IRModule) -> list[EndpointCandidate]:
        flask_imported = any(
            item.module in {"flask", "flask.blueprints"} or item.imported_name in {"Flask", "Blueprint"}
            for item in module.imports
        )
        if not flask_imported:
            return []
        candidates: list[EndpointCandidate] = []
        for candidate in super().detect(module):
            if candidate.endpoint.method:
                candidates.append(
                    EndpointCandidate(
                        endpoint=candidate.endpoint,
                        framework=self.framework,
                        confidence=0.88 if flask_imported else 0.68,
                        extraction_method="flask_route_decorator",
                    )
                )
        return candidates


class FastAPIEndpointDetector(GenericRouteDecoratorDetector):
    framework = "fastapi"

    def detect(self, module: IRModule) -> list[EndpointCandidate]:
        fastapi_imported = any(
            item.module == "fastapi" or item.imported_name in {"FastAPI", "APIRouter"}
            for item in module.imports
        )
        candidates: list[EndpointCandidate] = []
        for candidate in super().detect(module):
            method = candidate.endpoint.method.lower()
            if method in HTTP_METHODS and fastapi_imported:
                candidates.append(
                    EndpointCandidate(
                        endpoint=candidate.endpoint,
                        framework=self.framework,
                        confidence=0.9,
                        extraction_method="fastapi_route_decorator",
                    )
                )
        return candidates


class EndpointDetectorRegistry:
    def __init__(self) -> None:
        self.detectors: list[EndpointDetector] = [
            FlaskEndpointDetector(),
            FastAPIEndpointDetector(),
            GenericRouteDecoratorDetector(),
        ]

    def detect(self, module: IRModule) -> list[IREndpoint]:
        by_key: dict[tuple[str, str, str], EndpointCandidate] = {}
        for detector in self.detectors:
            for candidate in detector.detect(module):
                key = (
                    candidate.endpoint.method,
                    candidate.endpoint.path,
                    candidate.endpoint.handler_qualified_name,
                )
                existing = by_key.get(key)
                if existing is None or candidate.confidence > existing.confidence:
                    by_key[key] = candidate
        return [self._with_metadata(candidate) for candidate in by_key.values()]

    def _with_metadata(self, candidate: EndpointCandidate) -> IREndpoint:
        candidate.endpoint.metadata = {
            "framework": candidate.framework,
            "confidence": str(candidate.confidence),
            "extraction_method": candidate.extraction_method,
        }
        return candidate.endpoint


def _module_functions(module: IRModule) -> list[IRFunction]:
    functions = list(module.functions)
    for item in module.classes:
        functions.extend(_class_functions(item.body))
    return functions


def _class_functions(items) -> list[IRFunction]:
    functions: list[IRFunction] = []
    for item in items:
        if isinstance(item, IRFunction):
            functions.append(item)
        elif hasattr(item, "body"):
            functions.extend(_class_functions(item.body))
    return functions


def _endpoint(function: IRFunction, method: str, path: str) -> IREndpoint:
    return IREndpoint(
        method=method.upper(),
        path=path,
        handler=function.name,
        handler_qualified_name=function.qualified_name,
        file_path=function.file_path,
        start_line=function.start_line,
        end_line=function.end_line,
    )


def _first_string_arg(decorator: IRDecorator) -> str | None:
    if not decorator.args:
        return None
    return _string_value(decorator.args[0])


def _methods_from_decorator(decorator: IRDecorator) -> list[str]:
    raw = decorator.kwargs.get("methods")
    if not raw:
        return []
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    if isinstance(value, str):
        return [value.upper()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).upper() for item in value]
    return []


def _string_value(raw: str) -> str | None:
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw if raw.startswith("/") else None
    return value if isinstance(value, str) else None
