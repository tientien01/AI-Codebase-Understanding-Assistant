import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { GraphData, GraphProjectionInput, GraphView, Overview } from '../../types/api'

export function GraphPage({
  graph,
  graphView,
  projection,
  overview,
  onGraphView,
  onProjection,
  onAnalyzeArea,
}: {
  graph: GraphData | null
  graphView: GraphView
  projection: GraphProjectionInput
  overview: Overview | null
  onGraphView: (view: GraphView) => void
  onProjection: (patch: Partial<GraphProjectionInput>) => void
  onAnalyzeArea: (scopePath: string) => void
}) {
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const rootInput = useRef<HTMLInputElement>(null)
  const nodes = graph?.nodes ?? []
  const edges = graph?.edges ?? []
  const nodeById = new Map(nodes.map((node) => [node.id, node]))
  const activeNode = nodeById.get(selectedNodeId ?? '') ?? nodes[0]
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

  return (
    <div>
      <PageTitle title="Project Map" subtitle="Explore a server-bounded relationship projection with explicit coverage and provenance." />
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
          {graph.truncation?.reason ? <span>Reason: {readableType(graph.truncation.reason)}.</span> : null}
          {graph.unsupported_hops?.length ? <span>{graph.unsupported_hops.length} requested root or hop could not be resolved.</span> : null}
          {graph.can_expand ? <button type="button" onClick={expandProjection}>Request a larger bounded projection</button> : null}
        </div>
      ) : null}
      <div className="graph-workspace">
        <Panel title={graphViews.find((view) => view.id === graphView)?.label ?? 'Graph'}>
          <div className="graph-canvas" aria-label="Graph nodes">
            {nodes.map((node) => (
              <button
                type="button"
                className={`graph-node type-${node.type} coverage-${node.coverage ?? 'deep_indexed'} ${activeNode?.id === node.id ? 'active' : ''}`}
                key={node.id}
                onClick={() => setSelectedNodeId(node.id)}
              >
                <strong>{node.label}</strong>
                <span>{node.role || readableType(node.type)}</span>
                <em>{coverageLabel(node.coverage)}</em>
              </button>
            ))}
            {!nodes.length && <p>No nodes are available within this projection. Clear or broaden the filters.</p>}
          </div>
          <details className="graph-relation-list" open>
            <summary>Accessible relation list ({edges.length})</summary>
            {edges.length ? (
              <ul>
                {edges.map((edge, index) => (
                  <li key={`${edge.source}-${edge.target}-${edge.type}-${index}`}>
                    <button type="button" onClick={() => setSelectedNodeId(edge.source)}>{nodeById.get(edge.source)?.label ?? edge.source}</button>
                    <span>{readableType(edge.type)} · {supportLabel(edge.evidence_level)}</span>
                    <button type="button" onClick={() => setSelectedNodeId(edge.target)}>{nodeById.get(edge.target)?.label ?? edge.target}</button>
                  </li>
                ))}
              </ul>
            ) : <p>No supported relationships are included in this projection.</p>}
          </details>
        </Panel>
        <Panel title={activeNode?.label ?? 'Area details'}>
          {activeNode ? (
            <>
              <PreviewLine label="Status" value={coverageLabel(activeNode.coverage)} />
              <PreviewLine label="Type" value={activeNode.role || readableType(activeNode.type)} />
              <PreviewLine label="Layer" value={activeNode.layer || 'application'} />
              <PreviewLine label="Path" value={activeNode.scope_path || activeNode.file_path || 'project root'} />
              {activeNode.start_line ? <PreviewLine label="Lines" value={`${activeNode.start_line}-${activeNode.end_line ?? activeNode.start_line}`} /> : null}
              {activeNode.summary ? <PreviewLine label="Summary" value={activeNode.summary} /> : null}
              <button className="wide" type="button" onClick={() => onProjection({ rootKeys: [activeNode.id] })}>Focus projection here</button>
              {activeNode.coverage !== 'deep_indexed' && activeNode.coverage !== 'skipped' ? (
                <button className="primary wide" type="button" onClick={() => onAnalyzeArea(activeNode.scope_path || activeNode.file_path || '')}>
                  Analyze this area
                </button>
              ) : null}
            </>
          ) : <p>Select an area to inspect.</p>}
          <h3>Project summary</h3>
          <PreviewLine label="Endpoints" value={String(overview?.endpoints.length ?? 0)} />
          <PreviewLine label="Nodes included" value={String(nodes.length)} />
          <PreviewLine label="Relationships included" value={String(edges.length)} />
          <PreviewLine label="Ordering" value={graph?.provenance?.deterministic_order ? 'Deterministic' : 'Not reported'} />
        </Panel>
      </div>
    </div>
  )
}

const graphViews: { id: GraphView; label: string }[] = [
  { id: 'project-map', label: 'Project Map' },
  { id: 'dependencies', label: 'Dependencies' },
  { id: 'api-flow', label: 'API Flow' },
  { id: 'function-flow', label: 'Function Flow' },
  { id: 'data-flow', label: 'Data Flow' },
]

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
