from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.services.architecture import RuleBasedArchitectureEngine
from app.services.index_models import EndpointRecord, FileRecord, RepositoryState


def repository(tmp_path: Path, files: dict[str, str], endpoints: list[EndpointRecord] | None = None) -> RepositoryState:
    records: list[FileRecord] = []
    languages = {".py": "python", ".ts": "typescript", ".tsx": "typescript", ".java": "java", ".kt": "kotlin", ".cs": "csharp", ".go": "go", ".json": "config", ".xml": "config", ".mod": "config"}
    for relative_path, content in files.items():
        absolute_path = tmp_path / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_text(content, encoding="utf-8")
        suffix = absolute_path.suffix.lower()
        records.append(FileRecord(
            path=relative_path,
            absolute_path=absolute_path,
            language=languages.get(suffix, "config"),
            file_type="config" if absolute_path.name in {"package.json", "pom.xml", "go.mod"} else "source",
            size_bytes=len(content.encode()),
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        ))
    return RepositoryState("repo", "fixture", "upload_folder", None, tmp_path, status="indexed", files=records, endpoints=endpoints or [])


def labels(architecture) -> set[str]:
    return {component.label for component in architecture.components}


def test_spring_rules_detect_normalized_api_service_repository_and_database_owner(tmp_path: Path) -> None:
    state = repository(tmp_path, {
        "pom.xml": '<dependency>spring-boot</dependency><dependency>postgresql</dependency>',
        "src/main/java/com/acme/Application.java": "@SpringBootApplication public class Application { static void main(String[] args) {} }",
        "src/main/java/com/acme/user/UserController.java": "@RestController class UserController {}",
        "src/main/java/com/acme/user/UserService.java": "@Service class UserService {}",
        "src/main/java/com/acme/user/UserRepository.java": "interface UserRepository extends JpaRepository<User, Long> { /* postgresql */ }",
    })

    result = RuleBasedArchitectureEngine().build(state)

    assert result.style == "backend_api"
    assert "Spring Boot Backend" in labels(result)
    assert {"User API", "User Service", "User Repository", "PostgreSQL"} <= labels(result)
    database_relation = next(relation for relation in result.relations if relation.target == "infrastructure:postgresql")
    assert database_relation.source == "data_access:user"
    assert database_relation.support == "confirmed"


@pytest.mark.parametrize("files,expected_framework,expected_labels", [
    ({
        "src/Program.cs": "var builder = WebApplication.CreateBuilder(args);",
        "src/Controllers/UserController.cs": "[ApiController] class UserController : ControllerBase {}",
        "src/Services/UserService.cs": "class UserService {}",
        "src/Data/AppDbContext.cs": "class AppDbContext : DbContext {}",
    }, "ASP.NET Core", {"User API", "User Service"}),
    ({
        "go.mod": "module example.com/orders\nrequire github.com/gin-gonic/gin v1.0.0",
        "cmd/api/main.go": "package main\nimport \"github.com/gin-gonic/gin\"\nfunc main() {}",
        "internal/order/handler.go": "package order\nfunc Handle(c *gin.Context) {}",
        "internal/order/service.go": "package order\ntype Service struct {}",
        "internal/order/store.go": "package order\nimport \"database/sql\"\ntype Store struct {}",
    }, "Go HTTP", {"Order API", "Order Service", "Order Repository"}),
])
def test_popular_framework_rules_produce_normalized_roles(tmp_path: Path, files: dict[str, str], expected_framework: str, expected_labels: set[str]) -> None:
    state = repository(tmp_path, files)

    result = RuleBasedArchitectureEngine().build(state)

    assert expected_framework in result.technologies
    assert expected_labels <= labels(result)
    assert result.style == "backend_api"


def test_operational_endpoints_are_grouped_away_from_business_apis(tmp_path: Path) -> None:
    endpoints = [
        EndpointRecord("GET", "/health", "health", "app/routes/health.py", 1, 2),
        EndpointRecord("GET", "/debug", "debug", "app/routes/debug.py", 1, 2),
        EndpointRecord("GET", "/api/v1/users", "users", "app/routes/users.py", 1, 2),
    ]
    state = repository(tmp_path, {"app/main.py": "from fastapi import FastAPI", "app/routes/users.py": "from fastapi import APIRouter"}, endpoints)

    result = RuleBasedArchitectureEngine().build(state)

    operational = next(component for component in result.components if component.id == "api:operational")
    assert operational.label == "Operational Endpoints"
    assert operational.endpoint_count == 2
    assert "User API" in labels(result)
    assert all(relation.source != operational.id for relation in result.relations)


def test_event_driven_rules_select_broker_layout(tmp_path: Path) -> None:
    state = repository(tmp_path, {
        "src/consumers/order_consumer.java": '@KafkaListener(topics="orders") class OrderConsumer {}',
        "src/services/order_service.java": "@Service class OrderService {}",
    })

    result = RuleBasedArchitectureEngine().build(state)

    assert result.style == "event_driven"
    assert {"Order Worker", "Kafka"} <= labels(result)
    assert any(relation.target == "infrastructure:kafka" and relation.label == "publishes / consumes" for relation in result.relations)


def test_library_and_cli_styles_do_not_force_web_layers(tmp_path: Path) -> None:
    library = repository(tmp_path / "library", {
        "package.json": '{"name":"math-kit"}',
        "src/index.ts": "export { add } from './math'",
        "src/math.ts": "export function add(a: number, b: number) { return a + b }",
    })
    cli = repository(tmp_path / "cli", {"src/main.py": "import argparse\nif __name__ == '__main__': argparse.ArgumentParser()"})

    library_result = RuleBasedArchitectureEngine().build(library)
    cli_result = RuleBasedArchitectureEngine().build(cli)

    assert library_result.style == "library"
    assert cli_result.style == "cli"
    assert not any(component.kind == "api" for component in library_result.components + cli_result.components)


def test_manifest_only_infrastructure_does_not_invent_an_owner(tmp_path: Path) -> None:
    state = repository(tmp_path, {
        "package.json": '{"dependencies":{"pg":"postgresql"}}',
        "src/index.ts": "export const version = '1.0'",
    })

    result = RuleBasedArchitectureEngine().build(state)

    assert "PostgreSQL" in labels(result)
    assert not any(relation.target == "infrastructure:postgresql" for relation in result.relations)
    assert "PostgreSQL was detected, but its owning component could not be confirmed." in result.unknowns


def test_secret_like_paths_are_never_used_as_architecture_signals(tmp_path: Path) -> None:
    state = repository(tmp_path, {
        "src/main.py": "import argparse",
        "secrets/config.json": '{"provider":"openai","broker":"kafka"}',
        "credentials.json": '{"database":"postgresql"}',
    })

    result = RuleBasedArchitectureEngine().build(state)

    assert {"OpenAI API", "Kafka", "PostgreSQL"}.isdisjoint(labels(result))
