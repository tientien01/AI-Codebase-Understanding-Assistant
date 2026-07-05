import { Icon } from '../../components/common/Icon'
import { Activity, Checklist, EmptyState, Metric, Panel, PageTitle, StatCell } from '../../components/common/ui'
import type { Repository } from '../../types/api'
import { isRepositoryUsable } from '../../utils/repository'

export function DashboardPage({
  repositories,
  onNewProject,
  onOpen,
  onReindex,
  onDelete,
}: {
  repositories: Repository[]
  onNewProject: () => void
  onOpen: (id: string) => void
  onReindex: (id: string) => void
  onDelete: (id: string) => void
}) {
  const indexed = repositories.filter((repository) => isRepositoryUsable(repository)).length
  const indexing = repositories.filter((repository) => repository.status === 'indexing').length
  const failed = repositories.filter((repository) => repository.status === 'failed').length

  return (
    <div>
      <PageTitle title="Project Dashboard" subtitle="Manage and monitor all codebase analysis projects." />
      <div className="dashboard-layout">
        <div>
          <div className="toolbar">
            <span className="tab active">All Projects {repositories.length}</span>
            <span className="tab">Indexed {indexed}</span>
            <span className="tab">Indexing {indexing}</span>
            <span className="tab">Errors {failed}</span>
            <span className="tab">Not Indexed {repositories.filter((item) => !isRepositoryUsable(item)).length}</span>
            <div className="dashboard-tools">
              <button className="tool-button active"><Icon name="grid" /></button>
              <button className="tool-button"><Icon name="list" /></button>
              <button className="secondary">Last Scanned</button>
              <button className="tool-button"><Icon name="sliders" /></button>
            </div>
          </div>
          {repositories.length === 0 ? (
            <EmptyState title="No projects yet" description="Import a repository to start codebase analysis." action="New Project" onAction={onNewProject} />
          ) : (
            <div className="project-grid">
              {repositories.map((repository) => (
                <article className="project-card" key={repository.id}>
                  <div className="project-card-head">
                    <div className="project-icon"><Icon name="code" /></div>
                    <div className="project-title">
                      <div>
                        <h3>{repository.name}</h3>
                        <button className="star-button" aria-label="Favorite"><Icon name="star" /></button>
                      </div>
                      <p title={repository.source_label || repository.source_type}>{formatReadableRepositorySource(repository)}</p>
                    </div>
                    <span className={`badge ${isRepositoryUsable(repository) ? 'green' : repository.status === 'failed' ? 'red' : 'blue'}`}>{repository.status}</span>
                    <details className="project-menu">
                      <summary aria-label={`Actions for ${repository.name}`}><Icon name="more" /></summary>
                      <div className="project-menu-list">
                        <button onClick={() => onReindex(repository.id)}><Icon name="refresh" />Re-index</button>
                        <button disabled={!isRepositoryUsable(repository)} onClick={() => onOpen(repository.id)}><Icon name="git" />Open Workspace</button>
                        <button className="danger-text" onClick={() => onDelete(repository.id)}><Icon name="warning" />Delete</button>
                      </div>
                    </details>
                  </div>
                  <div className="project-stack" aria-label={`Detected stack for ${repository.name}`}>
                    {repository.detected_stack.length ? repository.detected_stack.map((item) => <span key={item}>{item}</span>) : <span>Stack available after indexing</span>}
                  </div>
                  <div className="project-stats">
                    <StatCell label="Files" value={repository.total_files} />
                    <StatCell label="API routes" value={repository.endpoints} />
                    <StatCell label="Functions/classes" value={repository.symbols} />
                  </div>
                  <p className="project-meta-line">Last indexed: {formatLastIndexed(repository.last_indexed_at)}</p>
                  <div className="card-actions">
                    <button className="primary" disabled={!isRepositoryUsable(repository)} onClick={() => onOpen(repository.id)}><Icon name="git" />Open Workspace</button>
                  </div>
                </article>
              ))}
              <button className="import-tile" onClick={onNewProject}>
                <strong>Import New Repository</strong>
                <span>Upload a folder, upload a zip, or connect GitHub when available.</span>
              </button>
            </div>
          )}
        </div>
        <aside className="right-stack">
          <Panel title="Recent Activity" action="View all">
            <Activity tone="success" text="Repository indexed successfully" meta="2 minutes ago" />
            <Activity tone="running" text="Indexing job started" meta="5 minutes ago" />
            <Activity tone="success" text="AI Codebase Assistant indexed successfully" meta="1 hour ago" />
            <Activity tone="danger" text="Scan completed with warnings" meta="2 hours ago" />
          </Panel>
          <Panel title="Workspace Insights">
            <div className="insight-grid">
              <Metric label="Projects" value={repositories.length} />
              <Metric label="Indexed" value={indexed} />
              <Metric label="Files" value={repositories.reduce((sum, item) => sum + item.total_files, 0)} />
              <Metric label="Functions" value={repositories.reduce((sum, item) => sum + item.symbols, 0)} />
            </div>
          </Panel>
          <Panel title="Getting Started">
            <Checklist items={['Import your first repository', 'Run codebase analysis', 'Explore AI Assistant', 'Set custom rules']} done={Math.min(2, repositories.length + 1)} />
          </Panel>
        </aside>
      </div>
    </div>
  )
}

function formatRepositorySource(repository: Repository) {
  if (repository.source_type === 'upload_folder') return 'Uploaded folder'
  if (repository.source_type === 'upload_zip') return `Uploaded ZIP${repository.source_label ? ` - ${repository.source_label}` : ''}`
  if (repository.source_type === 'local_path') return 'Imported folder'
  if (repository.source_type === 'github_url') return repository.source_label ?? repository.source_uri ?? 'GitHub repository'
  return repository.source_type
}

function formatReadableRepositorySource(repository: Repository) {
  if (repository.source_type === 'upload_folder') return sourceTypeLabel(repository.source_type)
  if (repository.source_type === 'upload_zip') return `${sourceTypeLabel(repository.source_type)}${repository.source_label ? ` - ${repository.source_label}` : ''}`
  if (repository.source_type === 'local_path') return sourceTypeLabel(repository.source_type)
  if (repository.source_type === 'github_url') return repository.source_label ?? repository.source_uri ?? sourceTypeLabel(repository.source_type)
  return formatRepositorySource(repository)
}

function sourceTypeLabel(sourceType: string) {
  const labels: Record<string, string> = {
    upload_folder: 'Uploaded folder',
    upload_zip: 'Uploaded ZIP',
    local_path: 'Imported folder',
    github_url: 'GitHub',
  }
  return labels[sourceType] ?? sourceType
}

function formatLastIndexed(value?: string) {
  if (!value) return 'Not indexed yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Indexed'
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
