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

const navItems: { page: Page; label: string; icon: string }[] = [
  { page: 'dashboard', label: 'Projects', icon: 'P' },
  { page: 'overview', label: 'Overview', icon: 'O' },
  { page: 'code', label: 'Code Explorer', icon: 'C' },
  { page: 'graph', label: 'Graph View', icon: 'G' },
  { page: 'api', label: 'API Explorer', icon: 'A' },
  { page: 'impact', label: 'Impact Analysis', icon: 'I' },
  { page: 'search', label: 'Search', icon: 'S' },
  { page: 'evaluation', label: 'Evaluation', icon: 'E' },
  { page: 'settings', label: 'Settings', icon: 'T' },
]

const indexingSteps = [
  'Scan repository files',
  'Apply ignore rules',
  'Parse Python AST',
  'Parse JavaScript / TypeScript',
  'Create citation chunks',
  'Build code graph',
  'Finalize project overview',
]

function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [selectedRepositoryId, setSelectedRepositoryId] = useState<string>('')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([])
  const [selectedFilePath, setSelectedFilePath] = useState('')
  const [fileContent, setFileContent] = useState<FileContent | null>(null)
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Import and index a repository, then ask about architecture, login flow, API endpoints, debugging points, or onboarding files.',
      citations: [],
      evidenceSufficient: false,
    },
  ])
  const [chatInput, setChatInput] = useState('Luong login hoat dong nhu the nao?')
  const [searchQuery, setSearchQuery] = useState('login auth token')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [localPath, setLocalPath] = useState('../tests/fixtures/fastapi_react_sample')
  const [projectName, setProjectName] = useState('fastapi-react-sample')
  const [importMode, setImportMode] = useState<'folder' | 'zip' | 'local'>('folder')
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [apiError, setApiError] = useState<string>('')

  const selectedRepository = useMemo(
    () => repositories.find((repository) => repository.id === selectedRepositoryId) ?? repositories[0],
    [repositories, selectedRepositoryId],
  )

  useEffect(() => {
    void loadRepositories()
    // Initial repository load should run once when the app starts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedRepository) return
    if (selectedRepository.status === 'indexed') {
      void loadOverview(selectedRepository.id)
      void loadGraph(selectedRepository.id)
      void loadFileTree(selectedRepository.id)
    }
    void loadIndexStatus(selectedRepository.id)
    // Reload workspace data when the selected repository identity or status changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRepository?.id, selectedRepository?.status])

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
        setSelectedFilePath(firstFile.path)
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

  async function importLocalRepository(event: FormEvent) {
    event.preventDefault()
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
    await indexNewRepository(result.repository_id)
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
    await indexNewRepository(result.repository_id)
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
    await indexNewRepository(result.repository_id)
  }

  async function indexNewRepository(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    await request(`${API_V1}/repositories/${repositoryId}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_reindex: true }),
    })
    await loadRepositories()
    await loadIndexStatus(repositoryId)
    await loadOverview(repositoryId)
    await loadGraph(repositoryId)
    await loadFileTree(repositoryId)
    setPage('indexing')
  }

  async function reindexSelectedRepository() {
    if (!selectedRepository) return
    await request(`${API_V1}/repositories/${selectedRepository.id}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_reindex: true }),
    })
    await loadRepositories()
    await loadIndexStatus(selectedRepository.id)
    setPage('indexing')
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
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <strong>AI Codebase Assistant</strong>
            <span>Beta</span>
          </div>
        </div>
        <nav>
          {navItems.map((item) => (
            <button key={item.page} className={page === item.page ? 'active' : ''} onClick={() => setPage(item.page)}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
        <IndexCard repository={selectedRepository} status={indexStatus} onReindex={reindexSelectedRepository} />
      </aside>

      <main className="main">
        <TopBar repository={selectedRepository} onNewProject={() => setPage('import')} />
        {apiError && <div className="error-banner">{apiError}</div>}
        <section className="content">{renderPage()}</section>
        <ChatDock
          disabled={!selectedRepository || selectedRepository.status !== 'indexed'}
          input={chatInput}
          messages={chatMessages}
          onInput={setChatInput}
          onSubmit={sendChatMessage}
          onEvidence={openEvidence}
        />
      </main>
    </div>
  )

  function renderPage() {
    if (page === 'dashboard') {
      return (
        <DashboardPage
          repositories={repositories}
          onNewProject={() => setPage('import')}
          onOpen={(id) => {
            setSelectedRepositoryId(id)
            setPage('overview')
          }}
          onReindex={async (id) => {
            setSelectedRepositoryId(id)
            await request(`${API_V1}/repositories/${id}/index`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ force_reindex: true }),
            })
            await loadRepositories()
            setPage('indexing')
          }}
        />
      )
    }
    if (page === 'import') {
      return (
        <ImportPage
          localPath={localPath}
          projectName={projectName}
          onPathChange={setLocalPath}
          onNameChange={setProjectName}
          mode={importMode}
          onModeChange={setImportMode}
          folderCount={folderFiles.length}
          zipFileName={zipFile?.name ?? ''}
          onFolderFiles={setFolderFiles}
          onZipFile={setZipFile}
          onSubmit={importLocalRepository}
        />
      )
    }
    if (page === 'indexing') return <IndexingPage status={indexStatus} onOpen={() => setPage('overview')} />
    if (page === 'overview') return <OverviewPage overview={overview} onAsk={sendChatMessage} setChatInput={setChatInput} />
    if (page === 'code') {
      return (
        <CodeExplorerPage
          overview={overview}
          fileTree={fileTree}
          selectedFilePath={selectedFilePath}
          fileContent={fileContent}
          onSelectFile={(filePath) => selectedRepository && loadFileContent(selectedRepository.id, filePath)}
        />
      )
    }
    if (page === 'graph') return <GraphPage graph={graph} overview={overview} />
    if (page === 'api') return <ApiExplorerPage overview={overview} />
    if (page === 'impact') return <DevelopingPage title="Impact Analysis" description="Impact analysis will use graph neighbors, imports, calls, API endpoints, and test references. MVP backend already exposes basic graph data." />
    if (page === 'search') return <SearchPage query={searchQuery} results={searchResults} onQuery={setSearchQuery} onSearch={runSearch} onEvidence={openEvidence} />
    if (page === 'evidence') return <EvidencePage evidence={selectedEvidence} />
    if (page === 'evaluation') return <DevelopingPage title="Evaluation" description="Evaluation dashboard is documented for later phase. MVP exposes grounded chat and citation behavior for manual testing first." />
    return <SettingsPage />
  }
}

