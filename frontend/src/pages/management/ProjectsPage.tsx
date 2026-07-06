import { useMemo, useState } from 'react'
import { Icon } from '../../components/common/Icon'
import { EmptyState, Panel, PageTitle } from '../../components/common/ui'
import type { IconName, Repository } from '../../types/api'
import { isRepositoryUsable } from '../../utils/repository'

type ProjectFilter = 'all' | 'indexed' | 'indexing' | 'needs_index' | 'failed' | 'stale'
type ProjectSort = 'last_indexed' | 'name' | 'status'
type ProjectView = 'grid' | 'list'

export function ProjectsPage({
  repositories,
  onNewProject,
  onOpen,
  onReindex,
  onDelete,
  onViewIndexJobs,
}: {
  repositories: Repository[]
  onNewProject: () => void
  onOpen: (id: string) => void
  onReindex: (id: string) => void
  onDelete: (id: string) => void
  onViewIndexJobs: () => void
}) {
  const [activeFilter, setActiveFilter] = useState<ProjectFilter>('all')
  const [sortBy, setSortBy] = useState<ProjectSort>('last_indexed')
  const [view, setView] = useState<ProjectView>('grid')
  const indexed = repositories.filter((repository) => isRepositoryUsable(repository)).length
  const indexing = repositories.filter((repository) => repository.status === 'indexing').length
  const failed = repositories.filter((repository) => repository.status === 'failed').length
  const stale = repositories.filter((repository) => repository.status === 'stale').length
  const notIndexed = repositories.filter((repository) => isNeedsIndex(repository)).length
  const visibleRepositories = useMemo(
    () => sortProjects(repositories.filter((repository) => matchesFilter(repository, activeFilter)), sortBy),
    [repositories, activeFilter, sortBy],
  )
  const nextActions = buildNextActions({ indexed, indexing, notIndexed, stale, failed }, setActiveFilter, onViewIndexJobs)
  const filterTabs: { key: ProjectFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: repositories.length },
    { key: 'indexed', label: 'Indexed', count: indexed },
    { key: 'indexing', label: 'Indexing', count: indexing },
    { key: 'needs_index', label: 'Needs index', count: notIndexed },
    { key: 'failed', label: 'Errors', count: failed },
    { key: 'stale', label: 'Outdated', count: stale },
  ]

  return (
    <div>
      <PageTitle title="Projects" subtitle="Manage your repositories, track indexing status, and open code workspaces." />
      <div className="dashboard-layout">
        <div>
          <div className="projects-toolbar">
            <div className="project-filter-tabs" aria-label="Project filters">
              {filterTabs.map((tab) => (
                <button key={tab.key} className={activeFilter === tab.key ? 'active' : ''} onClick={() => setActiveFilter(tab.key)}>
                  {tab.label}
                  <span>{tab.count}</span>
                </button>
              ))}
            </div>
            <div className="projects-view-tools">
              <label>
                <span>Sort by</span>
                <select value={sortBy} onChange={(event) => setSortBy(event.target.value as ProjectSort)}>
                  <option value="last_indexed">Last indexed</option>
                  <option value="name">Name</option>
                  <option value="status">Status</option>
                </select>
              </label>
              <button className={`tool-button ${view === 'grid' ? 'active' : ''}`} aria-label="Grid view" onClick={() => setView('grid')}><Icon name="grid" /></button>
              <button className={`tool-button ${view === 'list' ? 'active' : ''}`} aria-label="List view" onClick={() => setView('list')}><Icon name="list" /></button>
            </div>
          </div>
          {repositories.length === 0 ? (
            <EmptyState title="No projects yet" description="Import a repository to start codebase analysis." action="New Project" onAction={onNewProject} />
          ) : visibleRepositories.length === 0 ? (
            <EmptyState title="No projects match this filter" description="Choose another status filter or import a new repository." />
          ) : (
            <div className={`project-grid ${view === 'list' ? 'list-view' : ''}`}>
              {visibleRepositories.map((repository) => {
                const action = primaryActionFor(repository)
                const status = projectStatus(repository)
                return (
                  <article className={`project-card project-card-${status.tone}`} key={repository.id}>
                    <div className="project-card-head">
                      <div className="project-icon"><Icon name="code" /></div>
                      <div className="project-title">
                        <div>
                          <h3>{repository.name}</h3>
                        </div>
                        <p title={repository.source_label || repository.source_type}>{formatReadableRepositorySource(repository)}</p>
                      </div>
                      <span className={`badge ${status.badgeClass}`}>{status.label}</span>
                      <details className="project-menu">
                        <summary aria-label={`Actions for ${repository.name}`}><Icon name="more" /></summary>
                        <div className="project-menu-list">
                          <button onClick={action.handler === 'index' ? () => onReindex(repository.id) : action.handler === 'progress' ? onViewIndexJobs : () => onOpen(repository.id)}><Icon name={action.icon} />{action.label}</button>
                          {action.handler !== 'index' && repository.status !== 'indexing' && isRepositoryUsable(repository) && <button onClick={() => onReindex(repository.id)}><Icon name="refresh" />Re-index</button>}
                          {action.handler !== 'open' && isRepositoryUsable(repository) && <button onClick={() => onOpen(repository.id)}><Icon name="git" />Open Workspace</button>}
                          <button className="danger-text" onClick={() => onDelete(repository.id)}><Icon name="warning" />Delete</button>
                        </div>
                      </details>
                    </div>
                    <div className="project-stack" aria-label={`Detected stack for ${repository.name}`}>
                      {repository.detected_stack.length ? repository.detected_stack.map((item) => <span key={item}>{item}</span>) : <span>Stack available after indexing</span>}
                    </div>
                    <div className="project-stats">
                      <ProjectStat icon="file" label="Files indexed" value={repository.indexed_files} />
                      <ProjectStat icon="route" label="Endpoints" value={repository.endpoints} />
                      <ProjectStat icon="braces" label="Symbols" value={repository.symbols} />
                      <ProjectStat icon="clock" label="Last indexed" value={formatLastIndexedShort(repository.last_indexed_at)} />
                    </div>
                    {status.detail && <p className={`project-meta-line tone-${status.tone}`}>{status.detail}</p>}
                    <div className="card-actions">
                      <button
                        className={action.tone === 'primary' ? 'primary' : 'secondary'}
                        disabled={action.disabled}
                        onClick={action.handler === 'index' ? () => onReindex(repository.id) : action.handler === 'progress' ? onViewIndexJobs : () => onOpen(repository.id)}
                      >
                        <Icon name={action.icon} />{action.label}
                      </button>
                      {repository.status === 'stale' && isRepositoryUsable(repository) && <button className="secondary" onClick={() => onOpen(repository.id)}>Open Anyway</button>}
                    </div>
                  </article>
                )
              })}
              <button className="import-tile" onClick={onNewProject}>
                <strong>Import New Repository</strong>
                <span>Upload a folder, upload a zip, or connect GitHub when available.</span>
              </button>
            </div>
          )}
        </div>
        <aside className="right-stack">
          <Panel title="Next Actions">
            <div className="next-actions">
              {nextActions.map((action) => (
                <button className={`next-action-card ${action.tone}`} key={action.title} onClick={action.onClick}>
                  <span className="next-action-icon"><Icon name={action.icon} /></span>
                  <span className="next-action-copy">
                    <strong>{action.title}</strong>
                    <small>{action.description}</small>
                  </span>
                  <span className="next-action-meta">
                    <b>{action.count}</b>
                    <small>{action.cta}</small>
                  </span>
                </button>
              ))}
            </div>
          </Panel>
          <Panel title="Quick Actions">
            <div className="quick-actions">
              <button onClick={onNewProject}><Icon name="plus" /><span><strong>New Project</strong><small>Import a repository</small></span></button>
              <button onClick={onViewIndexJobs}><Icon name="layers" /><span><strong>View Index Jobs</strong><small>Monitor indexing tasks</small></span></button>
            </div>
          </Panel>
        </aside>
      </div>
    </div>
  )
}

