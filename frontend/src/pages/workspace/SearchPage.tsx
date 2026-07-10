import type { FormEvent } from 'react'
import { PageTitle, Panel } from '../../components/common/ui'
import type { Citation, SearchResult } from '../../types/api'

export function SearchPage({
  query,
  results,
  onQuery,
  onSearch,
  onEvidence,
}: {
  query: string
  results: SearchResult[]
  onQuery: (value: string) => void
  onSearch: (event: FormEvent) => void
  onEvidence: (citation: Citation) => void
}) {
  return (
    <div>
      <PageTitle title="Search" subtitle="Find files, functions, endpoints, docs, tests, and concepts across the indexed codebase." />
      <form className="search-bar" onSubmit={onSearch}>
        <input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Search functions, files, endpoints, concepts..." />
        <button className="primary">Search</button>
      </form>
      <div className="toolbar">
        <span className="tab active">Hybrid</span>
        <span className="tab">Keyword</span>
        <span className="tab">Semantic</span>
        <span className="tab">Files</span>
        <span className="tab">Endpoints</span>
        <span className="tab">Docs</span>
      </div>
      <Panel title="Search Results">
        {results.length ? (
          results.map((result) => (
            <button
              className="result-card"
              key={result.evidence_id}
              onClick={() =>
                onEvidence({
                  evidence_id: result.evidence_id,
                  file_path: result.file_path,
                  symbol_name: result.title,
                  start_line: result.start_line,
                  end_line: result.end_line,
                  index_version: result.index_version,
                  is_stale: result.is_stale,
                })
              }
            >
              <span>{result.file_path}</span>
              <strong>{result.title}</strong>
              <p>{result.preview}</p>
              <span className="badge">{readableLabel(result.result_type ?? 'chunk')}</span>
              <span className="badge">{readableLabel(result.retrieval_source ?? 'hybrid')}</span>
              {result.matched_terms?.length ? <small>Matched: {result.matched_terms.slice(0, 5).join(', ')}</small> : null}
              {result.is_stale && <span className="badge amber">Stale evidence</span>}
              <em>{result.score}</em>
            </button>
          ))
        ) : (
          <p>No results yet. Run a search after indexing.</p>
        )}
      </Panel>
    </div>
  )
}

function readableLabel(value: string) {
  return value.replaceAll('_', ' ')
}
