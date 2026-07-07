import { useState } from 'react'
import { ListRow, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { GraphData, GraphView, Overview } from '../../types/api'

type GraphNode = NonNullable<GraphData['nodes']>[number]

export function GraphPage({
  graph,
  graphView,
  overview,
  onGraphView,
  onAnalyzeArea,
}: {
  graph: GraphData | null
  graphView: GraphView
  overview: Overview | null
  onGraphView: (view: GraphView) => void
  onAnalyzeArea: (scopePath: string) => void
}) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const nodes = graph?.nodes.slice(0, 18) ?? []
  const edges = graph?.edges.slice(0, 8) ?? []
  const activeNode = selectedNode ?? nodes[0]
  return (
    <div>
      <PageTitle title="Project Map" subtitle="Explore the main areas of this repository and analyze details only when needed." />
      <div className="toolbar graph-toolbar">
        {graphViews.map((view) => (
          <button type="button" className={`tab ${graphView === view.id ? 'active' : ''}`} key={view.id} onClick={() => onGraphView(view.id)}>
            {view.label}
          </button>
        ))}
        <input className="panel-search" placeholder="Search node" />
      </div>
      <div className="graph-workspace">
        <Panel title={graphViews.find((view) => view.id === graphView)?.label ?? 'Graph'}>
          <div className="graph-canvas">
            {nodes.map((node, index) => (
              <button
                type="button"
                className={`graph-node type-${node.type} coverage-${node.coverage ?? 'deep_indexed'} ${activeNode?.id === node.id ? 'active' : ''}`}
                key={node.id}
                style={{ left: `${6 + (index % 4) * 23}%`, top: `${12 + Math.floor(index / 4) * 22}%` }}
                onClick={() => setSelectedNode(node)}
              >
                <strong>{node.label}</strong>
                <span>{node.role || readableType(node.type)}</span>
                <em>{coverageLabel(node.coverage)}</em>
              </button>
            ))}
            {!nodes.length && <p>No graph available. Index a repository first.</p>}
          </div>
        </Panel>
        <Panel title={activeNode?.label ?? 'Area details'}>
          {activeNode ? (
            <>
              <PreviewLine label="Status" value={coverageLabel(activeNode.coverage)} />
              <PreviewLine label="Type" value={activeNode.role || readableType(activeNode.type)} />
              <PreviewLine label="Path" value={activeNode.scope_path || activeNode.file_path || 'project root'} />
              {activeNode.coverage !== 'deep_indexed' && activeNode.coverage !== 'skipped' ? (
                <button className="primary wide" onClick={() => onAnalyzeArea(activeNode.scope_path || activeNode.file_path || '')}>
                  Analyze this area
                </button>
              ) : null}
            </>
          ) : (
            <p>Select an area to inspect.</p>
          )}
          <h3>Project summary</h3>
          <PreviewLine label="Endpoints" value={String(overview?.endpoints.length ?? 0)} />
          <PreviewLine label="Nodes in view" value={String(graph?.nodes.length ?? 0)} />
          <PreviewLine label="Relationships" value={String(graph?.edges.length ?? 0)} />
          <h3>Relationship sample</h3>
          {edges.map((edge) => <ListRow key={`${edge.source}-${edge.target}-${edge.type}`} title={readableType(edge.type)} detail={edge.evidence_level === 'map' ? 'Known from repository structure' : 'Backed by analyzed code'} meta={edge.evidence_level ?? 'deep'} />)}
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

function readableType(type: string) {
  return type.replaceAll('_', ' ')
}
