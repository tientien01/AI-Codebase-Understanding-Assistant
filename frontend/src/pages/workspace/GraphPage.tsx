import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, PointerEvent as ReactPointerEvent, RefObject } from 'react'
import { Icon } from '../../components/common/Icon'
import { PageTitle, PreviewLine } from '../../components/common/ui'
import type { GraphData, GraphProjectionInput, GraphView, IconName, Overview } from '../../types/api'
import { valueTraceContextLabel } from '../../utils/valueTrace'
import type { ValueTraceContext } from '../../utils/valueTrace'

type GraphNode = GraphData['nodes'][number]
type GraphEdge = GraphData['edges'][number]
type GraphSeed = NonNullable<GraphData['seeds']>[number]
type GraphExpansion = NonNullable<GraphData['expansion']>
type InspectorTab = 'overview' | 'relations' | 'evidence' | 'impact'

type ViewMeta = {
  id: GraphView
  label: string
  eyebrow: string
  question: string
  description: string
  focusLabel: string
  focusPlaceholder: string
  nodeMeaning: string
  edgeMeaning: string
  icon: IconName
  advanced?: boolean
  defaultNodeTypes: string[]
  defaultEdgeTypes: string[]
}

const NODE_WIDTH = 190
const NODE_HEIGHT = 86
const CANVAS_WIDTH = 1120
const PROGRESSIVE_CANVAS_WIDTH = 1240
const EMPTY_NODES: GraphNode[] = []
const EMPTY_EDGES: GraphEdge[] = []
const REQUEST_FLOW_NODE_TYPES = ['endpoint', 'api_call', 'function', 'method']
const REQUEST_FLOW_EDGE_TYPES = ['calls_api', 'exposes_endpoint', 'calls']
const CALL_FLOW_NODE_TYPES = ['function', 'method', 'builtin_call', 'stdlib_call', 'framework_call', 'external_call', 'unresolved_call']
const CALL_FLOW_EDGE_TYPES = ['calls', 'calls_builtin', 'calls_stdlib', 'calls_framework', 'calls_external', 'calls_unresolved']

const VIEW_META: Record<GraphView, ViewMeta> = {
  'project-map': {
    id: 'project-map',
    label: 'Explore relationships',
    eyebrow: 'Start here',
    question: 'What do you want to understand?',
    description: 'Choose a focused question. Architecture summary remains in Overview; this workspace explains supported code relationships.',
    focusLabel: 'Focus',
    focusPlaceholder: 'Choose a relationship question',
    nodeMeaning: 'A code entity relevant to the selected question',
    edgeMeaning: 'A supported relationship returned by the active index',
    icon: 'nodes',
    defaultNodeTypes: [],
    defaultEdgeTypes: [],
  },
  dependencies: {
    id: 'dependencies',
    label: 'Dependencies',
    eyebrow: 'Files and modules',
    question: 'What does this file use, and what uses it?',
    description: 'Choose a file or module, then follow resolved import relationships in either direction.',
    focusLabel: 'File or module',
    focusPlaceholder: 'Choose a file or module',
    nodeMeaning: 'Each node is an indexed file or module.',
    edgeMeaning: 'A → B means A imports B.',
    icon: 'git',
    defaultNodeTypes: ['file', 'module'],
    defaultEdgeTypes: ['imports'],
  },
  'api-flow': {
    id: 'api-flow',
    label: 'Request Flow',
    eyebrow: 'Endpoints and calls',
    question: 'Where can this API request go?',
    description: 'Start from an endpoint or resolved call and inspect only the downstream relationships supported by the index.',
    focusLabel: 'Endpoint or call',
    focusPlaceholder: 'Choose an endpoint or resolved call',
    nodeMeaning: 'A node is an endpoint, call site, function or method participating in the request path.',
    edgeMeaning: 'Arrows mean exposes endpoint, contains call, calls, or calls API as labeled.',
    icon: 'route',
    defaultNodeTypes: ['endpoint', 'api_call', 'call_site', 'function', 'method'],
    defaultEdgeTypes: ['exposes_endpoint', 'contains_call', 'calls', 'calls_api'],
  },
  'function-flow': {
    id: 'function-flow',
    label: 'Call Flow',
    eyebrow: 'Functions and methods',
    question: 'What does this function call, and what calls it?',
    description: 'Follow resolved calls between callable symbols. Compiler control-flow steps are excluded from this default view.',
    focusLabel: 'Function or method',
    focusPlaceholder: 'Choose a function or method',
    nodeMeaning: 'Each node is a function, method or resolved call site.',
    edgeMeaning: 'A → B means A contains or resolves a call toward B.',
    icon: 'braces',
    defaultNodeTypes: CALL_FLOW_NODE_TYPES,
    defaultEdgeTypes: CALL_FLOW_EDGE_TYPES,
  },
  'data-flow': {
    id: 'data-flow',
    label: 'Value Trace',
    eyebrow: 'Advanced · compiler-level',
    question: 'How is this indexed value defined and used?',
    description: 'Inspect compiler-level definitions and uses inside analyzed functions. This is not a system or database data-flow diagram.',
    focusLabel: 'Indexed value',
    focusPlaceholder: 'Choose a definition or use',
    nodeMeaning: 'Each node is an indexed parameter, definition, use, call result or return value.',
    edgeMeaning: 'Arrows are labeled with the exact dfg relation returned by analysis.',
    icon: 'share',
    advanced: true,
    defaultNodeTypes: ['dfg_node'],
    defaultEdgeTypes: [],
  },
}

const PRIMARY_VIEWS: GraphView[] = ['dependencies', 'api-flow', 'function-flow']

type GraphPageProps = {
  graph: GraphData | null
  graphView: GraphView
  projection: GraphProjectionInput
  overview: Overview | null
  onGraphView: (view: GraphView) => void
  onProjection: (patch: Partial<GraphProjectionInput>) => void
  onAnalyzeArea: (scopePath: string) => void
  onExpandNode?: (nodeId: string, direction: GraphProjectionInput['direction'], neighborOffset?: number) => Promise<GraphData | null>
  onOpenSource?: (node: GraphNode) => void
  onTraceValue?: (context: ValueTraceContext) => void
  embedded?: boolean
  onCloseEmbedded?: () => void
  onOpenFullGraph?: () => void
  onReturnToSource?: () => void
}

export function GraphPage(props: GraphPageProps) {
  if (props.graphView === 'dependencies') {
    const graphKey = [
      props.graph?.repository_id,
      props.graph?.index_version,
      props.graph?.dependency_scope_used,
      ...(props.graph?.nodes.map((node) => node.id) ?? []),
    ].join(':')
    return <ProgressiveDependencyGraph {...props} key={graphKey} />
  }
  if (props.graphView === 'api-flow') {
    const graphKey = [
      props.graph?.repository_id,
      props.graph?.index_version,
      props.graph?.seed_strategy,
    ].join(':')
    return <ProgressiveRequestFlow {...props} key={graphKey} />
  }
  if (props.graphView === 'function-flow') {
    const graphKey = [props.graph?.repository_id, props.graph?.index_version, props.graph?.seed_strategy].join(':')
    return <ProgressiveCallFlow {...props} key={graphKey} />
  }
  if (props.graphView === 'data-flow') {
    const graphKey = [props.graph?.repository_id, props.graph?.index_version, props.graph?.seed_strategy].join(':')
    return <ProgressiveValueFlow {...props} key={graphKey} />
  }
  return <LegacyGraphPage {...props} />
}

export function ValueTracePanel(props: Omit<GraphPageProps, 'graphView'>) {
  return <ProgressiveValueFlow {...props} graphView="data-flow" embedded />
}

function LegacyGraphPage({
  graph,
  graphView,
  projection,
  overview,
  onGraphView,
  onProjection,
  onAnalyzeArea,
  onOpenSource,
}: GraphPageProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const [zoom, setZoom] = useState(0.9)
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('overview')
  const viewportRef = useRef<HTMLDivElement>(null)
  const nodes = graph?.nodes ?? EMPTY_NODES
  const edges = graph?.edges ?? EMPTY_EDGES
  const meta = VIEW_META[graphView]
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes])
  const activeNode = nodeById.get(selectedNodeId ?? '')
  const focusedNode = nodeById.get(projection.rootKeys[0] ?? '')
  const layout = useMemo(() => buildLayerLayout(nodes), [nodes])
  const canvas = useGraphCanvasInteractions(layout.positions, { width: CANVAS_WIDTH, height: layout.height }, zoom, viewportRef)
  const relatedNodeIds = useMemo(() => connectedNodeIds(activeNode?.id, edges), [activeNode?.id, edges])
  const relatedEdges = activeNode ? edges.filter((edge) => edge.source === activeNode.id || edge.target === activeNode.id) : []
  const nodeTypes = unique([projection.nodeTypes[0], ...nodes.map((node) => node.type)])
  const edgeTypes = unique([projection.edgeTypes[0], ...edges.map((edge) => edge.type)])
  const includedEdgeTypes = unique(edges.map((edge) => edge.type))
  const availableNodes = graph?.counts?.available_nodes ?? nodes.length
  const availableEdges = graph?.counts?.available_edges ?? edges.length
  const limited = graph?.coverage?.state === 'limited' || Boolean(graph?.truncation?.truncated)
  const chooser = graphView === 'project-map'
  const focusOptions = useMemo(() => focusCandidates(nodes, graphView), [nodes, graphView])

  function chooseView(view: GraphView) {
    const next = VIEW_META[view]
    setSelectedNodeId(undefined)
    setInspectorTab('overview')
    onProjection(view === 'dependencies' ? {
      rootKeys: [],
      nodeTypes: [],
      edgeTypes: [],
      supportLevels: [],
      direction: 'both',
      projectionMode: 'seeds',
      dependencyScope: 'adaptive',
      neighborOffset: 0,
    } : view === 'api-flow' ? {
      rootKeys: [],
      nodeTypes: REQUEST_FLOW_NODE_TYPES.slice(0, 2),
      edgeTypes: REQUEST_FLOW_EDGE_TYPES,
      supportLevels: [],
      direction: 'both',
      projectionMode: 'seeds',
      seedLimit: 12,
      neighborOffset: 0,
    } : view === 'function-flow' ? {
      rootKeys: [],
      nodeTypes: CALL_FLOW_NODE_TYPES,
      edgeTypes: CALL_FLOW_EDGE_TYPES,
      supportLevels: [],
      direction: 'both',
      maxDepth: 1,
      projectionMode: 'seeds',
      seedLimit: 24,
      neighborOffset: 0,
    } : {
      rootKeys: [],
      nodeTypes: next.defaultNodeTypes,
      edgeTypes: next.defaultEdgeTypes,
      supportLevels: [],
      direction: 'both',
      maxDepth: 1,
      projectionMode: 'seeds',
      seedLimit: 24,
      neighborOffset: 0,
    })
    onGraphView(view)
  }

  function applyFocus(nodeId: string) {
    setSelectedNodeId(nodeId || undefined)
    setInspectorTab('overview')
    onProjection({ rootKeys: nodeId ? [nodeId] : [] })
  }

  function clearSelection() {
    setSelectedNodeId(undefined)
    setInspectorTab('overview')
  }

  function expandProjection() {
    onProjection({
      maxNodes: Math.min(220, Math.max(projection.maxNodes + 40, projection.maxNodes * 2)),
      maxEdges: Math.min(520, Math.max(projection.maxEdges + 80, projection.maxEdges * 2)),
    })
  }

  function selectNode(nodeId: string) {
    setSelectedNodeId(nodeId)
    setInspectorTab('overview')
  }

  return (
    <div className="graph-explorer-page">
      <PageTitle title="Graph Explorer" subtitle="Choose a code relationship to investigate, then focus the graph on a concrete file, endpoint, function, or value." />

      {chooser ? (
        <GraphJourneyChooser onChoose={chooseView} />
      ) : (
        <>
          <nav className="graph-view-nav" aria-label="Relationship views">
            <button type="button" className="graph-view-home" onClick={() => chooseView('project-map')}>
              <Icon name="grid" size={15} /> Choose question
            </button>
            {PRIMARY_VIEWS.map((view) => (
              <button type="button" className={graphView === view ? 'active' : ''} key={view} onClick={() => chooseView(view)}>
                <Icon name={VIEW_META[view].icon} size={15} /> {VIEW_META[view].label}
              </button>
            ))}
          </nav>

          <section className="graph-view-intro" aria-labelledby="graph-view-question">
            <div className="graph-view-intro-icon"><Icon name={meta.icon} size={22} /></div>
            <div>
              <span>{meta.eyebrow}</span>
              <h2 id="graph-view-question">{meta.question}</h2>
              <p>{meta.description}</p>
            </div>
            <dl className="graph-vocabulary">
              <div><dt>Nodes</dt><dd>{meta.nodeMeaning}</dd></div>
              <div><dt>Arrows</dt><dd>{meta.edgeMeaning}</dd></div>
            </dl>
          </section>

          <section className="graph-control-bar" aria-label="Graph projection controls">
            <label className="graph-focus-control">
              <span>{meta.focusLabel}</span>
              <select value={projection.rootKeys[0] ?? ''} onChange={(event) => applyFocus(event.target.value)}>
                <option value="">{meta.focusPlaceholder}</option>
                {focusOptions.map((node) => <option key={node.id} value={node.id}>{focusOptionLabel(node)}</option>)}
              </select>
            </label>
            <label>
              <span>Direction</span>
              <select value={projection.direction} onChange={(event) => onProjection({ direction: event.target.value as GraphProjectionInput['direction'] })}>
                <option value="both">Incoming and outgoing</option>
                <option value="outgoing">Outgoing</option>
                <option value="incoming">Incoming</option>
              </select>
            </label>
            <label>
              <span>Depth</span>
              <select value={projection.maxDepth} onChange={(event) => onProjection({ maxDepth: Number(event.target.value) })}>
                {[1, 2, 3, 4, 5, 6].map((depth) => <option key={depth} value={depth}>{depth} {depth === 1 ? 'level' : 'levels'}</option>)}
              </select>
            </label>
            <details className="graph-filter-menu">
              <summary><Icon name="sliders" size={15} /> Filters</summary>
              <div>
                <label>
                  Projection size
                  <select value={projection.maxNodes} onChange={(event) => {
                    const maxNodes = Number(event.target.value)
                    onProjection({ maxNodes, maxEdges: Math.min(520, maxNodes * 2) })
                  }}>
                    {[40, 80, 160, 220].map((size) => <option key={size} value={size}>Up to {size} nodes</option>)}
                  </select>
                </label>
                <label>
                  Node type
                  <select value={projection.nodeTypes.length === 1 ? projection.nodeTypes[0] : ''} onChange={(event) => onProjection({ nodeTypes: event.target.value ? [event.target.value] : meta.defaultNodeTypes })}>
                    <option value="">View defaults</option>
                    {nodeTypes.map((type) => <option key={type} value={type}>{readableType(type)}</option>)}
                  </select>
                </label>
                <label>
                  Relation type
                  <select value={projection.edgeTypes.length === 1 ? projection.edgeTypes[0] : ''} onChange={(event) => onProjection({ edgeTypes: event.target.value ? [event.target.value] : meta.defaultEdgeTypes })}>
                    <option value="">View defaults</option>
                    {edgeTypes.map((type) => <option key={type} value={type}>{readableType(type)}</option>)}
                  </select>
                </label>
                <label>
                  Support
                  <select value={projection.supportLevels[0] ?? ''} onChange={(event) => onProjection({ supportLevels: event.target.value ? [event.target.value] : [] })}>
                    <option value="">All support levels</option>
                    <option value="deep">Analyzed code</option>
                    <option value="map">Repository structure</option>
                    <option value="inferred">Inferred</option>
                  </select>
                </label>
              </div>
            </details>
          </section>

          {graph ? (
            <div className={`graph-projection-status ${limited ? 'limited' : 'complete'}`} role="status" aria-live="polite">
              <strong>{limited ? 'Limited projection' : 'Current bounded result'}</strong>
              <span>
                Showing {nodes.length} {nodes.length === 1 ? 'node' : 'nodes'} and {edges.length} {edges.length === 1 ? 'relationship' : 'relationships'}
                {focusedNode ? ` from ${focusedNode.label}` : ''}, {directionLabel(projection.direction)}, {projection.maxDepth} {projection.maxDepth === 1 ? 'level' : 'levels'}.
              </span>
              {limited ? <span>{nodes.length}/{availableNodes} nodes · {edges.length}/{availableEdges} relationships.</span> : null}
              {graph.truncation?.reason ? <span>Reason: {readableType(graph.truncation.reason)}.</span> : null}
              {graph.unsupported_hops?.length ? <span>{graph.unsupported_hops.length} requested focus or hop could not be resolved.</span> : null}
              {graph.can_expand ? <button type="button" onClick={expandProjection}>Expand bounded result</button> : null}
            </div>
          ) : null}

          <div className="graph-explorer-workspace">
            <section className="graph-stage-shell" aria-label="Interactive graph explorer">
              <div className="graph-stage-tools">
                <div className="graph-edge-legend" aria-label="Visible relationship types">
                  <strong>Arrows shown</strong>
                  {includedEdgeTypes.length
                    ? includedEdgeTypes.map((type) => <span key={type}>{readableType(type)}</span>)
                    : <span>No supported arrows in this result</span>}
                </div>
                <div className="graph-zoom" aria-label="Graph zoom controls">
                  {activeNode ? <button type="button" onClick={clearSelection}>Clear selection</button> : null}
                  <button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.55, value - 0.1))}>−</button>
                  <output aria-label="Current zoom">{Math.round(zoom * 100)}%</output>
                  <button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.25, value + 0.1))}>+</button>
                  <button type="button" onClick={() => setZoom(0.9)}>Fit</button>
                </div>
              </div>

              {!edges.length ? <GraphEmptyState meta={meta} hasNodes={Boolean(nodes.length)} limited={limited} onClearFocus={() => applyFocus('')} /> : null}

              <div className={`graph-stage-viewport interactive-graph-viewport ${canvas.panning ? 'panning' : ''}`} ref={viewportRef} {...canvas.viewportPointerHandlers} role="region" tabIndex={0} aria-label="Pannable graph canvas. Drag empty space to pan; drag nodes to reposition.">
                <div
                  className="graph-canvas graph-layer-canvas"
                  aria-label="Graph nodes"
                  style={{ width: CANVAS_WIDTH, height: layout.height, transform: `scale(${zoom})` }}
                >
                  {layout.layers.map((layer) => (
                    <div className={`graph-layer-band layer-${layer.id}`} style={{ top: layer.top, height: layer.height }} key={layer.id} aria-hidden="true">
                      <span>{layer.label}</span>
                    </div>
                  ))}
                  <svg className="graph-edges" width={CANVAS_WIDTH} height={layout.height} role="img" aria-label={`${edges.length} directional graph relationships`}>
                    <defs>
                      <marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
                        <path d="M 0 0 L 8 4 L 0 8 z" />
                      </marker>
                    </defs>
                    {edges.map((edge, index) => {
                      const source = canvas.positions.get(edge.source)
                      const target = canvas.positions.get(edge.target)
                      if (!source || !target) return null
                      const active = activeNode ? edge.source === activeNode.id || edge.target === activeNode.id : false
                      const sourceLabel = nodeById.get(edge.source)?.label ?? edge.source
                      const targetLabel = nodeById.get(edge.target)?.label ?? edge.target
                      return (
                        <path
                          className={`graph-edge support-${edge.evidence_level ?? 'deep'} ${active ? 'active' : ''}`}
                          d={edgePath(source, target, edgeLaneOffset(edge, edges))}
                          data-source={edge.source}
                          data-target={edge.target}
                          key={`${edge.source}-${edge.target}-${edge.type}-${index}`}
                          markerEnd="url(#graph-arrow)"
                        >
                          <title>{sourceLabel} {readableType(edge.type)} {targetLabel}</title>
                        </path>
                      )
                    })}
                  </svg>
                  {nodes.map((node) => {
                    const position = canvas.positions.get(node.id)
                    if (!position) return null
                    const dimmed = Boolean(activeNode && activeNode.id !== node.id && !relatedNodeIds.has(node.id))
                    return (
                      <button
                        type="button"
                        className={`graph-node graph-layer-node draggable-graph-node type-${node.type} coverage-${node.coverage ?? 'deep_indexed'} ${activeNode?.id === node.id ? 'active' : ''} ${dimmed ? 'dimmed' : ''}`}
                        style={{ left: position.x, top: position.y } as CSSProperties}
                        key={node.id}
                        {...canvas.nodePointerHandlers(node.id, position)}
                        onClick={() => { if (!canvas.consumeDraggedClick(node.id)) selectNode(node.id) }}
                        aria-pressed={activeNode?.id === node.id}
                      >
                        <span className="graph-node-type"><Icon name={nodeIcon(node)} size={12} /> {humanNodeType(node, graphView)}</span>
                        <strong>{humanNodeLabel(node, graphView)}</strong>
                        <small>{node.file_path || node.scope_path || coverageLabel(node.coverage)}</small>
                      </button>
                    )
                  })}
                  {!nodes.length && <p>No nodes are available within this projection.</p>}
                  <div className="graph-minimap" aria-hidden="true">
                    {nodes.slice(0, 80).map((node) => {
                      const position = canvas.positions.get(node.id)
                      return position ? <i key={node.id} style={{ left: position.x / 12, top: position.y / 12 }} /> : null
                    })}
                  </div>
                </div>
              </div>
              <details className="graph-relation-list">
                <summary>Relations ({edges.length}) <span>Keyboard and screen-reader alternative</span></summary>
                {edges.length ? (
                  <ul>
                    {edges.map((edge, index) => (
                      <li key={`${edge.source}-${edge.target}-${edge.type}-${index}`}>
                        <button type="button" onClick={() => selectNode(edge.source)}>{nodeById.get(edge.source)?.label ?? edge.source}</button>
                        <span>→ {readableType(edge.type)} · {supportLabel(edge.evidence_level)} →</span>
                        <button type="button" onClick={() => selectNode(edge.target)}>{nodeById.get(edge.target)?.label ?? edge.target}</button>
                      </li>
                    ))}
                  </ul>
                ) : <p>No supported relationships are included in this projection.</p>}
              </details>
            </section>

            <aside className="graph-inspector" aria-label="Selected graph entity">
              {activeNode ? (
                <>
                  <div className="graph-inspector-title">
                    <div className={`graph-entity-mark type-${activeNode.type}`} aria-hidden="true" />
                    <div><span>{humanNodeType(activeNode, graphView)}</span><h2>{humanNodeLabel(activeNode, graphView)}</h2></div>
                  </div>
                  <p className="graph-source-path">{activeNode.file_path || activeNode.scope_path || 'No source location reported'}</p>
                  <div className="graph-inspector-tabs" role="tablist" aria-label="Entity details">
                    {(['overview', 'relations', 'evidence', 'impact'] as InspectorTab[]).map((tab) => (
                      <button type="button" role="tab" aria-selected={inspectorTab === tab} className={inspectorTab === tab ? 'active' : ''} onClick={() => setInspectorTab(tab)} key={tab}>{readableType(tab)}</button>
                    ))}
                  </div>
                  {inspectorTab === 'overview' && (
                    <div className="graph-inspector-section">
                      <p>{activeNode.summary || 'No generated summary is available; inspect the source and supported relations instead.'}</p>
                      <PreviewLine label="Node meaning" value={humanNodeType(activeNode, graphView)} />
                      <PreviewLine label="Coverage" value={coverageLabel(activeNode.coverage)} />
                      <PreviewLine label="Index version" value={String(graph?.index_version ?? projection.indexVersion ?? 'active')} />
                      {activeNode.start_line ? <PreviewLine label="Lines" value={`${activeNode.start_line}-${activeNode.end_line ?? activeNode.start_line}`} /> : null}
                    </div>
                  )}
                  {inspectorTab === 'relations' && <RelationSummary edges={relatedEdges} activeNode={activeNode} nodeById={nodeById} onSelect={selectNode} />}
                  {inspectorTab === 'evidence' && <EvidenceSummary edges={relatedEdges} graph={graph} />}
                  {inspectorTab === 'impact' && (
                    <div className="graph-inspector-section">
                      <PreviewLine label="Direct relations" value={String(relatedEdges.filter((edge) => edge.evidence_level !== 'inferred').length)} />
                      <PreviewLine label="Inferred relations" value={String(relatedEdges.filter((edge) => edge.evidence_level === 'inferred').length)} />
                      <PreviewLine label="Unknown" value={String(graph?.coverage?.unknown.length ?? 0)} />
                      <p>Impact analysis uses the current active index. Historical comparison is unavailable in the compatibility API.</p>
                    </div>
                  )}
                  <div className="graph-inspector-actions">
                    <button className="primary wide" type="button" disabled={!activeNode.file_path} onClick={() => onOpenSource?.(activeNode)}>Open Source</button>
                    <button type="button" onClick={() => applyFocus(activeNode.id)}>Focus relationships</button>
                    {activeNode.coverage !== 'deep_indexed' && activeNode.coverage !== 'skipped' ? (
                      <button type="button" onClick={() => onAnalyzeArea(activeNode.scope_path || activeNode.file_path || '')}>Analyze area</button>
                    ) : null}
                  </div>
                </>
              ) : (
                <div className="graph-inspector-empty">
                  <Icon name={meta.icon} size={26} />
                  <h2>Select a node to inspect it</h2>
                  <p>{meta.nodeMeaning}</p>
                  <p>Selection highlights only direct neighbors. It does not remove nodes or change the server projection.</p>
                </div>
              )}
              <div className="graph-project-summary">
                <PreviewLine label="Current view" value={meta.label} />
                <PreviewLine label="Indexed endpoints" value={String(overview?.endpoints.length ?? 0)} />
                <PreviewLine label="Deterministic ordering" value={graph?.provenance?.deterministic_order ? 'Yes' : 'Not reported'} />
              </div>
            </aside>
          </div>
        </>
      )}
    </div>
  )
}

