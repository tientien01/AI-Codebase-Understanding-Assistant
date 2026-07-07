from __future__ import annotations

from app.services.code_analysis.models import DFGEdge, DFGGraph, DFGNode, IRExpression, IRFunction, IRStatement
from app.services.code_analysis.stable_ids import stable_node_id


class DFGBuilder:
    def build_function(self, repository_id: str, function: IRFunction) -> DFGGraph:
        graph = DFGGraph(function_id=function.id)
        definitions: dict[str, str] = {}
        for parameter in function.parameters:
            node = self._dfg_node(repository_id, function, "parameter", parameter.name, parameter.id, parameter.start_line)
            graph.nodes.append(node)
            definitions[parameter.name] = node.id
        self._walk_statements(repository_id, function, function.body, graph, definitions)
        return graph

    def _walk_statements(
        self,
        repository_id: str,
        function: IRFunction,
        statements: list[IRStatement],
        graph: DFGGraph,
        definitions: dict[str, str],
    ) -> None:
        for statement in statements:
            if statement.kind == "assignment":
                uses = self._collect_variable_uses(statement.expressions)
                for target in statement.targets:
                    if not target.name:
                        continue
                    definition = self._dfg_node(repository_id, function, "definition", target.name, target.id, target.start_line)
                    graph.nodes.append(definition)
                    for variable_name, use_expression in uses:
                        use_node = self._use_node(repository_id, function, variable_name, use_expression)
                        graph.nodes.append(use_node)
                        if variable_name in definitions:
                            graph.edges.append(DFGEdge(source=definitions[variable_name], target=use_node.id, type="dfg_reaches"))
                        graph.edges.append(DFGEdge(source=use_node.id, target=definition.id, type="dfg_computed_from"))
                    definitions[target.name] = definition.id
            elif statement.kind == "return":
                self._add_expression_uses(repository_id, function, statement.expressions, graph, definitions, "dfg_returned")
            else:
                self._add_expression_uses(repository_id, function, [*statement.expressions, *statement.targets], graph, definitions, "dfg_uses")
            self._walk_statements(repository_id, function, statement.body, graph, definitions.copy())
            self._walk_statements(repository_id, function, statement.orelse, graph, definitions.copy())
            self._walk_statements(repository_id, function, statement.handlers, graph, definitions.copy())

    def _add_expression_uses(
        self,
        repository_id: str,
        function: IRFunction,
        expressions: list[IRExpression],
        graph: DFGGraph,
        definitions: dict[str, str],
        edge_type: str,
    ) -> None:
        for variable_name, expression in self._collect_variable_uses(expressions):
            use_node = self._use_node(repository_id, function, variable_name, expression)
            graph.nodes.append(use_node)
            if variable_name in definitions:
                graph.edges.append(DFGEdge(source=definitions[variable_name], target=use_node.id, type=edge_type))

    def _collect_variable_uses(self, expressions: list[IRExpression]) -> list[tuple[str, IRExpression]]:
        uses: list[tuple[str, IRExpression]] = []
        for expression in expressions:
            if expression.kind in {"variable", "attribute"} and expression.name:
                uses.append((expression.name.split(".", 1)[0], expression))
            uses.extend(self._collect_variable_uses(expression.children))
        return uses

    def _use_node(self, repository_id: str, function: IRFunction, variable_name: str, expression: IRExpression) -> DFGNode:
        return self._dfg_node(repository_id, function, "use", variable_name, expression.id, expression.start_line)

    def _dfg_node(self, repository_id: str, function: IRFunction, kind: str, name: str, key: str, line: int) -> DFGNode:
        return DFGNode(
            id=stable_node_id(repository_id, "dfg", f"{function.id}:{kind}:{name}:{key}"),
            kind=kind,
            name=name,
            file_path=function.file_path,
            function_qualified_name=function.qualified_name,
            line=line,
        )
