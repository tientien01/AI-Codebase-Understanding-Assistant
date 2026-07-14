from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from app.services.architecture.models import ComponentCandidate, IndexedFileSignal, RoleRule, TechnologySignal


ROLE_RULES: tuple[RoleRule, ...] = (
    RoleRule("presentation", "presentation", "presentation", ("/frontend/", "/client/", "/components/", "/pages/", "/views/", "/screens/"), source_markers=("react", "@component", "vue", "svelte"), languages=("typescript", "javascript", "html"), base_score=20),
    RoleRule("api", "api", "api", ("/routes/", "/routers/", "/controllers/", "/endpoints/", "/handlers/"), ("controller.java", "controller.kt", "controller.cs"), ("@restcontroller", "@controller", "[apicontroller]", "router.", "app.route", "gin.context", "http.handler"), base_score=30),
    RoleRule("application", "application", "application", ("/services/", "/usecases/", "/use_cases/", "/application/"), ("service.py", "service.ts", "service.java", "service.kt", "service.cs", "service.go", "handler.cs"), ("@service", "@injectable", "irequesthandler", "mediatr"), base_score=25),
    RoleRule("domain", "domain", "domain", ("/domain/", "/entities/", "/aggregates/", "/valueobjects/", "/value_objects/"), ("entity.java", "entity.cs"), ("@entity", "aggregate root", "valueobject"), base_score=25),
    RoleRule("data_access", "data_access", "data_access", ("/repositories/", "/repository/", "/persistence/", "/storage/", "/dao/"), ("repository.py", "repository.ts", "repository.java", "repository.kt", "repository.cs", "repository.go", "store.go"), ("jparepository", "dbcontext", "sqlalchemy", "prisma", "mongoose", "gorm.", "database/sql", ".commit("), base_score=30),
    RoleRule("data_model", "data_access", "data_access", ("/models/", "/schemas/", "/entities/"), source_markers=("@entity", "basemodel", "db.model", "models.model", "dbset<"), base_score=15),
    RoleRule("messaging", "messaging", "messaging", ("/consumers/", "/producers/", "/events/", "/workers/", "/jobs/"), source_markers=("@kafkalistener", "kafka", "nats", "rabbitmq", "celery.task", "@task", "backgroundservice"), base_score=35),
    RoleRule("external_adapter", "external_adapter", "integration", ("/clients/", "/integrations/", "/adapters/", "/providers/"), ("client.py", "client.ts", "client.java", "client.cs", "client.go"), ("httpclient", "webclient", "requests.", "httpx.", "axios.", "fetch(", "openai", "generativeai"), base_score=20),
    RoleRule("entrypoint", "entrypoint", "entrypoint", name_suffixes=("main.py", "main.go", "main.rs", "lib.rs", "index.ts", "index.js", "program.cs", "application.java", "application.kt", "manage.py"), source_markers=("if __name__", "static void main", "func main()", "webapplication.createbuilder"), base_score=40),
)


TECHNOLOGY_SIGNALS: tuple[TechnologySignal, ...] = (
    TechnologySignal("postgresql", "PostgreSQL", "database", ("postgresql", "postgres://", "psycopg", "asyncpg", "npgsql"), "reads / writes"),
    TechnologySignal("mysql", "MySQL", "database", ("mysql", "pymysql", "mysqlconnector"), "reads / writes"),
    TechnologySignal("mongodb", "MongoDB", "database", ("mongodb", "mongoose", "pymongo"), "reads / writes"),
    TechnologySignal("redis", "Redis", "cache", ("redis", "stackexchange.redis"), "reads / writes"),
    TechnologySignal("qdrant", "Qdrant", "vector_store", ("qdrant",), "searches"),
    TechnologySignal("kafka", "Kafka", "message_broker", ("kafka", "@kafkalistener"), "publishes / consumes"),
    TechnologySignal("rabbitmq", "RabbitMQ", "message_broker", ("rabbitmq", "amqp", "masstransit"), "publishes / consumes"),
    TechnologySignal("object_storage", "Object Storage", "object_store", ("boto3", "minio", "s3client", "blobserviceclient"), "stores objects"),
    TechnologySignal("openai", "OpenAI API", "external_api", ("openai",), "HTTPS"),
    TechnologySignal("gemini", "Gemini API", "external_api", ("generativeai", "google.genai", "gemini"), "HTTPS"),
)


FRAMEWORK_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("React", ("react", ".tsx", ".jsx")),
    ("Next.js", ("next", "next.config")),
    ("NestJS", ("@nestjs/", "@controller(")),
    ("Express", ("express", "express.router")),
    ("FastAPI", ("fastapi", "apirouter")),
    ("Django", ("django", "models.model")),
    ("Flask", ("flask", "@app.route", "blueprint(")),
    ("Spring Boot", ("spring-boot", "@restcontroller", "@springbootapplication")),
    ("ASP.NET Core", ("[apicontroller]", "webapplication.createbuilder", "controllerbase")),
    ("Go HTTP", ("net/http", "gin-gonic", "go-chi", "labstack/echo", "gofiber")),
)