function ProgressiveDependencyGraph({
  graph,
  projection,
  onGraphView,
  onProjection,
  onAnalyzeArea,
  onExpandNode,
  onOpenSource,
}: GraphPageProps) {
  const [visibleGraph, setVisibleGraph] = useState<GraphData | null>(graph)
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const [direction, setDirection] = useState<GraphProjectionInput['direction']>(projection.direction)
  const [zoom, setZoom] = useState(0.9)
  const [searchValue, setSearchValue] = useState('')
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [expandingNodeId, setExpandingNodeId] = useState<string>()
  const [parentByNode, setParentByNode] = useState<Record<string, string>>({})
  const [expansionByKey, setExpansionByKey] = useState<Record<string, NonNullable<GraphData['expansion']>>>({})
  const [positionCache, setPositionCache] = useState(() => new Map<string, Position>())
  const viewportRef = useRef<HTMLDivElement>(null)

  const nodes = visibleGraph?.nodes ?? EMPTY_NODES
  const edges = visibleGraph?.edges ?? EMPTY_EDGES
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes])
  const activeNode = nodeById.get(selectedNodeId ?? '')
  const layout = useMemo(
    () => buildProgressiveLayout(nodes, edges, positionCache, parentByNode),
    [nodes, edges, parentByNode, positionCache],
  )
  const canvas = useGraphCanvasInteractions(layout.positions, layout, zoom, viewportRef)
  const relatedNodeIds = useMemo(() => connectedNodeIds(activeNode?.id, edges), [activeNode?.id, edges])
  const activePathIds = useMemo(() => dependencyBranchPath(activeNode?.id, parentByNode), [activeNode?.id, parentByNode])
  const seedById = useMemo(
    () => new Map((graph?.seeds ?? []).map((seed) => [seed.node_id, seed])),
    [graph?.seeds],
  )
  const scopeUsed = graph?.dependency_scope_used ?? visibleGraph?.dependency_scope_used ?? 'detected'
  const limited = graph?.coverage?.state === 'limited'
    || Object.values(expansionByKey).some((expansion) => expansion.limited)
    || Boolean(visibleGraph?.truncation?.truncated)
  const relationTypes = unique(edges.map((edge) => edge.type))
  const relatedEdges = activeNode ? edges.filter((edge) => edge.source === activeNode.id || edge.target === activeNode.id) : []

  function expansionKey(nodeId: string) {
    return `${nodeId}:${direction}`
  }

  async function selectAndExpand(nodeId: string) {
    const changingFocus = Boolean(selectedNodeId && selectedNodeId !== nodeId)
    setSelectedNodeId(nodeId)
    setInspectorOpen(true)
    if (!onExpandNode || expandingNodeId) return
    const key = expansionKey(nodeId)
    const prior = changingFocus ? undefined : expansionByKey[key]
    if (prior?.leaf || (prior && prior.next_neighbor_offset == null)) return
    setExpandingNodeId(nodeId)
    const existingIds = new Set((changingFocus ? graph?.nodes ?? EMPTY_NODES : nodes).map((node) => node.id))
    const delta = await onExpandNode(nodeId, direction, prior?.next_neighbor_offset ?? 0)
    setExpandingNodeId(undefined)
    if (!delta) return
    const newNodeIds = delta.nodes.filter((node) => node.id !== nodeId && !existingIds.has(node.id)).map((node) => node.id)
    setParentByNode((current) => {
      const next = changingFocus ? {} : { ...current }
      if (newNodeIds.length) {
        newNodeIds.forEach((childId) => { next[childId] ??= nodeId })
      }
      return next
    })
    if (delta.expansion) {
      setExpansionByKey((current) => ({ ...(changingFocus ? {} : current), [key]: delta.expansion! }))
    }
    setPositionCache(changingFocus ? new Map() : new Map(canvas.positions))
    setVisibleGraph((current) => mergeGraphProjection(changingFocus ? graph : current, delta))
  }

  function resetExploration() {
    setVisibleGraph(graph)
    setSelectedNodeId(undefined)
    setInspectorOpen(false)
    setParentByNode({})
    setExpansionByKey({})
    setPositionCache(new Map())
    canvas.resetNodePositions()
  }

  function changeDirection(value: GraphProjectionInput['direction']) {
    if (value === direction) return
    setDirection(value)
    resetExploration()
  }

  function changeScope(scope: NonNullable<GraphProjectionInput['dependencyScope']>) {
    onProjection({
      dependencyScope: scope,
      projectionMode: 'seeds',
      rootKeys: [],
      nodeTypes: scope === 'detected' ? ['file', 'module'] : scope === 'internal' ? ['file'] : [],
      edgeTypes: scope === 'detected' ? ['imports'] : scope === 'internal' ? ['imports_internal'] : [],
      supportLevels: [],
    })
  }

  function jumpToVisibleNode() {
    const match = nodes.find((node) => focusOptionLabel(node) === searchValue || node.label === searchValue)
    if (match) void selectAndExpand(match.id)
  }

  function fitVisibleGraph() {
    const viewport = viewportRef.current
    if (!viewport) return
    const horizontalScale = (viewport.clientWidth - 32) / layout.width
    const verticalScale = (viewport.clientHeight - 32) / layout.height
    setZoom(Math.max(0.55, Math.min(1.25, horizontalScale, verticalScale)))
    viewport.scrollTo?.({ top: 0, left: 0 })
  }

  return (
    <div className="graph-explorer-page progressive-dependency-page">
      <PageTitle title="Dependency Explorer" subtitle="Start from evidence-backed repository files, then expand only the branch you need." />

      <nav className="graph-view-nav graph-view-nav-compact" aria-label="Relationship views">
        <button type="button" className="graph-view-home" onClick={() => onGraphView('project-map')}><Icon name="grid" size={15} /> Choose question</button>
        {PRIMARY_VIEWS.map((view) => (
          <button type="button" className={view === 'dependencies' ? 'active' : ''} key={view} onClick={() => {
            if (view === 'api-flow') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: ['endpoint', 'api_call'], edgeTypes: REQUEST_FLOW_EDGE_TYPES, direction: 'both', seedLimit: 12, neighborOffset: 0 })
            else if (view === 'function-flow') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: CALL_FLOW_NODE_TYPES, edgeTypes: CALL_FLOW_EDGE_TYPES, direction: 'both', maxDepth: 1, seedLimit: 24, neighborOffset: 0 })
            else if (view !== 'dependencies') onProjection({ projectionMode: 'full', rootKeys: [], nodeTypes: VIEW_META[view].defaultNodeTypes, edgeTypes: VIEW_META[view].defaultEdgeTypes })
            onGraphView(view)
          }}>
            <Icon name={VIEW_META[view].icon} size={15} /> {VIEW_META[view].label}
          </button>
        ))}
      </nav>

      <section className="dependency-toolbar" aria-label="Dependency exploration controls">
        <div className="dependency-toolbar-title">
          <span>Suggested starting points</span>
          <strong>{scopeUsed === 'internal' ? 'Resolved internal files' : 'Detected file-to-module imports'}</strong>
        </div>
        <label className="dependency-search">
          <span className="sr-only">Find a visible file or module</span>
          <input list="dependency-visible-nodes" value={searchValue} placeholder="Find a visible file or module…" onChange={(event) => setSearchValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') jumpToVisibleNode() }} />
          <datalist id="dependency-visible-nodes">{nodes.map((node) => <option key={node.id} value={focusOptionLabel(node)} />)}</datalist>
          <button type="button" onClick={jumpToVisibleNode}>Focus</button>
        </label>
        <div className="dependency-segmented" aria-label="Dependency scope">
          {(['adaptive', 'internal', 'detected'] as const).map((scope) => (
            <button type="button" className={projection.dependencyScope === scope ? 'active' : ''} onClick={() => changeScope(scope)} key={scope}>
              {scope === 'adaptive' ? 'Auto' : scope === 'internal' ? 'Resolved internal' : 'Detected targets'}
            </button>
          ))}
        </div>
        <div className="dependency-segmented" aria-label="Relationship direction">
          {(['outgoing', 'incoming', 'both'] as const).map((value) => (
            <button type="button" className={direction === value ? 'active' : ''} onClick={() => changeDirection(value)} key={value}>
              {value === 'outgoing' ? 'Dependencies' : value === 'incoming' ? 'Dependents' : 'Both'}
            </button>
          ))}
        </div>
        <details className="dependency-help">
          <summary aria-label="About dependency graph">?</summary>
          <div>
            <strong>{scopeUsed === 'internal' ? 'A → B means file A resolves an import to file B.' : 'A → B means file A contains a detected import for module B.'}</strong>
            <p>Click a node to load one bounded hop. Suggested points are selected deterministically from roles, connectivity, coverage and graph-region diversity.</p>
          </div>
        </details>
        <details className="dependency-advanced">
          <summary><Icon name="sliders" size={14} /> Details</summary>
          <div>
            <PreviewLine label="Strategy" value={graph?.seed_strategy ?? 'Compatibility projection'} />
            <PreviewLine label="Support" value={graph?.provenance?.support_levels.map(supportLabel).join(', ') || 'Not reported'} />
            <PreviewLine label="Index version" value={String(graph?.index_version ?? projection.indexVersion ?? 'active')} />
          </div>
        </details>
        <button type="button" className="dependency-reset" onClick={resetExploration}><Icon name="refresh" size={14} /> Back to overview</button>
      </section>

      <div className={`dependency-compact-status ${limited ? 'limited' : ''}`} role="status" aria-live="polite">
        <span><strong>{nodes.length}</strong> visible nodes · <strong>{edges.length}</strong> relations</span>
        <span>{graph?.seeds?.length ?? nodes.length} suggested starting points</span>
        {graph?.additional_starting_points ? <span>+{graph.additional_starting_points} qualified points are outside this bounded overview</span> : null}
        {limited ? <span>Coverage is limited; absence of an edge is not proof of no dependency.</span> : null}
        {scopeUsed === 'detected' ? <span>Detected targets are import names, not confirmed external packages.</span> : null}
      </div>

      <section className={`dependency-stage-shell ${inspectorOpen ? 'inspector-open' : ''}`} aria-label="Progressive dependency graph">
        <div className="graph-stage-tools dependency-stage-tools">
          <div className="graph-edge-legend" aria-label="Visible relationship types">
            <strong>Visible arrows</strong>
            {relationTypes.length ? relationTypes.map((type) => <span key={type}>{readableType(type)}</span>) : <span>Expand a starting point to reveal relations</span>}
          </div>
          <div className="graph-zoom" aria-label="Graph zoom controls">
            <button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.55, value - 0.1))}>−</button>
            <output aria-label="Current zoom">{Math.round(zoom * 100)}%</output>
            <button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.25, value + 0.1))}>+</button>
            <button type="button" onClick={fitVisibleGraph}>Fit visible</button>
          </div>
        </div>

        {!nodes.length ? (
          <div className="dependency-empty" role="status">
            <Icon name="nodes" size={24} />
            <h2>No supported dependency starting point</h2>
            <p>{scopeUsed === 'internal' ? 'The active compatibility index has no resolved internal file imports. Switch to Detected imports to inspect syntax-level module targets.' : 'No detected file-to-module import relation is available in the active index.'}</p>
          </div>
        ) : (
          <div className={`graph-stage-viewport dependency-stage-viewport interactive-graph-viewport ${canvas.panning ? 'panning' : ''}`} ref={viewportRef} {...canvas.viewportPointerHandlers} role="region" tabIndex={0} aria-label="Pannable dependency canvas. Drag empty space to pan; drag nodes to reposition.">
            <div className="dependency-canvas-scale" style={{ width: layout.width * zoom, height: layout.height * zoom }}>
            <div className="graph-canvas graph-progressive-canvas" aria-label="Graph nodes" style={{ width: layout.width, height: layout.height, transform: `scale(${zoom})` }}>
              <svg className="graph-edges" width={layout.width} height={layout.height} role="img" aria-label={`${edges.length} directional graph relationships`}>
                <defs><marker id="dependency-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" /></marker></defs>
                {edges.map((edge, index) => {
                  const source = canvas.positions.get(edge.source)
                  const target = canvas.positions.get(edge.target)
                  if (!source || !target) return null
                  const active = activePathIds.has(edge.source) && activePathIds.has(edge.target)
                  const related = Boolean(activeNode && (edge.source === activeNode.id || edge.target === activeNode.id))
                  const dimmed = Boolean(activeNode && !active && !related)
                  return <path className={`graph-edge support-${edge.evidence_level ?? 'deep'} ${active ? 'active' : ''} ${dimmed ? 'dimmed' : ''}`} d={dependencyEdgePath(source, target, edgeLaneOffset(edge, edges))} key={`${edge.source}-${edge.target}-${edge.type}-${index}`} markerEnd="url(#dependency-arrow)"><title>{nodeById.get(edge.source)?.label ?? edge.source} {readableType(edge.type)} {nodeById.get(edge.target)?.label ?? edge.target}</title></path>
                })}
              </svg>
              {nodes.map((node) => {
                const position = canvas.positions.get(node.id)
                if (!position) return null
                const dimmed = Boolean(activeNode && !activePathIds.has(node.id) && !relatedNodeIds.has(node.id))
                const seed = seedById.get(node.id)
                const expansion = expansionByKey[expansionKey(node.id)]
                return (
                  <button type="button" className={`graph-node graph-layer-node dependency-node draggable-graph-node type-${node.type} ${activeNode?.id === node.id ? 'active' : ''} ${dimmed ? 'dimmed' : ''}`} style={{ left: position.x, top: position.y } as CSSProperties} key={node.id} {...canvas.nodePointerHandlers(node.id, position)} onClick={() => { if (!canvas.consumeDraggedClick(node.id)) void selectAndExpand(node.id) }} aria-pressed={activeNode?.id === node.id}>
                    <span className="graph-node-type"><Icon name={nodeIcon(node)} size={12} /> {node.type === 'module' ? 'Detected module' : 'Repository file'}</span>
                    <strong>{dependencyNodeLabel(node)}</strong>
                    <small title={node.file_path || node.scope_path || undefined}>{seed ? seedReasonLabel(seed) : node.file_path || node.scope_path || node.role || 'Import target'}</small>
                    <em className="dependency-node-state">{dependencyExpansionLabel(node.id, direction, seed, expansion, expandingNodeId === node.id)}</em>
                  </button>
                )
              })}
              <div className="graph-minimap" aria-hidden="true">{nodes.slice(0, 80).map((node) => { const position = canvas.positions.get(node.id); return position ? <i key={node.id} style={{ left: position.x / 15, top: position.y / 15 }} /> : null })}</div>
            </div>
            </div>
          </div>
        )}

        <details className="graph-relation-list dependency-relation-list">
          <summary>Relations ({edges.length}) <span>Keyboard and screen-reader alternative</span></summary>
          {edges.length ? <ul>{edges.map((edge, index) => <li key={`${edge.source}-${edge.target}-${edge.type}-${index}`}><button type="button" onClick={() => { void selectAndExpand(edge.source) }}>{nodeById.get(edge.source)?.label ?? edge.source}</button><span>→ {readableType(edge.type)} · {supportLabel(edge.evidence_level)} →</span><button type="button" onClick={() => { void selectAndExpand(edge.target) }}>{nodeById.get(edge.target)?.label ?? edge.target}</button></li>)}</ul> : <p>No relation has been expanded yet.</p>}
        </details>

        {inspectorOpen && activeNode ? (
          <aside className="graph-inspector dependency-inspector" aria-label="Selected graph entity">
            <button type="button" className="dependency-inspector-close" aria-label="Close selected entity" onClick={() => setInspectorOpen(false)}>×</button>
            <div className="graph-inspector-title"><div className={`graph-entity-mark type-${activeNode.type}`} aria-hidden="true" /><div><span>{activeNode.type === 'module' ? 'Detected module' : 'Repository file'}</span><h2>{activeNode.label}</h2></div></div>
            <p className="graph-source-path">{activeNode.file_path || activeNode.scope_path || 'No repository source target was resolved'}</p>
            <div className="graph-inspector-section">
              <p>{activeNode.summary || 'Expand this node to inspect its bounded dependency neighborhood.'}</p>
              <PreviewLine label="Incoming visible" value={String(relatedEdges.filter((edge) => edge.target === activeNode.id).length)} />
              <PreviewLine label="Outgoing visible" value={String(relatedEdges.filter((edge) => edge.source === activeNode.id).length)} />
              <PreviewLine label="Expansion" value={dependencyExpansionLabel(activeNode.id, direction, seedById.get(activeNode.id), expansionByKey[expansionKey(activeNode.id)], expandingNodeId === activeNode.id)} />
            </div>
            <div className="graph-inspector-actions">
              <button className="primary wide" type="button" disabled={!activeNode.file_path} onClick={() => onOpenSource?.(activeNode)}>Open Source</button>
              {canContinueExpansion(activeNode.id, direction, seedById.get(activeNode.id), expansionByKey[expansionKey(activeNode.id)]) ? <button type="button" onClick={() => { void selectAndExpand(activeNode.id) }}>{expansionByKey[expansionKey(activeNode.id)]?.next_neighbor_offset != null ? `Load ${expansionByKey[expansionKey(activeNode.id)]?.remaining_neighbors} more` : `Show ${direction === 'incoming' ? 'dependents' : direction === 'outgoing' ? 'dependencies' : 'both directions'}`}</button> : <button type="button" disabled>No more relations</button>}
              {activeNode.coverage !== 'deep_indexed' && activeNode.coverage !== 'skipped' ? <button type="button" onClick={() => onAnalyzeArea(activeNode.scope_path || activeNode.file_path || '')}>Analyze area</button> : null}
            </div>
          </aside>
        ) : null}
      </section>
    </div>
  )
}

