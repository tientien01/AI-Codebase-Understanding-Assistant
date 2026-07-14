import { AsyncStateNotice } from '../../components/common/AsyncState'
import { ConfigRow, PageTitle, Panel } from '../../components/common/ui'
import type { AsyncViewState } from '../../features/server-state'
import type { IndexStatus, Repository } from '../../types/api'

const evaluationApis = [
  'GET /evaluation/datasets',
  'POST /evaluation/runs',
  'GET /evaluation/runs/{run_id}',
  'GET /evaluation/runs/{run_id}/results',
]

export function EvaluationPage({
  repository,
  indexStatus,
  indexState,
  onRetry,
}: {
  repository?: Repository
  indexStatus: IndexStatus | null
  indexState: AsyncViewState
  onRetry: () => void
}) {
  const activeIndex = repository?.current_index_version ?? indexStatus?.index_version
  return (
    <div className="truthful-workspace-page">
      <PageTitle
        title="Evaluation"
        subtitle="Inspect the current repository context and whether an interactive, reproducible evaluation run is available."
      />

      <div className="readiness-context" aria-label="Current evaluation context">
        <span>Repository context</span>
        <strong>{repository?.name ?? 'No repository selected'}</strong>
        <small>Repository lifecycle: {repository?.status ?? 'unavailable'}</small>
        <small>Active index: {activeIndex ?? 'unavailable'}</small>
      </div>

      <div className="evaluation-grid">
        <Panel title="Interactive evaluation">
          <AsyncStateNotice state={{
            kind: 'unavailable',
            message: 'The public dataset, run, status, and result APIs are not implemented. No benchmark question, metric, threshold, or run result can be shown safely yet.',
          }} />
          <p className="boundary-copy">
            Offline deterministic CI evidence protects regressions, but it is not a user-triggered evaluation run and is not presented as one here.
          </p>
        </Panel>

        <Panel title="Current repository and index">
          <AsyncStateNotice state={indexState} onRetry={onRetry} />
          <ConfigRow label="Repository" value={repository?.name ?? 'Unavailable'} />
          <ConfigRow label="Repository lifecycle" value={readable(repository?.status)} />
          <ConfigRow label="Active index" value={activeIndex === undefined ? 'Unavailable' : String(activeIndex)} />
          <ConfigRow label="Index job state" value={readable(indexStatus?.status)} />
          <ConfigRow label="Current index stage" value={readable(indexStatus?.current_step)} />
          <ConfigRow
            label="Indexed source files"
            value={indexStatus ? `${indexStatus.processed_files} of ${indexStatus.total_files}` : 'Unavailable'}
          />
        </Panel>

        <Panel title="Missing accepted API prerequisites">
          <ul className="contract-list" aria-label="Missing evaluation APIs">
            {evaluationApis.map((endpoint) => <li key={endpoint}><code>{endpoint}</code></li>)}
          </ul>
        </Panel>

        <Panel title="Next safe action">
          <p className="boundary-copy">
            Implement and verify the accepted evaluation run lifecycle with frozen identities and per-case evidence before enabling run controls or metrics on this page.
          </p>
        </Panel>
      </div>
    </div>
  )
}

function readable(value: string | undefined) {
  if (!value) return 'Unavailable'
  return value.replaceAll('_', ' ').replace(/^./, (character) => character.toUpperCase())
}