function ProjectStat({ icon, label, value }: { icon: IconName; label: string; value?: string | number }) {
  return (
    <div className="project-stat-cell">
      <span className="project-stat-label"><Icon name={icon} />{label}</span>
      <strong>{value ?? 0}</strong>
    </div>
  )
}

function matchesFilter(repository: Repository, filter: ProjectFilter) {
  if (filter === 'all') return true
  if (filter === 'indexed') return isRepositoryUsable(repository)
  if (filter === 'indexing') return repository.status === 'indexing'
  if (filter === 'needs_index') return isNeedsIndex(repository)
  if (filter === 'failed') return repository.status === 'failed'
  if (filter === 'stale') return repository.status === 'stale'
  return true
}

function sortProjects(repositories: Repository[], sortBy: ProjectSort) {
  return [...repositories].sort((left, right) => {
    if (sortBy === 'name') return left.name.localeCompare(right.name)
    if (sortBy === 'status') return left.status.localeCompare(right.status) || left.name.localeCompare(right.name)
    return timestamp(right.last_indexed_at) - timestamp(left.last_indexed_at) || left.name.localeCompare(right.name)
  })
}

function timestamp(value?: string) {
  if (!value) return 0
  const parsed = new Date(value).getTime()
  return Number.isNaN(parsed) ? 0 : parsed
}