function ProgressiveRequestFlow({
  graph,
  projection,
  onGraphView,
  onProjection,
  onExpandNode,
  onOpenSource,
  onTraceValue,
}: GraphPageProps) {
  const [entryGraph, setEntryGraph] = useState<GraphData | null>(graph)
  const [lastEntryPage, setLastEntryPage] = useState<GraphData | null>(graph)
  const [visibleGraph, setVisibleGraph] = useState<GraphData | null>(graph)
  const [rootEntryId, setRootEntryId] = useState<string>()
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const [direction, setDirection] = useState<GraphProjectionInput['direction']>(projection.direction)
  const [zoom, setZoom] = useState(0.9)
  const [searchValue, setSearchValue] = useState('')
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [expandingNodeId, setExpandingNodeId] = useState<string>()
  const [parentByNode, setParentByNode] = useState<Record<string, string>>({})
  const [expansionByKey, setExpansionByKey] = useState<Record<string, GraphExpansion>>({})
  const [positionCache, setPositionCache] = useState(() => new Map<string, Position>())
  const viewportRef = useRef<HTMLDivElement>(null)
  const entryBatchSize = useMemo(() => requestEntryBatchSize(), [])

  if (graph && graph !== lastEntryPage && projection.projectionMode === 'seeds') {
    setLastEntryPage(graph)
    setEntryGraph((current) => projection.neighborOffset ? mergeRequestSeedPage(current, graph) : graph)
  }

  useEffect(() => {
    if (projection.projectionMode !== 'seeds' || projection.neighborOffset || (projection.seedLimit ?? 0) >= entryBatchSize) return
    onProjection({
      seedLimit: entryBatchSize,
      maxNodes: Math.max(projection.maxNodes, entryBatchSize),
      neighborOffset: 0,
    })
  }, [entryBatchSize, onProjection, projection.maxNodes, projection.neighborOffset, projection.projectionMode, projection.seedLimit])

  const allNodes = rootEntryId ? visibleGraph?.nodes ?? EMPTY_NODES : entryGraph?.nodes ?? EMPTY_NODES
  const allEdges = rootEntryId ? visibleGraph?.edges ?? EMPTY_EDGES : EMPTY_EDGES
  const pathNodeIds = useMemo(() => requestPathNodeIds(rootEntryId, parentByNode), [rootEntryId, parentByNode])
  const nodes = rootEntryId ? allNodes.filter((node) => pathNodeIds.has(node.id)) : allNodes
  const visibleIds = useMemo(() => new Set(nodes.map((node) => node.id)), [nodes])
  const edges = rootEntryId ? allEdges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)) : EMPTY_EDGES
  const nodeById = useMemo(() => new Map(allNodes.map((node) => [node.id, node])), [allNodes])
  const activeNode = nodeById.get(selectedNodeId ?? '')
  const rootNode = nodeById.get(rootEntryId ?? '')
  const layout = useMemo(
    () => buildProgressiveLayout(nodes, edges, positionCache, parentByNode),
    [nodes, edges, parentByNode, positionCache],
  )
  const requestCanvas = useGraphCanvasInteractions(layout.positions, layout, zoom, viewportRef)
  const seedById = useMemo(() => new Map((entryGraph?.seeds ?? []).map((seed) => [seed.node_id, seed])), [entryGraph?.seeds])
  const relatedEdges = activeNode ? edges.filter((edge) => edge.source === activeNode.id || edge.target === activeNode.id) : []
  const limited = graph?.coverage?.state === 'limited'
    || Object.values(expansionByKey).some((expansion) => expansion.limited)
    || Boolean(visibleGraph?.truncation?.truncated)
  const entryScope = requestEntryScope(projection.nodeTypes)
  const measured = entryGraph?.coverage?.measured ?? {}
  const entryTotal = entryGraph?.counts?.available_nodes ?? 0
  const remainingEntries = entryGraph?.additional_starting_points ?? 0

  function expansionKey(nodeId: string, requestedDirection = direction) {
    return `${nodeId}:${requestedDirection}`
  }

  function resetToEntryPoints() {
    setVisibleGraph(entryGraph)
    setRootEntryId(undefined)
    setSelectedNodeId(undefined)
    setInspectorOpen(false)
    setParentByNode({})
    setExpansionByKey({})
    setPositionCache(new Map())
    requestCanvas.resetNodePositions()
  }

  function changeDirection(value: GraphProjectionInput['direction']) {
    if (value === direction) return
    const focusNodeId = selectedNodeId ?? rootEntryId
    setDirection(value)
    if (focusNodeId) void expandFrom(focusNodeId, true, value)
  }

  function changeEntryScope(scope: 'all' | 'server' | 'client') {
    onProjection({
      projectionMode: 'seeds',
      rootKeys: [],
      nodeTypes: scope === 'server' ? ['endpoint'] : scope === 'client' ? ['api_call'] : ['endpoint', 'api_call'],
      edgeTypes: REQUEST_FLOW_EDGE_TYPES,
      direction: 'both',
      supportLevels: [],
      neighborOffset: 0,
    })
  }

  function loadMoreEntries() {
    if (!remainingEntries) return
    onProjection({
      projectionMode: 'seeds',
      seedLimit: Math.min(entryBatchSize, remainingEntries),
      maxNodes: Math.max(projection.maxNodes, entryBatchSize),
      neighborOffset: entryGraph?.nodes.length ?? 0,
    })
  }

  async function expandFrom(
    nodeId: string,
    focusPath = false,
    requestedDirection: GraphProjectionInput['direction'] = direction,
  ) {
    if (!onExpandNode || expandingNodeId) return
    const key = expansionKey(nodeId, requestedDirection)
    const prior = focusPath ? undefined : expansionByKey[key]
    if (prior?.leaf || (prior && prior.next_neighbor_offset == null)) return
    setSelectedNodeId(nodeId)
    setInspectorOpen(true)
    setExpandingNodeId(nodeId)
    const delta = await onExpandNode(nodeId, requestedDirection, prior?.next_neighbor_offset ?? 0)
    setExpandingNodeId(undefined)
    if (!delta) return
    const knownNodeIds = new Set(focusPath ? [nodeId] : allNodes.map((node) => node.id))
    const childIds = delta.nodes
      .filter((node) => node.id !== nodeId && (focusPath || !knownNodeIds.has(node.id)))
      .map((node) => node.id)
    setRootEntryId((current) => focusPath || !current ? nodeId : current)
    setParentByNode((current) => {
      const next = focusPath ? {} : { ...current }
      childIds.forEach((childId) => { next[childId] ??= nodeId })
      return next
    })
    if (delta.expansion) {
      setExpansionByKey((current) => ({ ...(focusPath ? {} : current), [key]: delta.expansion! }))
    }
    setPositionCache(focusPath ? new Map() : new Map(requestCanvas.positions))
    setVisibleGraph((current) => mergeGraphProjection(focusPath ? entryGraph : current, delta))
  }

  function selectEntry(nodeId: string) {
    void expandFrom(nodeId, true)
  }

  function selectPathNode(nodeId: string) {
    setSelectedNodeId(nodeId)
    setInspectorOpen(true)
  }

  function jumpToVisibleNode() {
    const match = nodes.find((node) => focusOptionLabel(node) === searchValue || node.label === searchValue)
    if (!match) return
    if (rootEntryId) selectPathNode(match.id)
    else selectEntry(match.id)
  }

  function fitVisibleGraph() {
    const viewport = viewportRef.current
    if (!viewport) return
    const horizontalScale = (viewport.clientWidth - 32) / layout.width
    const verticalScale = (viewport.clientHeight - 32) / layout.height
    setZoom(Math.max(0.55, Math.min(1.25, horizontalScale, verticalScale)))
    viewport.scrollTo?.({ top: 0, left: 0 })
  }

  return (
    <div className="graph-explorer-page progressive-request-flow-page">
      <PageTitle title="Request Flow" subtitle="Follow only the statically supported request path available in the active index." />

      <nav className="graph-view-nav graph-view-nav-compact" aria-label="Relationship views">
        <button type="button" className="graph-view-home" onClick={() => onGraphView('project-map')}><Icon name="grid" size={15} /> Choose question</button>
        {PRIMARY_VIEWS.map((view) => (
          <button type="button" className={view === 'api-flow' ? 'active' : ''} key={view} onClick={() => {
            if (view === 'dependencies') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: [], edgeTypes: [], dependencyScope: 'adaptive', direction: 'both', neighborOffset: 0 })
            else if (view === 'function-flow') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: CALL_FLOW_NODE_TYPES, edgeTypes: CALL_FLOW_EDGE_TYPES, direction: 'both', maxDepth: 1, seedLimit: 24, neighborOffset: 0 })
            else if (view !== 'api-flow') onProjection({ projectionMode: 'full', rootKeys: [], nodeTypes: VIEW_META[view].defaultNodeTypes, edgeTypes: VIEW_META[view].defaultEdgeTypes })
            onGraphView(view)
          }}>
            <Icon name={VIEW_META[view].icon} size={15} /> {VIEW_META[view].label}
          </button>
        ))}
      </nav>

      <section className="dependency-toolbar request-flow-toolbar" aria-label="Request flow controls">
        <div className="dependency-toolbar-title">
          <span>{rootEntryId ? 'Supported static path' : 'Request entry points'}</span>
          <strong>{rootNode ? dependencyNodeLabel(rootNode) : 'Choose where exploration starts'}</strong>
        </div>
        <label className="dependency-search">
          <span className="sr-only">Find a loaded endpoint, client call or function</span>
          <input list="request-flow-visible-nodes" value={searchValue} placeholder="Find endpoint, client call or function…" onChange={(event) => setSearchValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') jumpToVisibleNode() }} />
          <datalist id="request-flow-visible-nodes">{nodes.map((node) => <option key={node.id} value={focusOptionLabel(node)} />)}</datalist>
          <button type="button" onClick={jumpToVisibleNode}>Focus</button>
        </label>
        <div className="dependency-segmented" aria-label="Request entry-point scope">
          {(['all', 'server', 'client'] as const).map((scope) => (
            <button type="button" className={entryScope === scope ? 'active' : ''} onClick={() => changeEntryScope(scope)} key={scope}>
              {scope === 'all'
                ? `All (${Number(measured.indexed_endpoints ?? 0) + Number(measured.client_api_calls ?? 0)})`
                : scope === 'server'
                  ? `Server (${Number(measured.indexed_endpoints ?? 0)})`
                  : `Client (${Number(measured.client_api_calls ?? 0)})`}
            </button>
          ))}
        </div>
        <div className="dependency-segmented" aria-label="Request path direction">
          {(['incoming', 'outgoing', 'both'] as const).map((value) => (
            <button type="button" className={direction === value ? 'active' : ''} disabled={Boolean(expandingNodeId)} onClick={() => changeDirection(value)} key={value}>
              {value === 'incoming' ? 'Upstream' : value === 'outgoing' ? 'Downstream' : 'Supported full path'}
            </button>
          ))}
        </div>
        <details className="dependency-help">
          <summary aria-label="About request flow">?</summary>
          <div><strong>This is not a runtime trace.</strong><p>It shows only endpoint, handler and call relations supported by the active static index. Continue from a node to load one bounded hop.</p></div>
        </details>
        <button type="button" className="dependency-reset" onClick={resetToEntryPoints}><Icon name="refresh" size={14} /> Back to entry points</button>
      </section>

      <div className={`dependency-compact-status request-flow-status ${limited ? 'limited' : ''}`} role="status" aria-live="polite">
        <span><strong>{Number(measured.indexed_endpoints ?? 0)}</strong> endpoints</span>
        <span><strong>{Number(measured.resolved_handlers ?? 0)}</strong> handlers resolved</span>
        <span><strong>{Number(measured.client_api_calls ?? 0)}</strong> client calls</span>
        <span><strong>{Number(measured.matched_client_calls ?? 0)}</strong> client calls matched</span>
        {rootEntryId ? <span>{nodes.length} visible nodes · {edges.length} supported relations</span> : <span>{nodes.length} of {entryTotal} entry points loaded</span>}
        {limited ? <span>Analysis is partial; missing static support does not prove the runtime path is absent.</span> : null}
      </div>

      <div className="request-flow-breadcrumb" aria-label="Current request path">
        <span>Request Flow</span><span>/</span><strong>{rootNode ? dependencyNodeLabel(rootNode) : 'Entry points'}</strong>
        {activeNode && activeNode.id !== rootNode?.id ? <><span>/</span><strong>{dependencyNodeLabel(activeNode)}</strong></> : null}
      </div>

      {!rootEntryId ? <section className="request-entry-browser-summary" aria-label="Entry point browser status">
        <div><strong>{nodes.length} of {entryTotal}</strong><span>{entryScope === 'all' ? 'all entry points' : entryScope === 'server' ? 'server endpoints' : 'client calls'} loaded in deterministic order</span></div>
        {remainingEntries
          ? <button type="button" onClick={loadMoreEntries}>Load next {Math.min(entryBatchSize, remainingEntries)}</button>
          : <span>All indexed entries in this scope are loaded</span>}
      </section> : null}

      <section className={`dependency-stage-shell request-flow-stage ${inspectorOpen ? 'inspector-open' : ''}`} aria-label="Progressive request flow graph">
        <div className="graph-stage-tools dependency-stage-tools">
          <div className="graph-edge-legend" aria-label="Visible request relations">
            <strong>Visible arrows</strong>
            {edges.length ? unique(edges.map((edge) => flowRelationLabel(edge.type))).map((label) => <span key={label}>{label}</span>) : <span>Select an entry point to reveal a supported path</span>}
          </div>
          <div className="graph-zoom" aria-label="Graph zoom controls">
            <button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.55, value - 0.1))}>−</button>
            <output aria-label="Current zoom">{Math.round(zoom * 100)}%</output>
            <button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.25, value + 0.1))}>+</button>
            <button type="button" onClick={fitVisibleGraph}>Fit visible</button>
          </div>
        </div>

        {!nodes.length ? <div className="dependency-empty" role="status"><Icon name="route" size={24} /><h2>No supported request entry point</h2><p>The active index did not return an endpoint or client API call for this scope.</p></div> : (
          <div className={`graph-stage-viewport dependency-stage-viewport interactive-graph-viewport ${requestCanvas.panning ? 'panning' : ''}`} ref={viewportRef} {...requestCanvas.viewportPointerHandlers} role="region" tabIndex={0} aria-label="Pannable request canvas. Drag empty space to pan; drag nodes to reposition.">
            <div className="dependency-canvas-scale" style={{ width: layout.width * zoom, height: layout.height * zoom }}>
              <div className="graph-canvas graph-progressive-canvas" aria-label="Request flow nodes" style={{ width: layout.width, height: layout.height, transform: `scale(${zoom})` }}>
                <svg className="graph-edges" width={layout.width} height={layout.height} role="img" aria-label={`${edges.length} supported request relationships`}>
                  <defs><marker id="request-flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" /></marker></defs>
                  {edges.map((edge, index) => {
                    const source = requestCanvas.positions.get(edge.source)
                    const target = requestCanvas.positions.get(edge.target)
                    if (!source || !target) return null
                    const active = Boolean(activeNode && (edge.source === activeNode.id || edge.target === activeNode.id))
                    return <path className={`graph-edge support-${edge.evidence_level ?? 'deep'} ${active ? 'active' : ''}`} d={dependencyEdgePath(source, target, edgeLaneOffset(edge, edges))} key={`${edge.source}-${edge.target}-${edge.type}-${index}`} markerEnd="url(#request-flow-arrow)"><title>{dependencyNodeLabel(nodeById.get(edge.source)!)} {flowRelationLabel(edge.type)} {dependencyNodeLabel(nodeById.get(edge.target)!)}</title></path>
                  })}
                </svg>
                {nodes.map((node) => {
                  const position = requestCanvas.positions.get(node.id)
                  if (!position) return null
                  const seed = seedById.get(node.id)
                  const expansion = expansionByKey[expansionKey(node.id)]
                  return <button type="button" className={`graph-node graph-layer-node dependency-node request-flow-node draggable-graph-node type-${node.type} ${activeNode?.id === node.id ? 'active' : ''}`} style={{ left: position.x, top: position.y } as CSSProperties} key={node.id} {...requestCanvas.nodePointerHandlers(node.id, position)} onClick={() => { if (requestCanvas.consumeDraggedClick(node.id)) return; if (rootEntryId) selectPathNode(node.id); else selectEntry(node.id) }} aria-pressed={activeNode?.id === node.id}>
                    <span className="graph-node-type"><Icon name={nodeIcon(node)} size={12} /> {flowNodeType(node, rootEntryId)}</span>
                    <strong>{dependencyNodeLabel(node)}</strong>
                    <small title={node.file_path || node.scope_path || undefined}>{seed && !rootEntryId ? flowSeedReasonLabel(seed) : node.file_path || node.scope_path || node.role || 'Indexed request entity'}</small>
                    <em className="dependency-node-state">{rootEntryId ? flowExpansionLabel(node, direction, seed, expansion, expandingNodeId === node.id) : 'Select to explore path'}</em>
                  </button>
                })}
              </div>
            </div>
          </div>
        )}

        <details className="graph-relation-list dependency-relation-list">
          <summary>Relations ({edges.length}) <span>Keyboard and screen-reader alternative</span></summary>
          {edges.length ? <ul>{edges.map((edge, index) => <li key={`${edge.source}-${edge.target}-${edge.type}-${index}`}><button type="button" onClick={() => selectPathNode(edge.source)}>{dependencyNodeLabel(nodeById.get(edge.source)!)}</button><span>→ {flowRelationLabel(edge.type)} · {supportLabel(edge.evidence_level)} →</span><button type="button" onClick={() => selectPathNode(edge.target)}>{dependencyNodeLabel(nodeById.get(edge.target)!)}</button></li>)}</ul> : <p>No supported path relation has been expanded yet.</p>}
        </details>

        {inspectorOpen && activeNode ? <aside className="graph-inspector dependency-inspector request-flow-inspector" aria-label="Selected request flow entity">
          <button type="button" className="dependency-inspector-close" aria-label="Close selected entity" onClick={() => setInspectorOpen(false)}>×</button>
          <div className="graph-inspector-title"><div className={`graph-entity-mark type-${activeNode.type}`} aria-hidden="true" /><div><span>{flowNodeType(activeNode, rootEntryId)}</span><h2>{dependencyNodeLabel(activeNode)}</h2></div></div>
          <p className="graph-source-path">{activeNode.file_path || activeNode.scope_path || 'No repository source target was resolved'}</p>
          <div className="graph-inspector-section">
            <p>{activeNode.type === 'endpoint' ? 'Indexed server endpoint. Outgoing support may route to a resolved handler.' : activeNode.type === 'api_call' ? 'Detected client API call. A matched endpoint is compatibility evidence, not a runtime trace.' : 'Callable participating in the currently supported static request path.'}</p>
            <PreviewLine label="Upstream visible" value={String(relatedEdges.filter((edge) => edge.target === activeNode.id).length)} />
            <PreviewLine label="Downstream visible" value={String(relatedEdges.filter((edge) => edge.source === activeNode.id).length)} />
            <PreviewLine label="Path support" value={flowExpansionLabel(activeNode, direction, seedById.get(activeNode.id), expansionByKey[expansionKey(activeNode.id)], expandingNodeId === activeNode.id)} />
            <PreviewLine label="Index version" value={String(graph?.index_version ?? projection.indexVersion ?? 'active')} />
          </div>
          <div className="graph-inspector-actions">
            <button className="primary wide" type="button" disabled={!activeNode.file_path} onClick={() => onOpenSource?.(activeNode)}>Open Source</button>
            <button type="button" disabled={!activeNode.file_path || !activeNode.start_line} onClick={() => activeNode.file_path && activeNode.start_line && onTraceValue?.({ kind: 'scope', filePath: activeNode.file_path, startLine: activeNode.start_line, endLine: activeNode.end_line, label: dependencyNodeLabel(activeNode) })}><Icon name="share" size={13} /> Trace values in this scope</button>
            {canContinueExpansion(activeNode.id, direction, seedById.get(activeNode.id), expansionByKey[expansionKey(activeNode.id)]) ? <button type="button" onClick={() => { void expandFrom(activeNode.id) }}>Continue from here</button> : <button type="button" disabled>{flowTerminalLabel(activeNode, direction, seedById.get(activeNode.id))}</button>}
            {activeNode.id !== rootEntryId ? <button type="button" onClick={() => { void expandFrom(activeNode.id, true) }}>Focus path here</button> : null}
          </div>
        </aside> : null}
      </section>
    </div>
  )
}