function TopBar({ repository, onNewProject }: { repository?: Repository; onNewProject: () => void }) {
  return (
    <header className="topbar">
      <div className="select-pill">{repository?.name ?? 'No repository selected'}</div>
      <div className="select-pill">main</div>
      <div className={`status-pill ${repository?.status === 'indexed' ? 'green' : ''}`}>{repository?.status ?? 'not imported'}</div>
      <input className="global-search" placeholder="Search anything..." />
      <button className="primary" onClick={onNewProject}>
        New Project
      </button>
    </header>
  )
}

function IndexCard({ repository, status, onReindex }: { repository?: Repository; status: IndexStatus | null; onReindex: () => void }) {
  return (
    <div className="index-card">
      <div className="between">
        <h3>Index Status</h3>
        <span className="badge green">{repository?.status ?? 'Empty'}</span>
      </div>
      <dl>
        <div><dt>Files indexed</dt><dd>{repository?.indexed_files ?? 0}</dd></div>
        <div><dt>Chunks</dt><dd>{repository?.chunks ?? 0}</dd></div>
        <div><dt>Step</dt><dd>{status?.current_step ?? 'not started'}</dd></div>
      </dl>
      <div className="progress"><span style={{ width: `${status?.progress ?? 0}%` }} /></div>
      <button className="secondary wide" disabled={!repository} onClick={onReindex}>Re-index Project</button>
    </div>
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
  return (
    <div>
      <PageTitle title="Project Dashboard" subtitle="Manage and monitor codebase analysis projects." />
      <div className="toolbar">
        <span className="tab active">All Projects {repositories.length}</span>
        <span className="tab">Indexed {repositories.filter((item) => item.status === 'indexed').length}</span>
        <span className="tab">Errors 0</span>
        <button className="primary" onClick={onNewProject}>Import New Repository</button>
      </div>
      {repositories.length === 0 ? (
        <EmptyState title="No repository imported" description="Import the fixture repository or your own local project to start indexing." action="New Project" onAction={onNewProject} />
      ) : (
        <div className="dashboard-grid">
          <div className="project-grid">
            {repositories.map((repository) => (
              <article className="project-card" key={repository.id}>
                <div className="between">
                  <div>
                    <h3>{repository.name}</h3>
                    <p>{repository.source_uri}</p>
                  </div>
                  <span className={`badge ${repository.status === 'indexed' ? 'green' : 'blue'}`}>{repository.status}</span>
                </div>
                <div className="tech-row">
                  <span>Python</span><span>FastAPI</span><span>React</span><span>Local</span>
                </div>
                <div className="stats-row">
                  <Metric label="Files" value={repository.total_files} />
                  <Metric label="Symbols" value={repository.symbols} />
                  <Metric label="Endpoints" value={repository.endpoints} />
                </div>
                <div className="card-actions">
                  <button className="primary" onClick={() => onOpen(repository.id)}>Open Workspace</button>
                  <button className="secondary" onClick={() => onReindex(repository.id)}>Re-index</button>
                </div>
              </article>
            ))}
          </div>
          <aside className="right-stack">
            <Panel title="Recent Activity">
              <Activity text="Repository imported" tone="green" />
              <Activity text="Indexing completed" tone="blue" />
              <Activity text="Evidence layer ready" tone="green" />
            </Panel>
            <Panel title="Workspace Insights">
              <div className="stats-row two">
                <Metric label="Projects" value={repositories.length} />
                <Metric label="Indexed" value={repositories.filter((item) => item.status === 'indexed').length} />
              </div>
            </Panel>
          </aside>
        </div>
      )}
    </div>
  )
}

function ImportPage({
  localPath,
  projectName,
  onPathChange,
  onNameChange,
  mode,
  onModeChange,
  folderCount,
  zipFileName,
  onFolderFiles,
  onZipFile,
  onSubmit,
}: {
  localPath: string
  projectName: string
  onPathChange: (value: string) => void
  onNameChange: (value: string) => void
  mode: 'folder' | 'zip' | 'local'
  onModeChange: (value: 'folder' | 'zip' | 'local') => void
  folderCount: number
  zipFileName: string
  onFolderFiles: (value: File[]) => void
  onZipFile: (value: File | null) => void
  onSubmit: (event: FormEvent) => void
}) {
  return (
    <div>
      <PageTitle title="New Project" subtitle="Import and configure a repository to index and power code intelligence." />
      <div className="wizard">
        <span className="step active">1 Import Repo</span>
        <span className="step">2 Configure</span>
        <span className="step">3 Preview</span>
        <span className="step">4 Index</span>
      </div>
      <div className="two-column">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <h2>1. Import Repository</h2>
          <div className="source-grid">
            <button type="button" className={`source-card ${mode === 'folder' ? 'active' : ''}`} onClick={() => onModeChange('folder')}>
              Upload Folder<br /><small>Browser folder upload</small>
            </button>
            <button type="button" className={`source-card ${mode === 'zip' ? 'active' : ''}`} onClick={() => onModeChange('zip')}>
              Upload ZIP<br /><small>Archive import</small>
            </button>
            <button type="button" className={`source-card ${mode === 'local' ? 'active' : ''}`} onClick={() => onModeChange('local')}>
              Local Path<br /><small>Backend machine path</small>
            </button>
          </div>
          <label>Project Name<input value={projectName} onChange={(event) => onNameChange(event.target.value)} /></label>
          {mode === 'folder' && (
            <label>
              Project Folder
              <input
                type="file"
                multiple
                {...{ webkitdirectory: '', directory: '' }}
                onChange={(event) => onFolderFiles(Array.from(event.target.files ?? []))}
              />
              <span className="helper">{folderCount} files selected. Secret and unsupported files are filtered by backend.</span>
            </label>
          )}
          {mode === 'zip' && (
            <label>
              Repository ZIP
              <input type="file" accept=".zip" onChange={(event) => onZipFile(event.target.files?.[0] ?? null)} />
              <span className="helper">{zipFileName || 'No zip selected.'}</span>
            </label>
          )}
          {mode === 'local' && (
            <>
              <label>Local Path<input value={localPath} onChange={(event) => onPathChange(event.target.value)} /></label>
              <p className="helper">Default fixture path works when backend is started from the `backend` folder.</p>
            </>
          )}
          <h2>2. Configure Parsing & Indexing</h2>
          <div className="settings-grid">
            <ConfigRow label="Ignore folders" value=".git, node_modules, .venv, dist, build" />
            <ConfigRow label="Indexing Profile" value="Balanced" />
            <ConfigRow label="Python AST" value="Enabled" />
            <ConfigRow label="JS/TS parser" value="Heuristic MVP" />
          </div>
          <button className="primary wide" type="submit">Import and Index</button>
        </form>
        <Panel title="Import Preview">
          <PreviewLine label="Repository" value={projectName} />
          <PreviewLine label="Source" value={mode === 'folder' ? 'Uploaded folder' : mode === 'zip' ? 'Uploaded zip' : 'Local path'} />
          <PreviewLine label="Ignored" value=".env, secrets, credentials, node_modules" />
          <PreviewLine label="Supported" value="Python, JS, TS, Markdown, JSON, YAML" />
          <PreviewLine label="MVP behavior" value="Synchronous local indexing" />
        </Panel>
      </div>
    </div>
  )
}

function IndexingPage({ status, onOpen }: { status: IndexStatus | null; onOpen: () => void }) {
  return (
    <div>
      <PageTitle title="Indexing Repository" subtitle="Scan, parse, chunk and build a searchable evidence graph." />
      <div className="hero-progress">
        <strong>{status?.progress ?? 0}%</strong>
        <div className="progress"><span style={{ width: `${status?.progress ?? 0}%` }} /></div>
        <button className="primary" disabled={status?.status !== 'indexed'} onClick={onOpen}>Open Workspace</button>
      </div>
      <div className="three-column">
        <Panel title="Indexing Pipeline">
          <ol className="pipeline">
            {indexingSteps.map((step, index) => (
              <li key={step} className={status?.status === 'indexed' || index < 6 ? 'done' : ''}>{step}</li>
            ))}
          </ol>
        </Panel>
        <Panel title="Live Log">
          <div className="log-box">{status?.logs.map((log) => <p key={log}>{log}</p>) ?? <p>No job started.</p>}</div>
        </Panel>
        <Panel title="Indexing Metrics">
          <Metric label="Files processed" value={status?.processed_files ?? 0} />
          <Metric label="Failed files" value={status?.failed_files ?? 0} />
          <Metric label="Warnings" value={status?.warnings.length ?? 0} />
          <div className="warning-list">{status?.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div>
        </Panel>
      </div>
    </div>
  )
}

function OverviewPage({ overview, setChatInput, onAsk }: { overview: Overview | null; setChatInput: (value: string) => void; onAsk: () => void }) {
  if (!overview) return <EmptyState title="Repository is not indexed" description="Import and index a repository before opening the workspace." />
  const questions = ['How does the login flow work?', 'Which files define API endpoints?', 'Where should a new developer start?', 'What documentation gaps exist?']
  return (
    <WorkspaceLayout
      main={
        <>
          <PageTitle title={overview.name} subtitle="AI-powered code understanding with evidence and line citations." />
          <div className="stats-row cards">
            <Metric label="Files" value={overview.stats.files} />
            <Metric label="Functions" value={overview.stats.functions} />
            <Metric label="Classes" value={overview.stats.classes} />
            <Metric label="API Endpoints" value={overview.stats.endpoints} />
            <Metric label="Graph Nodes" value={overview.stats.graph_nodes} />
            <Metric label="Chunks" value={overview.stats.chunks} />
          </div>
          <div className="overview-grid">
            <Panel title="Architecture Summary">
              <div className="stack-flow">
                {overview.detected_stack.map((item) => <span key={item}>{item}</span>)}
              </div>
              <p>Project Mental Model is generated from parsed files, endpoints, symbols, docs and graph relations.</p>
            </Panel>
            <Panel title="Key Modules">
              {overview.modules.map((module) => <ListRow key={module.name} title={module.name} detail={module.summary} meta={`${module.file_count} files`} />)}
            </Panel>
            <Panel title="Important Files">
              {overview.important_files.map((file) => <ListRow key={file.file_path} title={file.file_path} detail={file.reason} />)}
            </Panel>
            <Panel title="Suggested Questions">
              {questions.map((question) => (
                <button
                  className="question-row"
                  key={question}
                  onClick={() => {
                    setChatInput(question)
                    setTimeout(onAsk, 0)
                  }}
                >
                  {question}
                </button>
              ))}
            </Panel>
          </div>
        </>
      }
      side={<AssistantPanel />}
    />
  )
}

function CodeExplorerPage({
  overview,
  fileTree,
  selectedFilePath,
  fileContent,
  onSelectFile,
}: {
  overview: Overview | null
  fileTree: FileTreeNode[]
  selectedFilePath: string
  fileContent: FileContent | null
  onSelectFile: (filePath: string) => void
}) {
  return (
    <WorkspaceLayout
      main={
        <div>
          <PageTitle title="Code Explorer" subtitle="Browse parsed files, detected symbols and citation-ready line ranges." />
          <div className="code-layout">
            <Panel title="Files">
              {fileTree.length === 0 ? (
                <p>No file tree available yet.</p>
              ) : (
                <FileTree nodes={fileTree} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} />
              )}
            </Panel>
            <Panel title={fileContent?.file_path ?? 'No file selected'}>
              <pre className="code-block">
                {fileContent
                  ? fileContent.lines.map((line, index) => `${String(index + 1).padStart(4, ' ')}  ${line}`).join('\n')
                  : 'Import and index a repository to inspect code.'}
              </pre>
            </Panel>
          </div>
          <div className="two-column bottom">
            <Panel title="Detected Symbols">
              {(fileContent?.symbols ?? []).length === 0 && <p>No symbol found for this file.</p>}
              {(fileContent?.symbols ?? []).map((symbol) => (
                <div className="list-row" key={`${symbol.file_path}-${symbol.start_line}`}>
                  <strong>{symbol.symbol_name}</strong>
                  <p>Lines {symbol.start_line}-{symbol.end_line}</p>
                </div>
              ))}
            </Panel>
            <Panel title="Call Relationships">
              <DevelopingInline text={`Detailed call graph inside Code Explorer is dang phat trien. ${overview?.endpoints.length ?? 0} endpoints are available in API Explorer.`} />
            </Panel>
          </div>
        </div>
      }
      side={<AssistantPanel />}
    />
  )
}

function GraphPage({ graph, overview }: { graph: GraphData | null; overview: Overview | null }) {
  return (
    <div>
      <PageTitle title="Advanced Analysis" subtitle="Explore relationships, API flows and graph evidence." />
      <div className="graph-grid">
        <Panel title="Module Graph">
          <div className="graph-canvas">
            {(graph?.nodes ?? []).slice(0, 12).map((node, index) => (
              <div className={`graph-node type-${node.type}`} key={node.id} style={{ left: `${8 + (index % 4) * 23}%`, top: `${15 + Math.floor(index / 4) * 26}%` }}>
                <strong>{node.label}</strong>
                <span>{node.type}</span>
              </div>
            ))}
            {!graph?.nodes.length && <p>No graph available yet.</p>}
          </div>
        </Panel>
        <div className="right-stack">
          <ApiMiniTable overview={overview} />
          <Panel title="Impact Analysis">
            <DevelopingInline text="Impact Analysis is dang phat trien. MVP graph currently exposes file, symbol and endpoint relations." />
          </Panel>
        </div>
      </div>
    </div>
  )
}

function ApiExplorerPage({ overview }: { overview: Overview | null }) {
  return (
    <div>
      <PageTitle title="API Explorer" subtitle="Detected FastAPI endpoints with handler file and line range." />
      <ApiMiniTable overview={overview} expanded />
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
      <PageTitle title="Search" subtitle="Search codebase by keyword and MVP semantic matching." />
      <div className="two-column">
        <div>
          <form className="search-box" onSubmit={onSearch}>
            <input value={query} onChange={(event) => onQuery(event.target.value)} />
            <button className="primary">Search</button>
          </form>
          <div className="filter-row">
            <span>Semantic Search</span><span>Keyword Search</span><span>Hybrid</span><span>Backend only</span><span>Endpoints</span>
          </div>
          <Panel title="Results">
            {results.length === 0 ? (
              <p>No results yet. Run a search after indexing.</p>
            ) : (
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
            )}
          </Panel>
        </div>
        <Panel title="Filters">
          <h3>Scope</h3><div className="filter-row"><span>Backend</span><span>Frontend</span><span>Docs</span><span>Tests</span></div>
          <h3>Entity Type</h3><div className="filter-row"><span>File</span><span>Function</span><span>Class</span><span>Endpoint</span></div>
          <h3>UX note</h3><p>Click a result to open the Evidence / Citation Viewer.</p>
        </Panel>
      </div>
    </div>
  )
}

function EvidencePage({ evidence }: { evidence: Evidence | null }) {
  return (
    <div>
      <PageTitle title="Evidence / Citation Viewer" subtitle="Verify an answer by file, line range and code preview." />
      {!evidence ? (
        <EmptyState title="No evidence selected" description="Ask a question or run search, then click a citation." />
      ) : (
        <div className="two-column evidence-view">
          <Panel title="AI Answer Context">
            <p>Selected citation supports a grounded answer claim.</p>
            <h3>Citation</h3>
            <div className="citation-card active">{evidence.file_path}:{evidence.start_line}-{evidence.end_line}</div>
            <PreviewLine label="Confidence" value={String(evidence.confidence_score)} />
            <PreviewLine label="Source" value={evidence.retrieval_source} />
          </Panel>
          <Panel title={`Source: ${evidence.file_path}`}>
            <p>Lines {evidence.start_line} - {evidence.end_line}</p>
            <pre className="code-block">{evidence.content_preview}</pre>
            <h3>Citation behavior</h3>
            <p>Clicking a citation opens the exact evidence object returned by the backend.</p>
          </Panel>
        </div>
      )}
    </div>
  )
}

function SettingsPage() {
  return (
    <div>
      <PageTitle title="Settings" subtitle="Parser, indexing, RAG, LLM and storage configuration for each project." />
      <div className="settings-page">
        <Panel title="Indexing Settings">
          <ConfigRow label="Ignore folders" value="node_modules, .venv, dist, build" />
          <ConfigRow label="Max file size" value="1 MB" />
          <ConfigRow label="Re-index mode" value="Full rebuild in MVP" />
        </Panel>
        <Panel title="Parser Settings">
          <ConfigRow label="Python AST" value="Enabled" />
          <ConfigRow label="JS/TS parser" value="Heuristic regex MVP" />
          <ConfigRow label="FastAPI endpoints" value="Enabled" />
        </Panel>
        <Panel title="RAG Settings">
          <ConfigRow label="Vector DB" value="Dang phat trien for real embeddings" />
          <ConfigRow label="Retriever" value="Keyword + metadata MVP" />
          <ConfigRow label="Citation validator" value="Enabled" />
        </Panel>
        <Panel title="LLM Settings">
          <ConfigRow label="Provider" value="Dang phat trien" />
          <ConfigRow label="Current answer mode" value="Grounded template from evidence" />
        </Panel>
      </div>
    </div>
  )
}

function DevelopingPage({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <PageTitle title={title} subtitle={description} />
      <div className="developing-card">
        <span>Đang phát triển</span>
        <p>This page is included to match ui_ux.md and the UI assets, but full functionality is outside the current MVP implementation.</p>
      </div>
    </div>
  )
}

function AssistantPanel() {
  return (
    <Panel title="AI Assistant">
      <ChatContent />
    </Panel>
  )
}

function ChatContent() {
  return <p className="helper">Use the chat input in the app shell after importing and indexing. Evidence appears in assistant messages.</p>
}

function ChatDock({
  disabled,
  input,
  messages,
  onInput,
  onSubmit,
  onEvidence,
}: {
  disabled: boolean
  input: string
  messages: ChatMessage[]
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
}) {
  return (
    <section className="chat-dock">
      <div className="chat-feed">
        {messages.slice(-4).map((message, index) => (
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
        <input
          disabled={disabled}
          value={input}
          onChange={(event) => onInput(event.target.value)}
          placeholder={disabled ? 'Import and index a repository before chatting.' : 'Ask anything about your codebase...'}
        />
        <button className="primary" disabled={disabled}>Send</button>
      </form>
    </section>
  )
}

function WorkspaceLayout({ main, side }: { main: ReactNode; side: ReactNode }) {
  return (
    <div className="workspace-layout">
      <div>{main}</div>
      <aside>{side}</aside>
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
            <button
              className={selectedFilePath === node.path ? 'active' : ''}
              style={{ paddingLeft: `${12 + depth * 16}px` }}
              onClick={() => onSelectFile(node.path)}
            >
              <span>File</span>
              {node.name}
            </button>
          ) : (
            <div className="tree-folder" style={{ paddingLeft: `${12 + depth * 16}px` }}>
              <span>Folder</span>
              {node.name}
            </div>
          )}
          {node.children.length > 0 && (
            <FileTree nodes={node.children} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} depth={depth + 1} />
          )}
        </div>
      ))}
    </div>
  )
}