function isNeedsIndex(repository: Repository) {
  return !isRepositoryUsable(repository) && repository.status !== 'indexing' && repository.status !== 'failed' && repository.status !== 'stale'
}

function projectStatus(repository: Repository) {
  if (repository.status === 'failed') {
    return { label: 'Error', badgeClass: 'red', tone: 'danger', detail: 'Indexing failed. Retry indexing or review Index Jobs.' }
  }
  if (repository.status === 'indexing') {
    return { label: 'Indexing', badgeClass: 'blue', tone: 'running', detail: 'Indexing is in progress.' }
  }
  if (repository.status === 'stale') {
    return { label: 'Outdated', badgeClass: 'purple', tone: 'warning', detail: 'Repository has changed since the last index.' }
  }
  if (isRepositoryUsable(repository)) {
    return { label: 'Indexed', badgeClass: 'green', tone: 'success', detail: '' }
  }
  return { label: 'Needs index', badgeClass: 'yellow', tone: 'warning', detail: 'Index this project to enable search, graph, and assistant features.' }
}

function primaryActionFor(repository: Repository): { label: string; icon: 'git' | 'refresh' | 'layers'; handler: 'open' | 'index' | 'progress'; tone: 'primary' | 'secondary'; disabled?: boolean } {
  if (repository.status === 'indexing') {
    return { label: 'View Progress', icon: 'layers', handler: 'progress', tone: 'secondary' }
  }
  if (repository.status === 'failed') {
    return { label: 'Retry Indexing', icon: 'refresh', handler: 'index', tone: 'secondary' }
  }
  if (repository.status === 'stale' || isNeedsIndex(repository)) {
    return { label: repository.status === 'stale' ? 'Re-index' : 'Start Indexing', icon: 'refresh', handler: 'index', tone: 'secondary' }
  }
  return { label: 'Open Workspace', icon: 'git', handler: 'open', tone: 'primary', disabled: !isRepositoryUsable(repository) }
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

function formatLastIndexedShort(value?: string) {
  if (!value) return 'Not indexed'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Indexed'
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return formatLastIndexed(value)
}

function buildNextActions(
  counts: { indexed: number; indexing: number; notIndexed: number; stale: number; failed: number },
  setActiveFilter: (filter: ProjectFilter) => void,
  onViewIndexJobs: () => void,
) {
  const actions: {
    title: string
    description: string
    cta: string
    count: number
    icon: IconName
    tone: 'danger' | 'warning' | 'running' | 'success'
    onClick: () => void
  }[] = []

  if (counts.failed > 0) {
    actions.push({
      title: 'Indexing errors need review',
      description: 'Open failed projects, inspect job details, then retry indexing.',
      cta: 'Review',
      count: counts.failed,
      icon: 'warning',
      tone: 'danger',
      onClick: () => setActiveFilter('failed'),
    })
  }

  if (counts.notIndexed > 0) {
    actions.push({
      title: 'Projects waiting for first index',
      description: 'Start indexing so search, graph, and assistant features become available.',
      cta: 'Start',
      count: counts.notIndexed,
      icon: 'spark',
      tone: 'warning',
      onClick: () => setActiveFilter('needs_index'),
    })
  }

  if (counts.stale > 0) {
    actions.push({
      title: 'Outdated projects detected',
      description: 'Re-index projects that changed after the last successful index.',
      cta: 'Refresh',
      count: counts.stale,
      icon: 'refresh',
      tone: 'warning',
      onClick: () => setActiveFilter('stale'),
    })
  }

  if (counts.indexing > 0) {
    actions.push({
      title: 'Indexing is running',
      description: 'Track live progress, warnings, pause, or cancel active jobs.',
      cta: 'Monitor',
      count: counts.indexing,
      icon: 'layers',
      tone: 'running',
      onClick: onViewIndexJobs,
    })
  }

  if (actions.length === 0) {
    actions.push({
      title: 'Workspace is ready',
      description: 'Open an indexed project and start exploring the codebase.',
      cta: 'Open',
      count: counts.indexed,
      icon: 'check',
      tone: 'success',
      onClick: () => setActiveFilter('indexed'),
    })
  }

  return actions
}
