import type { FormEvent } from 'react'
import { ListRow, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { ImpactItem, ImpactResult, Overview } from '../../types/api'

export function ImpactPage({
  overview,
  targetType,
  targetRef,
  result,
  onTargetType,
  onTargetRef,
  onRun,
}: {
  overview: Overview | null
  targetType: string
  targetRef: string
  result: ImpactResult | null
  onTargetType: (value: string) => void
  onTargetRef: (value: string) => void
  onRun: (event: FormEvent) => void
}) {
  return (
    <div>
      <PageTitle title="Impact Analysis" subtitle="Understand direct and indirect effects before changing a file, symbol, endpoint, or model." />
      <div className="impact-grid">
        <Panel title="Target">
          <form className="impact-form" onSubmit={onRun}>
            <label>
              Target type
              <select value={targetType} onChange={(event) => onTargetType(event.target.value)}>
                <option value="symbol">symbol</option>
                <option value="file">file</option>
                <option value="endpoint">endpoint</option>
                <option value="model">model</option>
                <option value="schema">schema</option>
              </select>
            </label>
            <label>
              Target reference
              <input value={targetRef} onChange={(event) => onTargetRef(event.target.value)} placeholder="login, GET /login, backend/app/main.py" />
            </label>
            <button className="primary">Run Impact Analysis</button>
          </form>
          <PreviewLine label="Indexed endpoints" value={String(overview?.endpoints.length ?? 0)} />
        </Panel>
        <Panel title="Impact Result">
          {result ? (
            <div className="impact-columns">
              <PreviewLine label="Risk" value={`${result.risk_level} (${result.risk_score})`} />
              <PreviewLine label="Target" value={targetLabel(result)} />
              <PreviewLine label="Direct" value={String(result.direct.length)} />
              <PreviewLine label="Indirect" value={String(result.indirect.length)} />
              <PreviewLine label="Files" value={String(result.affected_files.length)} />
              <PreviewLine label="Endpoints" value={String(result.affected_endpoints.length)} />
              <PreviewLine label="Tests" value={String(result.affected_tests.length)} />
            </div>
          ) : (
            <p>Choose a file, symbol, endpoint, model, or schema target and run analysis.</p>
          )}
        </Panel>
      </div>
      {result && (
        <div className="impact-grid">
          <ImpactList title="Direct Impact" items={result.direct} />
          <ImpactList title="Affected Endpoints" items={result.affected_endpoints} />
          <ImpactList title="Affected Tests" items={result.affected_tests} />
          <ImpactList title="Suggested Checks" items={result.suggested_checks.map((item, index) => ({ node_id: `check-${index}`, node_type: 'check', label: item, depth: 0, confidence: 1, reason: item }))} />
          {result.missing_relations.length ? (
            <Panel title="Known Gaps">
              {result.missing_relations.map((item) => <ListRow key={item} title="Missing relation" detail={item} />)}
            </Panel>
          ) : null}
          <ImpactList title="Affected Files" items={result.affected_files} />
        </div>
      )}
    </div>
  )
}

function ImpactList({ title, items }: { title: string; items: ImpactItem[] }) {
  return (
    <Panel title={title}>
      {items.length ? (
        items.slice(0, 8).map((item) => (
          <ListRow
            key={`${title}-${item.node_id}-${item.depth}`}
            title={item.label}
            detail={item.file_path ? `${item.file_path} - ${item.reason}` : item.reason}
            meta={`${readableLabel(item.node_type)} d${item.depth} ${Math.round(item.confidence * 100)}%`}
          />
        ))
      ) : (
        <p>No related items found in the current graph.</p>
      )}
    </Panel>
  )
}

function targetLabel(result: ImpactResult) {
  if (!result.target) return 'not resolved'
  const path = result.target.file_path ? ` - ${result.target.file_path}` : ''
  const lines = result.target.line_range ? `:${result.target.line_range}` : ''
  return `${result.target.label}${path}${lines}`
}

function readableLabel(value: string) {
  return value.replaceAll('_', ' ')
}