function ApiMiniTable({ overview, expanded = false }: { overview: Overview | null; expanded?: boolean }) {
  return (
    <Panel title={`API Explorer ${overview?.endpoints.length ?? 0} Endpoints`}>
      <table className="api-table">
        <thead><tr><th>Method</th><th>Path</th><th>Handler</th><th>Module</th></tr></thead>
        <tbody>
          {(overview?.endpoints ?? []).slice(0, expanded ? 50 : 8).map((endpoint) => (
            <tr key={`${endpoint.method}-${endpoint.path}-${endpoint.start_line}`}>
              <td><span className={`method ${endpoint.method.toLowerCase()}`}>{endpoint.method}</span></td>
              <td>{endpoint.path}</td>
              <td>{endpoint.handler}</td>
              <td>{endpoint.file_path}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!overview?.endpoints.length && <p>No endpoint detected. Index a FastAPI repository first.</p>}
    </Panel>
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

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
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

function Activity({ text, tone }: { text: string; tone: 'green' | 'blue' }) {
  return <div className={`activity ${tone}`}>{text}<span>just now</span></div>
}

function PreviewLine({ label, value }: { label: string; value: string }) {
  return <div className="preview-line"><span>{label}</span><strong>{value}</strong></div>
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return <div className="config-row"><span>{label}</span><strong>{value}</strong></div>
}

function DevelopingInline({ text }: { text: string }) {
  return <div className="developing-inline"><span>Đang phát triển</span><p>{text}</p></div>
}

function findFirstFile(nodes: FileTreeNode[]): FileTreeNode | null {
  for (const node of nodes) {
    if (node.type === 'file') return node
    const child = findFirstFile(node.children)
    if (child) return child
  }
  return null
}

export default App