function ProgressiveCallFlow({
  graph,
  projection,
  onGraphView,
  onProjection,
  onExpandNode,
  onOpenSource,
  onTraceValue,
}: GraphPageProps) {
  const [entryGraph, setEntryGraph] = useState<GraphData | null>(graph)
  const [lastEntryPage, setLastEntryPage] = useState<GraphData | null>(graph)
  const [visibleGraph, setVisibleGraph] = useState<GraphData | null>(graph)
  const [rootId, setRootId] = useState<string>()
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const [selectedEdgeKey, setSelectedEdgeKey] = useState<string>()
  const [direction, setDirection] = useState<GraphProjectionInput['direction']>(projection.direction)
  const [searchValue, setSearchValue] = useState('')
  const [zoom, setZoom] = useState(0.9)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [expandingNodeId, setExpandingNodeId] = useState<string>()
  const [parentByNode, setParentByNode] = useState<Record<string, string>>({})
  const [expansionByKey, setExpansionByKey] = useState<Record<string, GraphExpansion>>({})
  const [positionCache, setPositionCache] = useState(() => new Map<string, Position>())
  const viewportRef = useRef<HTMLDivElement>(null)
  const entryBatchSize = useMemo(() => requestEntryBatchSize(), [])

  if (graph && graph !== lastEntryPage && projection.projectionMode === 'seeds') {
    setLastEntryPage(graph)
    setEntryGraph((current) => projection.neighborOffset ? mergeRequestSeedPage(current, graph) : graph)
  }

  useEffect(() => {
    if (projection.projectionMode !== 'seeds' || projection.neighborOffset || (projection.seedLimit ?? 0) >= entryBatchSize) return
    onProjection({ seedLimit: entryBatchSize, maxNodes: Math.max(projection.maxNodes, entryBatchSize), neighborOffset: 0 })
  }, [entryBatchSize, onProjection, projection.maxNodes, projection.neighborOffset, projection.projectionMode, projection.seedLimit])

  const nodes = rootId ? visibleGraph?.nodes ?? EMPTY_NODES : entryGraph?.nodes ?? EMPTY_NODES
  const edges = rootId ? visibleGraph?.edges ?? EMPTY_EDGES : EMPTY_EDGES
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes])
  const activeNode = nodeById.get(selectedNodeId ?? '')
  const rootNode = nodeById.get(rootId ?? '')
  const activeEdge = edges.find((edge) => graphEdgeKey(edge) === selectedEdgeKey)
  const seedById = useMemo(() => new Map((entryGraph?.seeds ?? []).map((seed) => [seed.node_id, seed])), [entryGraph?.seeds])
  const layout = useMemo(() => buildProgressiveLayout(nodes, edges, positionCache, parentByNode), [nodes, edges, parentByNode, positionCache])
  const callCanvas = useGraphCanvasInteractions(layout.positions, layout, zoom, viewportRef)
  const relatedEdges = activeNode ? edges.filter((edge) => edge.source === activeNode.id || edge.target === activeNode.id) : []
  const measured = entryGraph?.coverage?.measured ?? {}
  const entryTotal = entryGraph?.counts?.available_nodes ?? 0
  const remainingEntries = entryGraph?.additional_starting_points ?? 0
  const limited = entryGraph?.coverage?.state === 'limited'
    || Boolean(visibleGraph?.truncation?.truncated)
    || Object.values(expansionByKey).some((expansion) => expansion.limited)

  function expansionKey(nodeId: string, requestedDirection = direction) {
    return `${nodeId}:${requestedDirection}`
  }

  function resetToCallables() {
    setVisibleGraph(entryGraph)
    setRootId(undefined)
    setSelectedNodeId(undefined)
    setSelectedEdgeKey(undefined)
    setInspectorOpen(false)
    setParentByNode({})
    setExpansionByKey({})
    setPositionCache(new Map())
    callCanvas.resetNodePositions()
  }

  async function expandFrom(
    nodeId: string,
    focusHere = false,
    requestedDirection: GraphProjectionInput['direction'] = direction,
  ) {
    if (!onExpandNode || expandingNodeId) return
    const key = expansionKey(nodeId, requestedDirection)
    const prior = focusHere ? undefined : expansionByKey[key]
    if (prior?.leaf || (prior && prior.next_neighbor_offset == null)) return
    setSelectedNodeId(nodeId)
    setSelectedEdgeKey(undefined)
    setInspectorOpen(true)
    setExpandingNodeId(nodeId)
    const delta = await onExpandNode(nodeId, requestedDirection, prior?.next_neighbor_offset ?? 0)
    setExpandingNodeId(undefined)
    if (!delta) return
    const knownNodeIds = new Set(focusHere ? [nodeId] : nodes.map((node) => node.id))
    const childIds = delta.nodes.filter((node) => node.id !== nodeId && !knownNodeIds.has(node.id)).map((node) => node.id)
    setRootId((current) => focusHere || !current ? nodeId : current)
    setParentByNode((current) => {
      const next = focusHere ? {} : { ...current }
      childIds.forEach((childId) => { next[childId] ??= nodeId })
      return next
    })
    if (delta.expansion) setExpansionByKey((current) => ({ ...(focusHere ? {} : current), [key]: delta.expansion! }))
    setPositionCache(focusHere ? new Map() : new Map(callCanvas.positions))
    setVisibleGraph((current) => mergeGraphProjection(focusHere ? null : current, delta))
  }

  function changeDirection(value: GraphProjectionInput['direction']) {
    if (value === direction) return
    setDirection(value)
    const focusNodeId = selectedNodeId ?? rootId
    if (focusNodeId) void expandFrom(focusNodeId, true, value)
  }

  function selectNode(nodeId: string) {
    setSelectedNodeId(nodeId)
    setSelectedEdgeKey(undefined)
    setInspectorOpen(true)
  }

  function selectEdge(edge: GraphEdge) {
    setSelectedEdgeKey(graphEdgeKey(edge))
    setSelectedNodeId(undefined)
    setInspectorOpen(true)
  }

  function jumpToCallable() {
    const match = nodes.find((node) => focusOptionLabel(node) === searchValue || node.label === searchValue)
    if (!match) return
    if (rootId) selectNode(match.id)
    else void expandFrom(match.id, true)
  }

  function loadMoreEntries() {
    if (!remainingEntries) return
    onProjection({
      projectionMode: 'seeds',
      seedLimit: Math.min(entryBatchSize, remainingEntries),
      maxNodes: Math.max(projection.maxNodes, entryBatchSize),
      neighborOffset: entryGraph?.nodes.length ?? 0,
    })
  }

  function fitVisibleGraph() {
    const viewport = viewportRef.current
    if (!viewport) return
    const horizontalScale = (viewport.clientWidth - 32) / layout.width
    const verticalScale = (viewport.clientHeight - 32) / layout.height
    setZoom(Math.max(0.55, Math.min(1.25, horizontalScale, verticalScale)))
    viewport.scrollTo?.({ top: 0, left: 0 })
  }

  return (
    <div className="graph-explorer-page progressive-request-flow-page progressive-call-flow-page">
      <PageTitle title="Call Flow" subtitle="Investigate statically supported callers and callees around one function or method." />

      <nav className="graph-view-nav graph-view-nav-compact" aria-label="Relationship views">
        <button type="button" className="graph-view-home" onClick={() => onGraphView('project-map')}><Icon name="grid" size={15} /> Choose question</button>
        {PRIMARY_VIEWS.map((view) => (
          <button type="button" className={view === 'function-flow' ? 'active' : ''} key={view} onClick={() => {
            if (view === 'dependencies') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: [], edgeTypes: [], dependencyScope: 'adaptive', direction: 'both', neighborOffset: 0 })
            else if (view === 'api-flow') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: ['endpoint', 'api_call'], edgeTypes: REQUEST_FLOW_EDGE_TYPES, direction: 'both', seedLimit: 12, neighborOffset: 0 })
            onGraphView(view)
          }}><Icon name={VIEW_META[view].icon} size={15} /> {VIEW_META[view].label}</button>
        ))}
      </nav>

      <section className="dependency-toolbar request-flow-toolbar call-flow-toolbar" aria-label="Call flow controls">
        <div className="dependency-toolbar-title"><span>{rootId ? 'Focused call graph' : 'Indexed callables'}</span><strong>{rootNode ? dependencyNodeLabel(rootNode) : 'Choose a function or method'}</strong></div>
        <label className="dependency-search">
          <span className="sr-only">Find a loaded function or method</span>
          <input list="call-flow-visible-nodes" value={searchValue} placeholder="Search function or method…" onChange={(event) => setSearchValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') jumpToCallable() }} />
          <datalist id="call-flow-visible-nodes">{nodes.filter((node) => ['function', 'method'].includes(node.type)).map((node) => <option key={node.id} value={focusOptionLabel(node)} />)}</datalist>
          <button type="button" onClick={jumpToCallable}>Focus</button>
        </label>
        <div className="dependency-segmented" aria-label="Call direction">
          {(['outgoing', 'incoming', 'both'] as const).map((value) => <button type="button" className={direction === value ? 'active' : ''} disabled={Boolean(expandingNodeId)} onClick={() => changeDirection(value)} key={value}>{value === 'outgoing' ? 'Calls' : value === 'incoming' ? 'Called by' : 'Both'}</button>)}
        </div>
        <details className="dependency-help"><summary aria-label="About call flow">?</summary><div><strong>This is a supported static call graph.</strong><p>It does not prove runtime order, branch execution, production use, or the absence of dynamic calls.</p></div></details>
        <button type="button" className="dependency-reset" onClick={resetToCallables}><Icon name="refresh" size={14} /> Back to callables</button>
      </section>

      <div className={`dependency-compact-status request-flow-status call-flow-status ${limited ? 'limited' : ''}`} role="status" aria-live="polite">
        <span><strong>{Number(measured.indexed_callables ?? entryTotal)}</strong> indexed functions/methods</span>
        <span><strong>{Number(measured.resolved_call_relations ?? 0)}</strong> resolved calls</span>
        <span><strong>{Number(measured.external_call_relations ?? 0)}</strong> external/library calls</span>
        <span><strong>{Number(measured.unresolved_call_relations ?? 0)}</strong> unresolved calls</span>
        <span><strong>{Number(measured.direct_recursive_callables ?? 0)}</strong> directly recursive</span>
        {rootId ? <span>{nodes.length} visible nodes · {edges.length} supported relations</span> : <span>{nodes.length} of {entryTotal} callables loaded</span>}
        {limited ? <span>Coverage is partial; no static edge is not proof that no runtime call exists.</span> : null}
      </div>

      {!rootId ? <section className="request-entry-browser-summary" aria-label="Callable browser status"><div><strong>{nodes.length} of {entryTotal}</strong><span>evidence-ranked callables loaded in deterministic order</span></div>{remainingEntries ? <button type="button" onClick={loadMoreEntries}>Load next {Math.min(entryBatchSize, remainingEntries)}</button> : <span>All indexed callables are loaded</span>}</section> : null}

      <section className={`dependency-stage-shell request-flow-stage call-flow-stage ${inspectorOpen ? 'inspector-open' : ''}`} aria-label="Progressive call flow graph">
        <div className="graph-stage-tools dependency-stage-tools">
          <div className="graph-edge-legend" aria-label="Visible call relations"><strong>Visible arrows</strong>{edges.length ? unique(edges.map((edge) => callRelationLabel(edge.type))).map((label) => <span key={label}>{label}</span>) : <span>{rootId ? 'No supported call relation in this bounded result' : 'Select a callable to reveal callers and callees'}</span>}</div>
          <div className="graph-zoom" aria-label="Graph zoom controls"><button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.55, value - 0.1))}>−</button><output aria-label="Current zoom">{Math.round(zoom * 100)}%</output><button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.25, value + 0.1))}>+</button><button type="button" onClick={fitVisibleGraph}>Fit visible</button></div>
        </div>

        {!nodes.length ? <div className="dependency-empty" role="status"><Icon name="braces" size={24} /><h2>No indexed callable is available</h2><p>The active index did not return a function or method for this scope.</p></div> : (
          <div className={`graph-stage-viewport dependency-stage-viewport interactive-graph-viewport ${callCanvas.panning ? 'panning' : ''}`} ref={viewportRef} {...callCanvas.viewportPointerHandlers} role="region" tabIndex={0} aria-label="Pannable call canvas. Drag empty space to pan; drag nodes to reposition.">
            <div className="dependency-canvas-scale" style={{ width: layout.width * zoom, height: layout.height * zoom }}>
              <div className="graph-canvas graph-progressive-canvas" aria-label="Call flow nodes" style={{ width: layout.width, height: layout.height, transform: `scale(${zoom})` }}>
                <svg className="graph-edges" width={layout.width} height={layout.height} role="img" aria-label={`${edges.length} supported call relationships`}>
                  <defs><marker id="call-flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" /></marker></defs>
                  {edges.map((edge, index) => {
                    const source = callCanvas.positions.get(edge.source)
                    const target = callCanvas.positions.get(edge.target)
                    if (!source || !target) return null
                    const selected = graphEdgeKey(edge) === selectedEdgeKey
                    return <path role="button" tabIndex={0} aria-label={`${dependencyNodeLabel(nodeById.get(edge.source)!)} ${callRelationLabel(edge.type)} ${dependencyNodeLabel(nodeById.get(edge.target)!)}`} className={`graph-edge call-flow-edge support-${edge.evidence_level ?? 'deep'} ${selected ? 'active' : ''} ${edge.type === 'calls_unresolved' ? 'unresolved' : ''}`} d={dependencyEdgePath(source, target, edgeLaneOffset(edge, edges))} key={`${graphEdgeKey(edge)}-${index}`} markerEnd="url(#call-flow-arrow)" onClick={() => selectEdge(edge)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectEdge(edge) } }}><title>{dependencyNodeLabel(nodeById.get(edge.source)!)} {callRelationLabel(edge.type)} {dependencyNodeLabel(nodeById.get(edge.target)!)}</title></path>
                  })}
                </svg>
                {nodes.map((node) => {
                  const position = callCanvas.positions.get(node.id)
                  if (!position) return null
                  const expansion = expansionByKey[expansionKey(node.id)]
                  const seed = seedById.get(node.id)
                  return <button type="button" className={`graph-node graph-layer-node dependency-node request-flow-node call-flow-node draggable-graph-node type-${node.type} ${activeNode?.id === node.id ? 'active' : ''} ${rootId === node.id ? 'root' : ''}`} style={{ left: position.x, top: position.y } as CSSProperties} key={node.id} {...callCanvas.nodePointerHandlers(node.id, position)} onClick={() => { if (callCanvas.consumeDraggedClick(node.id)) return; if (rootId) selectNode(node.id); else void expandFrom(node.id, true) }} aria-label={`${callNodeType(node, rootId === node.id)} ${dependencyNodeLabel(node)}`} aria-pressed={activeNode?.id === node.id}>
                    <span className="graph-node-type"><Icon name={nodeIcon(node)} size={12} /> {callNodeType(node, rootId === node.id)}</span>
                    <strong>{dependencyNodeLabel(node)}</strong>
                    <small title={node.file_path || node.scope_path || undefined}>{seed && !rootId ? callSeedReasonLabel(seed) : node.file_path || node.scope_path || callRelationTargetLabel(node)}</small>
                    <em className="dependency-node-state">{rootId ? callExpansionLabel(node, direction, seed, expansion, expandingNodeId === node.id) : 'Select to explore callers and callees'}</em>
                  </button>
                })}
              </div>
            </div>
          </div>
        )}

        <details className="graph-relation-list dependency-relation-list"><summary>Relations ({edges.length}) <span>Keyboard and screen-reader alternative</span></summary>{edges.length ? <ul>{edges.map((edge, index) => <li key={`${graphEdgeKey(edge)}-${index}`}><button type="button" onClick={() => selectNode(edge.source)}>{dependencyNodeLabel(nodeById.get(edge.source)!)}</button><button type="button" className="call-relation-button" onClick={() => selectEdge(edge)}>→ {callRelationLabel(edge.type)} · {supportLabel(edge.evidence_level)} →</button><button type="button" onClick={() => selectNode(edge.target)}>{dependencyNodeLabel(nodeById.get(edge.target)!)}</button></li>)}</ul> : <p>No supported call relation has been expanded. This does not prove that no runtime call exists.</p>}</details>

        {inspectorOpen && activeEdge ? <CallEdgeInspector edge={activeEdge} nodeById={nodeById} graph={visibleGraph} onClose={() => setInspectorOpen(false)} onOpenSource={onOpenSource} /> : null}
        {inspectorOpen && activeNode ? <aside className="graph-inspector dependency-inspector request-flow-inspector call-flow-inspector" aria-label="Selected call flow entity">
          <button type="button" className="dependency-inspector-close" aria-label="Close selected entity" onClick={() => setInspectorOpen(false)}>×</button>
          <div className="graph-inspector-title"><div className={`graph-entity-mark type-${activeNode.type}`} aria-hidden="true" /><div><span>{callNodeType(activeNode, activeNode.id === rootId)}</span><h2>{dependencyNodeLabel(activeNode)}</h2></div></div>
          <p className="graph-source-path">{sourceRangeLabel(activeNode)}</p>
          <div className="graph-inspector-section">
            <p>{callNodeDescription(activeNode)}</p>
            <PreviewLine label="Direct callers visible" value={String(relatedEdges.filter((edge) => edge.target === activeNode.id).length)} />
            <PreviewLine label="Direct callees visible" value={String(relatedEdges.filter((edge) => edge.source === activeNode.id).length)} />
            <PreviewLine label="Recursive signal" value={isNodeInCallCycle(activeNode.id, edges) ? 'Visible call cycle' : 'None in visible projection'} />
            <PreviewLine label="Support scope" value={limited ? 'Bounded / partial static index' : 'Current bounded static projection'} />
            <PreviewLine label="Index version" value={String(visibleGraph?.index_version ?? projection.indexVersion ?? 'active')} />
          </div>
          <div className="graph-inspector-actions"><button className="primary wide" type="button" disabled={!activeNode.file_path} onClick={() => onOpenSource?.(activeNode)}>Open Source</button><button type="button" disabled={!activeNode.file_path || !activeNode.start_line} onClick={() => activeNode.file_path && activeNode.start_line && onTraceValue?.({ kind: 'scope', filePath: activeNode.file_path, startLine: activeNode.start_line, endLine: activeNode.end_line, label: dependencyNodeLabel(activeNode) })}><Icon name="share" size={13} /> Trace values in this function</button>{canContinueExpansion(activeNode.id, direction, seedById.get(activeNode.id), expansionByKey[expansionKey(activeNode.id)]) ? <button type="button" onClick={() => { void expandFrom(activeNode.id) }}>Continue from here</button> : <button type="button" disabled>{callTerminalLabel(direction)}</button>}{activeNode.id !== rootId && ['function', 'method'].includes(activeNode.type) ? <button type="button" onClick={() => { void expandFrom(activeNode.id, true) }}>Focus here</button> : null}</div>
        </aside> : null}
      </section>
    </div>
  )
}

