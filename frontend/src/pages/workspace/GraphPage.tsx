import { useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { Icon } from '../../components/common/Icon'
import { PageTitle, PreviewLine } from '../../components/common/ui'
import type { GraphData, GraphProjectionInput, GraphView, IconName, Overview } from '../../types/api'

type GraphNode = GraphData['nodes'][number]
type GraphEdge = GraphData['edges'][number]
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

const NODE_WIDTH = 176
const NODE_HEIGHT = 70
const CANVAS_WIDTH = 1120
const EMPTY_NODES: GraphNode[] = []
const EMPTY_EDGES: GraphEdge[] = []

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
    defaultNodeTypes: ['function', 'method', 'call_site'],
    defaultEdgeTypes: ['calls', 'contains_call'],
  },
  'data-flow': {
    id: 'data-flow',
    label: 'Value Flow',
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

export function GraphPage({
  graph,
  graphView,
  projection,
  overview,
  onGraphView,
  onProjection,
  onAnalyzeArea,
  onOpenSource,
  onOpenImpact,
}: {
  graph: GraphData | null
  graphView: GraphView
  projection: GraphProjectionInput
  overview: Overview | null
  onGraphView: (view: GraphView) => void
  onProjection: (patch: Partial<GraphProjectionInput>) => void
  onAnalyzeArea: (scopePath: string) => void
  onOpenSource?: (node: GraphNode) => void
  onOpenImpact?: (node: GraphNode) => void
}) {
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const [zoom, setZoom] = useState(0.9)
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('overview')
  const nodes = graph?.nodes ?? EMPTY_NODES
  const edges = graph?.edges ?? EMPTY_EDGES
  const meta = VIEW_META[graphView]
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes])
  const activeNode = nodeById.get(selectedNodeId ?? '')
  const focusedNode = nodeById.get(projection.rootKeys[0] ?? '')
  const layout = useMemo(() => buildLayerLayout(nodes), [nodes])
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
    onProjection({
      rootKeys: [],
      nodeTypes: next.defaultNodeTypes,
      edgeTypes: next.defaultEdgeTypes,
      supportLevels: [],
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
            <button type="button" className={graphView === 'data-flow' ? 'active' : ''} onClick={() => chooseView('data-flow')}>
              <Icon name="share" size={15} /> Value Flow <span>Advanced</span>
            </button>
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

              <div className="graph-stage-viewport">
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
                      const source = layout.positions.get(edge.source)
                      const target = layout.positions.get(edge.target)
                      if (!source || !target) return null
                      const active = activeNode ? edge.source === activeNode.id || edge.target === activeNode.id : false
                      const sourceLabel = nodeById.get(edge.source)?.label ?? edge.source
                      const targetLabel = nodeById.get(edge.target)?.label ?? edge.target
                      return (
                        <path
                          className={`graph-edge support-${edge.evidence_level ?? 'deep'} ${active ? 'active' : ''}`}
                          d={edgePath(source, target)}
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
                    const position = layout.positions.get(node.id)
                    if (!position) return null
                    const dimmed = Boolean(activeNode && activeNode.id !== node.id && !relatedNodeIds.has(node.id))
                    return (
                      <button
                        type="button"
                        className={`graph-node graph-layer-node type-${node.type} coverage-${node.coverage ?? 'deep_indexed'} ${activeNode?.id === node.id ? 'active' : ''} ${dimmed ? 'dimmed' : ''}`}
                        style={{ left: position.x, top: position.y } as CSSProperties}
                        key={node.id}
                        onClick={() => selectNode(node.id)}
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
                      const position = layout.positions.get(node.id)
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
                    <button type="button" onClick={() => onOpenImpact?.(activeNode)}>Analyze Impact</button>
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
      <button type="button" className="graph-advanced-entry" onClick={() => onChoose('data-flow')}>
        <Icon name="share" size={18} />
        <span><strong>Value Flow</strong><small>Advanced compiler-level definitions and uses; not system data flow.</small></span>
        <Icon name="chevronRight" size={18} />
      </button>
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

type Position = { x: number; y: number }

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

function edgePath(source: Position, target: Position) {
  const startX = source.x + NODE_WIDTH / 2
  const startY = source.y + NODE_HEIGHT
  const endX = target.x + NODE_WIDTH / 2
  const endY = target.y
  const direction = endY >= startY ? 1 : -1
  const curve = Math.max(36, Math.abs(endY - startY) * 0.45) * direction
  return `M ${startX} ${startY} C ${startX} ${startY + curve}, ${endX} ${endY - curve}, ${endX} ${endY}`
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
