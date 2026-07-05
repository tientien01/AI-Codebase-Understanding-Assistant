import { useState } from 'react'
import { ListRow, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { GraphData, Overview } from '../../types/api'

type GraphNode = NonNullable<GraphData['nodes']>[number]

export function GraphPage({
  graph,
  overview,
  onAnalyzeArea,
}: {
  graph: GraphData | null
  overview: Overview | null
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
        <span className="tab active">Project Map</span>
        <span className="tab">Ready areas</span>
        <span className="tab">Needs analysis</span>
        <span className="tab">API Flow</span>
        <input className="panel-search" placeholder="Search node" />
      </div>
      <div className="graph-workspace">
        <Panel title="Repository Areas">
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
          <PreviewLine label="Ready areas" value={String(graph?.nodes.filter((node) => node.coverage === 'deep_indexed').length ?? 0)} />
          <PreviewLine label="Needs analysis" value={String(graph?.nodes.filter((node) => node.coverage === 'mapped').length ?? 0)} />
          <h3>Relationship sample</h3>
          {edges.map((edge) => <ListRow key={`${edge.source}-${edge.target}-${edge.type}`} title={readableType(edge.type)} detail={edge.evidence_level === 'map' ? 'Known from repository structure' : 'Backed by analyzed code'} meta={edge.evidence_level ?? 'deep'} />)}
        </Panel>
      </div>
    </div>
  )
}

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