function CallEdgeInspector({ edge, nodeById, graph, onClose, onOpenSource }: { edge: GraphEdge; nodeById: Map<string, GraphNode>; graph: GraphData | null; onClose: () => void; onOpenSource?: (node: GraphNode) => void }) {
  const caller = nodeById.get(edge.source)
  const callee = nodeById.get(edge.target)
  const evidenceNode = caller?.file_path ? caller : callee
  return <aside className="graph-inspector dependency-inspector request-flow-inspector call-flow-inspector" aria-label="Selected call relation">
    <button type="button" className="dependency-inspector-close" aria-label="Close selected relation" onClick={onClose}>×</button>
    <div className="graph-inspector-title"><div className="graph-entity-mark type-call_site" aria-hidden="true" /><div><span>{callRelationLabel(edge.type)}</span><h2>{caller?.label ?? edge.source} → {callee?.label ?? edge.target}</h2></div></div>
    <div className="graph-inspector-section">
      <PreviewLine label="Caller" value={caller?.label ?? edge.source} />
      <PreviewLine label="Callee / target" value={callee?.label ?? edge.target} />
      <PreviewLine label="Source evidence" value={edgeEvidenceLocation(edge, caller)} />
      {edge.metadata?.expression ? <PreviewLine label="Expression" value={edge.metadata.expression} /> : null}
      <PreviewLine label="Resolution" value={callResolutionLabel(edge)} />
      <PreviewLine label="Support" value={supportLabel(edge.evidence_level)} />
      <PreviewLine label="Provenance" value={readableType(graph?.provenance?.source ?? 'not reported')} />
      <PreviewLine label="Index version" value={String(graph?.index_version ?? 'active')} />
      <p>Support labels describe indexed static evidence; they are not runtime observations or calibrated probabilities.</p>
    </div>
    <div className="graph-inspector-actions"><button className="primary wide" type="button" disabled={!evidenceNode?.file_path} onClick={() => evidenceNode && onOpenSource?.(evidenceNode)}>Open Source Evidence</button></div>
  </aside>
}

