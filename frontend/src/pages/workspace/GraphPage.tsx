import { ListRow, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { GraphData, Overview } from '../../types/api'

export function GraphPage({ graph, overview }: { graph: GraphData | null; overview: Overview | null }) {
  const nodes = graph?.nodes.slice(0, 18) ?? []
  const edges = graph?.edges.slice(0, 8) ?? []
  return (
    <div>
      <PageTitle title="Graph View" subtitle="Visualize file, symbol, endpoint, and API call relationships." />
      <div className="toolbar graph-toolbar">
        <span className="tab active">Module Graph</span>
        <span className="tab">Call Graph</span>
        <span className="tab">API Flow</span>
        <span className="tab">Impact Graph</span>
        <input className="panel-search" placeholder="Search node" />
      </div>
      <div className="graph-workspace">
        <Panel title="Codebase Graph">
          <div className="graph-canvas">
            {nodes.map((node, index) => (
              <div className={`graph-node type-${node.type}`} key={node.id} style={{ left: `${6 + (index % 4) * 23}%`, top: `${12 + Math.floor(index / 4) * 22}%` }}>
                <strong>{node.label}</strong>
                <span>{node.type}</span>
              </div>
            ))}
            {!nodes.length && <p>No graph available. Index a repository first.</p>}
          </div>
        </Panel>
        <Panel title="Selected Node Details">
          <PreviewLine label="Graph nodes" value={String(graph?.nodes.length ?? 0)} />
          <PreviewLine label="Graph edges" value={String(graph?.edges.length ?? 0)} />
          <PreviewLine label="Endpoints" value={String(overview?.endpoints.length ?? 0)} />
          <h3>Relation sample</h3>
          {edges.map((edge) => <ListRow key={`${edge.source}-${edge.target}-${edge.type}`} title={edge.type} detail={`${edge.source} -> ${edge.target}`} meta={String(edge.confidence)} />)}
        </Panel>
      </div>
    </div>
  )
}