OPERATIONAL_DOMAINS = {"debug", "health", "metrics", "metric", "ready", "readiness", "live", "liveness", "status", "ops", "internal"}


class FrameworkAwareDetector:
    """Classify indexed files using bounded, explainable framework and structure rules."""

    def detect_frameworks(self, files: list[IndexedFileSignal]) -> list[str]:
        joined_paths = "\n".join(file.normalized_path for file in files)
        joined_content = "\n".join(file.content.lower() for file in files)
        detected = {
            label for label, markers in FRAMEWORK_MARKERS
            if any(marker in joined_paths or marker in joined_content for marker in markers)
        }
        return sorted(detected)

    def classify_files(self, files: list[IndexedFileSignal]) -> list[ComponentCandidate]:
        grouped: dict[tuple[str, str], ComponentCandidate] = {}
        for file in files:
            matches = self._score_file(file)
            if not matches:
                continue
            score, rule, reasons = matches[0]
            domain = domain_from_path(file.path, rule.role)
            key = (rule.role, domain)
            candidate = grouped.setdefault(key, ComponentCandidate(rule.role, rule.kind, rule.layer, domain))
            candidate.files.append(file.path)
            candidate.score += score
            candidate.evidence.extend((file.path, reason) for reason in reasons)
        return sorted(grouped.values(), key=lambda item: (layer_order(item.layer), item.domain, item.role))[:20]

    def detect_technologies(self, files: list[IndexedFileSignal]) -> dict[TechnologySignal, list[str]]:
        detected: dict[TechnologySignal, list[str]] = defaultdict(list)
        for file in files:
            content = file.content.lower()
            path = file.normalized_path
            for signal in TECHNOLOGY_SIGNALS:
                if any(marker in content or marker in path for marker in signal.markers):
                    detected[signal].append(file.path)
        return {signal: sorted(set(paths))[:8] for signal, paths in detected.items()}

    @staticmethod
    def _score_file(file: IndexedFileSignal) -> list[tuple[int, RoleRule, list[str]]]:
        path = f"/{file.normalized_path}"
        name = Path(file.path).name.lower()
        content = file.content.lower()
        scored: list[tuple[int, RoleRule, list[str]]] = []
        for rule in ROLE_RULES:
            if rule.languages and file.language not in rule.languages:
                continue
            score = rule.base_score
            reasons: list[str] = []
            if any(token in path for token in rule.path_tokens):
                score += 35
                reasons.append(f"path matches {rule.role} convention")
            if any(name.endswith(suffix) for suffix in rule.name_suffixes):
                score += 30
                reasons.append(f"file name matches {rule.role} convention")
            marker = next((marker for marker in rule.source_markers if marker in content), None)
            if marker:
                score += 40
                reasons.append(f"indexed source marker: {marker}")
            if reasons:
                scored.append((score, rule, reasons))
        return sorted(scored, key=lambda item: (-item[0], layer_order(item[1].layer), item[1].role))


def domain_from_path(path: str, role: str) -> str:
    normalized = path.replace("\\", "/")
    stem = Path(normalized).stem
    removable = {
        role, "service", "services", "controller", "controllers", "router", "routes", "handler", "handlers",
        "repository", "repositories", "client", "adapter", "provider", "model", "models", "schema", "schemas",
        "store", "storage", "view", "views", "component", "components", "api", "impl", "implementation",
        "consumer", "consumers", "producer", "producers", "worker", "workers", "job", "jobs",
    }
    words = [word for word in re.split(r"[_\-.]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem).lower()) if word not in removable]
    if words and words[0] not in {"index", "main", "base", "program", "application"}:
        return slug("-".join(words))
    parts = [part.lower() for part in normalized.split("/")[:-1]]
    meaningful = [part for part in parts if part not in removable | {"src", "app", "backend", "frontend", "internal", "pkg", "cmd"}]
    return slug(meaningful[-1] if meaningful else "application")


def endpoint_domain(path: str, file_path: str) -> str:
    segments = [part.lower() for part in path.strip("/").split("/") if part and not part.startswith("{")]
    meaningful = [part for part in segments if part not in {"api", "v1", "v2", "v3"}]
    value = meaningful[0] if len(meaningful) > 1 else domain_from_path(file_path, "api")
    return "operational" if value in OPERATIONAL_DOMAINS else slug(value)


def display_domain(domain: str) -> str:
    aliases = {
        "auth": "Authentication", "users": "User", "user": "User", "operational": "Operational",
        "models": "Data", "application": "Application", "config": "Configuration", "gemini": "Gemini",
    }
    return aliases.get(domain, domain.replace("_", " ").replace("-", " ").title())


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "application"


def layer_order(layer: str) -> int:
    return {"entrypoint": 0, "presentation": 1, "api": 2, "application": 3, "domain": 4, "data_access": 5, "messaging": 6, "integration": 7}.get(layer, 9)