function ProgressiveValueFlow({
  graph,
  projection,
  onGraphView,
  onProjection,
  onExpandNode,
  onOpenSource,
  embedded = false,
  onCloseEmbedded,
  onOpenFullGraph,
  onReturnToSource,
}: GraphPageProps) {
  const [entryGraph, setEntryGraph] = useState<GraphData | null>(graph)
  const [lastEntryPage, setLastEntryPage] = useState<GraphData | null>(graph)
  const [visibleGraph, setVisibleGraph] = useState<GraphData | null>(graph)
  const [rootId, setRootId] = useState<string>()
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const [selectedEdgeKey, setSelectedEdgeKey] = useState<string>()
  const [direction, setDirection] = useState<GraphProjectionInput['direction']>(projection.direction)
  const [searchValue, setSearchValue] = useState('')
  const [zoom, setZoom] = useState(0.9)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [embeddedCollapsed, setEmbeddedCollapsed] = useState(false)
  const [expandingNodeId, setExpandingNodeId] = useState<string>()
  const [expansionByKey, setExpansionByKey] = useState<Record<string, GraphExpansion>>({})
  const [positionCache, setPositionCache] = useState(() => new Map<string, Position>())
  const viewportRef = useRef<HTMLDivElement>(null)

  if (graph && graph !== lastEntryPage && projection.projectionMode === 'seeds') {
    setLastEntryPage(graph)
    setEntryGraph((current) => projection.neighborOffset ? mergeRequestSeedPage(current, graph) : graph)
  }

  const nodes = rootId ? visibleGraph?.nodes ?? EMPTY_NODES : entryGraph?.nodes ?? EMPTY_NODES
  const edges = rootId ? visibleGraph?.edges ?? EMPTY_EDGES : EMPTY_EDGES
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes])
  const activeNode = nodeById.get(selectedNodeId ?? '')
  const activeEdge = edges.find((edge) => graphEdgeKey(edge) === selectedEdgeKey)
  const rootNode = nodeById.get(rootId ?? '')
  const seedById = useMemo(() => new Map((entryGraph?.seeds ?? []).map((seed) => [seed.node_id, seed])), [entryGraph?.seeds])
  const layout = useMemo(() => buildValueFlowLayout(nodes, edges, rootId, positionCache), [nodes, edges, rootId, positionCache])
  const valueCanvas = useGraphCanvasInteractions(layout.positions, layout, zoom, viewportRef)
  const relatedEdges = activeNode ? edges.filter((edge) => edge.source === activeNode.id || edge.target === activeNode.id) : []
  const measured = entryGraph?.coverage?.measured ?? {}
  const entryTotal = entryGraph?.counts?.available_nodes ?? 0
  const traceContext = projection.rootKeys[0]
  const hasTraceContext = Boolean(traceContext)
  const hasBoundedInterproceduralSupport = entryGraph?.coverage?.unknown?.includes('interprocedural_value_flow_limited') ?? false
  const entryBatchSize = requestEntryBatchSize()
  const remainingEntries = entryGraph?.additional_starting_points ?? 0
  const limited = entryGraph?.coverage?.state === 'limited'
    || Boolean(visibleGraph?.truncation?.truncated)
    || Object.values(expansionByKey).some((expansion) => expansion.limited)

  function expansionKey(nodeId: string, requestedDirection = direction) {
    return `${nodeId}:${requestedDirection}`
  }

  function resetToContext() {
    setVisibleGraph(entryGraph)
    setRootId(undefined)
    setSelectedNodeId(undefined)
    setSelectedEdgeKey(undefined)
    setInspectorOpen(false)
    setExpansionByKey({})
    setPositionCache(new Map())
    valueCanvas.resetNodePositions()
  }

  async function expandFrom(
    nodeId: string,
    focusHere = false,
    requestedDirection: GraphProjectionInput['direction'] = direction,
  ) {
    if (!onExpandNode || expandingNodeId) return
    const key = expansionKey(nodeId, requestedDirection)
    const prior = focusHere ? undefined : expansionByKey[key]
    if (prior?.leaf || (prior && prior.next_neighbor_offset == null)) return
    setSelectedNodeId(nodeId)
    setSelectedEdgeKey(undefined)
    setInspectorOpen(true)
    setExpandingNodeId(nodeId)
    const delta = await onExpandNode(nodeId, requestedDirection, prior?.next_neighbor_offset ?? 0)
    setExpandingNodeId(undefined)
    if (!delta) return
    setRootId((current) => focusHere || !current ? nodeId : current)
    if (delta.expansion) setExpansionByKey((current) => ({ ...(focusHere ? {} : current), [key]: delta.expansion! }))
    setPositionCache(focusHere ? new Map() : new Map(valueCanvas.positions))
    setVisibleGraph((current) => mergeGraphProjection(focusHere ? null : current, delta))
  }

  function changeDirection(value: GraphProjectionInput['direction']) {
    if (value === direction) return
    setDirection(value)
    const focusNodeId = selectedNodeId ?? rootId
    if (focusNodeId) void expandFrom(focusNodeId, true, value)
  }

  function selectNode(nodeId: string) {
    setSelectedNodeId(nodeId)
    setSelectedEdgeKey(undefined)
    setInspectorOpen(true)
  }

  function selectEdge(edge: GraphEdge) {
    setSelectedEdgeKey(graphEdgeKey(edge))
    setSelectedNodeId(undefined)
    setInspectorOpen(true)
  }

  function jumpToValue() {
    const match = nodes.find((node) => valueOptionLabel(node) === searchValue || valueNodeName(node) === searchValue)
    if (!match) return
    if (rootId) selectNode(match.id)
    else void expandFrom(match.id, true)
  }

  function loadMoreEntries() {
    if (!remainingEntries) return
    onProjection({
      projectionMode: 'seeds',
      seedLimit: Math.min(entryBatchSize, remainingEntries),
      maxNodes: Math.max(projection.maxNodes, entryBatchSize),
      neighborOffset: entryGraph?.nodes.length ?? 0,
    })
  }

  function fitVisibleGraph() {
    const viewport = viewportRef.current
    if (!viewport) return
    const horizontalScale = (viewport.clientWidth - 32) / layout.width
    const verticalScale = (viewport.clientHeight - 32) / layout.height
    setZoom(Math.max(0.55, Math.min(1.25, horizontalScale, verticalScale)))
    viewport.scrollTo?.({ top: 0, left: 0 })
  }

  return <div className={`graph-explorer-page progressive-request-flow-page progressive-value-flow-page ${embedded ? 'embedded-value-trace' : ''} ${embeddedCollapsed ? 'embedded-collapsed' : ''} ${hasTraceContext ? '' : 'value-trace-no-context'}`}>
    {embedded ? <div className="embedded-value-trace-header"><div><span>Source investigation</span><h2>Value Trace</h2></div><div><button type="button" aria-expanded={!embeddedCollapsed} aria-label={embeddedCollapsed ? 'Expand embedded value trace' : 'Collapse embedded value trace'} onClick={() => setEmbeddedCollapsed((value) => !value)}>{embeddedCollapsed ? 'Expand' : 'Minimize'}</button><button type="button" onClick={onOpenFullGraph}><Icon name="expand" size={13} /> Open full graph</button><button type="button" aria-label="Close embedded value trace" title="Close Value Trace" onClick={onCloseEmbedded}>×</button></div></div> : <PageTitle title="Value Trace" subtitle="Investigate one source value or callable scope without browsing every indexed variable." />}

    {embedded && embeddedCollapsed ? <div className="embedded-value-trace-summary" role="status"><strong>{rootNode ? valueNodeName(rootNode) : hasTraceContext ? valueTraceContextLabel(traceContext) : 'No value selected'}</strong><span>{nodes.length} visible values · {edges.length} relations</span></div> : null}

    {!embedded ? <nav className="graph-view-nav graph-view-nav-compact" aria-label="Relationship views">
      <button type="button" className="graph-view-home" onClick={() => onGraphView('project-map')}><Icon name="grid" size={15} /> Choose question</button>
      {PRIMARY_VIEWS.map((view) => <button type="button" key={view} onClick={() => {
        if (view === 'dependencies') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: [], edgeTypes: [], dependencyScope: 'adaptive', direction: 'both', neighborOffset: 0 })
        else if (view === 'api-flow') onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: ['endpoint', 'api_call'], edgeTypes: REQUEST_FLOW_EDGE_TYPES, direction: 'both', seedLimit: 12, neighborOffset: 0 })
        else onProjection({ projectionMode: 'seeds', rootKeys: [], nodeTypes: CALL_FLOW_NODE_TYPES, edgeTypes: CALL_FLOW_EDGE_TYPES, direction: 'both', maxDepth: 1, seedLimit: 24, neighborOffset: 0 })
        onGraphView(view)
      }}><Icon name={VIEW_META[view].icon} size={15} /> {VIEW_META[view].label}</button>)}
    </nav> : null}

    <section className="dependency-toolbar request-flow-toolbar value-flow-toolbar" aria-label="Value flow controls">
      <div className="dependency-toolbar-title"><span>{rootId ? 'Focused value trace' : 'Source context'}</span><strong>{rootNode ? valueNodeName(rootNode) : hasTraceContext ? valueTraceContextLabel(traceContext) : 'Choose a value from Code Explorer, Request Flow, or Call Flow'}</strong></div>
      <label className="dependency-search"><span className="sr-only">Search loaded indexed values</span><input list="value-flow-visible-nodes" value={searchValue} placeholder="Search value, parameter or use…" onChange={(event) => setSearchValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') jumpToValue() }} /><datalist id="value-flow-visible-nodes">{nodes.map((node) => <option key={node.id} value={valueOptionLabel(node)} />)}</datalist><button type="button" onClick={jumpToValue}>Focus</button></label>
      <div className="dependency-segmented" aria-label="Value direction">{(['incoming', 'outgoing', 'both'] as const).map((value) => <button type="button" className={direction === value ? 'active' : ''} disabled={Boolean(expandingNodeId)} onClick={() => changeDirection(value)} key={value}>{value === 'incoming' ? 'Comes from' : value === 'outgoing' ? 'Flows to' : 'Both'}</button>)}</div>
      <details className="dependency-help"><summary aria-label="About value flow">?</summary><div><strong>Partial static value analysis.</strong><p>Current support is intraprocedural and inferred. Missing edges do not prove that a value is unused at runtime.</p></div></details>
      {rootId ? <button type="button" className="dependency-reset" onClick={resetToContext}><Icon name="refresh" size={14} /> Back to matched values</button> : null}
      {!embedded && hasTraceContext && onReturnToSource ? <button type="button" className="dependency-reset" onClick={onReturnToSource}><Icon name="code" size={14} /> Back to source</button> : null}
    </section>

    {hasTraceContext ? <div className={`dependency-compact-status request-flow-status value-flow-status ${limited ? 'limited' : ''}`} role="status" aria-live="polite">
      <span><strong>{Number(measured.indexed_value_nodes ?? entryTotal)}</strong> matched values</span>
      <span><strong>{Number(measured.parameter_nodes ?? 0)}</strong> parameters</span>
      <span><strong>{Number(measured.definition_nodes ?? 0)}</strong> definitions</span>
      <span><strong>{Number(measured.use_nodes ?? 0)}</strong> uses</span>
      <span><strong>{Number(measured.supported_value_relations ?? entryGraph?.counts?.available_edges ?? 0)}</strong> supported relations</span>
      {rootId ? <span>{nodes.length} visible values · {edges.length} relations</span> : <span>{nodes.length} of {entryTotal} values loaded</span>}
      <span>{hasBoundedInterproceduralSupport ? 'Resolved direct Python calls are traced across bounded argument and return steps; other cross-function flow remains unavailable.' : 'Intraprocedural static support only; cross-function flow is unavailable.'}</span>
    </div> : null}

    {!rootId && hasTraceContext ? <section className="request-entry-browser-summary" aria-label="Matched value status"><div><strong>{nodes.length} of {entryTotal}</strong><span>context-matched indexed values loaded in deterministic order</span></div>{remainingEntries ? <button type="button" onClick={loadMoreEntries}>Load next {Math.min(entryBatchSize, remainingEntries)}</button> : <span>All values matching this context are loaded</span>}</section> : null}

    <section className={`dependency-stage-shell request-flow-stage value-flow-stage ${inspectorOpen ? 'inspector-open' : ''}`} aria-label="Progressive value flow graph">
      <div className="graph-stage-tools dependency-stage-tools"><div className="graph-edge-legend" aria-label="Visible value relations"><strong>Visible arrows</strong>{edges.length ? unique(edges.map((edge) => valueRelationLabel(edge.type))).map((label) => <span key={label}>{label}</span>) : <span>{rootId ? 'No supported relation in this bounded result' : 'Select a value to trace origins and uses'}</span>}</div><div className="graph-zoom" aria-label="Graph zoom controls"><button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.55, value - 0.1))}>−</button><output aria-label="Current zoom">{Math.round(zoom * 100)}%</output><button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.25, value + 0.1))}>+</button><button type="button" onClick={fitVisibleGraph}>Fit visible</button></div></div>

      {!nodes.length ? <div className="dependency-empty value-trace-guidance" role="status"><Icon name="share" size={24} /><h2>{hasTraceContext ? 'No indexed value matched this context' : 'Start from a value in context'}</h2><p>{hasTraceContext ? 'The active static DFG has no value at this file, line, or scope. This does not prove the value has no runtime flow.' : 'Open Code Explorer and choose an identifier, or select an endpoint or function in Request Flow or Call Flow, then choose Trace values.'}</p></div> : <div className={`graph-stage-viewport dependency-stage-viewport interactive-graph-viewport ${valueCanvas.panning ? 'panning' : ''}`} ref={viewportRef} {...valueCanvas.viewportPointerHandlers} role="region" tabIndex={0} aria-label="Pannable value canvas. Drag empty space to pan; drag nodes to reposition."><div className="dependency-canvas-scale" style={{ width: layout.width * zoom, height: layout.height * zoom }}><div className="graph-canvas graph-progressive-canvas value-flow-canvas" aria-label="Value flow nodes" style={{ width: layout.width, height: layout.height, transform: `scale(${zoom})` }}>
        <svg className="graph-edges" width={layout.width} height={layout.height} role="img" aria-label={`${edges.length} supported value relationships`}><defs><marker id="value-flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" /></marker></defs>{edges.map((edge, index) => { const source = valueCanvas.positions.get(edge.source); const target = valueCanvas.positions.get(edge.target); if (!source || !target) return null; const selected = graphEdgeKey(edge) === selectedEdgeKey; return <path role="button" tabIndex={0} aria-label={`${valueNodeName(nodeById.get(edge.source)!)} ${valueRelationLabel(edge.type)} ${valueNodeName(nodeById.get(edge.target)!)}`} className={`graph-edge value-flow-edge support-${edge.evidence_level ?? 'inferred'} ${selected ? 'active' : ''}`} d={dependencyEdgePath(source, target, edgeLaneOffset(edge, edges))} key={`${graphEdgeKey(edge)}-${index}`} markerEnd="url(#value-flow-arrow)" onClick={() => selectEdge(edge)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectEdge(edge) } }}><title>{valueNodeName(nodeById.get(edge.source)!)} {valueRelationLabel(edge.type)} {valueNodeName(nodeById.get(edge.target)!)}</title></path> })}</svg>
        {nodes.map((node) => { const position = valueCanvas.positions.get(node.id); if (!position) return null; const seed = seedById.get(node.id); const expansion = expansionByKey[expansionKey(node.id)]; return <button type="button" className={`graph-node graph-layer-node dependency-node request-flow-node value-flow-node draggable-graph-node role-${(node.role || 'unresolved').toLowerCase()} ${activeNode?.id === node.id ? 'active' : ''} ${rootId === node.id ? 'root' : ''}`} style={{ left: position.x, top: position.y } as CSSProperties} key={node.id} {...valueCanvas.nodePointerHandlers(node.id, position)} onClick={() => { if (valueCanvas.consumeDraggedClick(node.id)) return; if (rootId) selectNode(node.id); else void expandFrom(node.id, true) }} aria-label={`${valueRoleLabel(node)} ${valueNodeName(node)}`} aria-pressed={activeNode?.id === node.id}><span className="graph-node-type"><Icon name="share" size={12} /> {valueRoleLabel(node)}</span><strong>{valueNodeName(node)}</strong><small title={node.file_path || undefined}>{sourceRangeLabel(node)}</small><em className="dependency-node-state">{rootId ? valueExpansionLabel(direction, seed, expansion, expandingNodeId === node.id) : valueSeedReasonLabel(seed)}</em></button> })}
      </div></div></div>}

      <details className="graph-relation-list dependency-relation-list"><summary>Relations ({edges.length}) <span>Keyboard and screen-reader alternative</span></summary>{edges.length ? <ul>{edges.map((edge, index) => <li key={`${graphEdgeKey(edge)}-${index}`}><button type="button" onClick={() => selectNode(edge.source)}>{valueNodeName(nodeById.get(edge.source)!)}</button><button type="button" className="call-relation-button" onClick={() => selectEdge(edge)}>→ {valueRelationLabel(edge.type)} · {supportLabel(edge.evidence_level)} →</button><button type="button" onClick={() => selectNode(edge.target)}>{valueNodeName(nodeById.get(edge.target)!)}</button></li>)}</ul> : <p>No supported value relation has been expanded. This does not prove that the value is unused at runtime.</p>}</details>

      {inspectorOpen && activeEdge ? <ValueEdgeInspector edge={activeEdge} nodeById={nodeById} graph={visibleGraph} onClose={() => setInspectorOpen(false)} onOpenSource={onOpenSource} /> : null}
      {inspectorOpen && activeNode ? <aside className="graph-inspector dependency-inspector request-flow-inspector value-flow-inspector" aria-label="Selected value flow entity"><button type="button" className="dependency-inspector-close" aria-label="Close selected value" onClick={() => setInspectorOpen(false)}>×</button><div className="graph-inspector-title"><div className="graph-entity-mark type-dfg_node" aria-hidden="true" /><div><span>{valueRoleLabel(activeNode)}</span><h2>{valueNodeName(activeNode)}</h2></div></div><p className="graph-source-path">{sourceRangeLabel(activeNode)}</p><div className="graph-inspector-section"><p>{valueNodeDescription(activeNode)}</p><PreviewLine label="Direct origins visible" value={String(relatedEdges.filter((edge) => edge.target === activeNode.id).length)} /><PreviewLine label="Direct uses visible" value={String(relatedEdges.filter((edge) => edge.source === activeNode.id).length)} /><PreviewLine label="Analysis scope" value={hasBoundedInterproceduralSupport ? 'Current function plus resolved direct Python calls' : 'Current function only'} /><PreviewLine label="Support" value="Inferred static DFG" /><PreviewLine label="Index version" value={String(visibleGraph?.index_version ?? projection.indexVersion ?? 'active')} /><p>Missing static relations do not prove missing runtime behavior.</p></div><div className="graph-inspector-actions"><button className="primary wide" type="button" disabled={!activeNode.file_path} onClick={() => onOpenSource?.(activeNode)}>Open Source</button>{canContinueExpansion(activeNode.id, direction, seedById.get(activeNode.id), expansionByKey[expansionKey(activeNode.id)]) ? <button type="button" onClick={() => { void expandFrom(activeNode.id) }}>Continue one step</button> : <button type="button" disabled>{valueTerminalLabel(direction)}</button>}{activeNode.id !== rootId ? <button type="button" onClick={() => { void expandFrom(activeNode.id, true) }}>Focus here</button> : null}</div></aside> : null}
    </section>
  </div>
}

function ValueEdgeInspector({ edge, nodeById, graph, onClose, onOpenSource }: { edge: GraphEdge; nodeById: Map<string, GraphNode>; graph: GraphData | null; onClose: () => void; onOpenSource?: (node: GraphNode) => void }) {
  const source = nodeById.get(edge.source)
  const target = nodeById.get(edge.target)
  const evidenceNode = target?.file_path ? target : source
  return <aside className="graph-inspector dependency-inspector request-flow-inspector value-flow-inspector" aria-label="Selected value relation"><button type="button" className="dependency-inspector-close" aria-label="Close selected relation" onClick={onClose}>×</button><div className="graph-inspector-title"><div className="graph-entity-mark type-dfg_node" aria-hidden="true" /><div><span>{valueRelationLabel(edge.type)}</span><h2>{valueNodeName(source!)} → {valueNodeName(target!)}</h2></div></div><div className="graph-inspector-section"><PreviewLine label="Origin / source" value={valueNodeName(source!)} /><PreviewLine label="Destination / use" value={valueNodeName(target!)} /><PreviewLine label="Source evidence" value={edgeEvidenceLocation(edge, evidenceNode)} /><PreviewLine label="Stored relation" value={readableType(edge.type)} /><PreviewLine label="Support" value={supportLabel(edge.evidence_level)} /><PreviewLine label="Analysis scope" value={isInterproceduralValueRelation(edge.type) ? 'Resolved direct Python call boundary' : 'Intraprocedural'} /><PreviewLine label="Provenance" value={readableType(graph?.provenance?.source ?? 'not reported')} /><PreviewLine label="Index version" value={String(graph?.index_version ?? 'active')} /><p>This relation is inferred by static DFG analysis; it is not a runtime trace or calibrated probability.</p></div><div className="graph-inspector-actions"><button className="primary wide" type="button" disabled={!evidenceNode?.file_path} onClick={() => evidenceNode && onOpenSource?.(evidenceNode)}>Open Source Evidence</button></div></aside>
}

function GraphJourneyChooser({ onChoose }: { onChoose: (view: GraphView) => void }) {
  return (
    <section className="graph-journey-chooser" aria-labelledby="graph-journey-title">
      <div className="graph-journey-heading">
        <span>Relationship explorer</span>
        <h2 id="graph-journey-title">What do you want to understand?</h2>
        <p>Overview already summarizes the architecture. Start here when you need to investigate a concrete relationship backed by the active index.</p>
      </div>
      <div className="graph-journey-grid">
        {PRIMARY_VIEWS.map((view) => {
          const meta = VIEW_META[view]
          return (
            <button type="button" key={view} onClick={() => onChoose(view)}>
              <span className="graph-journey-icon"><Icon name={meta.icon} size={22} /></span>
              <span><strong>{meta.label}</strong><small>{meta.question}</small></span>
              <Icon name="chevronRight" size={18} />
            </button>
          )
        })}
      </div>
    </section>
  )
}

function GraphEmptyState({ meta, hasNodes, limited, onClearFocus }: { meta: ViewMeta; hasNodes: boolean; limited: boolean; onClearFocus: () => void }) {
  return (
    <div className="graph-empty-explanation" role="status">
      <Icon name={limited ? 'warning' : 'nodes'} size={20} />
      <div>
        <strong>{hasNodes ? 'No supported arrows in this result' : 'No nodes match this relationship question'}</strong>
        <p>
          {limited
            ? 'The bounded projection is incomplete. Expand it or clear the focus before concluding that no relationship exists.'
            : `The active index returned no ${meta.label.toLowerCase()} relationship for this scope. This can be a valid leaf result or an unresolved static-analysis target.`}
        </p>
      </div>
      <button type="button" onClick={onClearFocus}>Clear focus</button>
    </div>
  )
}

function RelationSummary({ edges, activeNode, nodeById, onSelect }: { edges: GraphEdge[]; activeNode: GraphNode; nodeById: Map<string, GraphNode>; onSelect: (id: string) => void }) {
  return (
    <div className="graph-inspector-list">
      {edges.length ? edges.slice(0, 12).map((edge, index) => {
        const otherId = edge.source === activeNode.id ? edge.target : edge.source
        return (
          <button type="button" onClick={() => onSelect(otherId)} key={`${edge.source}-${edge.target}-${index}`}>
            <strong>{nodeById.get(otherId)?.label ?? otherId}</strong>
            <span>{edge.source === activeNode.id ? 'Outgoing' : 'Incoming'} · {readableType(edge.type)}</span>
          </button>
        )
      }) : <p>No relation is included for this node.</p>}
    </div>
  )
}

function EvidenceSummary({ edges, graph }: { edges: GraphEdge[]; graph: GraphData | null }) {
  const levels = edges.reduce<Record<string, number>>((counts, edge) => {
    const key = edge.evidence_level ?? 'deep'
    counts[key] = (counts[key] ?? 0) + 1
    return counts
  }, {})
  return (
    <div className="graph-inspector-section">
      <PreviewLine label="Analyzed code" value={String(levels.deep ?? 0)} />
      <PreviewLine label="Repository structure" value={String(levels.map ?? 0)} />
      <PreviewLine label="Inferred" value={String(levels.inferred ?? 0)} />
      <PreviewLine label="Provenance" value={readableType(graph?.provenance?.source ?? 'not reported')} />
      <p>These are relation support levels, not citation IDs. Open source or Evidence Viewer for validated source evidence.</p>
    </div>
  )
}

function mergeGraphProjection(current: GraphData | null, delta: GraphData): GraphData {
  if (!current) return delta
  const nodes = new Map(current.nodes.map((node) => [node.id, node]))
  delta.nodes.forEach((node) => nodes.set(node.id, node))
  const edges = new Map(current.edges.map((edge) => [graphEdgeKey(edge), edge]))
  delta.edges.forEach((edge) => edges.set(graphEdgeKey(edge), edge))
  const mergedNodes = [...nodes.values()]
  const mergedEdges = [...edges.values()].sort((left, right) => graphEdgeKey(left).localeCompare(graphEdgeKey(right)))
  const unknown = unique([...(current.coverage?.unknown ?? []), ...(delta.coverage?.unknown ?? [])])
  return {
    ...current,
    nodes: mergedNodes,
    edges: mergedEdges,
    counts: {
      available_nodes: Math.max(current.counts?.available_nodes ?? 0, delta.counts?.available_nodes ?? 0, mergedNodes.length),
      included_nodes: mergedNodes.length,
      available_edges: Math.max(current.counts?.available_edges ?? 0, delta.counts?.available_edges ?? 0, mergedEdges.length),
      included_edges: mergedEdges.length,
      available_counts_are_estimates: false,
    },
    coverage: {
      state: unknown.length || delta.coverage?.state === 'limited' ? 'limited' : 'ready',
      measured: { ...(current.coverage?.measured ?? {}), ...(delta.coverage?.measured ?? {}) },
      unknown,
    },
    truncation: delta.truncation ?? current.truncation,
    provenance: delta.provenance ?? current.provenance,
  }
}

