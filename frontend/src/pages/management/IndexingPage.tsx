import { ListRow, Metric, PageTitle, Panel, PreviewLine, Progress } from '../../components/common/ui'
import { pipelineSteps } from '../../config/navigation'
import type { IndexStatus, Repository } from '../../types/api'
import { isRepositoryUsable, reconcileRepositoryIndexStatus } from '../../utils/repository'

export function IndexingPage({
  repository,
  status,
  onOpen,
  onPause,
  onResume,
  onCancel,
}: {
  repository?: Repository
  status: IndexStatus | null
  onOpen: () => void
  onPause: () => void
  onResume: () => void
  onCancel: () => void
}) {
  const readyRepository = reconcileRepositoryIndexStatus(repository, status)
  const progress = status?.progress ?? (isRepositoryUsable(readyRepository) ? 100 : 0)
  const currentStageIndex = stageIndexFor(status?.current_step, status?.status, progress)
  const isRunning = status?.status === 'running'
  const isPaused = status?.status === 'paused'
  const isCancelling = status?.status === 'cancelling'
  const completed = isRepositoryUsable(readyRepository) || status?.status === 'completed' || status?.status === 'completed_with_warnings'
  const statusLabel = formatStatus(status?.status ?? repository?.status ?? 'not started')
  const skippedFiles = status?.skipped_files ?? 0
  const failedFiles = status?.failed_files ?? 0
  const warningCount = status?.warnings.length ?? 0
  const symbols = status?.stats.symbols ?? repository?.symbols ?? 0
  const endpoints = status?.stats.endpoints ?? repository?.endpoints ?? 0
  const chunks = status?.stats.chunks ?? repository?.chunks ?? 0
  const graphNodes = status?.stats.graph_nodes ?? repository?.graph_nodes ?? 0
  const activityLogs = (status?.logs ?? []).slice(-8).map(formatLogLine)

  return (
    <div>
      <PageTitle title={`Index Job: ${repository?.name ?? 'No project selected'}`} subtitle="Preparing this repository for search, code exploration, graph view, and cited answers." />
      <div className="indexing-header">
        <div>
          <span className="status-dot">Status: {statusLabel}</span>
          <div className="progress-line">
            <strong>{progress}%</strong>
            <Progress value={progress} />
            <span>{status?.processed_files ?? 0} / {status?.total_files ?? 0} files</span>
          </div>
        </div>
        <div className="header-actions">
          {isRunning && <button className="secondary" onClick={onPause}>Pause</button>}
          {isPaused && <button className="secondary" onClick={onResume}>Resume</button>}
          {(isRunning || isPaused || isCancelling) && <button className="secondary" disabled={isCancelling} onClick={onCancel}>{isCancelling ? 'Cancelling' : 'Cancel'}</button>}
          <button className="primary" disabled={!isRepositoryUsable(readyRepository)} onClick={onOpen}>Open Workspace</button>
        </div>
      </div>
      <div className="indexing-grid">
        <Panel title="Indexing Pipeline">
          <ol className="pipeline">
            {pipelineSteps.map((step, index) => {
              const done = completed || index < currentStageIndex
              const active = !done && index === currentStageIndex
              return (
                <li key={step} className={done ? 'done' : active ? 'active' : ''}>
                  <span>{index + 1}</span>
                  <div>
                    <strong>{step}</strong>
                    <small>{done ? 'Completed' : active ? activeStageLabel(status?.status) : 'Queued'}</small>
                  </div>
                </li>
              )
            })}
          </ol>
        </Panel>
        <div className="index-center">
          <Panel title={completed ? 'Index Result' : 'Current Stage'}>
            <PreviewLine label="Stage" value={formatStep(status?.current_step ?? 'Waiting for job')} />
            <PreviewLine label="Files processed" value={`${status?.processed_files ?? 0} / ${status?.total_files ?? 0}`} />
            <Progress value={progress} />
          </Panel>
          <Panel title="Diagnostics">
            <div className="insight-grid">
              <Metric label="Warnings" value={warningCount} />
              <Metric label="Skipped Files" value={skippedFiles} />
              <Metric label="Failed Files" value={failedFiles} />
            </div>
            {status?.error_message && <ListRow title={status.error_code ?? 'Indexing failed'} detail={status.error_message} />}
            {status?.warnings.length ? status.warnings.slice(0, 5).map((warning) => <ListRow key={warning} title={warning} detail="Review scanner or parser warning." />) : <p>No warnings or failed files reported.</p>}
          </Panel>
          <Panel title="Activity Log">
            <div className="log-box">{activityLogs.length ? activityLogs.map((log, index) => <p key={`${log.time}-${log.message}-${index}`}><span>{log.time}</span>{log.message}</p>) : <p>No job log yet.</p>}</div>
          </Panel>
        </div>
        <aside className="right-stack">
          <Panel title="Index Output">
            <div className="insight-grid">
              <Metric label="Files Indexed" value={status?.processed_files ?? repository?.indexed_files ?? 0} />
              <Metric label="Symbols" value={symbols} />
              <Metric label="Endpoints" value={endpoints} />
              <Metric label="Chunks" value={chunks} />
              <Metric label="Graph Nodes" value={graphNodes} />
              <Metric label="Index Version" value={status?.index_version ?? repository?.current_index_version ?? 0} />
            </div>
          </Panel>
          <Panel title="Job Timing">
            <PreviewLine label="Started" value={formatDateTime(status?.started_at)} />
            <PreviewLine label="Finished" value={formatDateTime(status?.finished_at)} />
            <PreviewLine label="Duration" value={formatDuration(status?.started_at, status?.finished_at)} />
          </Panel>
        </aside>
      </div>
    </div>
  )
}

