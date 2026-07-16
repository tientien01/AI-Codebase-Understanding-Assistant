import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Icon } from '../common/Icon'
import { PreviewLine, Progress, SideInfo } from '../common/ui'
import { managementNav, workspaceNav } from '../../config/navigation'
import { pathForPage } from '../../routing/routes'
import type { IndexStatus, Page, Repository } from '../../types/api'
import { isRepositoryUsable } from '../../utils/repository'

const SIDEBAR_STORAGE_KEY = 'aica:sidebar'
const LEGACY_WORKSPACE_SIDEBAR_KEY = 'aica:workspace-sidebar'

export function ManagementShell({
  page,
  repository,
  status,
}: {
  page: Page
  repository?: Repository
  status: IndexStatus | null
}) {
  const { collapsed, toggleSidebar } = usePersistentSidebarState()
  return (
    <aside className={`sidebar management-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <SidebarBrand collapsed={collapsed} onToggle={toggleSidebar} />
      <nav className="nav-list">
        {managementNav.map((item, index) => (
          <NavLink
            key={`${item.label}-${index}`}
            aria-current={isManagementNavActive(page, item.label) ? 'page' : undefined}
            className={() => isManagementNavActive(page, item.label) ? 'active' : ''}
            to={pathForPage(item.page)}
            title={collapsed ? item.label : undefined}
          >
            <span className="nav-mark"><Icon name={item.icon} /></span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
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
  onReindex,
}: {
  page: Page
  repository?: Repository
  status: IndexStatus | null
  onReindex: () => void
}) {
  const { collapsed, toggleSidebar } = usePersistentSidebarState()
  const lastCodeLocation = useLastCodeLocation(repository?.id, page)

  return (
    <aside className={`sidebar workspace-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <SidebarBrand collapsed={collapsed} onToggle={toggleSidebar} />
      <Link className="back-link" to="/projects" title="Back to Projects"><span className="nav-mark"><Icon name="expand" /></span><span className="nav-label">Back to Projects</span></Link>
      <nav className="nav-list">
        {workspaceNav.map((item) => (
          <NavLink
            key={item.page}
            aria-current={page === item.page ? 'page' : undefined}
            className={() => page === item.page ? 'active' : ''}
            to={repository
              ? item.page === 'code' && lastCodeLocation
                ? lastCodeLocation
                : pathForPage(item.page, repository.id)
              : '/projects'}
            title={collapsed ? item.label : undefined}
          >
            <span className="nav-mark"><Icon name={item.icon} /></span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <SideInfo title="Index Status">
        <span className={`badge ${isRepositoryUsable(repository) ? 'green' : 'blue'}`}>{repository?.status ?? 'empty'}</span>
        <PreviewLine label="Files indexed" value={String(repository?.indexed_files ?? 0)} />
        <Progress value={status?.progress ?? (isRepositoryUsable(repository) ? 100 : 0)} />
        <button className="secondary wide" disabled={!repository} onClick={onReindex}>Re-index Project</button>
      </SideInfo>
    </aside>
  )
}

function useLastCodeLocation(repositoryId: string | undefined, page: Page) {
  const location = useLocation()
  const storageKey = repositoryId ? `aica:last-code-location:${repositoryId}` : undefined
  const canonicalCodePath = repositoryId ? pathForPage('code', repositoryId) : undefined
  const currentLocation = `${location.pathname}${location.search}`
  const stored = storageKey && typeof window !== 'undefined' ? window.sessionStorage.getItem(storageKey) : undefined
  const lastCodeLocation = canonicalCodePath && (stored === canonicalCodePath || stored?.startsWith(`${canonicalCodePath}?`))
    ? stored
    : undefined

  useEffect(() => {
    if (page !== 'code' || !storageKey || !canonicalCodePath
      || (currentLocation !== canonicalCodePath && !currentLocation.startsWith(`${canonicalCodePath}?`))) return
    window.sessionStorage.setItem(storageKey, currentLocation)
  }, [canonicalCodePath, currentLocation, page, storageKey])

  return page === 'code' ? currentLocation : lastCodeLocation
}

function SidebarBrand({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return <div className="sidebar-brand-row">
    <Brand compact={collapsed} />
    <button type="button" className="sidebar-toggle" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed} onClick={onToggle} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
      <Icon name={collapsed ? 'collapse' : 'expand'} size={16} />
    </button>
  </div>
}

function usePersistentSidebarState() {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    const stored = window.localStorage.getItem(SIDEBAR_STORAGE_KEY)
      ?? window.localStorage.getItem(LEGACY_WORKSPACE_SIDEBAR_KEY)
    return stored === 'collapsed'
  })

  function toggleSidebar() {
    setCollapsed((current) => {
      const next = !current
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, next ? 'collapsed' : 'expanded')
      return next
    })
  }

  return { collapsed, toggleSidebar }
}

export function TopBar({
  mode,
  page,
  repository,
}: {
  mode: 'management' | 'workspace'
  page: Page
  repository?: Repository
  status: IndexStatus | null
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
          {page !== 'projects' && <Link className="secondary topbar-back" to="/projects">Back to Projects</Link>}
          <button className="ghost-icon" aria-label="Help"><Icon name="help" /></button>
          <button className="ghost-icon" aria-label="Notifications"><Icon name="bell" /></button>
          <div className="avatar">JD<span /></div>
          <Link className="primary new-project" to="/import"><Icon name="plus" />New Project</Link>
        </>
      ) : (
        <>
          <button className="ghost-icon" aria-label="Help"><Icon name="help" /></button>
          <button className="ghost-icon" aria-label="Notifications"><Icon name="bell" /></button>
          <div className="avatar">JD<span /></div>
        </>
      )}
    </header>
  )
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? 'compact' : ''}`} title={compact ? 'AI Codebase Assistant' : undefined}>
      <div className="brand-mark"><Icon name="code" /></div>
      <div className="brand-copy">
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
