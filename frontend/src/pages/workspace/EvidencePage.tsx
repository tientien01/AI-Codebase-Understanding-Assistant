import { EmptyState, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { Evidence } from '../../types/api'

export function EvidencePage({ evidence }: { evidence: Evidence | null }) {
  const sourceLines = evidence?.content_preview.split(/\r?\n/) ?? []

  return (
    <div>
      <PageTitle title="Evidence / Citation Viewer" subtitle="Verify AI answers by file path, line range, source preview, and retrieval reason." />
      {!evidence ? (
        <EmptyState title="No evidence selected" description="Ask the assistant or run search, then click a citation." />
      ) : (
        <div className="evidence-grid">
          <Panel title="Evidence details">
            <PreviewLine label="Evidence ID" value={evidence.evidence_id} />
            <PreviewLine label="Source type" value={evidence.source_type} />
            <PreviewLine label="File" value={evidence.file_path} />
            <PreviewLine label="Lines" value={`${evidence.start_line}-${evidence.end_line}`} />
            <PreviewLine label="Index version" value={String(evidence.index_version ?? 0)} />
            <PreviewLine label="Stale" value={evidence.is_stale ? 'Yes' : 'No'} />
            <PreviewLine label="Confidence" value={`${Math.round(evidence.confidence_score * 100)}%`} />
            <PreviewLine label="Retrieval" value={evidence.retrieval_source} />
          </Panel>
          <Panel title={`${evidence.file_path}:${evidence.start_line}-${evidence.end_line}`}>
            <div className="evidence-source" role="region" aria-label="Cited source preview" tabIndex={0}>
              {sourceLines.map((line, index) => (
                <div className="evidence-source-line" key={`${evidence.start_line + index}-${line}`}>
                  <span aria-hidden="true">{evidence.start_line + index}</span>
                  <code>{line || ' '}</code>
                </div>
              ))}
            </div>
            <div className="evidence-reason">
              <strong>Why this evidence was selected</strong>
              <p>{evidence.relevance_reason || 'Selected as supporting source for the cited answer.'}</p>
            </div>
          </Panel>
        </div>
      )}
    </div>
  )
}
