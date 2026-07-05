import { InDevelopmentInline, Panel, PreviewLine } from '../../components/common/ui'
import type { GraphData, Overview } from '../../types/api'

export function GraphDetails({ graph }: { graph: GraphData | null }) {
  return (
    <Panel title="Analysis Coverage">
      <PreviewLine label="Ready" value={String(graph?.nodes.filter((node) => node.coverage === 'deep_indexed').length ?? 0)} />
      <PreviewLine label="Needs analysis" value={String(graph?.nodes.filter((node) => node.coverage === 'mapped').length ?? 0)} />
      <PreviewLine label="Relationships" value={String(graph?.edges.length ?? 0)} />
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

export function ApiDetails({ overview }: { overview: Overview | null }) {
  const endpoint = overview?.endpoints[0]
  return (
    <Panel title="API Detail">
      {endpoint ? (
        <>
          <PreviewLine label="Path" value={endpoint.path} />
          <PreviewLine label="Method" value={endpoint.method} />
          <PreviewLine label="Handler" value={endpoint.handler} />
          <PreviewLine label="File" value={endpoint.file_path} />
        </>
      ) : (
        <p>No endpoint selected.</p>
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
      <InDevelopmentInline text="Graph trace and answer-to-evidence mapping will improve with the agent workflow." />
    </Panel>
  )
}
