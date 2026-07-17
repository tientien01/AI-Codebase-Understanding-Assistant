import { EmptyState, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { Evidence } from '../../types/api'

export function EvidencePage({ evidence, onOpenCode }: { evidence: Evidence | null; onOpenCode?: (filePath: string, line: number) => void }) {
  const sourceLines = evidence?.content_preview.split(/\r?\n/) ?? []

  return (
    <div>
      <PageTitle title="Evidence / Citation Viewer" subtitle="Verify AI answers by file path, line range, source preview, and retrieval reason." />
      {!evidence ? (
        <EmptyState title="No evidence selected" description="Ask the assistant or run search, then click a citation." />
      ) : (
        <div className="evidence-grid evidence-viewer-grid">
          <Panel title="Citation summary">
            <div className="evidence-location">
              <span className={`badge ${evidence.is_stale ? 'amber' : 'green'}`}>{evidence.is_stale ? 'Stale evidence' : 'Current evidence'}</span>
              <strong>{evidence.file_path}</strong>
              <span>Lines {evidence.start_line}–{evidence.end_line} · Index v{evidence.index_version ?? 0}</span>
            </div>
            <div className="evidence-metadata">
              <PreviewLine label="Support" value={evidence.source_type} />
              <PreviewLine label="Retrieval" value={evidence.retrieval_source} />
              <PreviewLine label="Confidence" value={`${Math.round(evidence.confidence_score * 100)}%`} />
            </div>
            <button className="primary wide" type="button" onClick={() => onOpenCode?.(evidence.file_path, evidence.start_line)}>Open in Code Explorer</button>
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
