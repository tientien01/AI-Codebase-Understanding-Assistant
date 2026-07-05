from __future__ import annotations

from app.core.errors import DomainError
from app.schemas.api import CitationDTO, FileContentResponse, FileTreeNodeDTO
from app.services.repositories.repository_service import RepositoryService
from app.services.text_utils import read_text


class FileService:
    def __init__(self, repositories: RepositoryService) -> None:
        self.repositories = repositories

    def get_file_tree(self, repository_id: str) -> list[FileTreeNodeDTO]:
        repository = self.repositories.get_indexed_repository(repository_id)
        root: dict[str, dict | None] = {}
        for file_record in repository.files:
            cursor = root
            parts = file_record.path.split("/")
            for part in parts[:-1]:
                child = cursor.setdefault(part, {})
                if child is None:
                    break
                cursor = child
            cursor.setdefault(parts[-1], None)
        return self._tree_dict_to_dto(root, "")

    def get_file_content(self, repository_id: str, file_path: str) -> FileContentResponse:
        repository = self.repositories.get_indexed_repository(repository_id)
        file_record = next((item for item in repository.files if item.path == file_path), None)
        if file_record is None:
            raise DomainError("FILE_NOT_FOUND", "File not found in index.", 404, {"file_path": file_path})
        content = read_text(file_record.absolute_path)
        return FileContentResponse(
            file_path=file_record.path,
            language=file_record.language,
            content=content,
            lines=content.splitlines(),
            symbols=[
                CitationDTO(
                    evidence_id=f"symbol_{symbol.id}",
                    file_path=symbol.file_path,
                    symbol_name=symbol.name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    index_version=repository.current_index_version,
                )
                for symbol in repository.symbols
                if symbol.file_path == file_record.path
            ],
        )

    def _tree_dict_to_dto(self, tree: dict[str, dict | None], prefix: str) -> list[FileTreeNodeDTO]:
        nodes: list[FileTreeNodeDTO] = []
        for name, child in sorted(tree.items()):
            node_path = f"{prefix}/{name}".strip("/")
            if child is None:
                nodes.append(FileTreeNodeDTO(name=name, path=node_path, type="file"))
            else:
                nodes.append(FileTreeNodeDTO(name=name, path=node_path, type="directory", children=self._tree_dict_to_dto(child, node_path)))
        return nodes
