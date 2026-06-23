import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'
const API_V1 = `${API_BASE}/api/v1`

type Page =
  | 'dashboard'
  | 'import'
  | 'indexing'
  | 'overview'
  | 'code'
  | 'graph'
  | 'api'
  | 'assistant'
  | 'impact'
  | 'search'
  | 'evidence'
  | 'evaluation'
  | 'settings'

type Repository = {
  id: string
  name: string
  source_type: string
  source_uri?: string
  status: string
  total_files: number
  indexed_files: number
  symbols: number
  endpoints: number
  chunks: number
  graph_nodes: number
  last_indexed_at?: string
}

type IndexStatus = {
  repository_id: string
  status: string
  current_step: string
  total_files: number
  processed_files: number
  failed_files: number
  progress: number
  logs: string[]
  warnings: string[]
}

type Overview = {
  repository_id: string
  name: string
  detected_stack: string[]
  important_files: { file_path: string; reason: string }[]
  modules: { name: string; summary: string; file_count: number }[]
  endpoints: { method: string; path: string; handler: string; file_path: string; start_line: number; end_line: number }[]
  documentation_gaps: string[]
  stats: Record<string, number>
}

type Citation = {
  evidence_id: string
  file_path: string
  symbol_name?: string
  start_line: number
  end_line: number
}

type Evidence = Citation & {
  repository_id: string
  source_type: string
  content_preview: string
  relevance_reason: string
  confidence_score: number
  retrieval_source: string
  metadata: Record<string, string>
}

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  evidenceSufficient?: boolean
}

type GraphData = {
  nodes: { id: string; type: string; label: string; file_path?: string }[]
  edges: { source: string; target: string; type: string; confidence: number }[]
}

type SearchResult = {
  evidence_id: string
  file_path: string
  title: string
  preview: string
  start_line: number
  end_line: number
  score: number
}

type FileTreeNode = {
  name: string
  path: string
  type: 'file' | 'directory'
  children: FileTreeNode[]
}

type FileContent = {
  file_path: string
  language: string
  content: string
  lines: string[]
  symbols: Citation[]
}

type ImportMode = 'github' | 'folder' | 'zip' | 'local'
type IconName =
  | 'home'
  | 'folder'
  | 'clock'
  | 'star'
  | 'layers'
  | 'settings'
  | 'nodes'
  | 'share'
  | 'sliders'
  | 'spark'
  | 'target'
  | 'search'
  | 'chart'
  | 'code'
  | 'grid'
  | 'list'
  | 'bell'
  | 'help'
  | 'plus'
  | 'more'
  | 'refresh'
  | 'pause'
  | 'warning'
  | 'check'
  | 'git'

const managementNav: { page: Page; label: string; icon: IconName }[] = [
  { page: 'dashboard', label: 'Dashboard', icon: 'home' },
  { page: 'dashboard', label: 'Projects', icon: 'folder' },
  { page: 'dashboard', label: 'Recent', icon: 'clock' },
  { page: 'dashboard', label: 'Favorites', icon: 'star' },
  { page: 'indexing', label: 'Index Jobs', icon: 'layers' },
  { page: 'settings', label: 'Settings', icon: 'settings' },
]

const workspaceNav: { page: Page; label: string; icon: IconName }[] = [
  { page: 'overview', label: 'Overview', icon: 'home' },
  { page: 'code', label: 'Code Explorer', icon: 'nodes' },
  { page: 'graph', label: 'Graph View', icon: 'share' },
  { page: 'api', label: 'API Explorer', icon: 'sliders' },
  { page: 'assistant', label: 'AI Assistant', icon: 'spark' },
  { page: 'impact', label: 'Impact Analysis', icon: 'target' },
  { page: 'search', label: 'Search', icon: 'search' },
  { page: 'evaluation', label: 'Evaluation', icon: 'chart' },
  { page: 'settings', label: 'Settings', icon: 'settings' },
]

const pipelineSteps = [
  'Scan repository files',
  'Apply ignore rules',
  'Parse Python AST',
  'Parse JavaScript / TypeScript',
  'Detect FastAPI endpoints',
  'Build code graph',
  'Chunk source code',
  'Generate embeddings',
  'Store vector index',
  'Validate citations',
  'Post-process and finalize',
]

