import { ListRow, Metric, PageTitle, Panel, PreviewLine, Progress } from '../../components/common/ui'
import { pipelineSteps } from '../../config/navigation'
import type { IndexStatus, Repository } from '../../types/api'
import { isRepositoryUsable } from '../../utils/repository'

export function IndexingPage({
  repository,
  status,
  onOpen,
}: {
  repository?: Repository
  status: IndexStatus | null
  onOpen: () => void
}) {
  const progress = status?.progress ?? (isRepositoryUsable(repository) ? 100 : 0)

  return (
    <div>
      <PageTitle title={`Indexing Repository: ${repository?.name ?? 'No project selected'}`} subtitle="Processing source files to build a searchable knowledge graph and evidence index." />
      <div className="indexing-header">
        <div>
          <span className="status-dot">Status: {status?.status ?? repository?.status ?? 'not started'}</span>
          <div className="progress-line">
            <strong>{progress}%</strong>
            <Progress value={progress} />
            <span>{status?.processed_files ?? 0} / {status?.total_files ?? 0} files</span>
          </div>
        </div>
        <div className="header-actions">
          <button className="secondary" disabled>Pause</button>
          <button className="secondary" disabled>Cancel</button>
          <button className="primary" disabled={!isRepositoryUsable(repository)} onClick={onOpen}>Open Workspace</button>
        </div>
      </div>
      <div className="indexing-grid">
        <Panel title="Indexing Pipeline">
          <ol className="pipeline">
            {pipelineSteps.map((step, index) => {
              const done = isRepositoryUsable(repository) || index < Math.floor((progress / 100) * pipelineSteps.length)
              const active = !done && index === Math.floor((progress / 100) * pipelineSteps.length)
              return (
                <li key={step} className={done ? 'done' : active ? 'active' : ''}>
                  <span>{index + 1}</span>
                  <div>
                    <strong>{step}</strong>
                    <small>{done ? 'Completed' : active ? 'In Progress' : 'Queued'}</small>
                  </div>
                </li>
              )
            })}
          </ol>
        </Panel>
        <div className="index-center">
          <Panel title="Currently Processing">
            <PreviewLine label="Current step" value={status?.current_step ?? 'Waiting for job'} />
            <PreviewLine label="Processing file" value="backend/app/api/routes.py" />
            <Progress value={progress} />
          </Panel>
          <Panel title="Live Log">
            <div className="log-box">{status?.logs.length ? status.logs.map((log) => <p key={log}>{log}</p>) : <p>No job log yet.</p>}</div>
          </Panel>
          <Panel title={`Warnings and Skipped Files ${status?.warnings.length ?? 0}`}>
            {status?.warnings.length ? status.warnings.map((warning) => <ListRow key={warning} title={warning} detail="Review scanner or parser warning." />) : <p>No warning reported.</p>}
          </Panel>
        </div>
        <aside className="right-stack">
          <Panel title="Indexing Metrics">
            <div className="insight-grid">
              <Metric label="Files Processed" value={status?.processed_files ?? 0} />
              <Metric label="Failed Files" value={status?.failed_files ?? 0} />
              <Metric label="Graph Nodes" value={repository?.graph_nodes ?? 0} />
              <Metric label="Chunks" value={repository?.chunks ?? 0} />
            </div>
          </Panel>
          <Panel title="Throughput">
            <div className="chart-placeholder">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <p>Current throughput is simulated until background jobs are implemented.</p>
          </Panel>
          <Panel title="Index Configuration">
            <PreviewLine label="Branch" value="main" />
            <PreviewLine label="Embedding model" value="dang phat trien" />
            <PreviewLine label="Chunk size" value="MVP parser chunks" />
            <PreviewLine label="Max file size" value="1 MB" />
          </Panel>
        </aside>
      </div>
    </div>
  )
}
