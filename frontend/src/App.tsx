import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { requestJson, API_V1 } from './api/client'
import { AssistantChat, AssistantPanel } from './components/chat/AssistantChat'
import { FileTree } from './components/code/FileTree'
import { Icon } from './components/common/Icon'
import {
  Activity,
  ConfigRow,
  EmptyState,
  InDevelopmentInline,
  InDevelopmentPanel,
  ListRow,
  Metric,
  PageTitle,
  Panel,
  PreviewLine,
  Progress,
  SideInfo,
} from './components/common/ui'
import { managementNav, workspaceNav } from './config/navigation'
import { DashboardPage, ImportPage, IndexingPage } from './pages/management'
import type {
  ChatMessage,
  Citation,
  Evidence,
  FileContent,
  FileTreeNode,
  GraphData,
  ImportMode,
  IndexStatus,
  Overview,
  Page,
  Repository,
  SearchResult,
} from './types/api'
import './App.css'

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
    try {
      return await requestJson<T>(url, options)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Request failed'
      setApiError(message)
      throw error
    }
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

export default App