function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [selectedRepositoryId, setSelectedRepositoryId] = useState('')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([])
  const [selectedFilePath, setSelectedFilePath] = useState('')
  const [fileContent, setFileContent] = useState<FileContent | null>(null)
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null)
  const [chatInput, setChatInput] = useState('How does the login flow work?')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Import and index a repository, then ask architecture, API flow, debugging, onboarding, or impact questions.',
      evidenceSufficient: false,
    },
  ])
  const [searchQuery, setSearchQuery] = useState('login auth token')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [projectName, setProjectName] = useState('fastapi-react-sample')
  const [localPath, setLocalPath] = useState('../tests/fixtures/fastapi_react_sample')
  const [githubUrl, setGithubUrl] = useState('https://github.com/username/awesome-project')
  const [importMode, setImportMode] = useState<ImportMode>('folder')
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [apiError, setApiError] = useState('')

  const selectedRepository = useMemo(
    () => repositories.find((repository) => repository.id === selectedRepositoryId) ?? repositories[0],
    [repositories, selectedRepositoryId],
  )

  const isWorkspacePage = ['overview', 'code', 'graph', 'api', 'assistant', 'impact', 'search', 'evidence', 'evaluation'].includes(page)

  useEffect(() => {
    void loadRepositories()
    // Load once on app start.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedRepository) return
    void loadIndexStatus(selectedRepository.id)
    if (selectedRepository.status === 'indexed') {
      void loadWorkspaceData(selectedRepository.id)
    }
    // Reload when active repository changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRepository?.id, selectedRepository?.status])

  useEffect(() => {
    if (page !== 'indexing' || !selectedRepository) return
    const timer = window.setInterval(() => {
      void loadIndexStatus(selectedRepository.id)
      void loadRepositories()
    }, 2500)
    return () => window.clearInterval(timer)
    // Poll only while viewing indexing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, selectedRepository?.id])

  async function request<T>(url: string, options?: RequestInit): Promise<T> {
    setApiError('')
    const response = await fetch(url, options)
    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      const message = payload?.error?.message ?? `Request failed with status ${response.status}`
      setApiError(message)
      throw new Error(message)
    }
    return response.json() as Promise<T>
  }

  async function loadRepositories() {
    try {
      const data = await request<Repository[]>(`${API_V1}/repositories`)
      setRepositories(data)
      if (!selectedRepositoryId && data[0]) setSelectedRepositoryId(data[0].id)
    } catch {
      setRepositories([])
    }
  }

  async function loadWorkspaceData(repositoryId: string) {
    await Promise.all([loadOverview(repositoryId), loadGraph(repositoryId), loadFileTree(repositoryId)])
  }

  async function loadOverview(repositoryId: string) {
    try {
      setOverview(await request<Overview>(`${API_V1}/repositories/${repositoryId}/overview`))
    } catch {
      setOverview(null)
    }
  }

  async function loadIndexStatus(repositoryId: string) {
    try {
      setIndexStatus(await request<IndexStatus>(`${API_V1}/repositories/${repositoryId}/index/status`))
    } catch {
      setIndexStatus(null)
    }
  }

  async function loadGraph(repositoryId: string) {
    try {
      setGraph(await request<GraphData>(`${API_V1}/repositories/${repositoryId}/graph`))
    } catch {
      setGraph(null)
    }
  }

  async function loadFileTree(repositoryId: string) {
    try {
      const tree = await request<FileTreeNode[]>(`${API_V1}/repositories/${repositoryId}/files/tree`)
      setFileTree(tree)
      const firstFile = findFirstFile(tree)
      if (firstFile && !selectedFilePath) {
        await loadFileContent(repositoryId, firstFile.path)
      }
    } catch {
      setFileTree([])
    }
  }

  async function loadFileContent(repositoryId: string, filePath: string) {
    const content = await request<FileContent>(`${API_V1}/repositories/${repositoryId}/files/content?path=${encodeURIComponent(filePath)}`)
    setSelectedFilePath(filePath)
    setFileContent(content)
  }

  async function submitImport(event: FormEvent) {
    event.preventDefault()
    if (importMode === 'github') {
      setApiError('GitHub URL import is dang phat trien. Use Upload Folder, Upload ZIP, or Local Path for this frontend pass.')
      return
    }
    if (importMode === 'zip') {
      await uploadZipRepository()
      return
    }
    if (importMode === 'folder') {
      await uploadFolderRepository()
      return
    }
    const result = await request<{ repository_id: string }>(`${API_V1}/repositories/import-local`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: projectName, local_path: localPath }),
    })
    await indexRepository(result.repository_id)
  }

  async function uploadZipRepository() {
    if (!zipFile) {
      setApiError('Choose a zip file before importing.')
      return
    }
    const formData = new FormData()
    formData.append('file', zipFile)
    formData.append('name', projectName || zipFile.name.replace(/\.zip$/i, ''))
    const result = await request<{ repository_id: string }>(`${API_V1}/repositories/upload`, {
      method: 'POST',
      body: formData,
    })
    await indexRepository(result.repository_id)
  }

  async function uploadFolderRepository() {
    if (folderFiles.length === 0) {
      setApiError('Choose a project folder before importing.')
      return
    }
    const formData = new FormData()
    for (const file of folderFiles) {
      const uploadFile = file as File & { webkitRelativePath?: string }
      formData.append('files', file)
      formData.append('relative_paths', uploadFile.webkitRelativePath || file.name)
    }
    formData.append('name', projectName || folderFiles[0].name)
    const result = await request<{ repository_id: string }>(`${API_V1}/repositories/upload-folder`, {
      method: 'POST',
      body: formData,
    })
    await indexRepository(result.repository_id)
  }

  async function indexRepository(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    await request(`${API_V1}/repositories/${repositoryId}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_reindex: true }),
    })
    await loadRepositories()
    await loadIndexStatus(repositoryId)
    setPage('indexing')
  }

  async function reindexRepository(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    await request(`${API_V1}/repositories/${repositoryId}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_reindex: true }),
    })
    await loadRepositories()
    await loadIndexStatus(repositoryId)
    setPage('indexing')
  }

  async function openWorkspace(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    await loadWorkspaceData(repositoryId)
    setPage('overview')
  }

  async function sendChatMessage(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository || !chatInput.trim()) return
    const userText = chatInput.trim()
    setChatInput('')
    setChatMessages((items) => [...items, { role: 'user', content: userText }])
    const response = await request<{
      answer: string
      citations: Citation[]
      evidence_sufficient: boolean
    }>(`${API_V1}/repositories/${selectedRepository.id}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, options: { max_retrieval_rounds: 2 } }),
    })
    setChatMessages((items) => [
      ...items,
      {
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        evidenceSufficient: response.evidence_sufficient,
      },
    ])
  }

  async function openEvidence(citation: Citation) {
    if (!selectedRepository) return
    const evidence = await request<Evidence>(`${API_V1}/repositories/${selectedRepository.id}/evidence/${citation.evidence_id}`)
    setSelectedEvidence(evidence)
    setPage('evidence')
  }

  async function runSearch(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository) return
    const response = await request<{ results: SearchResult[] }>(
      `${API_V1}/repositories/${selectedRepository.id}/search?q=${encodeURIComponent(searchQuery)}`,
    )
    setSearchResults(response.results)
  }

  return (
    <div className="app-shell">
      {isWorkspacePage ? (
        <WorkspaceShell
          page={page}
          repository={selectedRepository}
          status={indexStatus}
          onNavigate={setPage}
          onBack={() => setPage('dashboard')}
          onReindex={() => selectedRepository && reindexRepository(selectedRepository.id)}
        />
      ) : (
        <ManagementShell page={page} status={indexStatus} repository={selectedRepository} onNavigate={setPage} />
      )}

      <main className={isWorkspacePage ? 'main workspace-main' : 'main'}>
        <TopBar
          mode={isWorkspacePage ? 'workspace' : 'management'}
          page={page}
          repository={selectedRepository}
          status={indexStatus}
          onNewProject={() => setPage('import')}
          onBack={() => setPage('dashboard')}
        />
        {apiError && <div className="error-banner">{apiError}</div>}
        <section className="content">{renderPage()}</section>
      </main>
    </div>
  )

  function renderPage() {
    if (page === 'dashboard') {
      return (
        <DashboardPage
          repositories={repositories}
          onNewProject={() => setPage('import')}
          onOpen={openWorkspace}
          onReindex={reindexRepository}
        />
      )
    }
    if (page === 'import') {
      return (
        <ImportPage
          mode={importMode}
          projectName={projectName}
          localPath={localPath}
          githubUrl={githubUrl}
          folderCount={folderFiles.length}
          zipFileName={zipFile?.name ?? ''}
          onModeChange={setImportMode}
          onNameChange={setProjectName}
          onPathChange={setLocalPath}
          onGithubUrlChange={setGithubUrl}
          onFolderFiles={setFolderFiles}
          onZipFile={setZipFile}
          onSubmit={submitImport}
        />
      )
    }
    if (page === 'indexing') {
      return (
        <IndexingPage
          status={indexStatus}
          repository={selectedRepository}
          onOpen={() => selectedRepository && openWorkspace(selectedRepository.id)}
        />
      )
    }
    if (page === 'overview') {
      return (
        <WorkspacePage
          main={<OverviewPage overview={overview} onQuestion={(question) => setChatInput(question)} />}
          side={<AssistantPanel input={chatInput} messages={chatMessages} disabled={!canChat(selectedRepository)} onInput={setChatInput} onSubmit={sendChatMessage} onEvidence={openEvidence} />}
        />
      )
    }
    if (page === 'code') {
      return (
        <WorkspacePage
          main={
            <CodeExplorerPage
              fileTree={fileTree}
              selectedFilePath={selectedFilePath}
              fileContent={fileContent}
              overview={overview}
              onSelectFile={(filePath) => selectedRepository && loadFileContent(selectedRepository.id, filePath)}
            />
          }
          side={<AssistantPanel input={chatInput} messages={chatMessages} disabled={!canChat(selectedRepository)} onInput={setChatInput} onSubmit={sendChatMessage} onEvidence={openEvidence} />}
        />
      )
    }
    if (page === 'graph') return <WorkspacePage main={<GraphPage graph={graph} overview={overview} />} side={<GraphDetails graph={graph} />} />
    if (page === 'api') return <WorkspacePage main={<ApiExplorerPage overview={overview} />} side={<ApiDetails overview={overview} />} />
    if (page === 'assistant') {
      return (
        <WorkspacePage
          main={<AssistantFullPage input={chatInput} messages={chatMessages} disabled={!canChat(selectedRepository)} onInput={setChatInput} onSubmit={sendChatMessage} onEvidence={openEvidence} />}
          side={<EvidenceSummary />}
        />
      )
    }
    if (page === 'impact') return <WorkspacePage main={<ImpactPage overview={overview} />} side={<InDevelopmentPanel title="Impact backend" detail="Requires POST /repositories/{id}/impact." />} />
    if (page === 'search') return <WorkspacePage main={<SearchPage query={searchQuery} results={searchResults} onQuery={setSearchQuery} onSearch={runSearch} onEvidence={openEvidence} />} side={<SearchFilters />} />
    if (page === 'evidence') return <WorkspacePage main={<EvidencePage evidence={selectedEvidence} />} side={<EvidenceSummary />} />
    if (page === 'evaluation') return <WorkspacePage main={<EvaluationPage />} side={<InDevelopmentPanel title="Evaluation runner" detail="Requires evaluation datasets, runs, and metrics APIs." />} />
    return <SettingsPage isWorkspace={isWorkspacePage} />
  }
}

function ManagementShell({
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
          <button
            key={`${item.label}-${index}`}
            className={isManagementNavActive(page, item.label) ? 'active' : ''}
            onClick={() => onNavigate(item.page)}
          >
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

function WorkspaceShell({
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
        <span className={`badge ${repository?.status === 'indexed' ? 'green' : 'blue'}`}>{repository?.status ?? 'empty'}</span>
        <PreviewLine label="Files indexed" value={String(repository?.indexed_files ?? 0)} />
        <PreviewLine label="Chunks" value={String(repository?.chunks ?? 0)} />
        <PreviewLine label="Step" value={status?.current_step ?? 'completed'} />
        <Progress value={status?.progress ?? (repository?.status === 'indexed' ? 100 : 0)} />
        <button className="secondary wide" disabled={!repository} onClick={onReindex}>Re-index Project</button>
      </SideInfo>
    </aside>
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

function TopBar({
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
          <div className={`status-pill ${repository?.status === 'indexed' ? 'green' : ''}`}>{repository?.status ?? 'not indexed'}</div>
        </>
      ) : (
        <div className="topbar-title">{mode === 'management' ? 'Project Management' : 'Workspace'}</div>
      )}
      <label className="global-search-shell">
        <Icon name="search" />
        <input className="global-search" placeholder={mode === 'workspace' ? 'Search anything...' : 'Search projects, repositories, files...'} />
        <kbd>⌘ K</kbd>
      </label>
      {mode === 'management' ? (
        <>
          {page !== 'dashboard' && <button className="secondary topbar-back" onClick={onBack}>Back to Projects</button>}
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
          <div className="topbar-meta">Indexing {status?.progress ?? (repository?.status === 'indexed' ? 100 : 0)}%</div>
        </>
      )}
    </header>
  )
}

function DashboardPage({
  repositories,
  onNewProject,
  onOpen,
  onReindex,
}: {
  repositories: Repository[]
  onNewProject: () => void
  onOpen: (id: string) => void
  onReindex: (id: string) => void
}) {
  const indexed = repositories.filter((repository) => repository.status === 'indexed').length
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
            <span className="tab">Not Indexed {repositories.filter((item) => item.status !== 'indexed').length}</span>
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
                      <p>{repository.source_uri || repository.source_type}</p>
                    </div>
                    <span className={`badge ${repository.status === 'indexed' ? 'green' : repository.status === 'failed' ? 'red' : 'blue'}`}>{repository.status}</span>
                    <button className="more-button" aria-label="More actions"><Icon name="more" /></button>
                  </div>
                  <div className="tech-row">
                    <span><Icon name="code" />Python</span>
                    <span><Icon name="check" />FastAPI</span>
                    <span><Icon name="nodes" />React</span>
                    <span>+2</span>
                  </div>
                  <div className="project-stats">
                    <StatCell label="Files" value={repository.total_files} />
                    <StatCell label="Functions" value={repository.symbols} />
                    <StatCell label="Classes" value={Math.max(0, Math.round(repository.symbols / 6))} />
                  </div>
                  <div className="project-health-grid">
                    <div>
                      <span>Last scan</span>
                      <strong>{repository.last_indexed_at ? 'indexed' : 'not scanned'}</strong>
                    </div>
                    <div>
                      <span>{repository.status === 'indexing' ? 'Progress' : repository.status === 'failed' ? 'Errors' : 'Index Health'}</span>
                      <strong>{repository.status === 'indexed' ? '98%' : repository.status === 'indexing' ? '74%' : repository.status === 'failed' ? '14' : repository.status}</strong>
                      <Progress value={repository.status === 'indexed' ? 98 : repository.status === 'indexing' ? 74 : repository.status === 'failed' ? 62 : 0} />
                    </div>
                  </div>
                  <div className="card-actions">
                    {repository.status === 'indexing' ? (
                      <button className="primary" onClick={() => onReindex(repository.id)}><Icon name="pause" />Pause Indexing</button>
                    ) : repository.status === 'failed' ? (
                      <button className="danger"><Icon name="warning" />View Errors</button>
                    ) : (
                      <button className="primary" disabled={repository.status !== 'indexed'} onClick={() => onOpen(repository.id)}><Icon name="git" />Open Workspace</button>
                    )}
                    <button className="secondary" onClick={() => onReindex(repository.id)}><Icon name="refresh" />Re-index</button>
                    <button className="more-button" aria-label="More actions"><Icon name="more" /></button>
                  </div>
                </article>
              ))}
              <button className="import-tile" onClick={onNewProject}>
                <strong>Import New Repository</strong>
                <span>Connect GitHub, upload zip, upload folder, or use local path.</span>
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

function ImportPage({
  mode,
  projectName,
  localPath,
  githubUrl,
  folderCount,
  zipFileName,
  onModeChange,
  onNameChange,
  onPathChange,
  onGithubUrlChange,
  onFolderFiles,
  onZipFile,
  onSubmit,
}: {
  mode: ImportMode
  projectName: string
  localPath: string
  githubUrl: string
  folderCount: number
  zipFileName: string
  onModeChange: (mode: ImportMode) => void
  onNameChange: (value: string) => void
  onPathChange: (value: string) => void
  onGithubUrlChange: (value: string) => void
  onFolderFiles: (files: File[]) => void
  onZipFile: (file: File | null) => void
  onSubmit: (event: FormEvent) => void
}) {
  return (
    <form onSubmit={onSubmit}>
      <PageTitle title="New Project" subtitle="Import and configure a repository to index and power code intelligence." />
      <WizardSteps />
      <div className="import-layout">
        <div className="form-sections">
          <Panel title="1. Import Repository">
            <div className="source-grid">
              <SourceCard label="Upload ZIP" active={mode === 'zip'} onClick={() => onModeChange('zip')} detail="Upload a .zip file" />
              <SourceCard label="GitHub URL" active={mode === 'github'} onClick={() => onModeChange('github')} detail="Import from GitHub" />
              <SourceCard label="Local Folder" active={mode === 'folder'} onClick={() => onModeChange('folder')} detail="Use browser folder upload" />
              <SourceCard label="Local Path" active={mode === 'local'} onClick={() => onModeChange('local')} detail="Trusted backend path" />
            </div>
            <div className="form-grid">
              {mode === 'github' && (
                <label>
                  Repository URL
                  <input value={githubUrl} onChange={(event) => onGithubUrlChange(event.target.value)} />
                  <span>GitHub URL import is dang phat trien in backend.</span>
                </label>
              )}
              {mode === 'local' && (
                <label>
                  Local path
                  <input value={localPath} onChange={(event) => onPathChange(event.target.value)} />
                  <span>Use a path the backend can read.</span>
                </label>
              )}
              {mode === 'folder' && (
                <label>
                  Local folder
                  <input
                    type="file"
                    multiple
                    ref={(input) => {
                      if (input) input.setAttribute('webkitdirectory', 'true')
                    }}
                    onChange={(event) => onFolderFiles(Array.from(event.target.files ?? []))}
                  />
                  <span>{folderCount ? `${folderCount} files selected` : 'Choose a folder to upload.'}</span>
                </label>
              )}
              {mode === 'zip' && (
                <label>
                  Zip file
                  <input type="file" accept=".zip" onChange={(event) => onZipFile(event.target.files?.[0] ?? null)} />
                  <span>{zipFileName || 'Choose a repository zip.'}</span>
                </label>
              )}
              <label>
                Project name
                <input value={projectName} onChange={(event) => onNameChange(event.target.value)} />
              </label>
              <label>
                Default branch
                <input value="main" readOnly />
              </label>
            </div>
          </Panel>
          <Panel title="2. Configure Parsing and Indexing">
            <div className="configure-grid">
              <label>
                Ignore patterns
                <textarea value={'.git/\n.github/\nnode_modules/\nvenv/\n__pycache__/\n*.log'} readOnly />
                <span>One pattern per line. Secret files are always skipped.</span>
              </label>
              <div>
                <h3>Indexing Profile</h3>
                <div className="profile-grid">
                  <ProfileCard title="Fast" detail="Quick indexing for large codebases." />
                  <ProfileCard title="Balanced" detail="Recommended default for most projects." active />
                  <ProfileCard title="Deep Analysis" detail="Maximum graph and impact depth." />
                </div>
              </div>
            </div>
            <details className="advanced-settings">
              <summary>Advanced Settings</summary>
              <div className="setting-chips">
                <span>Parse Python AST</span>
                <span>Parse JS/TS</span>
                <span>Detect FastAPI endpoints</span>
                <span>Build code graph</span>
                <span>Generate embeddings</span>
                <span>Enable citations</span>
              </div>
            </details>
          </Panel>
        </div>
        <aside className="preview-column">
          <Panel title="Import Preview">
            <h3>Repository</h3>
            <PreviewLine label="Repository" value={mode === 'github' ? githubUrl : projectName} />
            <PreviewLine label="Branch" value="main" />
            <PreviewLine label="Commit" value="pending" />
            <h3>Estimated Size</h3>
            <PreviewLine label="Files" value={String(folderCount || 128)} />
            <PreviewLine label="LOC" value="estimated after scan" />
            <PreviewLine label="Size" value="calculated on import" />
            <h3>Detected Languages</h3>
            <LanguageBar label="Python" value={47} />
            <LanguageBar label="TypeScript" value={25} />
            <LanguageBar label="JavaScript" value={15} />
            <LanguageBar label="Others" value={13} />
            <h3>Excluded Patterns</h3>
            <div className="setting-chips">
              <span>.git/</span>
              <span>node_modules/</span>
              <span>venv/</span>
              <span>__pycache__/</span>
            </div>
            <h3>Estimated Indexing</h3>
            <PreviewLine label="Chunks" value="calculated after scan" />
            <PreviewLine label="Embeddings" value="dang phat trien" />
            <PreviewLine label="Estimated time" value="1-3 min" />
          </Panel>
          <div className="footer-actions">
            <button type="button" className="secondary">Cancel</button>
            <button type="submit" className="primary">Start Indexing</button>
          </div>
        </aside>
      </div>
    </form>
  )
}

function IndexingPage({
  repository,
  status,
  onOpen,
}: {
  repository?: Repository
  status: IndexStatus | null
  onOpen: () => void
}) {
  const progress = status?.progress ?? (repository?.status === 'indexed' ? 100 : 0)

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
          <button className="primary" disabled={repository?.status !== 'indexed'} onClick={onOpen}>Open Workspace</button>
        </div>
      </div>
      <div className="indexing-grid">
        <Panel title="Indexing Pipeline">
          <ol className="pipeline">
            {pipelineSteps.map((step, index) => {
              const done = repository?.status === 'indexed' || index < Math.floor((progress / 100) * pipelineSteps.length)
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

function OverviewPage({ overview, onQuestion }: { overview: Overview | null; onQuestion: (question: string) => void }) {
  if (!overview) return <EmptyState title="Repository is not indexed" description="Open an indexed repository to view the workspace overview." />

  const questions = [
    'How does the login flow work?',
    'Which files are related to authentication?',
    'Where is JWT validation implemented?',
    'Show me the database models.',
  ]

  return (
    <div>
      <PageTitle title={overview.name} subtitle="AI-powered code understanding for faster navigation, smarter debugging, and grounded answers." />
      <div className="stats-strip">
        <Metric label="Files" value={overview.stats.files} />
        <Metric label="Functions" value={overview.stats.functions} />
        <Metric label="Classes" value={overview.stats.classes} />
        <Metric label="API Endpoints" value={overview.stats.endpoints} />
        <Metric label="Graph Nodes" value={overview.stats.graph_nodes} />
        <Metric label="Indexed Chunks" value={overview.stats.chunks} />
      </div>
      <div className="overview-grid">
        <Panel title="Architecture Summary">
          <div className="architecture-map">
            <span>Client Web</span>
            <span>API Gateway</span>
            <span>Auth Service</span>
            <span>User Service</span>
            <span>Data Layer</span>
          </div>
          <div className="stack-row">{overview.detected_stack.map((item) => <span key={item}>{item}</span>)}</div>
        </Panel>
        <Panel title="Recent Activity">
          <Activity text="Indexed source files" meta="latest run" />
          <Activity text="Updated API schema" meta={`${overview.endpoints.length} endpoints`} />
          <Activity text="Project mental model generated" meta="available" />
        </Panel>
        <Panel title="Suggested Questions">
          {questions.map((question) => (
            <button className="question-row" key={question} onClick={() => onQuestion(question)}>{question}</button>
          ))}
        </Panel>
        <Panel title="Key Modules">
          {overview.modules.map((module) => <ListRow key={module.name} title={module.name} detail={module.summary} meta={`${module.file_count} files`} />)}
        </Panel>
        <Panel title="Important Files">
          {overview.important_files.map((file) => <ListRow key={file.file_path} title={file.file_path} detail={file.reason} />)}
        </Panel>
        <Panel title="Documentation Gaps">
          {overview.documentation_gaps.map((gap) => <ListRow key={gap} title={gap} detail="Generated by current indexing rules." />)}
        </Panel>
      </div>
    </div>
  )
}

function CodeExplorerPage({
  fileTree,
  selectedFilePath,
  fileContent,
  overview,
  onSelectFile,
}: {
  fileTree: FileTreeNode[]
  selectedFilePath: string
  fileContent: FileContent | null
  overview: Overview | null
  onSelectFile: (filePath: string) => void
}) {
  return (
    <div>
      <PageTitle title="Code Explorer" subtitle="Browse source files with parsed symbols, endpoints, imports, and citation-ready line ranges." />
      <div className="code-explorer-grid">
        <Panel title="File Tree">
          <input className="panel-search" placeholder="Search file" />
          {fileTree.length ? <FileTree nodes={fileTree} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} /> : <p>No file tree available.</p>}
        </Panel>
        <Panel title={fileContent?.file_path ?? 'No file selected'}>
          <div className="file-tabs">
            <span>{fileContent?.file_path ?? 'empty'}</span>
          </div>
          <pre className="code-block">
            {fileContent ? fileContent.lines.map((line, index) => `${String(index + 1).padStart(4, ' ')}  ${line}`).join('\n') : 'Import and index a repository to inspect code.'}
          </pre>
        </Panel>
        <Panel title="Detected Intelligence">
          <h3>Symbols</h3>
          {(fileContent?.symbols ?? []).length ? (
            fileContent?.symbols.map((symbol) => <ListRow key={`${symbol.file_path}-${symbol.start_line}`} title={symbol.symbol_name ?? 'symbol'} detail={`Lines ${symbol.start_line}-${symbol.end_line}`} />)
          ) : (
            <p>No symbol found for this file.</p>
          )}
          <h3>Endpoints</h3>
          {(overview?.endpoints ?? []).filter((endpoint) => endpoint.file_path === fileContent?.file_path).map((endpoint) => (
            <ListRow key={`${endpoint.method}-${endpoint.path}`} title={`${endpoint.method} ${endpoint.path}`} detail={endpoint.handler} />
          ))}
          <h3>Call Relationships</h3>
          <InDevelopmentInline text="Jump to definition and references need richer graph query APIs." />
        </Panel>
      </div>
    </div>
  )
}

function GraphPage({ graph, overview }: { graph: GraphData | null; overview: Overview | null }) {
  const nodes = graph?.nodes.slice(0, 18) ?? []
  const edges = graph?.edges.slice(0, 8) ?? []
  return (
    <div>
      <PageTitle title="Graph View" subtitle="Visualize file, symbol, endpoint, and API call relationships." />
      <div className="toolbar graph-toolbar">
        <span className="tab active">Module Graph</span>
        <span className="tab">Call Graph</span>
        <span className="tab">API Flow</span>
        <span className="tab">Impact Graph</span>
        <input className="panel-search" placeholder="Search node" />
      </div>
      <div className="graph-workspace">
        <Panel title="Codebase Graph">
          <div className="graph-canvas">
            {nodes.map((node, index) => (
              <div className={`graph-node type-${node.type}`} key={node.id} style={{ left: `${6 + (index % 4) * 23}%`, top: `${12 + Math.floor(index / 4) * 22}%` }}>
                <strong>{node.label}</strong>
                <span>{node.type}</span>
              </div>
            ))}
            {!nodes.length && <p>No graph available. Index a repository first.</p>}
          </div>
        </Panel>
        <Panel title="Selected Node Details">
          <PreviewLine label="Graph nodes" value={String(graph?.nodes.length ?? 0)} />
          <PreviewLine label="Graph edges" value={String(graph?.edges.length ?? 0)} />
          <PreviewLine label="Endpoints" value={String(overview?.endpoints.length ?? 0)} />
          <h3>Relation sample</h3>
          {edges.map((edge) => <ListRow key={`${edge.source}-${edge.target}-${edge.type}`} title={edge.type} detail={`${edge.source} -> ${edge.target}`} meta={String(edge.confidence)} />)}
        </Panel>
      </div>
    </div>
  )
}

function ApiExplorerPage({ overview }: { overview: Overview | null }) {
  const endpoints = overview?.endpoints ?? []
  return (
    <div>
      <PageTitle title="API Explorer" subtitle="Detected FastAPI endpoints, handler files, modules, and source line ranges." />
      <div className="api-layout">
        <Panel title="Endpoints">
          <div className="toolbar">
            <span className="tab active">All</span>
            <span className="tab">GET</span>
            <span className="tab">POST</span>
            <span className="tab">Auth required</span>
          </div>
          <table className="api-table">
            <thead><tr><th>Method</th><th>Path</th><th>Handler</th><th>File</th><th>Lines</th></tr></thead>
            <tbody>
              {endpoints.map((endpoint) => (
                <tr key={`${endpoint.method}-${endpoint.path}-${endpoint.start_line}`}>
                  <td><span className={`method ${endpoint.method.toLowerCase()}`}>{endpoint.method}</span></td>
                  <td>{endpoint.path}</td>
                  <td>{endpoint.handler}</td>
                  <td>{endpoint.file_path}</td>
                  <td>{endpoint.start_line}-{endpoint.end_line}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!endpoints.length && <p>No endpoint detected.</p>}
        </Panel>
        <Panel title="Endpoint Detail">
          {endpoints[0] ? (
            <>
              <PreviewLine label="Endpoint path" value={endpoints[0].path} />
              <PreviewLine label="HTTP method" value={endpoints[0].method} />
              <PreviewLine label="Handler" value={endpoints[0].handler} />
              <PreviewLine label="File" value={endpoints[0].file_path} />
              <InDevelopmentInline text="Request model, response model, auth hint, and internal calls need richer parser output." />
            </>
          ) : (
            <p>Index a FastAPI repository to inspect endpoints.</p>
          )}
        </Panel>
      </div>
    </div>
  )
}

function AssistantFullPage({
  input,
  messages,
  disabled,
  onInput,
  onSubmit,
  onEvidence,
}: {
  input: string
  messages: ChatMessage[]
  disabled: boolean
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
}) {
  return (
    <div>
      <PageTitle title="AI Assistant" subtitle="Ask grounded questions about architecture, API flow, debugging, onboarding, and impact." />
      <AssistantChat input={input} messages={messages} disabled={disabled} onInput={onInput} onSubmit={onSubmit} onEvidence={onEvidence} full />
    </div>
  )
}

function ImpactPage({ overview }: { overview: Overview | null }) {
  return (
    <div>
      <PageTitle title="Impact Analysis" subtitle="Understand direct and indirect effects before changing a file, symbol, endpoint, or model." />
      <div className="impact-grid">
        <Panel title="Target">
          <label>
            Target type
            <select defaultValue="symbol"><option>symbol</option><option>file</option><option>endpoint</option><option>model</option></select>
          </label>
          <label>
            Target reference
            <input defaultValue="authenticate_user" />
          </label>
          <button className="primary" disabled>Run Impact Analysis</button>
        </Panel>
        <Panel title="Impact Result">
          <InDevelopmentInline text="Backend impact API is dang phat trien. Current graph has enough foundation for file/symbol/endpoint neighbors." />
          <div className="impact-columns">
            <ListRow title="Direct impact" detail={`${overview?.endpoints.length ?? 0} endpoints can be considered after graph query support.`} />
            <ListRow title="Affected tests" detail="Requires test parser and tested_by relations." />
            <ListRow title="Suggested checks" detail="Login success, invalid password, token validation." />
          </div>
        </Panel>
      </div>
    </div>
  )
}

function SearchPage({
  query,
  results,
  onQuery,
  onSearch,
  onEvidence,
}: {
  query: string
  results: SearchResult[]
  onQuery: (value: string) => void
  onSearch: (event: FormEvent) => void
  onEvidence: (citation: Citation) => void
}) {
  return (
    <div>
      <PageTitle title="Search" subtitle="Find files, functions, endpoints, docs, tests, and concepts across the indexed codebase." />
      <form className="search-bar" onSubmit={onSearch}>
        <input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Search functions, files, endpoints, concepts..." />
        <button className="primary">Search</button>
      </form>
      <div className="toolbar">
        <span className="tab active">Hybrid</span>
        <span className="tab">Keyword</span>
        <span className="tab">Semantic</span>
        <span className="tab">Files</span>
        <span className="tab">Endpoints</span>
        <span className="tab">Docs</span>
      </div>
      <Panel title="Search Results">
        {results.length ? (
          results.map((result) => (
            <button
              className="result-card"
              key={result.evidence_id}
              onClick={() =>
                onEvidence({
                  evidence_id: result.evidence_id,
                  file_path: result.file_path,
                  symbol_name: result.title,
                  start_line: result.start_line,
                  end_line: result.end_line,
                })
              }
            >
              <span>{result.file_path}</span>
              <strong>{result.title}</strong>
              <p>{result.preview}</p>
              <em>{result.score}</em>
            </button>
          ))
        ) : (
          <p>No results yet. Run a search after indexing.</p>
        )}
      </Panel>
    </div>
  )
}

function EvidencePage({ evidence }: { evidence: Evidence | null }) {
  return (
    <div>
      <PageTitle title="Evidence / Citation Viewer" subtitle="Verify AI answers by file path, line range, source preview, and retrieval reason." />
      {!evidence ? (
        <EmptyState title="No evidence selected" description="Ask the assistant or run search, then click a citation." />
      ) : (
        <div className="evidence-grid">
          <Panel title="Citation Context">
            <PreviewLine label="Evidence ID" value={evidence.evidence_id} />
            <PreviewLine label="Source type" value={evidence.source_type} />
            <PreviewLine label="File" value={evidence.file_path} />
            <PreviewLine label="Lines" value={`${evidence.start_line}-${evidence.end_line}`} />
            <PreviewLine label="Confidence" value={String(evidence.confidence_score)} />
            <PreviewLine label="Retrieval" value={evidence.retrieval_source} />
          </Panel>
          <Panel title="Source Preview">
            <pre className="code-block compact">{evidence.content_preview}</pre>
            <p>{evidence.relevance_reason}</p>
          </Panel>
        </div>
      )}
    </div>
  )
}

function EvaluationPage() {
  const questions = ['Where is login implemented?', 'Which files are related to authentication?', 'What happens if User model changes?', 'Explain restaurant recommendation flow.']
  return (
    <div>
      <PageTitle title="Evaluation" subtitle="Measure answer groundedness, citation coverage, retrieval precision, and failed questions." />
      <div className="evaluation-grid">
        <Panel title="Benchmark Questions">
          {questions.map((question) => <ListRow key={question} title={question} detail="Pending evaluation runner." meta="not run" />)}
        </Panel>
        <Panel title="Metrics">
          <Metric label="Answer groundedness" value="-" />
          <Metric label="Citation coverage" value="-" />
          <Metric label="Retrieval precision" value="-" />
          <Metric label="Average latency" value="-" />
          <InDevelopmentInline text="Evaluation backend is dang phat trien." />
        </Panel>
      </div>
    </div>
  )
}

function SettingsPage({ isWorkspace }: { isWorkspace: boolean }) {
  return (
    <div>
      <PageTitle title="Settings" subtitle={isWorkspace ? 'Workspace parser, RAG, LLM, and storage configuration.' : 'Project management and import settings.'} />
      <div className="settings-grid">
        <Panel title="Project Settings">
          <ConfigRow label="Default indexing profile" value="Balanced" />
          <ConfigRow label="Local path import" value="Enabled for trusted paths" />
        </Panel>
        <Panel title="Indexing Settings">
          <ConfigRow label="Ignore folders" value="node_modules, .venv, dist, build" />
          <ConfigRow label="Max file size" value="1 MB" />
          <ConfigRow label="Re-index mode" value="Full rebuild" />
        </Panel>
        <Panel title="Parser Settings">
          <ConfigRow label="Python AST" value="Enabled" />
          <ConfigRow label="JS/TS parser" value="Basic heuristic" />
          <ConfigRow label="FastAPI endpoint detection" value="Enabled" />
        </Panel>
        <Panel title="RAG and LLM Settings">
          <ConfigRow label="Current retrieval" value="Keyword + metadata MVP" />
          <ConfigRow label="Vector embeddings" value="Dang phat trien" />
          <ConfigRow label="LLM provider" value="Dang phat trien" />
        </Panel>
        <Panel title="Danger Zone">
          <button className="secondary" disabled>Delete Project</button>
        </Panel>
      </div>
    </div>
  )
}

function WorkspacePage({ main, side }: { main: ReactNode; side: ReactNode }) {
  return (
    <div className="workspace-layout">
      <div>{main}</div>
      <aside>{side}</aside>
    </div>
  )
}

function AssistantPanel({
  input,
  messages,
  disabled,
  onInput,
  onSubmit,
  onEvidence,
}: {
  input: string
  messages: ChatMessage[]
  disabled: boolean
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
}) {
  return (
    <Panel title="AI Assistant">
      <AssistantChat input={input} messages={messages} disabled={disabled} onInput={onInput} onSubmit={onSubmit} onEvidence={onEvidence} />
    </Panel>
  )
}

function AssistantChat({
  input,
  messages,
  disabled,
  full = false,
  onInput,
  onSubmit,
  onEvidence,
}: {
  input: string
  messages: ChatMessage[]
  disabled: boolean
  full?: boolean
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
}) {
  return (
    <div className={full ? 'assistant-chat full' : 'assistant-chat'}>
      <div className="chat-feed">
        {messages.map((message, index) => (
          <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
            <strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong>
            <p>{message.content}</p>
            {message.citations && message.citations.length > 0 && (
              <div className="citation-list">
                {message.citations.map((citation) => (
                  <button key={citation.evidence_id} onClick={() => onEvidence(citation)}>
                    {citation.file_path}:{citation.start_line}-{citation.end_line}
                  </button>
                ))}
              </div>
            )}
            {message.evidenceSufficient === false && <span className="badge amber">Insufficient evidence</span>}
          </article>
        ))}
      </div>
      <form className="chat-form" onSubmit={onSubmit}>
        <input disabled={disabled} value={input} onChange={(event) => onInput(event.target.value)} placeholder={disabled ? 'Index a repository before chatting.' : 'Ask anything about your codebase...'} />
        <button className="primary" disabled={disabled}>Send</button>
      </form>
    </div>
  )
}

function FileTree({
  nodes,
  selectedFilePath,
  onSelectFile,
  depth = 0,
}: {
  nodes: FileTreeNode[]
  selectedFilePath: string
  onSelectFile: (filePath: string) => void
  depth?: number
}) {
  return (
    <div className="file-tree">
      {nodes.map((node) => (
        <div key={node.path}>
          {node.type === 'file' ? (
            <button className={selectedFilePath === node.path ? 'active' : ''} style={{ paddingLeft: `${12 + depth * 16}px` }} onClick={() => onSelectFile(node.path)}>
              <span>File</span>{node.name}
            </button>
          ) : (
            <div className="tree-folder" style={{ paddingLeft: `${12 + depth * 16}px` }}><span>Dir</span>{node.name}</div>
          )}
          {node.children.length > 0 && <FileTree nodes={node.children} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} depth={depth + 1} />}
        </div>
      ))}
    </div>
  )
}

function GraphDetails({ graph }: { graph: GraphData | null }) {
  return (
    <Panel title="Node Details">
      <PreviewLine label="Nodes" value={String(graph?.nodes.length ?? 0)} />
      <PreviewLine label="Edges" value={String(graph?.edges.length ?? 0)} />
      <h3>Filters</h3>
      <div className="setting-chips">
        <span>file</span>
        <span>symbol</span>
        <span>endpoint</span>
        <span>calls_api</span>
      </div>
    </Panel>
  )
}

function ApiDetails({ overview }: { overview: Overview | null }) {
  const endpoint = overview?.endpoints[0]
  return (
    <Panel title="API Detail">
      {endpoint ? (
        <>
          <PreviewLine label="Path" value={endpoint.path} />
          <PreviewLine label="Method" value={endpoint.method} />
          <PreviewLine label="Handler" value={endpoint.handler} />
          <PreviewLine label="File" value={endpoint.file_path} />
        </>
      ) : (
        <p>No endpoint selected.</p>
      )}
    </Panel>
  )
}

function SearchFilters() {
  return (
    <Panel title="Filters">
      <h3>Scope</h3>
      <div className="setting-chips"><span>Files</span><span>Functions</span><span>Classes</span><span>Endpoints</span><span>Docs</span><span>Tests</span></div>
      <h3>Areas</h3>
      <div className="setting-chips"><span>Frontend</span><span>Backend</span><span>Config</span></div>
    </Panel>
  )
}

function EvidenceSummary() {
  return (
    <Panel title="Evidence">
      <p>Click a citation from chat or search to open the Evidence Viewer.</p>
      <InDevelopmentInline text="Graph trace and answer-to-evidence mapping will improve with the agent workflow." />
    </Panel>
  )
}

function InDevelopmentPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <Panel title={title}>
      <InDevelopmentInline text={detail} />
    </Panel>
  )
}

function WizardSteps() {
  return (
    <div className="wizard">
      {['Import Repo', 'Configure', 'Preview', 'Index'].map((step, index) => (
        <div className={`wizard-step ${index === 0 ? 'active' : ''}`} key={step}>
          <span>{index + 1}</span>{step}
        </div>
      ))}
    </div>
  )
}

function SourceCard({ label, detail, active, onClick }: { label: string; detail: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" className={`source-card ${active ? 'active' : ''}`} onClick={onClick}>
      <strong>{label}</strong>
      <span>{detail}</span>
    </button>
  )
}

function ProfileCard({ title, detail, active = false }: { title: string; detail: string; active?: boolean }) {
  return (
    <div className={`profile-card ${active ? 'active' : ''}`}>
      <strong>{title}</strong>
      <p>{detail}</p>
      {active && <span>Recommended</span>}
    </div>
  )
}

function Checklist({ items, done }: { items: string[]; done: number }) {
  return (
    <div className="checklist">
      {items.map((item, index) => (
        <div key={item} className={index < done ? 'done' : ''}>
          <span>{index < done ? 'Done' : 'Todo'}</span>
          {item}
        </div>
      ))}
      <Progress value={(done / items.length) * 100} />
    </div>
  )
}

function Activity({ text, meta, tone = 'success' }: { text: string; meta: string; tone?: 'success' | 'running' | 'danger' | 'neutral' }) {
  return (
    <div className="activity">
      <span className={`activity-icon ${tone}`}>
        <Icon name={tone === 'danger' ? 'warning' : tone === 'running' ? 'refresh' : 'check'} />
      </span>
      <span>{text}</span>
      <b>{meta}</b>
    </div>
  )
}

function PageTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-title">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
  )
}

function Panel({ title, action, children }: { title: string; action?: string; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        {action && <button>{action}</button>}
      </div>
      {children}
    </section>
  )
}

function SideInfo({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="side-info">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

function Metric({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
    </div>
  )
}

function StatCell({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="stat-cell">
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
    </div>
  )
}

function ListRow({ title, detail, meta }: { title: string; detail: string; meta?: string }) {
  return (
    <div className="list-row">
      <strong>{title}</strong>
      <p>{detail}</p>
      {meta && <span>{meta}</span>}
    </div>
  )
}

function EmptyState({ title, description, action, onAction }: { title: string; description: string; action?: string; onAction?: () => void }) {
  return (
    <div className="empty-state">
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <button className="primary" onClick={onAction}>{action}</button>}
    </div>
  )
}

function PreviewLine({ label, value }: { label: string; value: string }) {
  return <div className="preview-line"><span>{label}</span><strong>{value}</strong></div>
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return <div className="config-row"><span>{label}</span><strong>{value}</strong></div>
}

function LanguageBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="language-bar">
      <PreviewLine label={label} value={`${value}%`} />
      <Progress value={value} />
    </div>
  )
}

function Progress({ value }: { value: number }) {
  return (
    <div className="progress">
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

function InDevelopmentInline({ text }: { text: string }) {
  return (
    <div className="developing-inline">
      <span>Dang phat trien</span>
      <p>{text}</p>
    </div>
  )
}

function findFirstFile(nodes: FileTreeNode[]): FileTreeNode | null {
  for (const node of nodes) {
    if (node.type === 'file') return node
    const child = findFirstFile(node.children)
    if (child) return child
  }
  return null
}

function canChat(repository?: Repository) {
  return Boolean(repository && repository.status === 'indexed')
}

function isManagementNavActive(page: Page, label: string) {
  if (page === 'dashboard') return label === 'Projects'
  if (page === 'indexing') return label === 'Index Jobs'
  if (page === 'settings') return label === 'Settings'
  if (page === 'import') return label === 'Projects'
  return false
}

function Icon({ name }: { name: IconName }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    strokeWidth: 2,
  }
  const paths: Record<IconName, ReactNode> = {
    home: <><path d="M3 10.8 12 4l9 6.8" /><path d="M5 10v10h14V10" /><path d="M10 20v-6h4v6" /></>,
    folder: <><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    star: <><path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9Z" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5Z" /><path d="m3 12 9 5 9-5" /><path d="m3 16 9 5 9-5" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1-2 3.4-.2-.1a1.8 1.8 0 0 0-1.9 0 1.8 1.8 0 0 0-.9 1.6V22H9.2v-.2a1.8 1.8 0 0 0-.9-1.6 1.8 1.8 0 0 0-1.9 0l-.2.1-2-3.4.1-.1A1.7 1.7 0 0 0 4.6 15 1.8 1.8 0 0 0 3 14H3v-4h.1a1.8 1.8 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1 2-3.4.2.1a1.8 1.8 0 0 0 1.9 0 1.8 1.8 0 0 0 .9-1.6V2h5.6v.2a1.8 1.8 0 0 0 .9 1.6 1.8 1.8 0 0 0 1.9 0l.2-.1 2 3.4-.1.1a1.7 1.7 0 0 0-.3 1.8 1.8 1.8 0 0 0 1.5 1h.1v4h-.1a1.8 1.8 0 0 0-1.5 1Z" /></>,
    nodes: <><circle cx="6" cy="6" r="3" /><circle cx="18" cy="6" r="3" /><circle cx="12" cy="18" r="3" /><path d="m8.5 8 2 7" /><path d="m15.5 8-2 7" /><path d="M9 6h6" /></>,
    share: <><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="m8.6 10.8 6.8-4.6" /><path d="m8.6 13.2 6.8 4.6" /></>,
    sliders: <><path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h16" /><circle cx="8" cy="6" r="2" /><circle cx="15" cy="12" r="2" /><circle cx="11" cy="18" r="2" /></>,
    spark: <><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6Z" /><path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7Z" /></>,
    target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
    chart: <><path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 15v-4" /><path d="M12 15V8" /><path d="M16 15v-6" /></>,
    code: <><path d="m9 18-6-6 6-6" /><path d="m15 6 6 6-6 6" /><path d="m14 4-4 16" /></>,
    grid: <><path d="M4 4h7v7H4z" /><path d="M13 4h7v7h-7z" /><path d="M4 13h7v7H4z" /><path d="M13 13h7v7h-7z" /></>,
    list: <><path d="M8 6h13" /><path d="M8 12h13" /><path d="M8 18h13" /><path d="M3 6h.01" /><path d="M3 12h.01" /><path d="M3 18h.01" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.8 2.8 0 1 1 4.8 2c-.9.8-1.8 1.3-1.8 3" /><path d="M12 17h.01" /></>,
    plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
    more: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
    refresh: <><path d="M20 12a8 8 0 0 1-14.9 4" /><path d="M4 16v5h5" /><path d="M4 12A8 8 0 0 1 18.9 8" /><path d="M20 8V3h-5" /></>,
    pause: <><path d="M9 5v14" /><path d="M15 5v14" /></>,
    warning: <><path d="m12 3 10 18H2Z" /><path d="M12 9v5" /><path d="M12 17h.01" /></>,
    check: <><path d="m5 12 4 4L19 6" /></>,
    git: <><path d="m7 7 10 10" /><circle cx="7" cy="7" r="3" /><circle cx="17" cy="17" r="3" /><path d="M7 10v4a3 3 0 0 0 3 3h4" /></>,
  }

  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
      <g {...common}>{paths[name]}</g>
    </svg>
  )
}

export default App