function mergeRequestSeedPage(current: GraphData | null, page: GraphData): GraphData {
  if (!current || current.repository_id !== page.repository_id || current.index_version !== page.index_version) return page
  const nodes = new Map(current.nodes.map((node) => [node.id, node]))
  page.nodes.forEach((node) => nodes.set(node.id, node))
  const seeds = new Map((current.seeds ?? []).map((seed) => [seed.node_id, seed]))
  const pageSeeds = page.seeds ?? []
  pageSeeds.forEach((seed) => seeds.set(seed.node_id, seed))
  return {
    ...page,
    nodes: [...nodes.values()],
    seeds: [...seeds.values()],
    counts: {
      available_nodes: page.counts?.available_nodes ?? nodes.size,
      included_nodes: nodes.size,
      available_edges: page.counts?.available_edges ?? 0,
      included_edges: 0,
      available_counts_are_estimates: page.counts?.available_counts_are_estimates ?? false,
    },
  }
}

function requestEntryBatchSize() {
  if (typeof window === 'undefined') return 24
  if (window.innerWidth >= 1700) return 48
  if (window.innerWidth >= 1200) return 32
  return 24
}

function graphEdgeKey(edge: GraphEdge) {
  return `${edge.source}\u0000${edge.target}\u0000${edge.type}`
}

function dependencyExpansionLabel(
  nodeId: string,
  direction: GraphProjectionInput['direction'],
  seed: GraphSeed | undefined,
  expansion: GraphExpansion | undefined,
  loading: boolean,
) {
  if (loading) return 'Expanding…'
  if (expansion?.leaf) return 'Leaf · no additional relations'
  if (expansion?.next_neighbor_offset != null) return `${expansion.remaining_neighbors} more to load`
  if (expansion) return 'Fully expanded'
  const available = direction === 'incoming'
    ? seed?.incoming_available
    : direction === 'outgoing'
      ? seed?.outgoing_available
      : (seed?.incoming_available ?? 0) + (seed?.outgoing_available ?? 0)
  if (available === 0 && seed) return 'Leaf in this direction'
  return available ? `${available} neighbor${available === 1 ? '' : 's'} to explore` : `Click to explore ${nodeId ? '' : 'relations'}`.trim()
}

function canContinueExpansion(
  nodeId: string,
  direction: GraphProjectionInput['direction'],
  seed: GraphSeed | undefined,
  expansion: GraphExpansion | undefined,
) {
  if (expansion) return !expansion.leaf && expansion.next_neighbor_offset != null
  const available = direction === 'incoming'
    ? seed?.incoming_available
    : direction === 'outgoing'
      ? seed?.outgoing_available
      : (seed?.incoming_available ?? 0) + (seed?.outgoing_available ?? 0)
  return nodeId.length > 0 && (seed ? (available ?? 0) > 0 : true)
}

function seedReasonLabel(seed: GraphSeed) {
  const labels: Record<string, string> = {
    application_entrypoint: 'Application entrypoint',
    endpoint_owner: 'Owns an indexed endpoint',
    dependency_bridge: 'Connects dependency regions',
    many_dependents: 'Used by many files',
    many_dependencies: 'Uses many dependencies',
    graph_region_representative: 'Repository region representative',
  }
  return seed.reason_codes.map((reason) => labels[reason] ?? readableType(reason)).join(' · ')
}

function dependencyNodeLabel(node: GraphNode) {
  const label = node.label?.trim()
  if (label) return label
  const path = (node.file_path || node.scope_path || '').replace(/\\/g, '/')
  return path.split('/').filter(Boolean).at(-1) || node.id
}

function requestEntryScope(nodeTypes: string[]): 'all' | 'server' | 'client' {
  const includesServer = nodeTypes.includes('endpoint')
  const includesClient = nodeTypes.includes('api_call')
  if (includesServer && !includesClient) return 'server'
  if (includesClient && !includesServer) return 'client'
  return 'all'
}

function requestPathNodeIds(rootNodeId: string | undefined, parentByNode: Record<string, string>) {
  const path = new Set<string>()
  if (!rootNodeId) return path
  path.add(rootNodeId)
  Object.keys(parentByNode).forEach((nodeId) => {
    const visited = new Set<string>()
    let current: string | undefined = nodeId
    while (current && !visited.has(current)) {
      if (current === rootNodeId) {
        path.add(nodeId)
        return
      }
      visited.add(current)
      current = parentByNode[current]
    }
  })
  return path
}

function flowRelationLabel(type: string) {
  const labels: Record<string, string> = {
    calls_api: 'Client calls endpoint',
    exposes_endpoint: 'Endpoint handled by',
    calls: 'Calls',
    contains_call: 'Contains call site',
  }
  return labels[type] ?? readableType(type)
}

function flowNodeType(node: GraphNode, rootEntryId: string | undefined) {
  if (node.type === 'endpoint') return 'Server endpoint'
  if (node.type === 'api_call') return 'Client API call'
  if (node.type === 'method') return rootEntryId ? 'Request-path method' : 'Method'
  if (node.type === 'function') return rootEntryId ? 'Request-path function' : 'Function'
  return readableType(node.type)
}

function flowSeedReasonLabel(seed: GraphSeed) {
  const labels: Record<string, string> = {
    server_endpoint: 'Indexed server endpoint',
    handler_resolved: 'Handler resolved',
    handler_unresolved: 'Handler unresolved',
    client_api_call: 'Detected client API call',
    client_call_matched: 'Matched to endpoint',
    client_call_unmatched: 'No endpoint match',
  }
  return seed.reason_codes.map((reason) => labels[reason] ?? readableType(reason)).join(' / ')
}

function flowExpansionLabel(
  node: GraphNode,
  direction: GraphProjectionInput['direction'],
  seed: GraphSeed | undefined,
  expansion: GraphExpansion | undefined,
  loading: boolean,
) {
  if (loading) return 'Loading next hop...'
  if (expansion?.leaf) return flowTerminalLabel(node, direction, seed)
  if (expansion?.next_neighbor_offset != null) return `${expansion.remaining_neighbors} more supported neighbors`
  if (expansion) return 'Hop fully loaded'
  const available = direction === 'incoming'
    ? seed?.incoming_available
    : direction === 'outgoing'
      ? seed?.outgoing_available
      : (seed?.incoming_available ?? 0) + (seed?.outgoing_available ?? 0)
  if (seed && available === 0) return flowTerminalLabel(node, direction, seed)
  if (available) return `${available} supported hop${available === 1 ? '' : 's'} available`
  return node.id ? 'Continue to inspect one hop' : 'No supported static relation'
}

function flowTerminalLabel(
  node: GraphNode,
  direction: GraphProjectionInput['direction'],
  seed: GraphSeed | undefined,
) {
  const reasons = new Set(seed?.reason_codes ?? [])
  if (direction === 'incoming') {
    if (node.type === 'api_call') return 'Client call is the first indexed boundary'
    if (node.type === 'endpoint') return 'No matched client call'
    return 'No statically resolved caller'
  }
  if (direction === 'outgoing') {
    if (node.type === 'api_call') return reasons.has('client_call_unmatched') ? 'No matched server endpoint' : 'No additional supported server hop'
    if (node.type === 'endpoint') return reasons.has('handler_unresolved') ? 'Handler was not resolved' : 'No additional supported handler hop'
    return 'No statically resolved callee'
  }
  if (node.type === 'api_call') return reasons.has('client_call_unmatched') ? 'No matched endpoint or indexed caller' : 'No additional supported request hop'
  if (node.type === 'endpoint') return reasons.has('handler_unresolved') ? 'No matched client call or resolved handler' : 'No additional supported request hop'
  return 'No additional statically supported hop'
}

function callRelationLabel(type: string) {
  const labels: Record<string, string> = {
    calls: 'Resolved call',
    calls_builtin: 'Built-in call',
    calls_stdlib: 'Standard-library call',
    calls_framework: 'Framework call',
    calls_external: 'External call',
    calls_unresolved: 'Unresolved call',
  }
  return labels[type] ?? readableType(type)
}

function callNodeType(node: GraphNode, root: boolean) {
  if (root) return 'Selected callable'
  if (node.type === 'function') return 'Function'
  if (node.type === 'method') return 'Method'
  if (node.type === 'builtin_call') return 'Built-in target'
  if (node.type === 'stdlib_call') return 'Standard-library target'
  if (node.type === 'framework_call') return 'Framework target'
  if (node.type === 'external_call') return 'External target'
  if (node.type === 'unresolved_call') return 'Unresolved target'
  return readableType(node.type)
}

function callRelationTargetLabel(node: GraphNode) {
  if (node.type === 'unresolved_call') return 'Target could not be statically resolved'
  if (['builtin_call', 'stdlib_call', 'framework_call', 'external_call'].includes(node.type)) return 'Target outside resolved repository callables'
  return node.role || 'Indexed callable'
}

function callNodeDescription(node: GraphNode) {
  if (node.type === 'unresolved_call') return 'A call expression was indexed, but its target could not be resolved. It is shown explicitly instead of being upgraded to a function relation.'
  if (['builtin_call', 'stdlib_call', 'framework_call', 'external_call'].includes(node.type)) return 'A classified non-repository call target from the static index.'
  return 'An indexed callable in the current bounded static call projection.'
}

function callSeedReasonLabel(seed: GraphSeed) {
  const labels: Record<string, string> = {
    endpoint_handler: 'Endpoint handler',
    many_callers: 'Many direct callers',
    many_callees: 'Many direct callees',
    direct_recursion: 'Direct recursion',
    no_supported_internal_caller: 'No supported internal caller',
    indexed_callable: 'Indexed callable',
  }
  return seed.reason_codes.map((reason) => labels[reason] ?? readableType(reason)).join(' · ')
}

function callExpansionLabel(
  node: GraphNode,
  direction: GraphProjectionInput['direction'],
  seed: GraphSeed | undefined,
  expansion: GraphExpansion | undefined,
  loading: boolean,
) {
  if (loading) return 'Loading one bounded hop…'
  if (expansion?.leaf) return callTerminalLabel(direction)
  if (expansion?.next_neighbor_offset != null) return `${expansion.remaining_neighbors} more relations to load`
  if (expansion) return 'Current hop fully loaded'
  const available = direction === 'incoming'
    ? seed?.incoming_available
    : direction === 'outgoing'
      ? seed?.outgoing_available
      : (seed?.incoming_available ?? 0) + (seed?.outgoing_available ?? 0)
  if (seed && available === 0) return callTerminalLabel(direction)
  if (available) return `${available} direct relation${available === 1 ? '' : 's'} available`
  return ['function', 'method'].includes(node.type) ? 'Continue to inspect one hop' : callRelationTargetLabel(node)
}

function callTerminalLabel(direction: GraphProjectionInput['direction']) {
  if (direction === 'incoming') return 'No supported internal caller found'
  if (direction === 'outgoing') return 'No supported callee found'
  return 'No additional supported static call found'
}

function valueNodeName(node: GraphNode) {
  const role = (node.role || '').trim()
  const prefix = role ? `${role}:` : ''
  return prefix && node.label.toLowerCase().startsWith(prefix.toLowerCase())
    ? node.label.slice(prefix.length).trim()
    : node.label
}

function valueRoleLabel(node: GraphNode) {
  const labels: Record<string, string> = {
    parameter: 'Parameter',
    definition: 'Definition',
    use: 'Use',
    argument: 'Call argument',
    call_result: 'Call result',
    return: 'Function return',
  }
  return labels[(node.role || '').toLowerCase()] ?? 'Unresolved value role'
}

function valueNodeDescription(node: GraphNode) {
  if (node.role === 'parameter') return 'A function parameter represented by the current intraprocedural DFG.'
  if (node.role === 'definition') return 'A local value definition or assignment represented by the current intraprocedural DFG.'
  if (node.role === 'use') return 'A supported read or use of a value inside the current function.'
  if (node.role === 'argument') return 'A positional argument at a statically analyzed call site.'
  if (node.role === 'call_result') return 'The result boundary of a statically analyzed function call.'
  if (node.role === 'return') return 'A supported return boundary that may flow back to a resolved caller.'
  return 'The index returned a DFG value node without a supported semantic role.'
}

function valueOptionLabel(node: GraphNode) {
  const location = node.file_path || node.scope_path
  const line = node.start_line ? `:${node.start_line}` : ''
  return `${valueNodeName(node)} — ${valueRoleLabel(node)}${location ? ` — ${location}${line}` : ''}`
}

function valueRelationLabel(type: string) {
  const labels: Record<string, string> = {
    dfg_reaches: 'Reaches use',
    dfg_computed_from: 'Contributes to definition',
    dfg_uses: 'Used by expression',
    dfg_returned: 'Used in return',
    dfg_parameter: 'Supplies parameter',
    dfg_defines: 'Defines',
    dfg_argument: 'Supplies call argument',
    dfg_argument_to_parameter: 'Binds to callee parameter',
    dfg_return: 'Supplies function return',
    dfg_return_to_call_result: 'Returns to caller',
    dfg_call_result_to_definition: 'Defines caller result',
  }
  return labels[type] ?? readableType(type.replace(/^dfg_/, ''))
}

function isInterproceduralValueRelation(type: string) {
  return type === 'dfg_argument_to_parameter' || type === 'dfg_return_to_call_result'
}

function valueSeedReasonLabel(seed: GraphSeed | undefined) {
  if (!seed) return 'Select to trace supported origins and uses'
  const labels: Record<string, string> = {
    value_parameter: 'Function input',
    value_definition: 'Local definition',
    value_use: 'Value use',
    value_role_unresolved: 'Role unresolved',
    has_supported_origin: 'Supported origin available',
    has_supported_use: 'Supported use available',
    multiple_supported_uses: 'Multiple supported uses',
  }
  return seed.reason_codes.map((reason) => labels[reason] ?? readableType(reason)).join(' · ')
}

function valueExpansionLabel(
  direction: GraphProjectionInput['direction'],
  seed: GraphSeed | undefined,
  expansion: GraphExpansion | undefined,
  loading: boolean,
) {
  if (loading) return 'Loading one bounded step…'
  if (expansion?.leaf) return valueTerminalLabel(direction)
  if (expansion?.next_neighbor_offset != null) return `${expansion.remaining_neighbors} more relations to load`
  if (expansion) return 'Current step fully loaded'
  const available = direction === 'incoming'
    ? seed?.incoming_available
    : direction === 'outgoing'
      ? seed?.outgoing_available
      : (seed?.incoming_available ?? 0) + (seed?.outgoing_available ?? 0)
  if (seed && available === 0) return valueTerminalLabel(direction)
  return available ? `${available} direct relation${available === 1 ? '' : 's'} available` : 'Continue to inspect one step'
}

function valueTerminalLabel(direction: GraphProjectionInput['direction']) {
  if (direction === 'incoming') return 'No additional supported origin found'
  if (direction === 'outgoing') return 'No additional supported use found'
  return 'No additional supported relation found'
}

function sourceRangeLabel(node: GraphNode) {
  const path = node.file_path || node.scope_path
  if (!path) return 'No repository source target was resolved'
  if (node.start_line && node.end_line) return `${path}:${node.start_line}–${node.end_line}`
  if (node.start_line) return `${path}:${node.start_line}`
  return path
}

function edgeEvidenceLocation(edge: GraphEdge, caller: GraphNode | undefined) {
  const path = edge.metadata?.path || edge.metadata?.file_path || caller?.file_path || caller?.scope_path
  const line = edge.metadata?.line || edge.metadata?.start_line || caller?.start_line
  if (!path) return 'No source locator reported by this projection'
  return line ? `${path}:${line}` : path
}

function callResolutionLabel(edge: GraphEdge) {
  if (edge.type === 'calls') return edge.evidence_level === 'inferred' ? 'Inferred callable relation' : 'Static symbol resolution'
  if (edge.type === 'calls_unresolved') return 'Unresolved static target'
  if (edge.type === 'calls_builtin') return 'Classified built-in target'
  if (edge.type === 'calls_stdlib') return 'Classified standard-library target'
  if (edge.type === 'calls_framework') return 'Classified framework target'
  if (edge.type === 'calls_external') return 'Classified external target'
  return 'Indexed static relation'
}

function isNodeInCallCycle(nodeId: string, edges: GraphEdge[]) {
  const outgoing = new Map<string, string[]>()
  edges.forEach((edge) => outgoing.set(edge.source, [...(outgoing.get(edge.source) ?? []), edge.target]))
  const frontier = [...(outgoing.get(nodeId) ?? [])]
  const visited = new Set<string>()
  while (frontier.length) {
    const current = frontier.pop()!
    if (current === nodeId) return true
    if (visited.has(current)) continue
    visited.add(current)
    frontier.push(...(outgoing.get(current) ?? []))
  }
  return false
}

function dependencyBranchPath(nodeId: string | undefined, parentByNode: Record<string, string>) {
  const path = new Set<string>()
  let current = nodeId
  while (current && !path.has(current)) {
    path.add(current)
    current = parentByNode[current]
  }
  return path
}

type Position = { x: number; y: number }

