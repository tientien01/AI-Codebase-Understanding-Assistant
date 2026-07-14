from app.services.application.container import ApplicationContainer
from app.services.application.use_cases import (
    AssistantUseCases,
    ExplorationUseCases,
    GraphUseCases,
    IndexingUseCases,
    RepositoryUseCases,
    SearchUseCases,
)
from app.services.ingestion.import_session_service import ImportSessionService
from app.services.settings.settings_service import SettingsService
from app.services.security import AccessService


application_container = ApplicationContainer()


def get_repository_use_cases() -> RepositoryUseCases:
    return application_container.repository_use_cases


def get_import_session_service() -> ImportSessionService:
    return application_container.ingestion


def get_indexing_use_cases() -> IndexingUseCases:
    return application_container.indexing_use_cases


def get_exploration_use_cases() -> ExplorationUseCases:
    return application_container.exploration_use_cases


def get_assistant_use_cases() -> AssistantUseCases:
    return application_container.assistant_use_cases


def get_graph_use_cases() -> GraphUseCases:
    return application_container.graph_use_cases


def get_search_use_cases() -> SearchUseCases:
    return application_container.search_use_cases


def get_settings_service() -> SettingsService:
    return application_container.settings_service


def get_access_service() -> AccessService:
    return application_container.access_service
