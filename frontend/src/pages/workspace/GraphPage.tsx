import { useMemo, useRef, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { GraphData, GraphProjectionInput, GraphView, Overview } from '../../types/api'

type GraphNode = GraphData['nodes'][number]
type GraphEdge = GraphData['edges'][number]
type InspectorTab = 'overview' | 'relations' | 'evidence' | 'impact'

const NODE_WIDTH = 176
const NODE_HEIGHT = 70
const CANVAS_WIDTH = 1120
const EMPTY_NODES: GraphNode[] = []
const EMPTY_EDGES: GraphEdge[] = []

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
  const rootInput = useRef<HTMLInputElement>(null)
  const nodes = graph?.nodes ?? EMPTY_NODES
  const edges = graph?.edges ?? EMPTY_EDGES
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes])
  const activeNode = nodeById.get(selectedNodeId ?? '') ?? nodes[0]
  const layout = useMemo(() => buildLayerLayout(nodes), [nodes])
  const relatedNodeIds = useMemo(() => connectedNodeIds(activeNode?.id, edges), [activeNode?.id, edges])
  const relatedEdges = activeNode ? edges.filter((edge) => edge.source === activeNode.id || edge.target === activeNode.id) : []
  const nodeTypes = unique([projection.nodeTypes[0], ...nodes.map((node) => node.type)])
  const edgeTypes = unique([projection.edgeTypes[0], ...edges.map((edge) => edge.type)])
  const availableNodes = graph?.counts?.available_nodes ?? nodes.length
  const availableEdges = graph?.counts?.available_edges ?? edges.length
  const limited = graph?.coverage?.state === 'limited' || graph?.truncation?.truncated

  function applyRoot(event: FormEvent) {
    event.preventDefault()
    const root = rootInput.current?.value.trim() ?? ''
    onProjection({ rootKeys: root ? [root] : [] })
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
      <PageTitle title="Graph Explorer" subtitle="Explore a lively, server-bounded architecture map without losing evidence, coverage, or uncertainty." />
      <div className="toolbar graph-toolbar" aria-label="Graph views">
        {graphViews.map((view) => (
          <button type="button" className={`tab ${graphView === view.id ? 'active' : ''}`} key={view.id} onClick={() => onGraphView(view.id)}>
            {view.label}
          </button>
        ))}
      </div>
      <Panel title="Projection controls">
        <div className="graph-projection-controls">
          <form className="graph-root-form" onSubmit={applyRoot}>
            <label htmlFor="graph-root">Root key</label>
            <input key={projection.rootKeys[0] ?? 'no-root'} ref={rootInput} id="graph-root" className="panel-search" defaultValue={projection.rootKeys[0] ?? ''} placeholder="Focus a canonical node key" />
            <button type="submit">Apply root</button>
            {projection.rootKeys.length ? <button type="button" onClick={() => onProjection({ rootKeys: [] })}>Clear root</button> : null}
          </form>
          <label>
            Direction
            <select value={projection.direction} onChange={(event) => onProjection({ direction: event.target.value as GraphProjectionInput['direction'] })}>
              <option value="both">Incoming and outgoing</option>
              <option value="outgoing">Outgoing</option>
              <option value="incoming">Incoming</option>
            </select>
          </label>
          <label>
            Depth
            <select value={projection.maxDepth} onChange={(event) => onProjection({ maxDepth: Number(event.target.value) })}>
              {[0, 1, 2, 3, 4, 5, 6].map((depth) => <option key={depth} value={depth}>{depth}</option>)}
            </select>
          </label>
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
            <select value={projection.nodeTypes[0] ?? ''} onChange={(event) => onProjection({ nodeTypes: event.target.value ? [event.target.value] : [] })}>
              <option value="">All node types</option>
              {nodeTypes.map((type) => <option key={type} value={type}>{readableType(type)}</option>)}
            </select>
          </label>
          <label>
            Relation type
            <select value={projection.edgeTypes[0] ?? ''} onChange={(event) => onProjection({ edgeTypes: event.target.value ? [event.target.value] : [] })}>
              <option value="">All relation types</option>
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
      </Panel>
      {graph ? (
        <div className={`graph-projection-status ${limited ? 'limited' : 'complete'}`} role="status" aria-live="polite">
          <strong>{limited ? 'Limited projection' : 'Complete within requested scope'}</strong>
          <span>{nodes.length} of {availableNodes} nodes and {edges.length} of {availableEdges} relationships included.</span>
          <span>Coverage: {graph.coverage?.state ?? 'not reported'}.</span>
          <span>Index: {graph.index_version ?? projection.indexVersion ?? 'active'}.</span>
          {graph.truncation?.reason ? <span>Reason: {readableType(graph.truncation.reason)}.</span> : <span>Not truncated.</span>}
          {graph.unsupported_hops?.length ? <span>{graph.unsupported_hops.length} requested root or hop could not be resolved.</span> : null}
          {graph.can_expand ? <button type="button" onClick={expandProjection}>Request a larger bounded projection</button> : null}
        </div>
      ) : null}
      <div className="graph-explorer-workspace">
        <section className="graph-stage-shell" aria-label="Interactive graph explorer">
          <div className="graph-stage-tools">
            <div className="graph-legend" aria-label="Node type legend">
              {['endpoint', 'router', 'service', 'repository', 'database', 'model'].map((type) => <span className={`legend-${type}`} key={type}>{readableType(type)}</span>)}
            </div>
            <div className="graph-zoom" aria-label="Graph zoom controls">
              <button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.55, value - 0.1))}>−</button>
              <output aria-label="Current zoom">{Math.round(zoom * 100)}%</output>
              <button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.25, value + 0.1))}>+</button>
              <button type="button" onClick={() => setZoom(0.9)}>Fit</button>
            </div>
          </div>
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
                  return (
                    <path
                      className={`graph-edge support-${edge.evidence_level ?? 'deep'} ${active ? 'active' : 'muted'}`}
                      d={edgePath(source, target)}
                      data-source={edge.source}
                      data-target={edge.target}
                      key={`${edge.source}-${edge.target}-${edge.type}-${index}`}
                      markerEnd="url(#graph-arrow)"
                    />
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
                    <span className="graph-node-type">{node.role || readableType(node.type)}</span>
                    <strong>{node.label}</strong>
                    <small>{node.file_path || node.scope_path || coverageLabel(node.coverage)}</small>
                  </button>
                )
              })}
              {!nodes.length && <p>No nodes are available within this projection. Clear or broaden the filters.</p>}
              <div className="graph-minimap" aria-hidden="true">
                {nodes.slice(0, 80).map((node) => {
                  const position = layout.positions.get(node.id)
                  return position ? <i key={node.id} style={{ left: position.x / 12, top: position.y / 12 }} /> : null
                })}
              </div>
            </div>
          </div>
          <details className="graph-relation-list" open>
            <summary>Accessible relation list ({edges.length})</summary>
            {edges.length ? (
              <ul>
                {edges.map((edge, index) => (
                  <li key={`${edge.source}-${edge.target}-${edge.type}-${index}`}>
                    <button type="button" onClick={() => selectNode(edge.source)}>{nodeById.get(edge.source)?.label ?? edge.source}</button>
                    <span>{readableType(edge.type)} · {supportLabel(edge.evidence_level)}</span>
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
                <div><span>{activeNode.role || readableType(activeNode.type)}</span><h2>{activeNode.label}</h2></div>
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
                  <PreviewLine label="Layer" value={activeNode.layer || layerForNode(activeNode).label} />
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
                <button type="button" onClick={() => onProjection({ rootKeys: [activeNode.id] })}>Focus path</button>
                <button type="button" onClick={() => onOpenImpact?.(activeNode)}>Analyze Impact</button>
                {activeNode.coverage !== 'deep_indexed' && activeNode.coverage !== 'skipped' ? (
                  <button type="button" onClick={() => onAnalyzeArea(activeNode.scope_path || activeNode.file_path || '')}>Analyze area</button>
                ) : null}
              </div>
            </>
          ) : <p>Select an area to inspect.</p>}
          <div className="graph-project-summary">
            <PreviewLine label="Endpoints" value={String(overview?.endpoints.length ?? 0)} />
            <PreviewLine label="Deterministic ordering" value={graph?.provenance?.deterministic_order ? 'Yes' : 'Not reported'} />
          </div>
        </aside>
      </div>
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

const graphViews: { id: GraphView; label: string }[] = [
  { id: 'project-map', label: 'Architecture' },
  { id: 'dependencies', label: 'Dependencies' },
  { id: 'api-flow', label: 'API Flow' },
  { id: 'function-flow', label: 'Function Flow' },
  { id: 'data-flow', label: 'Data Flow' },
]

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
  const value = `${node.layer ?? ''} ${node.type} ${node.role ?? ''}`.toLowerCase()
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

function readableType(type: string) {
  return type.replaceAll('_', ' ')
}

function unique(values: Array<string | undefined>) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort()
}
