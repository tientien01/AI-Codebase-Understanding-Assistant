from __future__ import annotations

from collections.abc import Iterable

from app.services.code_analysis.models import (
    DFGEdge,
    DFGGraph,
    DFGNode,
    IRExpression,
    IRFunction,
    IRModule,
    IRStatement,
    ReferenceArtifact,
    canonical_symbol_key,
)
from app.services.code_analysis.stable_ids import stable_node_id


class DFGBuilder:
    """Build deterministic local DFGs and bind only resolver-confirmed calls."""

    def build_function(self, repository_id: str, function: IRFunction) -> DFGGraph:
        graph = DFGGraph(function_id=function.id)
        definitions: dict[str, str] = {}
        for parameter in function.parameters:
            node = self._dfg_node(repository_id, function, "parameter", parameter.name, parameter.id, parameter.start_line)
            self._append_node(graph, node)
            definitions[parameter.name] = node.id
        self._walk_statements(repository_id, function, function.body, graph, definitions)
        return graph

    def bind_resolved_calls(
        self,
        repository_id: str,
        module: IRModule,
        functions: list[IRFunction],
        graphs: list[DFGGraph],
        references: ReferenceArtifact | None,
    ) -> None:
        """Add cross-function DFG edges for exact, same-module resolver outcomes.

        The v1 Python IR preserves positional call children but not keyword labels.
        Binding therefore stops at keyword, ambiguous, unresolved and external calls
        instead of guessing from names.
        """
        if references is None:
            return

        graph_by_function = {graph.function_id: graph for graph in graphs}
        function_by_key: dict[str, IRFunction] = {}
        for function in functions:
            # Exactly one of these keys can be present in a resolver outcome. Keeping
            # both lets this compatibility builder consume module functions and methods
            # without reimplementing the resolver's ownership rules.
            for symbol_kind in ("function", "method"):
                function_by_key[canonical_symbol_key(module.file_key, function.qualified_name, symbol_kind)] = function

        used_call_ids: set[str] = set()
        for reference in references.references:
            if reference.reference_type != "call" or reference.outcome != "resolved":
                continue
            caller = function_by_key.get(reference.source_entity_key or "")
            callee = function_by_key.get(reference.target_keys[0])
            if caller is None or callee is None:
                continue
            caller_graph = graph_by_function.get(caller.id)
            callee_graph = graph_by_function.get(callee.id)
            if caller_graph is None or callee_graph is None:
                continue

            span = reference.source_spans[0]
            call = next(
                (
                    item
                    for item in self._call_expressions(caller.body)
                    if item.id not in used_call_ids
                    and item.name == reference.raw_reference
                    and item.start_line == span.start_line
                    and item.end_line == span.end_line
                ),
                None,
            )
            if call is None:
                continue
            used_call_ids.add(call.id)
            self._bind_call(repository_id, caller, callee, call, caller_graph, callee_graph)

    def _bind_call(
        self,
        repository_id: str,
        caller: IRFunction,
        callee: IRFunction,
        call: IRExpression,
        caller_graph: DFGGraph,
        callee_graph: DFGGraph,
    ) -> None:
        arguments = self._call_arguments(call)
        parameters = list(callee.parameters)
        if call.name and call.name.startswith("self.") and parameters and parameters[0].name in {"self", "cls"}:
            parameters = parameters[1:]

        for index, (argument, parameter) in enumerate(zip(arguments, parameters, strict=False)):
            argument_node = self._argument_node(repository_id, caller, call, argument, index)
            parameter_node = self._dfg_node(
                repository_id,
                callee,
                "parameter",
                parameter.name,
                parameter.id,
                parameter.start_line,
            )
            if argument_node.id in {node.id for node in caller_graph.nodes} and parameter_node.id in {
                node.id for node in callee_graph.nodes
            }:
                self._append_edge(
                    caller_graph,
                    DFGEdge(
                        argument_node.id,
                        parameter_node.id,
                        "dfg_argument_to_parameter",
                        confidence=0.9,
                        metadata=self._resolved_call_metadata(call),
                    ),
                )

        call_result = self._call_result_node(repository_id, caller, call)
        if call_result.id not in {node.id for node in caller_graph.nodes}:
            return
        for return_node in (node for node in callee_graph.nodes if node.kind == "return"):
            self._append_edge(
                caller_graph,
                DFGEdge(
                    return_node.id,
                    call_result.id,
                    "dfg_return_to_call_result",
                    confidence=0.9,
                    metadata=self._resolved_call_metadata(call),
                ),
            )

    def _walk_statements(
        self,
        repository_id: str,
        function: IRFunction,
        statements: list[IRStatement],
        graph: DFGGraph,
        definitions: dict[str, str],
    ) -> None:
        for statement in statements:
            self._add_call_boundaries(repository_id, function, statement.expressions, graph, definitions)
            if statement.kind == "assignment":
                uses = self._collect_variable_uses(statement.expressions)
                call_results = self._call_result_nodes(repository_id, function, statement.expressions)
                for target in statement.targets:
                    if not target.name:
                        continue
                    definition = self._dfg_node(repository_id, function, "definition", target.name, target.id, target.start_line)
                    self._append_node(graph, definition)
                    for variable_name, use_expression in uses:
                        use_node = self._use_node(repository_id, function, variable_name, use_expression)
                        self._append_node(graph, use_node)
                        if variable_name in definitions:
                            self._append_edge(graph, DFGEdge(definitions[variable_name], use_node.id, "dfg_reaches"))
                        self._append_edge(graph, DFGEdge(use_node.id, definition.id, "dfg_computed_from"))
                    for call_result in call_results:
                        self._append_edge(graph, DFGEdge(call_result.id, definition.id, "dfg_call_result_to_definition"))
                    definitions[target.name] = definition.id
            elif statement.kind == "return":
                uses = self._add_expression_uses(
                    repository_id,
                    function,
                    statement.expressions,
                    graph,
                    definitions,
                    "dfg_returned",
                )
                return_node = self._dfg_node(
                    repository_id,
                    function,
                    "return",
                    function.name,
                    statement.id,
                    statement.start_line,
                )
                self._append_node(graph, return_node)
                for use_node in uses:
                    self._append_edge(graph, DFGEdge(use_node.id, return_node.id, "dfg_return"))
                for call_result in self._call_result_nodes(repository_id, function, statement.expressions):
                    self._append_edge(graph, DFGEdge(call_result.id, return_node.id, "dfg_return"))
            else:
                self._add_expression_uses(
                    repository_id,
                    function,
                    [*statement.expressions, *statement.targets],
                    graph,
                    definitions,
                    "dfg_uses",
                )
            self._walk_statements(repository_id, function, statement.body, graph, definitions.copy())
            self._walk_statements(repository_id, function, statement.orelse, graph, definitions.copy())
            self._walk_statements(repository_id, function, statement.handlers, graph, definitions.copy())

    def _add_call_boundaries(
        self,
        repository_id: str,
        function: IRFunction,
        expressions: list[IRExpression],
        graph: DFGGraph,
        definitions: dict[str, str],
    ) -> None:
        for call in self._calls_from_expressions(expressions):
            call_result = self._call_result_node(repository_id, function, call)
            self._append_node(graph, call_result)
            for index, argument in enumerate(self._call_arguments(call)):
                argument_node = self._argument_node(repository_id, function, call, argument, index)
                self._append_node(graph, argument_node)
                for variable_name, use_expression in self._collect_variable_uses([argument]):
                    use_node = self._use_node(repository_id, function, variable_name, use_expression)
                    self._append_node(graph, use_node)
                    if variable_name in definitions:
                        self._append_edge(graph, DFGEdge(definitions[variable_name], use_node.id, "dfg_reaches"))
                    self._append_edge(graph, DFGEdge(use_node.id, argument_node.id, "dfg_argument"))
                for nested_result in self._call_result_nodes(repository_id, function, [argument]):
                    self._append_edge(graph, DFGEdge(nested_result.id, argument_node.id, "dfg_argument"))

    def _add_expression_uses(
        self,
        repository_id: str,
        function: IRFunction,
        expressions: list[IRExpression],
        graph: DFGGraph,
        definitions: dict[str, str],
        edge_type: str,
    ) -> list[DFGNode]:
        nodes: list[DFGNode] = []
        for variable_name, expression in self._collect_variable_uses(expressions):
            use_node = self._use_node(repository_id, function, variable_name, expression)
            self._append_node(graph, use_node)
            nodes.append(use_node)
            if variable_name in definitions:
                self._append_edge(graph, DFGEdge(definitions[variable_name], use_node.id, edge_type))
        return nodes

    def _collect_variable_uses(self, expressions: list[IRExpression]) -> list[tuple[str, IRExpression]]:
        uses: list[tuple[str, IRExpression]] = []
        for expression in expressions:
            if expression.kind == "call":
                # The first child is the callee expression, not a flowing value.
                uses.extend(self._collect_variable_uses(self._call_arguments(expression)))
                continue
            if expression.kind in {"variable", "attribute"} and expression.name:
                uses.append((expression.name.split(".", 1)[0], expression))
            uses.extend(self._collect_variable_uses(expression.children))
        return uses

    def _call_expressions(self, statements: Iterable[IRStatement]) -> list[IRExpression]:
        calls: list[IRExpression] = []
        for statement in statements:
            calls.extend(self._calls_from_expressions([*statement.expressions, *statement.targets]))
            calls.extend(self._call_expressions(statement.body))
            calls.extend(self._call_expressions(statement.orelse))
            calls.extend(self._call_expressions(statement.handlers))
        return calls

    def _calls_from_expressions(self, expressions: list[IRExpression]) -> list[IRExpression]:
        calls: list[IRExpression] = []
        for expression in expressions:
            if expression.kind == "call":
                calls.append(expression)
            calls.extend(self._calls_from_expressions(expression.children))
        return calls

    def _call_arguments(self, call: IRExpression) -> list[IRExpression]:
        return call.children[1:] if call.kind == "call" and call.children else []

    def _call_result_nodes(
        self,
        repository_id: str,
        function: IRFunction,
        expressions: list[IRExpression],
    ) -> list[DFGNode]:
        return [self._call_result_node(repository_id, function, call) for call in self._calls_from_expressions(expressions)]

    def _argument_node(
        self,
        repository_id: str,
        function: IRFunction,
        call: IRExpression,
        argument: IRExpression,
        index: int,
    ) -> DFGNode:
        name = argument.name or argument.value or argument.text.strip() or f"argument {index + 1}"
        return self._dfg_node(
            repository_id,
            function,
            "argument",
            name,
            f"{call.id}:argument:{index}:{argument.id}",
            argument.start_line,
        )

    def _call_result_node(self, repository_id: str, function: IRFunction, call: IRExpression) -> DFGNode:
        return self._dfg_node(
            repository_id,
            function,
            "call_result",
            call.name or call.text.strip() or "call result",
            call.id,
            call.start_line,
        )

    def _resolved_call_metadata(self, call: IRExpression) -> dict[str, str]:
        return {
            "path": call.file_path,
            "line": str(call.start_line),
            "resolution": "static_resolved",
            "scope": "direct_interprocedural",
        }

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

    def _append_node(self, graph: DFGGraph, node: DFGNode) -> None:
        if all(existing.id != node.id for existing in graph.nodes):
            graph.nodes.append(node)

    def _append_edge(self, graph: DFGGraph, edge: DFGEdge) -> None:
        identity = (edge.source, edge.target, edge.type)
        if all((existing.source, existing.target, existing.type) != identity for existing in graph.edges):
            graph.edges.append(edge)