function stageIndexFor(step?: string, status?: string, progress = 0) {
  if (status === 'completed' || status === 'completed_with_warnings' || progress >= 100) return pipelineSteps.length
  if (status === 'cancelled' || status === 'failed') return Math.min(Math.floor((progress / 100) * pipelineSteps.length), pipelineSteps.length - 1)
  const normalized = step ?? ''
  if (normalized === 'queued') return 0
  if (normalized === 'scan_repository_files' || normalized === 'apply_ignore_rules') return 1
  if (normalized === 'parse_source_code') return 3
  if (normalized === 'create_chunks') return 4
  if (normalized === 'build_code_graph') return 5
  if (normalized === 'finalize' || normalized === 'completed') return 7
  return Math.min(Math.floor((progress / 100) * pipelineSteps.length), pipelineSteps.length - 1)
}

function activeStageLabel(status?: string) {
  if (status === 'paused') return 'Paused'
  if (status === 'cancelling') return 'Cancelling'
  if (status === 'failed') return 'Failed'
  return 'In Progress'
}

function formatStatus(status: string) {
  return status.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatStep(step: string) {
  const labels: Record<string, string> = {
    queued: 'Preparing source',
    scan_repository_files: 'Scanning and filtering files',
    apply_ignore_rules: 'Scanning and filtering files',
    parse_source_code: 'Extracting code structure',
    create_chunks: 'Creating searchable chunks',
    build_code_graph: 'Building relationship graph',
    finalize: 'Saving index',
    completed: 'Completed',
    cancelled: 'Cancelled',
    cancelled_previous_index_retained: 'Cancelled, previous index retained',
    index_failed_previous_index_retained: 'Failed, previous index retained',
  }
  return labels[step] ?? formatStatus(step)
}

function formatLogLine(log: string) {
  const [timestamp, ...messageParts] = log.split(' ')
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) {
    return { time: '', message: log }
  }
  const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  return {
    time,
    message: formatStep(messageParts.join(' ') || log),
  }
}

function formatDateTime(value?: string) {
  if (!value) return 'Not available'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Not available'
  return date.toLocaleString()
}

function formatDuration(start?: string, finish?: string) {
  if (!start) return 'Not available'
  const startedAt = new Date(start).getTime()
  const finishedAt = finish ? new Date(finish).getTime() : Date.now()
  if (Number.isNaN(startedAt) || Number.isNaN(finishedAt) || finishedAt < startedAt) return 'Not available'
  const seconds = Math.max(0, Math.round((finishedAt - startedAt) / 100) / 10)
  return `${seconds}s`
}
