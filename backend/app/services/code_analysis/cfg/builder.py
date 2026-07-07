from __future__ import annotations

from app.services.code_analysis.models import CFGEdge, CFGGraph, CFGNode, IRFunction, IRStatement
from app.services.code_analysis.stable_ids import stable_node_id


class CFGBuilder:
    def build_function(self, repository_id: str, function: IRFunction) -> CFGGraph:
        graph = CFGGraph(function_id=function.id)
        entry = self._node(repository_id, function, "entry", "ENTRY", function.start_line, function.start_line)
        exit_node = self._node(repository_id, function, "exit", "EXIT", function.end_line, function.end_line)
        graph.nodes.extend([entry, exit_node])
        open_nodes = [entry.id]
        open_nodes = self._build_block(repository_id, function, function.body, graph, open_nodes, exit_node.id)
        for source in open_nodes:
            graph.edges.append(CFGEdge(source=source, target=exit_node.id, type="cfg_next"))
        return graph

    def _build_block(
        self,
        repository_id: str,
        function: IRFunction,
        statements: list[IRStatement],
        graph: CFGGraph,
        predecessors: list[str],
        exit_id: str,
    ) -> list[str]:
        open_nodes = predecessors
        for statement in statements:
            if statement.kind == "branch":
                open_nodes = self._build_branch(repository_id, function, statement, graph, open_nodes, exit_id)
            elif statement.kind == "loop":
                open_nodes = self._build_loop(repository_id, function, statement, graph, open_nodes, exit_id)
            elif statement.kind == "try":
                open_nodes = self._build_try(repository_id, function, statement, graph, open_nodes, exit_id)
            else:
                node = self._statement_node(repository_id, function, statement)
                graph.nodes.append(node)
                edge_type = "cfg_return" if statement.kind == "return" else "cfg_next"
                for source in open_nodes:
                    graph.edges.append(CFGEdge(source=source, target=node.id, type="cfg_next"))
                if statement.kind in {"return", "raise"}:
                    graph.edges.append(CFGEdge(source=node.id, target=exit_id, type=edge_type))
                    open_nodes = []
                else:
                    open_nodes = [node.id]
        return open_nodes

    def _build_branch(
        self,
        repository_id: str,
        function: IRFunction,
        statement: IRStatement,
        graph: CFGGraph,
        predecessors: list[str],
        exit_id: str,
    ) -> list[str]:
        branch = self._statement_node(repository_id, function, statement, kind="BRANCH")
        graph.nodes.append(branch)
        for source in predecessors:
            graph.edges.append(CFGEdge(source=source, target=branch.id, type="cfg_next"))
        then_open = self._build_block(repository_id, function, statement.body, graph, [branch.id], exit_id)
        if statement.body:
            graph.edges.append(CFGEdge(source=branch.id, target=self._first_statement_id(repository_id, function, statement.body), type="cfg_true"))
        else:
            then_open = [branch.id]
        else_open = self._build_block(repository_id, function, statement.orelse, graph, [branch.id], exit_id) if statement.orelse else [branch.id]
        if statement.orelse:
            graph.edges.append(CFGEdge(source=branch.id, target=self._first_statement_id(repository_id, function, statement.orelse), type="cfg_false"))
        return [*then_open, *else_open]

    def _build_loop(
        self,
        repository_id: str,
        function: IRFunction,
        statement: IRStatement,
        graph: CFGGraph,
        predecessors: list[str],
        exit_id: str,
    ) -> list[str]:
        loop = self._statement_node(repository_id, function, statement, kind="LOOP")
        graph.nodes.append(loop)
        for source in predecessors:
            graph.edges.append(CFGEdge(source=source, target=loop.id, type="cfg_next"))
        body_open = self._build_block(repository_id, function, statement.body, graph, [loop.id], exit_id)
        if statement.body:
            graph.edges.append(CFGEdge(source=loop.id, target=self._first_statement_id(repository_id, function, statement.body), type="cfg_loop_body"))
        for source in body_open:
            graph.edges.append(CFGEdge(source=source, target=loop.id, type="cfg_loop_back", confidence=0.8))
        return [loop.id]

    def _build_try(
        self,
        repository_id: str,
        function: IRFunction,
        statement: IRStatement,
        graph: CFGGraph,
        predecessors: list[str],
        exit_id: str,
    ) -> list[str]:
        try_node = self._statement_node(repository_id, function, statement, kind="TRY")
        graph.nodes.append(try_node)
        for source in predecessors:
            graph.edges.append(CFGEdge(source=source, target=try_node.id, type="cfg_next"))
        body_open = self._build_block(repository_id, function, statement.body, graph, [try_node.id], exit_id)
        handler_open = self._build_block(repository_id, function, statement.handlers, graph, [try_node.id], exit_id) if statement.handlers else []
        if statement.handlers:
            graph.edges.append(CFGEdge(source=try_node.id, target=self._first_statement_id(repository_id, function, statement.handlers), type="cfg_exception", confidence=0.75))
        return [*body_open, *handler_open]

    def _statement_node(self, repository_id: str, function: IRFunction, statement: IRStatement, kind: str | None = None) -> CFGNode:
        label = kind or statement.kind.upper()
        return CFGNode(
            id=stable_node_id(repository_id, "cfg", f"{function.id}:{statement.id}:{label}"),
            kind=label,
            label=label.title(),
            file_path=function.file_path,
            function_qualified_name=function.qualified_name,
            start_line=statement.start_line,
            end_line=statement.end_line,
        )

    def _node(self, repository_id: str, function: IRFunction, key: str, kind: str, start_line: int, end_line: int) -> CFGNode:
        return CFGNode(
            id=stable_node_id(repository_id, "cfg", f"{function.id}:{key}"),
            kind=kind,
            label=kind.title(),
            file_path=function.file_path,
            function_qualified_name=function.qualified_name,
            start_line=start_line,
            end_line=end_line,
        )

    def _first_statement_id(self, repository_id: str, function: IRFunction, statements: list[IRStatement]) -> str:
        first = statements[0]
        kind = "BRANCH" if first.kind == "branch" else "LOOP" if first.kind == "loop" else "TRY" if first.kind == "try" else first.kind.upper()
        return stable_node_id(repository_id, "cfg", f"{function.id}:{first.id}:{kind}")
