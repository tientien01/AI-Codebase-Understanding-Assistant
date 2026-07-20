import { Panel, PreviewLine } from '../../components/common/ui'
import type { ApiEndpoint, GraphData } from '../../types/api'

export function GraphDetails({ graph }: { graph: GraphData | null }) {
  const includedNodes = graph?.counts?.included_nodes ?? graph?.nodes.length ?? 0
  const availableNodes = graph?.counts?.available_nodes ?? includedNodes
  const includedEdges = graph?.counts?.included_edges ?? graph?.edges.length ?? 0
  const availableEdges = graph?.counts?.available_edges ?? includedEdges
  return (
    <Panel title="Analysis Coverage">
      <PreviewLine label="Ready" value={String(graph?.nodes.filter((node) => node.coverage === 'deep_indexed').length ?? 0)} />
      <PreviewLine label="Needs analysis" value={String(graph?.nodes.filter((node) => node.coverage === 'mapped').length ?? 0)} />
      <PreviewLine label="Nodes included" value={`${includedNodes} of ${availableNodes}`} />
      <PreviewLine label="Relationships included" value={`${includedEdges} of ${availableEdges}`} />
      <PreviewLine label="Projection state" value={graph?.coverage?.state === 'limited' ? 'Limited' : 'Complete within scope'} />
      <PreviewLine label="Truncation" value={graph?.truncation?.reason?.replaceAll('_', ' ') ?? 'None'} />
      <h3>Status</h3>
      <div className="setting-chips">
        <span>Ready</span>
        <span>Analyzing</span>
        <span>Needs analysis</span>
        <span>Skipped</span>
      </div>
    </Panel>
  )
}

export function ApiDetails({
  endpoint,
  requestedEndpointKey,
  onOpenSource,
  onTraceFlow,
}: {
  endpoint?: ApiEndpoint
  requestedEndpointKey?: string
  onOpenSource: (endpoint: ApiEndpoint) => void
  onTraceFlow: (endpoint: ApiEndpoint) => void
}) {
  return (
    <Panel title="API Detail">
      {endpoint ? (
        <>
          <PreviewLine label="Path" value={endpoint.path} />
          <PreviewLine label="Method" value={endpoint.method} />
          <PreviewLine label="Handler" value={endpoint.handler} />
          <PreviewLine label="File" value={endpoint.file_path} />
          <PreviewLine label="Lines" value={`${endpoint.start_line}-${endpoint.end_line}`} />
          {endpoint.metadata?.framework && <PreviewLine label="Framework" value={endpoint.metadata.framework} />}
          <div className="api-detail-actions">
            <button type="button" className="primary" onClick={() => onOpenSource(endpoint)}>Open source</button>
            <button type="button" className="secondary" onClick={() => onTraceFlow(endpoint)}>Trace request flow</button>
          </div>
          <p className="api-detail-note">Auth and schema details appear only when supported by deterministic indexed evidence.</p>
        </>
      ) : (
        <p>{requestedEndpointKey
          ? 'This endpoint is not available in the active index. Select another endpoint.'
          : 'Select an endpoint to inspect its handler and source evidence.'}</p>
      )}
    </Panel>
  )
}

export function SearchFilters() {
  return (
    <Panel title="Filters">
      <h3>Scope</h3>
      <div className="setting-chips"><span>Files</span><span>Functions</span><span>Classes</span><span>Endpoints</span><span>Docs</span><span>Tests</span></div>
      <h3>Areas</h3>
      <div className="setting-chips"><span>Frontend</span><span>Backend</span><span>Config</span></div>
    </Panel>
  )
}

export function EvidenceSummary() {
  return (
    <Panel title="Evidence">
      <p>Click a citation from chat or search to open the Evidence Viewer.</p>
      <p className="evidence-side-note">Each citation opens the exact indexed file range and explains why it supports the answer.</p>
    </Panel>
  )
}
