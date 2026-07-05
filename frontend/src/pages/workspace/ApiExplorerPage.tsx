import { PageTitle, Panel } from '../../components/common/ui'
import type { Overview } from '../../types/api'

export function ApiExplorerPage({ overview }: { overview: Overview | null }) {
  const endpoints = overview?.endpoints ?? []
  return (
    <div>
      <PageTitle title="API Explorer" subtitle="Detected FastAPI endpoints, handler files, modules, and source line ranges." />
      <div className="api-layout">
        <Panel title="Endpoints">
          <div className="toolbar">
            <span className="tab active">All</span>
            <span className="tab">GET</span>
            <span className="tab">POST</span>
            <span className="tab">Auth required</span>
          </div>
          <table className="api-table">
            <thead><tr><th>Method</th><th>Path</th><th>Handler</th><th>File</th><th>Lines</th></tr></thead>
            <tbody>
              {endpoints.map((endpoint) => (
                <tr key={`${endpoint.method}-${endpoint.path}-${endpoint.start_line}`}>
                  <td><span className={`method ${endpoint.method.toLowerCase()}`}>{endpoint.method}</span></td>
                  <td>{endpoint.path}</td>
                  <td>{endpoint.handler}</td>
                  <td>{endpoint.file_path}</td>
                  <td>{endpoint.start_line}-{endpoint.end_line}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!endpoints.length && <p>No endpoint detected.</p>}
        </Panel>
      </div>
    </div>
  )
}
