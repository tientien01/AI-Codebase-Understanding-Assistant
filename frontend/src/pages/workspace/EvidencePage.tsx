import { EmptyState, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { Evidence } from '../../types/api'

export function EvidencePage({ evidence }: { evidence: Evidence | null }) {
  return (
    <div>
      <PageTitle title="Evidence / Citation Viewer" subtitle="Verify AI answers by file path, line range, source preview, and retrieval reason." />
      {!evidence ? (
        <EmptyState title="No evidence selected" description="Ask the assistant or run search, then click a citation." />
      ) : (
        <div className="evidence-grid">
          <Panel title="Citation Context">
            <PreviewLine label="Evidence ID" value={evidence.evidence_id} />
            <PreviewLine label="Source type" value={evidence.source_type} />
            <PreviewLine label="File" value={evidence.file_path} />
            <PreviewLine label="Lines" value={`${evidence.start_line}-${evidence.end_line}`} />
            <PreviewLine label="Index version" value={String(evidence.index_version ?? 0)} />
            <PreviewLine label="Stale" value={evidence.is_stale ? 'Yes' : 'No'} />
            <PreviewLine label="Confidence" value={String(evidence.confidence_score)} />
            <PreviewLine label="Retrieval" value={evidence.retrieval_source} />
          </Panel>
          <Panel title="Source Preview">
            <pre className="code-block compact">{evidence.content_preview}</pre>
            <p>{evidence.relevance_reason}</p>
          </Panel>
        </div>
      )}
    </div>
  )
}
