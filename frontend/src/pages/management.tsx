import type { FormEvent } from 'react'
import { Icon } from '../components/common/Icon'
import {
  Activity,
  Checklist,
  EmptyState,
  LanguageBar,
  ListRow,
  Metric,
  PageTitle,
  Panel,
  PreviewLine,
  ProfileCard,
  Progress,
  SourceCard,
  StatCell,
  WizardSteps,
} from '../components/common/ui'
import { pipelineSteps } from '../config/navigation'
import type { ImportMode, IndexStatus, Repository } from '../types/api'

export function DashboardPage({
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

export function ImportPage({
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

export function IndexingPage({
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
