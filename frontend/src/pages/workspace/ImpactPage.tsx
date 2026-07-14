import type { FormEvent } from 'react'
import { ListRow, PageTitle, Panel, PreviewLine } from '../../components/common/ui'
import type { ImpactItem, ImpactResult, Overview } from '../../types/api'

export function ImpactPage({ overview, targetType, targetRef, result, onTargetType, onTargetRef, onRun }: {
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
      <PageTitle title="Diff Impact" subtitle="Assess confirmed, inferred, and unknown effects without turning missing graph coverage into a false no-impact result." />
      <div className="impact-compare-notice" role="status">
        <div><strong>Current active index</strong><span>Target impact is available.</span></div>
        <span className="impact-compare-arrow" aria-hidden="true">→</span>
        <div><strong>Historical comparison</strong><span>Unavailable: the compatibility API does not expose version snapshots.</span></div>
      </div>
      <div className="impact-grid">
        <Panel title="Analysis target">
          <form className="impact-form" onSubmit={onRun}>
            <label>
              Target type
              <select value={targetType} onChange={(event) => onTargetType(event.target.value)}>
                <option value="symbol">symbol</option><option value="file">file</option><option value="endpoint">endpoint</option><option value="model">model</option><option value="schema">schema</option>
              </select>
            </label>
            <label>
              Target reference
              <input value={targetRef} onChange={(event) => onTargetRef(event.target.value)} placeholder="login, GET /login, backend/app/main.py" />
            </label>
            <button className="primary">Analyze Current Impact</button>
          </form>
          <PreviewLine label="Indexed endpoints" value={String(overview?.endpoints.length ?? 0)} />
        </Panel>
        <Panel title="Impact summary">
          {result ? (
            <>
              <div className="impact-target"><span>Resolved target</span><strong>{targetLabel(result)}</strong></div>
              <div className="impact-summary-cards">
                <ImpactCount tone="direct" label="Direct" value={result.direct.length} />
                <ImpactCount tone="inferred" label="Inferred" value={result.indirect.length} />
                <ImpactCount tone="unknown" label="Unknown" value={result.missing_relations.length} />
              </div>
              <p className="impact-classification">Server classification: {readableLabel(result.risk_level)}. Inspect relation reasons rather than treating this label as a calibrated probability.</p>
            </>
          ) : <p>Choose a target and run analysis. Zero displayed results will not be described as zero impact.</p>}
        </Panel>
      </div>
      {result && (
        <>
          <div className="impact-result-groups">
            <ImpactList title="Direct" description="Current graph relations with non-inferred support." items={result.direct} />
            <ImpactList title="Inferred" description="Possible effects that require verification." items={result.indirect} />
            <Panel title="Unknown">
              {result.missing_relations.length ? result.missing_relations.map((item) => <ListRow key={item} title="Coverage gap" detail={item} />) : <p>No unresolved relation was reported. This does not prove complete repository coverage.</p>}
            </Panel>
          </div>
          <div className="impact-grid">
            <ImpactList title="Affected Endpoints" description="Endpoint relations reported for this target." items={result.affected_endpoints} />
            <ImpactList title="Affected Tests" description="Tests to inspect before accepting the change." items={result.affected_tests} />
            <ImpactList title="Affected Files" description="Files reached by the current bounded analysis." items={result.affected_files} />
            <Panel title="Verification checklist">
              {result.suggested_checks.length ? result.suggested_checks.map((item) => <label className="verification-check" key={item}><input type="checkbox" />{item}</label>) : <p>No deterministic check was suggested.</p>}
            </Panel>
          </div>
        </>
      )}
    </div>
  )
}

function ImpactCount({ tone, label, value }: { tone: string; label: string; value: number }) {
  return <div className={`impact-count tone-${tone}`}><strong>{value}</strong><span>{label}</span></div>
}

function ImpactList({ title, description, items }: { title: string; description: string; items: ImpactItem[] }) {
  return (
    <Panel title={title}>
      <p>{description}</p>
      {items.length ? items.slice(0, 12).map((item) => (
        <ListRow key={`${title}-${item.node_id}-${item.depth}`} title={item.label} detail={item.file_path ? `${item.file_path} — ${item.reason}` : item.reason} meta={`${readableLabel(item.node_type)} · depth ${item.depth}${item.via_edge ? ` · ${readableLabel(item.via_edge)}` : ''}`} />
      )) : <p>No item was returned in this group; inspect Unknown and coverage before concluding no impact.</p>}
    </Panel>
  )
}

function targetLabel(result: ImpactResult) {
  if (!result.target) return 'not resolved'
  const path = result.target.file_path ? ` — ${result.target.file_path}` : ''
  const lines = result.target.line_range ? `:${result.target.line_range}` : ''
  return `${result.target.label}${path}${lines}`
}

function readableLabel(value: string) {
  return value.replaceAll('_', ' ')
}
