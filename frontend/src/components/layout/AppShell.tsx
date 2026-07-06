import { Icon } from '../common/Icon'
import { PreviewLine, Progress, SideInfo } from '../common/ui'
import { managementNav, workspaceNav } from '../../config/navigation'
import type { IndexStatus, Page, Repository } from '../../types/api'
import { isRepositoryUsable } from '../../utils/repository'

export function ManagementShell({
  page,
  repository,
  status,
  onNavigate,
}: {
  page: Page
  repository?: Repository
  status: IndexStatus | null
  onNavigate: (page: Page) => void
}) {
  return (
    <aside className="sidebar">
      <Brand />
      <nav className="nav-list">
        {managementNav.map((item, index) => (
          <button key={`${item.label}-${index}`} className={isManagementNavActive(page, item.label) ? 'active' : ''} onClick={() => onNavigate(item.page)}>
            <span className="nav-mark"><Icon name={item.icon} /></span>
            {item.label}
          </button>
        ))}
      </nav>
      <SideInfo title="Current Index Job">
        <strong>{repository?.name ?? 'No project selected'}</strong>
        <div className="side-progress">
          <span>Overall Progress</span>
          <b>{status?.progress ?? 0}%</b>
        </div>
        <Progress value={status?.progress ?? 0} />
        <PreviewLine label="Status" value={status?.status ?? 'not started'} />
        <PreviewLine label="Step" value={status?.current_step ?? 'none'} />
      </SideInfo>
    </aside>
  )
}

export function WorkspaceShell({
  page,
  repository,
  status,
  onNavigate,
  onBack,
  onReindex,
}: {
  page: Page
  repository?: Repository
  status: IndexStatus | null
  onNavigate: (page: Page) => void
  onBack: () => void
  onReindex: () => void
}) {
  return (
    <aside className="sidebar">
      <Brand />
      <button className="back-link" onClick={onBack}>Back to Projects</button>
      <nav className="nav-list">
        {workspaceNav.map((item) => (
          <button key={item.page} className={page === item.page ? 'active' : ''} onClick={() => onNavigate(item.page)}>
            <span className="nav-mark"><Icon name={item.icon} /></span>
            {item.label}
          </button>
        ))}
      </nav>
      <SideInfo title="Index Status">
        <span className={`badge ${isRepositoryUsable(repository) ? 'green' : 'blue'}`}>{repository?.status ?? 'empty'}</span>
        <PreviewLine label="Files indexed" value={String(repository?.indexed_files ?? 0)} />
        <PreviewLine label="Chunks" value={String(repository?.chunks ?? 0)} />
        <PreviewLine label="Step" value={status?.current_step ?? 'completed'} />
        <Progress value={status?.progress ?? (isRepositoryUsable(repository) ? 100 : 0)} />
        <button className="secondary wide" disabled={!repository} onClick={onReindex}>Re-index Project</button>
      </SideInfo>
    </aside>
  )
}

export function TopBar({
  mode,
  page,
  repository,
  status,
  onNewProject,
  onBack,
}: {
  mode: 'management' | 'workspace'
  page: Page
  repository?: Repository
  status: IndexStatus | null
  onNewProject: () => void
  onBack: () => void
}) {
  return (
    <header className="topbar">
      {mode === 'workspace' ? (
        <>
          <div className="select-pill">{repository?.name ?? 'No repository'}</div>
          <div className="select-pill">main</div>
          <div className={`status-pill ${isRepositoryUsable(repository) ? 'green' : ''}`}>{repository?.status ?? 'not indexed'}</div>
        </>
      ) : (
        <div className="topbar-title">{mode === 'management' ? 'Projects' : 'Workspace'}</div>
      )}
      <label className="global-search-shell">
        <Icon name="search" />
        <input className="global-search" placeholder={mode === 'workspace' ? 'Search anything...' : 'Search projects...'} />
        <kbd>Ctrl K</kbd>
      </label>
      {mode === 'management' ? (
        <>
          {page !== 'projects' && <button className="secondary topbar-back" onClick={onBack}>Back to Projects</button>}
          <button className="ghost-icon" aria-label="Help"><Icon name="help" /></button>
          <button className="ghost-icon" aria-label="Notifications"><Icon name="bell" /></button>
          <div className="avatar">JD<span /></div>
          <button className="primary new-project" onClick={onNewProject}><Icon name="plus" />New Project</button>
        </>
      ) : (
        <>
          <button className="ghost-icon" aria-label="Help"><Icon name="help" /></button>
          <button className="ghost-icon" aria-label="Notifications"><Icon name="bell" /></button>
          <div className="avatar">JD<span /></div>
          <div className="topbar-meta">Indexing {status?.progress ?? (isRepositoryUsable(repository) ? 100 : 0)}%</div>
        </>
      )}
    </header>
  )
}

function Brand() {
  return (
    <div className="brand">
      <div className="brand-mark"><Icon name="code" /></div>
      <div>
        <strong>AI Codebase Assistant</strong>
        <span>Beta</span>
      </div>
    </div>
  )
}

function isManagementNavActive(page: Page, label: string) {
  if (page === 'projects') return label === 'Projects'
  if (page === 'indexing') return label === 'Index Jobs'
  if (page === 'settings') return label === 'Settings'
  if (page === 'import') return label === 'Projects'
  return false
}
