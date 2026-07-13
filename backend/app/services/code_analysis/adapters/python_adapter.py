from __future__ import annotations

import ast

from app.services.code_analysis.adapters.base import LanguageAdapter
from app.services.code_analysis.diagnostics import parser_diagnostic
from app.services.code_analysis.models import (
    IRClass,
    IREndpoint,
    IRDecorator,
    IRExpression,
    IRFunction,
    IRImport,
    IRModule,
    IRNode,
    IRParameter,
    IRStatement,
    ParseRequest,
)
from app.services.code_analysis.stable_ids import stable_ast_id, stable_file_id, stable_hash


class PythonAdapter(LanguageAdapter):
    language = "python"
    parser_version = "python-ast-ir-v1"

    def parse(self, request: ParseRequest) -> IRModule:
        if request.language != self.language:
            raise ValueError(f"PythonAdapter cannot parse language '{request.language}'")
        repository_id = request.repository_id
        file_path = request.file_path
        source = request.source
        module = IRModule(
            schema_version="parsed-file/v1",
            repository_id=repository_id,
            index_version_id=request.index_version_id,
            file_key=request.file_key,
            content_hash=request.content_hash,
            adapter_name="python-ast",
            adapter_version=self.parser_version,
            id=stable_file_id(repository_id, file_path),
            file_path=file_path,
            language=self.language,
        )
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            module.diagnostics.append(
                parser_diagnostic(
                    file_path,
                    self.parser_version,
                    "parse",
                    "Python syntax error. File could not be converted to IR.",
                    exc.lineno,
                    "error",
                )
            )
            return module

        lines = source.splitlines()
        module.imports = self._imports(repository_id, file_path, lines, tree)
        for index, node in enumerate(tree.body):
            ast_path = f"Module.body[{index}]"
            if isinstance(node, ast.ClassDef):
                module.classes.append(self._class(repository_id, file_path, lines, node, ast_path, None))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                module.functions.append(self._function(repository_id, file_path, lines, node, ast_path, None))
            else:
                statement = self._statement(repository_id, file_path, lines, node, ast_path, "module")
                if statement:
                    module.statements.append(statement)
        return module

    def _imports(self, repository_id: str, file_path: str, lines: list[str], tree: ast.AST) -> list[IRImport]:
        imports: list[IRImport] = []
        for index, node in enumerate(ast.walk(tree)):
            if isinstance(node, ast.Import):
                for alias_index, alias in enumerate(node.names):
                    imports.append(
                        self._import_node(
                            repository_id,
                            file_path,
                            lines,
                            node,
                            f"Import[{index}].names[{alias_index}]",
                            alias.name,
                            None,
                            alias.asname,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module_name = "." * node.level + (node.module or "")
                for alias_index, alias in enumerate(node.names):
                    imports.append(
                        self._import_node(
                            repository_id,
                            file_path,
                            lines,
                            node,
                            f"ImportFrom[{index}].names[{alias_index}]",
                            module_name,
                            alias.name,
                            alias.asname,
                            node.level,
                        )
                    )
        return imports

    def _import_node(
        self,
        repository_id: str,
        file_path: str,
        lines: list[str],
        node: ast.AST,
        ast_path: str,
        module: str,
        imported_name: str | None,
        alias: str | None,
        level: int = 0,
    ) -> IRImport:
        return IRImport(
            id=self._node_id(repository_id, file_path, "module", ast_path, "import", node, lines),
            kind="import",
            file_path=file_path,
            ast_path=ast_path,
            start_line=getattr(node, "lineno", 1),
            end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            text=self._node_text(lines, node),
            module=module,
            imported_name=imported_name,
            alias=alias,
            level=level,
        )

    def _class(
        self,
        repository_id: str,
        file_path: str,
        lines: list[str],
        node: ast.ClassDef,
        ast_path: str,
        parent: str | None,
    ) -> IRClass:
        qualified_name = f"{parent}.{node.name}" if parent else node.name
        item = IRClass(
            id=self._node_id(repository_id, file_path, qualified_name, ast_path, "class", node, lines),
            kind="class",
            file_path=file_path,
            ast_path=ast_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            text=self._node_text(lines, node),
            name=node.name,
            qualified_name=qualified_name,
            bases=[self._name(base) or "" for base in node.bases],
        )
        for index, child in enumerate(node.body):
            child_path = f"{ast_path}.body[{index}]"
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                item.body.append(self._function(repository_id, file_path, lines, child, child_path, qualified_name))
            elif isinstance(child, ast.ClassDef):
                item.body.append(self._class(repository_id, file_path, lines, child, child_path, qualified_name))
        return item

    def _function(
        self,
        repository_id: str,
        file_path: str,
        lines: list[str],
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        ast_path: str,
        parent: str | None,
    ) -> IRFunction:
        qualified_name = f"{parent}.{node.name}" if parent else node.name
        function = IRFunction(
            id=self._node_id(repository_id, file_path, qualified_name, ast_path, "function", node, lines),
            kind="function",
            file_path=file_path,
            ast_path=ast_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            text=self._node_text(lines, node),
            name=node.name,
            qualified_name=qualified_name,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            metadata={"signature": self._signature(node)},
            decorators=[self._decorator(decorator) for decorator in node.decorator_list],
        )
        function.parameters = [
            IRParameter(
                id=self._node_id(repository_id, file_path, qualified_name, f"{ast_path}.args[{index}]", "parameter", arg, lines),
                kind="parameter",
                file_path=file_path,
                ast_path=f"{ast_path}.args[{index}]",
                start_line=getattr(arg, "lineno", node.lineno),
                end_line=getattr(arg, "end_lineno", getattr(arg, "lineno", node.lineno)),
                text=arg.arg,
                name=arg.arg,
            )
            for index, arg in enumerate(node.args.args)
        ]
        function.body = [
            statement
            for index, child in enumerate(node.body)
            if (statement := self._statement(repository_id, file_path, lines, child, f"{ast_path}.body[{index}]", qualified_name))
        ]
        return function

    def _statement(
        self,
        repository_id: str,
        file_path: str,
        lines: list[str],
        node: ast.stmt,
        ast_path: str,
        scope_key: str,
    ) -> IRStatement | None:
        kind = self._statement_kind(node)
        statement = IRStatement(
            id=self._node_id(repository_id, file_path, scope_key, ast_path, kind, node, lines),
            kind=kind,
            file_path=file_path,
            ast_path=ast_path,
            start_line=getattr(node, "lineno", 1),
            end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            text=self._node_text(lines, node),
        )
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            statement.targets = [self._expression(repository_id, file_path, lines, target, f"{ast_path}.target[{index}]", scope_key) for index, target in enumerate(self._assignment_targets(node))]
            statement.expressions = [self._expression(repository_id, file_path, lines, value, f"{ast_path}.value", scope_key) for value in self._assignment_values(node)]
        elif isinstance(node, ast.Return):
            statement.expressions = [self._expression(repository_id, file_path, lines, node.value, f"{ast_path}.value", scope_key)] if node.value else []
        elif isinstance(node, ast.If):
            statement.expressions = [self._expression(repository_id, file_path, lines, node.test, f"{ast_path}.test", scope_key)]
            statement.body = [item for index, child in enumerate(node.body) if (item := self._statement(repository_id, file_path, lines, child, f"{ast_path}.body[{index}]", scope_key))]
            statement.orelse = [item for index, child in enumerate(node.orelse) if (item := self._statement(repository_id, file_path, lines, child, f"{ast_path}.orelse[{index}]", scope_key))]
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            if isinstance(node, (ast.For, ast.AsyncFor)):
                statement.targets = [self._expression(repository_id, file_path, lines, node.target, f"{ast_path}.target", scope_key)]
                statement.expressions = [self._expression(repository_id, file_path, lines, node.iter, f"{ast_path}.iter", scope_key)]
            else:
                statement.expressions = [self._expression(repository_id, file_path, lines, node.test, f"{ast_path}.test", scope_key)]
            statement.body = [item for index, child in enumerate(node.body) if (item := self._statement(repository_id, file_path, lines, child, f"{ast_path}.body[{index}]", scope_key))]
            statement.orelse = [item for index, child in enumerate(node.orelse) if (item := self._statement(repository_id, file_path, lines, child, f"{ast_path}.orelse[{index}]", scope_key))]
        elif isinstance(node, ast.Try):
            statement.body = [item for index, child in enumerate(node.body) if (item := self._statement(repository_id, file_path, lines, child, f"{ast_path}.body[{index}]", scope_key))]
            statement.handlers = [
                item
                for handler_index, handler in enumerate(node.handlers)
                for index, child in enumerate(handler.body)
                if (item := self._statement(repository_id, file_path, lines, child, f"{ast_path}.handlers[{handler_index}].body[{index}]", scope_key))
            ]
        elif isinstance(node, ast.Expr):
            statement.expressions = [self._expression(repository_id, file_path, lines, node.value, f"{ast_path}.value", scope_key)]
        else:
            statement.expressions = [
                self._expression(repository_id, file_path, lines, child, f"{ast_path}.expr[{index}]", scope_key)
                for index, child in enumerate(ast.iter_child_nodes(node))
                if isinstance(child, ast.expr)
            ]
        return statement

    def _expression(
        self,
        repository_id: str,
        file_path: str,
        lines: list[str],
        node: ast.AST | None,
        ast_path: str,
        scope_key: str,
    ) -> IRExpression:
        if node is None:
            return IRExpression(
                id=self._node_id(repository_id, file_path, scope_key, ast_path, "empty", ast.Pass(), lines),
                kind="empty",
                file_path=file_path,
                ast_path=ast_path,
                start_line=1,
                end_line=1,
            )
        kind = self._expression_kind(node)
        expression = IRExpression(
            id=self._node_id(repository_id, file_path, scope_key, ast_path, kind, node, lines),
            kind=kind,
            file_path=file_path,
            ast_path=ast_path,
            start_line=getattr(node, "lineno", 1),
            end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            text=self._node_text(lines, node),
            name=self._name(node),
            value=self._literal_value(node),
        )
        expression.children = [
            self._expression(repository_id, file_path, lines, child, f"{ast_path}.children[{index}]", scope_key)
            for index, child in enumerate(ast.iter_child_nodes(node))
            if isinstance(child, ast.expr)
        ]
        return expression

    def _decorator(self, node: ast.AST) -> IRDecorator:
        call = node if isinstance(node, ast.Call) else None
        target = call.func if call else node
        kwargs = {
            keyword.arg or "kwargs": self._literal_or_name(keyword.value)
            for keyword in (call.keywords if call else [])
        }
        args = [self._literal_or_name(arg) for arg in (call.args if call else [])]
        return IRDecorator(
            name=self._name(target) or self._node_text([], node) or type(node).__name__,
            args=args,
            kwargs=kwargs,
            line=getattr(node, "lineno", None),
        )

    def _literal_or_name(self, node: ast.AST) -> str:
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError):
            return self._name(node) or ast.unparse(node)
        return repr(value)

    def _node_id(self, repository_id: str, file_path: str, scope_key: str, ast_path: str, node_kind: str, node: ast.AST, lines: list[str]) -> str:
        snippet = self._node_text(lines, node)
        return stable_ast_id(repository_id, file_path, scope_key, ast_path, node_kind, stable_hash(snippet, length=12))

    def _node_text(self, lines: list[str], node: ast.AST) -> str:
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        return "\n".join(lines[start - 1 : end]) if lines else ""

    def _statement_kind(self, node: ast.stmt) -> str:
        if isinstance(node, ast.If):
            return "branch"
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            return "loop"
        if isinstance(node, ast.Return):
            return "return"
        if isinstance(node, ast.Raise):
            return "raise"
        if isinstance(node, ast.Try):
            return "try"
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            return "assignment"
        return "statement"

    def _expression_kind(self, node: ast.AST) -> str:
        if isinstance(node, ast.Call):
            return "call"
        if isinstance(node, ast.Name):
            return "variable"
        if isinstance(node, ast.Attribute):
            return "attribute"
        if isinstance(node, ast.Constant):
            return "literal"
        if isinstance(node, ast.Compare):
            return "compare"
        if isinstance(node, ast.BinOp):
            return "binary_op"
        if isinstance(node, ast.BoolOp):
            return "bool_op"
        return "expression"

    def _assignment_targets(self, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> list[ast.expr]:
        if isinstance(node, ast.Assign):
            return list(node.targets)
        return [node.target]

    def _assignment_values(self, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> list[ast.expr]:
        value = getattr(node, "value", None)
        return [value] if value is not None else []

    def _name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        if isinstance(node, ast.Call):
            return self._name(node.func)
        return None

    def _literal_value(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant):
            return repr(node.value)
        return None

    def _signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        args = [arg.arg for arg in node.args.args]
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({', '.join(args)})"
