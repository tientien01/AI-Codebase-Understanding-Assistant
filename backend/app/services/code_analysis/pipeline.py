from __future__ import annotations

from app.services.chunking_service import ChunkingService
from app.services.code_analysis.adapters.python_adapter import PythonAdapter
from app.services.code_analysis.cfg.builder import CFGBuilder
from app.services.code_analysis.cpg.emitter import CPGEmitter
from app.services.code_analysis.dfg.builder import DFGBuilder
from app.services.code_analysis.models import CPGResult, IRClass, IRFunction, IRModule
from app.services.index_models import FileRecord, RepositoryState


class CodeAnalysisPipeline:
    def __init__(self, chunking: ChunkingService) -> None:
        self.chunking = chunking
        self.python_adapter = PythonAdapter()
        self.cfg_builder = CFGBuilder()
        self.dfg_builder = DFGBuilder()
        self.emitter = CPGEmitter(chunking)

    def parse_python(self, repository: RepositoryState, file_record: FileRecord, text: str) -> bool:
        module = self.python_adapter.parse(repository.id, file_record.path, text)
        if module.diagnostics:
            for diagnostic in module.diagnostics:
                repository.failed_file_records.append(diagnostic)
            if any(item.get("severity") == "error" for item in module.diagnostics):
                return False
        result = self._analyze_module(repository.id, module)
        self.emitter.apply(repository, result)
        return True

    def _analyze_module(self, repository_id: str, module: IRModule) -> CPGResult:
        functions = self._functions(module)
        return CPGResult(
            module=module,
            cfg_graphs=[self.cfg_builder.build_function(repository_id, function) for function in functions],
            dfg_graphs=[self.dfg_builder.build_function(repository_id, function) for function in functions],
        )

    def _functions(self, module: IRModule) -> list[IRFunction]:
        items: list[IRFunction] = list(module.functions)
        for item in module.classes:
            items.extend(self._functions_from_class(item))
        return items

    def _functions_from_class(self, item: IRClass) -> list[IRFunction]:
        functions: list[IRFunction] = []
        for child in item.body:
            if isinstance(child, IRFunction):
                functions.append(child)
            elif isinstance(child, IRClass):
                functions.extend(self._functions_from_class(child))
        return functions
