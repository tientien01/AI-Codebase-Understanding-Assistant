import { AppRoutes } from './AppRoutes'
import { ManagementShell, TopBar, WorkspaceShell } from './components/layout/AppShell'
import { useAppController } from './hooks/useAppController'
import './App.css'

function App() {
  const controller = useAppController()

  return (
    <div className="app-shell">
      {controller.isWorkspacePage ? (
        <WorkspaceShell
          page={controller.page}
          repository={controller.selectedRepository}
          status={controller.indexStatus}
          onNavigate={controller.setPage}
          onBack={() => controller.setPage('dashboard')}
          onReindex={() => controller.selectedRepository && controller.reindexRepository(controller.selectedRepository.id)}
        />
      ) : (
        <ManagementShell
          page={controller.page}
          status={controller.indexStatus}
          repository={controller.selectedRepository}
          onNavigate={controller.setPage}
        />
      )}

      <main className={controller.isWorkspacePage ? 'main workspace-main' : 'main'}>
        <TopBar
          mode={controller.isWorkspacePage ? 'workspace' : 'management'}
          page={controller.page}
          repository={controller.selectedRepository}
          status={controller.indexStatus}
          onNewProject={() => controller.setPage('import')}
          onBack={() => controller.setPage('dashboard')}
        />
        {controller.apiError && <div className="error-banner">{controller.apiError}</div>}
        <section className="content">
          <AppRoutes {...controller} />
        </section>
      </main>
    </div>
  )
}

export default App
