import { useMemo, useState } from 'react'
import { PageTitle, Panel } from '../../components/common/ui'
import type { ApiEndpoint } from '../../types/api'
import { endpointKeyFor } from '../../utils/apiEndpoint'

type ApiExplorerPageProps = {
  endpoints: ApiEndpoint[]
  selectedEndpointKey?: string
  onSelectEndpoint: (endpointKey: string) => void
}

export function ApiExplorerPage({ endpoints, selectedEndpointKey, onSelectEndpoint }: ApiExplorerPageProps) {
  const [query, setQuery] = useState('')
  const [method, setMethod] = useState('ALL')
  const methods = useMemo(
    () => [...new Set(endpoints.map((endpoint) => endpoint.method.toUpperCase()))].sort(),
    [endpoints],
  )
  const filteredEndpoints = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return endpoints.filter((endpoint) => {
      if (method !== 'ALL' && endpoint.method.toUpperCase() !== method) return false
      if (!normalizedQuery) return true
      return [endpoint.path, endpoint.handler, endpoint.file_path]
        .some((value) => value.toLowerCase().includes(normalizedQuery))
    })
  }, [endpoints, method, query])
  const filtersActive = method !== 'ALL' || Boolean(query.trim())

  return (
    <div className="api-explorer-page">
      <PageTitle title="API Explorer" subtitle="Browse detected endpoints, handlers, source locations, and supported request flows." />
      <Panel title={`Endpoints (${filteredEndpoints.length} of ${endpoints.length})`}>
        <div className="api-filter-row">
          <label className="api-search">
            <span>Search endpoints</span>
            <input
              type="search"
              value={query}
              placeholder="Path, handler, or source file"
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          {filtersActive && (
            <button type="button" className="secondary" onClick={() => { setQuery(''); setMethod('ALL') }}>
              Clear filters
            </button>
          )}
        </div>
        <div className="toolbar api-method-filters" aria-label="Filter endpoints by HTTP method">
          {['ALL', ...methods].map((candidate) => (
            <button
              type="button"
              className={`tab ${method === candidate ? 'active' : ''}`}
              aria-pressed={method === candidate}
              onClick={() => setMethod(candidate)}
              key={candidate}
            >
              {candidate === 'ALL' ? 'All methods' : candidate}
            </button>
          ))}
        </div>
        <div className="api-table-scroll">
          <table className="api-table">
            <thead><tr><th>Method</th><th>Path</th><th>Handler</th><th>File</th><th>Lines</th></tr></thead>
            <tbody>
              {filteredEndpoints.map((endpoint) => {
                const endpointKey = endpointKeyFor(endpoint)
                const selected = endpointKey === selectedEndpointKey
                return (
                  <tr className={selected ? 'selected' : ''} aria-selected={selected} key={endpointKey}>
                    <td><span className={`method ${endpoint.method.toLowerCase()}`}>{endpoint.method}</span></td>
                    <td>
                      <button
                        type="button"
                        className="api-endpoint-select"
                        aria-label={`Select ${endpoint.method} ${endpoint.path}`}
                        onClick={() => onSelectEndpoint(endpointKey)}
                      >
                        {endpoint.path}
                      </button>
                    </td>
                    <td>{endpoint.handler}</td>
                    <td>{endpoint.file_path}</td>
                    <td>{endpoint.start_line}-{endpoint.end_line}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {!endpoints.length && <p role="status">No API endpoint was detected in the active index.</p>}
        {Boolean(endpoints.length) && !filteredEndpoints.length && (
          <p role="status">No endpoint matches the current filters.</p>
        )}
      </Panel>
    </div>
  )
}
