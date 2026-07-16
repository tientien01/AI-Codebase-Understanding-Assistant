from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit


HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}
_CLIENT_HINTS = ("api", "client", "http")


@dataclass(frozen=True)
class ExtractedClientCall:
    method: str
    route: str
    start_line: int
    end_line: int
    client: str
    extraction_method: str


class JavaScriptClientCallExtractor:
    import_pattern = re.compile(
        r"\bimport\s+(?P<bindings>[^;\n]+?)\s+from\s*['\"](?P<module>[^'\"]+)['\"]",
        re.MULTILINE,
    )
    configured_client_pattern = re.compile(
        r"\b(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?P<factory>[A-Za-z_$][\w$]*)\.create\s*\(",
    )
    member_call_pattern = re.compile(
        r"\b(?P<client>[A-Za-z_$][\w$]*)\s*\.\s*(?P<method>get|post|put|delete|patch|options|head)"
        r"\s*\(\s*(?P<quote>['\"`])(?P<route>.*?)(?P=quote)",
        re.IGNORECASE | re.DOTALL,
    )
    fetch_call_pattern = re.compile(
        r"(?:\b|\.)(?P<client>fetch)\s*\(\s*(?P<quote>['\"`])(?P<route>.*?)(?P=quote)",
        re.IGNORECASE | re.DOTALL,
    )
    interpolation_pattern = re.compile(r"\$\{(?P<expression>[^{}]+)\}")
    base_url_pattern = re.compile(r"\bbaseURL\s*:\s*['\"`](?P<value>[^'\"`]+)['\"`]", re.IGNORECASE)
    fetch_method_pattern = re.compile(r"\bmethod\s*:\s*['\"](?P<method>get|post|put|delete|patch|options|head)['\"]", re.IGNORECASE)

    def extract(self, text: str) -> list[ExtractedClientCall]:
        imported_clients, axios_aliases = self._imported_clients(text)
        configured_clients = self._configured_clients(text, axios_aliases)
        accepted_clients = imported_clients | axios_aliases | set(configured_clients)
        calls: list[ExtractedClientCall] = []

        for match in self.member_call_pattern.finditer(text):
            client = match.group("client")
            if client not in accepted_clients:
                continue
            route = self._normalize_route(match.group("route"), configured_clients.get(client))
            if route is None:
                continue
            calls.append(self._call(text, match, match.group("method"), route, client, "javascript-http-member/v1"))

        for match in self.fetch_call_pattern.finditer(text):
            route = self._normalize_route(match.group("route"), None)
            if route is None:
                continue
            method = self._fetch_method(text, match.end())
            calls.append(self._call(text, match, method, route, "fetch", "javascript-fetch/v1"))

        return sorted(calls, key=lambda call: (call.start_line, call.end_line, call.method, call.route, call.client))

    def _imported_clients(self, text: str) -> tuple[set[str], set[str]]:
        clients: set[str] = set()
        axios_aliases: set[str] = {"axios"}
        for match in self.import_pattern.finditer(text):
            module = match.group("module")
            bindings = match.group("bindings").strip()
            local_names = self._local_import_names(bindings)
            if module.lower() == "axios":
                axios_aliases.update(local_names)
                continue
            if self._looks_like_client(module) or any(self._looks_like_client(name) for name in local_names):
                clients.update(local_names)
        return clients, axios_aliases

    def _configured_clients(self, text: str, axios_aliases: set[str]) -> dict[str, str | None]:
        clients: dict[str, str | None] = {}
        for match in self.configured_client_pattern.finditer(text):
            if match.group("factory") not in axios_aliases:
                continue
            call_tail = text[match.end() : match.end() + 800]
            closing = call_tail.find(")")
            options = call_tail if closing < 0 else call_tail[:closing]
            base_match = self.base_url_pattern.search(options)
            clients[match.group("name")] = base_match.group("value") if base_match else None
        return clients

    def _normalize_route(self, raw_route: str, base_url: str | None) -> str | None:
        route = raw_route.strip()
        if not route:
            return None
        route = self.interpolation_pattern.sub(lambda match: "{" + self._parameter_name(match.group("expression")) + "}", route)
        if "${" in route:
            return None
        parsed = urlsplit(route)
        path = parsed.path or "/"
        if base_url:
            base_path = urlsplit(base_url).path.rstrip("/")
            path = f"{base_path}/{path.lstrip('/')}" if base_path else path
        normalized = "/" + path.lstrip("/")
        return normalized.rstrip("/") or "/"

    def _fetch_method(self, text: str, route_end: int) -> str:
        tail = text[route_end : route_end + 400]
        closing = tail.find(")")
        options = tail if closing < 0 else tail[:closing]
        match = self.fetch_method_pattern.search(options)
        return match.group("method").upper() if match else "GET"

    def _call(self, text: str, match: re.Match[str], method: str, route: str, client: str, extraction_method: str) -> ExtractedClientCall:
        start_line = text.count("\n", 0, match.start()) + 1
        end_line = text.count("\n", 0, match.end()) + 1
        return ExtractedClientCall(
            method=method.upper(),
            route=route,
            start_line=start_line,
            end_line=end_line,
            client=client,
            extraction_method=extraction_method,
        )

    def _local_import_names(self, bindings: str) -> set[str]:
        names: set[str] = set()
        default_binding = bindings.split(",", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_$][\w$]*", default_binding):
            names.add(default_binding)
        namespace = re.search(r"\*\s+as\s+([A-Za-z_$][\w$]*)", bindings)
        if namespace:
            names.add(namespace.group(1))
        named = re.search(r"\{(?P<items>[^}]+)\}", bindings)
        if named:
            for item in named.group("items").split(","):
                parts = re.split(r"\s+as\s+", item.strip())
                if parts and parts[-1]:
                    names.add(parts[-1].strip())
        return names

    def _looks_like_client(self, value: str) -> bool:
        compact = re.sub(r"[^a-z]", "", value.lower())
        return any(hint in compact for hint in _CLIENT_HINTS)

    def _parameter_name(self, expression: str) -> str:
        identifiers = re.findall(r"[A-Za-z_$][\w$]*", expression)
        return identifiers[-1] if identifiers else "dynamic"