function useGraphCanvasInteractions(
  basePositions: Map<string, Position>,
  bounds: { width: number; height: number },
  zoom: number,
  viewportRef: RefObject<HTMLDivElement | null>,
) {
  const [manualPositions, setManualPositions] = useState(() => new Map<string, Position>())
  const [panning, setPanning] = useState(false)
  const panState = useRef<{ pointerId: number; clientX: number; clientY: number; scrollLeft: number; scrollTop: number } | undefined>(undefined)
  const nodeDrag = useRef<{ pointerId: number; nodeId: string; clientX: number; clientY: number; origin: Position; moved: boolean } | undefined>(undefined)
  const suppressedClickNode = useRef<string | undefined>(undefined)
  const positions = useMemo(() => {
    const next = new Map(basePositions)
    manualPositions.forEach((position, nodeId) => { if (next.has(nodeId)) next.set(nodeId, position) })
    return next
  }, [basePositions, manualPositions])

  function onViewportPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return
    const target = event.target as Element
    if (target.closest('button, a, input, summary, path[role="button"]')) return
    const viewport = viewportRef.current
    if (!viewport) return
    event.preventDefault()
    event.currentTarget.setPointerCapture?.(event.pointerId)
    panState.current = {
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      scrollLeft: viewport.scrollLeft,
      scrollTop: viewport.scrollTop,
    }
    setPanning(true)
  }

  function onViewportPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    const active = panState.current
    const viewport = viewportRef.current
    if (!active || !viewport || active.pointerId !== event.pointerId) return
    viewport.scrollLeft = active.scrollLeft - (event.clientX - active.clientX)
    viewport.scrollTop = active.scrollTop - (event.clientY - active.clientY)
  }

  function endViewportPan(event: ReactPointerEvent<HTMLDivElement>) {
    if (panState.current?.pointerId !== event.pointerId) return
    event.currentTarget.releasePointerCapture?.(event.pointerId)
    panState.current = undefined
    setPanning(false)
  }

  function nodePointerHandlers(nodeId: string, position: Position) {
    return {
      onPointerDown(event: ReactPointerEvent<HTMLButtonElement>) {
        if (event.button !== 0) return
        event.stopPropagation()
        event.currentTarget.setPointerCapture?.(event.pointerId)
        nodeDrag.current = { pointerId: event.pointerId, nodeId, clientX: event.clientX, clientY: event.clientY, origin: position, moved: false }
      },
      onPointerMove(event: ReactPointerEvent<HTMLButtonElement>) {
        const active = nodeDrag.current
        if (!active || active.pointerId !== event.pointerId || active.nodeId !== nodeId) return
        const deltaX = (event.clientX - active.clientX) / zoom
        const deltaY = (event.clientY - active.clientY) / zoom
        if (!active.moved && Math.hypot(deltaX, deltaY) < 4) return
        active.moved = true
        const next = {
          x: Math.max(20, Math.min(bounds.width - NODE_WIDTH - 20, active.origin.x + deltaX)),
          y: Math.max(20, Math.min(bounds.height - NODE_HEIGHT - 20, active.origin.y + deltaY)),
        }
        setManualPositions((current) => new Map(current).set(nodeId, next))
      },
      onPointerUp(event: ReactPointerEvent<HTMLButtonElement>) {
        const active = nodeDrag.current
        if (!active || active.pointerId !== event.pointerId || active.nodeId !== nodeId) return
        event.currentTarget.releasePointerCapture?.(event.pointerId)
        if (active.moved) suppressedClickNode.current = nodeId
        nodeDrag.current = undefined
      },
      onPointerCancel(event: ReactPointerEvent<HTMLButtonElement>) {
        if (nodeDrag.current?.pointerId === event.pointerId) nodeDrag.current = undefined
      },
    }
  }

  function consumeDraggedClick(nodeId: string) {
    if (suppressedClickNode.current !== nodeId) return false
    suppressedClickNode.current = undefined
    return true
  }

  function resetNodePositions() {
    setManualPositions(new Map())
  }

  return {
    positions,
    panning,
    viewportPointerHandlers: {
      onPointerDown: onViewportPointerDown,
      onPointerMove: onViewportPointerMove,
      onPointerUp: endViewportPan,
      onPointerCancel: endViewportPan,
    },
    nodePointerHandlers,
    consumeDraggedClick,
    resetNodePositions,
  }
}

function buildProgressiveLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  cache: Map<string, Position>,
  parentByNode: Record<string, string>,
) {
  const nodeById = new Map(nodes.map((node) => [node.id, node]))
  const positions = new Map<string, Position>()
  const columnGap = NODE_WIDTH + 110
  const rowGap = NODE_HEIGHT + 42
  const rootStartX = 650
  const rootColumns = 3
  const roots = nodes
    .filter((node) => !parentByNode[node.id] || !nodeById.has(parentByNode[node.id]))
    .sort((left, right) => {
      const leftCached = cache.get(left.id)
      const rightCached = cache.get(right.id)
      if (leftCached && rightCached) return leftCached.y - rightCached.y || leftCached.x - rightCached.x
      if (leftCached) return -1
      if (rightCached) return 1
      return left.id.localeCompare(right.id)
    })

  roots.forEach((node, index) => {
    const cached = cache.get(node.id)
    positions.set(node.id, cached ?? {
      x: rootStartX + (index % rootColumns) * columnGap,
      y: 70 + Math.floor(index / rootColumns) * rowGap,
    })
  })

  const pending = new Set(nodes.filter((node) => !positions.has(node.id)).map((node) => node.id))
  for (let pass = 0; pass < nodes.length && pending.size; pass += 1) {
    const ready = [...pending]
      .filter((nodeId) => positions.has(parentByNode[nodeId]))
      .sort((leftId, rightId) => {
        const leftCached = cache.get(leftId)
        const rightCached = cache.get(rightId)
        if (leftCached && rightCached) return leftCached.y - rightCached.y
        if (leftCached) return -1
        if (rightCached) return 1
        const leftParent = positions.get(parentByNode[leftId])!
        const rightParent = positions.get(parentByNode[rightId])!
        return leftParent.y - rightParent.y || leftId.localeCompare(rightId)
      })
    if (!ready.length) break
    ready.forEach((nodeId) => {
      const cached = cache.get(nodeId)
      if (cached) {
        positions.set(nodeId, cached)
        pending.delete(nodeId)
        return
      }
      const parentId = parentByNode[nodeId]
      const parent = positions.get(parentId)!
      const siblings = nodes
        .filter((candidate) => parentByNode[candidate.id] === parentId)
        .sort((left, right) => {
          const leftCached = cache.get(left.id)
          const rightCached = cache.get(right.id)
          if (leftCached && rightCached) return leftCached.y - rightCached.y
          if (leftCached) return -1
          if (rightCached) return 1
          return left.id.localeCompare(right.id)
        })
      const siblingIndex = siblings.findIndex((candidate) => candidate.id === nodeId)
      const relation = edges.find((edge) =>
        (edge.source === parentId && edge.target === nodeId)
        || (edge.target === parentId && edge.source === nodeId),
      )
      const outgoing = relation?.source === parentId
      positions.set(nodeId, {
        x: parent.x + (outgoing ? columnGap : -columnGap),
        y: Math.max(40, parent.y + (siblingIndex - (siblings.length - 1) / 2) * rowGap),
      })
      pending.delete(nodeId)
    })
  }

  // Malformed/cyclic parent metadata must not make nodes disappear. Place any
  // remainder in a deterministic fallback column before collision resolution.
  ;[...pending].sort().forEach((nodeId, index) => {
    positions.set(nodeId, { x: rootStartX, y: 70 + (roots.length + index) * rowGap })
  })

  const columns = new Map<number, string[]>()
  positions.forEach((position, nodeId) => {
    const key = Math.round(position.x)
    columns.set(key, [...(columns.get(key) ?? []), nodeId])
  })
  columns.forEach((nodeIds) => {
    const cachedIds = nodeIds.filter((nodeId) => cache.has(nodeId)).sort((left, right) => cache.get(left)!.y - cache.get(right)!.y)
    const newIds = nodeIds.filter((nodeId) => !cache.has(nodeId)).sort((left, right) => positions.get(left)!.y - positions.get(right)!.y || left.localeCompare(right))
    let nextY = 40
    ;[...cachedIds, ...newIds].forEach((nodeId) => {
      const position = positions.get(nodeId)!
      const y = Math.max(position.y, nextY)
      positions.set(nodeId, { x: position.x, y })
      nextY = Math.max(nextY, y + rowGap)
    })
  })

  const minX = Math.min(40, ...[...positions.values()].map((position) => position.x))
  if (minX < 40) {
    const shift = 40 - minX
    positions.forEach((position, nodeId) => positions.set(nodeId, { x: position.x + shift, y: position.y }))
  }
  const width = Math.max(PROGRESSIVE_CANVAS_WIDTH, ...[...positions.values()].map((position) => position.x + NODE_WIDTH + 80))
  const height = Math.max(680, ...[...positions.values()].map((position) => position.y + NODE_HEIGHT + 100))
  return { positions, width, height }
}

function buildValueFlowLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  rootId: string | undefined,
  cache: Map<string, Position>,
) {
  const positions = new Map<string, Position>()
  const columnGap = NODE_WIDTH + 120
  const rowGap = NODE_HEIGHT + 42
  if (!rootId || !nodes.some((node) => node.id === rootId)) {
    const columns = 3
    nodes.slice().sort((left, right) => valueOptionLabel(left).localeCompare(valueOptionLabel(right)) || left.id.localeCompare(right.id)).forEach((node, index) => {
      positions.set(node.id, {
        x: 120 + (index % columns) * columnGap,
        y: 60 + Math.floor(index / columns) * rowGap,
      })
    })
  } else {
    const rank = new Map<string, number>([[rootId, 0]])
    const queue = [rootId]
    const orderedEdges = edges.slice().sort((left, right) => graphEdgeKey(left).localeCompare(graphEdgeKey(right)))
    while (queue.length) {
      const current = queue.shift()!
      const currentRank = rank.get(current) ?? 0
      orderedEdges.forEach((edge) => {
        if (edge.target === current && !rank.has(edge.source)) {
          rank.set(edge.source, currentRank - 1)
          queue.push(edge.source)
        }
        if (edge.source === current && !rank.has(edge.target)) {
          rank.set(edge.target, currentRank + 1)
          queue.push(edge.target)
        }
      })
    }
    nodes.forEach((node) => { if (!rank.has(node.id)) rank.set(node.id, 0) })
    const minRank = Math.min(...rank.values())
    const columns = new Map<number, GraphNode[]>()
    nodes.forEach((node) => {
      const nodeRank = rank.get(node.id) ?? 0
      columns.set(nodeRank, [...(columns.get(nodeRank) ?? []), node])
    })
    ;[...columns.entries()].sort(([left], [right]) => left - right).forEach(([nodeRank, columnNodes]) => {
      columnNodes.sort((left, right) => {
        const leftCached = cache.get(left.id)
        const rightCached = cache.get(right.id)
        if (leftCached && rightCached) return leftCached.y - rightCached.y || left.id.localeCompare(right.id)
        if (leftCached) return -1
        if (rightCached) return 1
        return valueOptionLabel(left).localeCompare(valueOptionLabel(right)) || left.id.localeCompare(right.id)
      })
      columnNodes.forEach((node, index) => positions.set(node.id, {
        x: 80 + (nodeRank - minRank) * columnGap,
        y: Math.max(50 + index * rowGap, cache.get(node.id)?.y ?? 0),
      }))
    })
  }
  const width = Math.max(PROGRESSIVE_CANVAS_WIDTH, ...[...positions.values()].map((position) => position.x + NODE_WIDTH + 100))
  const height = Math.max(680, ...[...positions.values()].map((position) => position.y + NODE_HEIGHT + 100))
  return { positions, width, height }
}

function dependencyEdgePath(source: Position, target: Position, laneOffset = 0) {
  if (source.x === target.x && source.y === target.y) {
    const x = source.x + NODE_WIDTH
    const middleY = source.y + NODE_HEIGHT / 2
    return `M ${x} ${middleY - 10} C ${x + 74} ${source.y - 38}, ${x + 74} ${source.y + NODE_HEIGHT + 38}, ${x} ${middleY + 10}`
  }
  const movingRight = target.x >= source.x
  const startX = movingRight ? source.x + NODE_WIDTH : source.x
  const endX = movingRight ? target.x : target.x + NODE_WIDTH
  const startY = source.y + NODE_HEIGHT / 2
  const endY = target.y + NODE_HEIGHT / 2
  const curve = Math.max(50, Math.abs(endX - startX) * 0.45)
  return `M ${startX} ${startY} C ${startX + (movingRight ? curve : -curve)} ${startY + laneOffset}, ${endX - (movingRight ? curve : -curve)} ${endY + laneOffset}, ${endX} ${endY}`
}

function edgeLaneOffset(edge: GraphEdge, edges: GraphEdge[]) {
  if (edge.source === edge.target) return 0
  const sameDirection = edges
    .filter((candidate) => candidate.source === edge.source && candidate.target === edge.target)
    .sort((left, right) => graphEdgeKey(left).localeCompare(graphEdgeKey(right)))
  const parallelIndex = sameDirection.findIndex((candidate) => graphEdgeKey(candidate) === graphEdgeKey(edge))
  const parallelOffset = (parallelIndex - (sameDirection.length - 1) / 2) * 12
  const reverseExists = edges.some((candidate) => candidate.source === edge.target && candidate.target === edge.source)
  const reverseOffset = reverseExists ? (edge.source.localeCompare(edge.target) < 0 ? -16 : 16) : 0
  return parallelOffset + reverseOffset
}

function buildLayerLayout(nodes: GraphNode[]) {
  const groups = new Map<string, { id: string; label: string; nodes: GraphNode[] }>()
  nodes.forEach((node) => {
    const layer = layerForNode(node)
    const group = groups.get(layer.id) ?? { ...layer, nodes: [] }
    group.nodes.push(node)
    groups.set(layer.id, group)
  })
  const orderedIds = ['client', 'api', 'domain', 'data', 'other']
  const orderedGroups = orderedIds.map((id) => groups.get(id)).filter((group): group is NonNullable<typeof group> => Boolean(group))
  const positions = new Map<string, Position>()
  const layers: { id: string; label: string; top: number; height: number }[] = []
  const columns = 5
  const gapX = (CANVAS_WIDTH - 80 - NODE_WIDTH * columns) / (columns - 1)
  let cursorY = 24
  orderedGroups.forEach((group) => {
    const rows = Math.max(1, Math.ceil(group.nodes.length / columns))
    const height = 56 + rows * 108
    layers.push({ id: group.id, label: group.label, top: cursorY, height })
    group.nodes.forEach((node, index) => {
      positions.set(node.id, {
        x: 40 + (index % columns) * (NODE_WIDTH + gapX),
        y: cursorY + 48 + Math.floor(index / columns) * 108,
      })
    })
    cursorY += height + 16
  })
  return { positions, layers, height: Math.max(360, cursorY + 24) }
}

function layerForNode(node: GraphNode) {
  const value = `${node.layer ?? ''} ${node.type} ${node.role ?? ''} ${node.file_path ?? ''}`.toLowerCase()
  if (/client|frontend|component|page|view|ui/.test(value)) return { id: 'client', label: 'Client experience' }
  if (/api|endpoint|route|router|controller|handler/.test(value)) return { id: 'api', label: 'API boundary' }
  if (/database|table|repository|storage|cache|model|schema/.test(value)) return { id: 'data', label: 'Data and persistence' }
  if (/service|domain|function|class|module|package|job|worker/.test(value)) return { id: 'domain', label: 'Domain and services' }
  return { id: 'other', label: 'Supporting code' }
}

function connectedNodeIds(nodeId: string | undefined, edges: GraphEdge[]) {
  const ids = new Set<string>()
  if (!nodeId) return ids
  ids.add(nodeId)
  edges.forEach((edge) => {
    if (edge.source === nodeId) ids.add(edge.target)
    if (edge.target === nodeId) ids.add(edge.source)
  })
  return ids
}

function edgePath(source: Position, target: Position, laneOffset = 0) {
  if (source.x === target.x && source.y === target.y) {
    const x = source.x + NODE_WIDTH
    const middleY = source.y + NODE_HEIGHT / 2
    return `M ${x} ${middleY - 10} C ${x + 70} ${source.y - 34}, ${x + 70} ${source.y + NODE_HEIGHT + 34}, ${x} ${middleY + 10}`
  }
  const startX = source.x + NODE_WIDTH / 2
  const startY = source.y + NODE_HEIGHT
  const endX = target.x + NODE_WIDTH / 2
  const endY = target.y
  const direction = endY >= startY ? 1 : -1
  const curve = Math.max(36, Math.abs(endY - startY) * 0.45) * direction
  return `M ${startX} ${startY} C ${startX + laneOffset} ${startY + curve}, ${endX + laneOffset} ${endY - curve}, ${endX} ${endY}`
}

function focusCandidates(nodes: GraphNode[], view: GraphView) {
  const preferred = nodes.filter((node) => {
    if (view === 'dependencies') return ['file', 'module'].includes(node.type)
    if (view === 'api-flow') return ['endpoint', 'api_call', 'call_site', 'function', 'method'].includes(node.type)
    if (view === 'function-flow') return ['function', 'method', 'call_site'].includes(node.type)
    if (view === 'data-flow') return node.type === 'dfg_node'
    return true
  })
  return (preferred.length ? preferred : nodes).slice().sort((left, right) => focusOptionLabel(left).localeCompare(focusOptionLabel(right)))
}

function focusOptionLabel(node: GraphNode) {
  const location = node.file_path || node.scope_path
  return location ? `${node.label} — ${location}` : node.label
}

function humanNodeLabel(node: GraphNode, view: GraphView) {
  if (view === 'data-flow') {
    const role = readableType(node.role || node.type)
    return node.label.toLowerCase().startsWith(role.toLowerCase()) ? node.label : `${role}: ${node.label}`
  }
  return node.label
}

function humanNodeType(node: GraphNode, view: GraphView) {
  if (view === 'dependencies') return node.type === 'module' ? 'Module' : 'File'
  if (view === 'api-flow') {
    if (node.type === 'endpoint') return 'API endpoint'
    if (node.type === 'api_call') return 'API call'
    if (node.type === 'call_site') return 'Call site'
  }
  if (view === 'function-flow' && node.type === 'call_site') return 'Resolved call site'
  if (view === 'data-flow') return readableType(node.role || 'Value step')
  return readableType(node.role || node.type)
}

function nodeIcon(node: GraphNode): IconName {
  if (node.type === 'endpoint' || node.type === 'api_call') return 'route'
  if (node.type === 'file' || node.type === 'module') return 'file'
  if (node.type === 'database' || node.type === 'repository') return 'database'
  if (node.type === 'service') return 'server'
  if (node.type === 'dfg_node') return 'share'
  return 'braces'
}

function coverageLabel(coverage?: string) {
  if (coverage === 'mapped') return 'Needs analysis'
  if (coverage === 'analyzing') return 'Analyzing'
  if (coverage === 'skipped') return 'Skipped'
  if (coverage === 'failed') return 'Issue found'
  return 'Ready'
}

function supportLabel(support?: string) {
  if (support === 'map') return 'repository structure'
  if (support === 'inferred') return 'inferred relation'
  return 'analyzed code'
}

function directionLabel(direction: GraphProjectionInput['direction']) {
  if (direction === 'incoming') return 'incoming only'
  if (direction === 'outgoing') return 'outgoing only'
  return 'both directions'
}

function readableType(type: string) {
  return type.replaceAll('_', ' ')
}

function unique(values: Array<string | undefined>) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort()
}
