import { useMemo, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AppRoutes } from './AppRoutes'
import { AsyncStateNotice } from './components/common/AsyncState'
import { ManagementShell, TopBar, WorkspaceShell } from './components/layout/AppShell'
import { isBlockingAsyncState } from './features/server-state'
import { useAppController } from './hooks/useAppController'
import { RouteRecoveryPage } from './pages/routing'
import { pathForPage, resolveAppRoute } from './routing/routes'
import { isRepositoryUsable } from './utils/repository'
import './App.css'

function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const route = useMemo(
    () => resolveAppRoute({ pathname: location.pathname, search: location.search }),
    [location.pathname, location.search],
  )
  const controller = useAppController(route, navigate)
  const [projectSearchQuery, setProjectSearchQuery] = useState('')

  if (location.pathname === '/') return <Navigate replace to="/projects" />

  const routeContent = (() => {
    if (route.status === 'invalid') {
      return (
        <RouteRecoveryPage
          title="This location is not available"
          description={route.reason === 'unsafe_source_path'
            ? 'Source links must use a safe repository-relative path.'
            : 'Check the shared URL or return to the project list.'}
          requestedPath={`${location.pathname}${location.search}`}
        />
      )
    }
    if (route.repositoryId && !controller.repositoriesLoaded) {
      return <div className="route-loading" role="status">Loading repository context…</div>
    }
    if (route.repositoryId && controller.repositoriesLoadFailed) {
      return (
        <RouteRecoveryPage
          title="Repository context could not be verified"
          description="The repository list request failed, so this deep link was not resolved against unrelated local state."
          requestedPath={`${location.pathname}${location.search}`}
          onRetry={controller.reloadRepositories}
        />
      )
    }
    if (route.repositoryId && !controller.selectedRepository) {
      return (
        <RouteRecoveryPage
          title="Repository not found"
          description="This repository is no longer available to the current workspace."
          requestedPath={`${location.pathname}${location.search}`}
        />
      )
    }
    if (route.repositoryId && controller.selectedRepository && !isRepositoryUsable(controller.selectedRepository)) {
      return (
        <RouteRecoveryPage
          title="Repository workspace is unavailable"
          description="Index this repository before opening deep-linked workspace features."
          requestedPath={`${location.pathname}${location.search}`}
          actionPath={pathForPage('indexing')}
          actionLabel="View Index Jobs"
        />
      )
    }
    if (isBlockingAsyncState(controller.pageState)) {
      return <AsyncStateNotice state={controller.pageState} onRetry={controller.retryActivePage} />
    }
    return <AppRoutes {...controller} route={route} projectSearchQuery={projectSearchQuery} />
  })()

  return (
    <div className="app-shell">
      {controller.isWorkspacePage ? (
        <WorkspaceShell
          page={controller.page}
          repository={controller.selectedRepository}
          status={controller.indexStatus}
          onReindex={() => controller.selectedRepository && controller.reindexRepository(controller.selectedRepository.id)}
        />
      ) : (
        <ManagementShell
          page={controller.page}
          status={controller.indexStatus}
          repository={controller.selectedRepository}
        />
      )}

      <main className={controller.isWorkspacePage ? 'main workspace-main' : 'main'}>
        <TopBar
          mode={controller.isWorkspacePage ? 'workspace' : 'management'}
          page={controller.page}
          repository={controller.selectedRepository}
          status={controller.indexStatus}
          projectSearchQuery={projectSearchQuery}
          onProjectSearchChange={setProjectSearchQuery}
        />
        {controller.apiError && <div className="error-banner">{controller.apiError}</div>}
        <section className="content">
          {!isBlockingAsyncState(controller.pageState) && (
            <AsyncStateNotice state={controller.pageState} onRetry={controller.retryActivePage} />
          )}
          {routeContent}
        </section>
      </main>
    </div>
  )
}

export default App
