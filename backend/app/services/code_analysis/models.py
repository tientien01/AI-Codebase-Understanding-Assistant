from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IRNode:
    id: str
    kind: str
    file_path: str
    ast_path: str
    start_line: int
    end_line: int
    text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class IRImport(IRNode):
    module: str = ""
    imported_name: str | None = None
    alias: str | None = None
    level: int = 0


@dataclass
class IRDecorator:
    name: str
    args: list[str] = field(default_factory=list)
    kwargs: dict[str, str] = field(default_factory=dict)
    line: int | None = None


@dataclass
class IRParameter(IRNode):
    name: str = ""


@dataclass
class IRExpression(IRNode):
    name: str | None = None
    value: str | None = None
    children: list["IRExpression"] = field(default_factory=list)


@dataclass
class IRStatement(IRNode):
    expressions: list[IRExpression] = field(default_factory=list)
    targets: list[IRExpression] = field(default_factory=list)
    body: list["IRStatement"] = field(default_factory=list)
    orelse: list["IRStatement"] = field(default_factory=list)
    handlers: list["IRStatement"] = field(default_factory=list)


@dataclass
class IRFunction(IRNode):
    name: str = ""
    qualified_name: str = ""
    parameters: list[IRParameter] = field(default_factory=list)
    body: list[IRStatement] = field(default_factory=list)
    decorators: list[IRDecorator] = field(default_factory=list)
    is_async: bool = False


@dataclass
class IRClass(IRNode):
    name: str = ""
    qualified_name: str = ""
    body: list[IRNode] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)


@dataclass
class IREndpoint:
    method: str
    path: str
    handler: str
    handler_qualified_name: str
    file_path: str
    start_line: int
    end_line: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class IRModule:
    id: str
    file_path: str
    language: str
    imports: list[IRImport] = field(default_factory=list)
    classes: list[IRClass] = field(default_factory=list)
    functions: list[IRFunction] = field(default_factory=list)
    statements: list[IRStatement] = field(default_factory=list)
    endpoints: list[IREndpoint] = field(default_factory=list)
    diagnostics: list[dict[str, str | int | None]] = field(default_factory=list)


@dataclass
class CFGNode:
    id: str
    kind: str
    label: str
    file_path: str
    function_qualified_name: str
    start_line: int
    end_line: int


@dataclass
class CFGEdge:
    source: str
    target: str
    type: str
    confidence: float = 0.9


@dataclass
class CFGGraph:
    function_id: str
    nodes: list[CFGNode] = field(default_factory=list)
    edges: list[CFGEdge] = field(default_factory=list)


@dataclass
class DFGNode:
    id: str
    kind: str
    name: str
    file_path: str
    function_qualified_name: str
    line: int


@dataclass
class DFGEdge:
    source: str
    target: str
    type: str
    confidence: float = 0.85


@dataclass
class DFGGraph:
    function_id: str
    nodes: list[DFGNode] = field(default_factory=list)
    edges: list[DFGEdge] = field(default_factory=list)


@dataclass
class CPGResult:
    module: IRModule
    cfg_graphs: list[CFGGraph] = field(default_factory=list)
    dfg_graphs: list[DFGGraph] = field(default_factory=list)
