import type { FormEvent } from 'react'
import { LanguageBar, PageTitle, Panel, PreviewLine, ProfileCard, Progress, SourceCard, WizardSteps } from '../../components/common/ui'
import type { ImportMode, ImportPreview } from '../../types/api'

export function ImportPage({
  mode,
  projectName,
  githubUrl,
  folderCount,
  zipFileName,
  preview,
  uploadProgress,
  isPreviewLoading,
  onModeChange,
  onNameChange,
  onGithubUrlChange,
  onFolderFiles,
  onZipFile,
  onSubmit,
}: {
  mode: ImportMode
  projectName: string
  githubUrl: string
  folderCount: number
  zipFileName: string
  preview: ImportPreview | null
  uploadProgress: number
  isPreviewLoading: boolean
  onModeChange: (mode: ImportMode) => void
  onNameChange: (value: string) => void
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
            </div>
            <div className="form-grid">
              {mode === 'github' && (
                <label>
                  Repository URL
                  <input value={githubUrl} onChange={(event) => onGithubUrlChange(event.target.value)} />
                  <span>Paste a public GitHub repository URL to prepare preview automatically.</span>
                </label>
              )}
              {mode === 'folder' && (
                <label>
                  Local folder
                  <input type="file" multiple ref={(input) => input?.setAttribute('webkitdirectory', 'true')} onChange={(event) => onFolderFiles(Array.from(event.target.files ?? []))} />
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
                <span>Use tree-sitter</span>
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
            {isPreviewLoading ? <div className="preview-status">Preparing preview...</div> : null}
            <PreviewLine label="Repository" value={preview?.project_summary.suggested_name ?? (mode === 'github' ? githubUrl : projectName)} />
            {uploadProgress > 0 && uploadProgress < 100 ? (
              <>
                <PreviewLine label="Upload" value={`${uploadProgress}%`} />
                <Progress value={uploadProgress} />
              </>
            ) : null}
            <PreviewLine label="Branch" value="main" />
            <PreviewLine label="Commit" value="pending" />
            <h3>Estimated Size</h3>
            <PreviewLine label="Files" value={String(preview?.file_statistics.total_files ?? folderCount)} />
            <PreviewLine label="Indexable" value={String(preview?.file_statistics.supported_files ?? 0)} />
            <PreviewLine label="Skipped" value={String(preview?.file_statistics.skipped_files ?? 0)} />
            <PreviewLine label="LOC" value="estimated after scan" />
            <PreviewLine label="Size" value={preview ? `${Math.round(preview.project_summary.repository_size_bytes / 1024)} KB` : 'calculated on preview'} />
            <h3>Detected Languages</h3>
            {previewLanguageEntries(preview).map(([language, count]) => (
              <LanguageBar key={language} label={languageLabel(language)} value={previewPercent(count, preview?.file_statistics.supported_files ?? 0)} />
            ))}
            <h3>Excluded Patterns</h3>
            <div className="setting-chips">
              {(preview?.ignore_summary.length ? preview.ignore_summary : [
                { pattern: '.git/', skipped_count: 0, reason: 'default' },
                { pattern: 'node_modules/', skipped_count: 0, reason: 'default' },
                { pattern: 'venv/', skipped_count: 0, reason: 'default' },
                { pattern: '__pycache__/', skipped_count: 0, reason: 'default' },
              ]).map((item) => <span key={`${item.pattern}-${item.reason}`}>{item.pattern} {item.skipped_count ? `(${item.skipped_count})` : ''}</span>)}
            </div>
            {preview?.security_warnings.length ? (
              <>
                <h3>Security Warnings</h3>
                {preview.security_warnings.slice(0, 4).map((warning) => (
                  <PreviewLine key={warning.file_path} label={warning.risk_type} value={`${warning.file_path} ${warning.action}`} />
                ))}
              </>
            ) : null}
            <h3>Estimated Indexing</h3>
            <PreviewLine label="Chunks" value="calculated after scan" />
            <PreviewLine label="Embeddings" value="dang phat trien" />
            <PreviewLine label="Estimated time" value={preview ? `${preview.project_summary.estimated_index_time_seconds}s` : 'available after preview'} />
            {preview?.activity_logs.length ? (
              <>
                <h3>Import Activity</h3>
                <div className="import-activity-log">
                  {preview.activity_logs.map((item) => (
                    <div className={`import-log-row level-${item.level}`} key={`${item.timestamp}-${item.stage}`}>
                      <div>
                        <strong>{activityStageLabel(item.stage)}</strong>
                        <span>{formatActivityTime(item.timestamp)}</span>
                      </div>
                      <p>{item.message}</p>
                      {Object.keys(item.details).length ? <small>{formatLogDetails(item.details)}</small> : null}
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </Panel>
          <div className="footer-actions">
            <button type="button" className="secondary">Cancel</button>
            <button type="submit" className="primary" disabled={!preview || isPreviewLoading}>{preview ? 'Start Indexing' : isPreviewLoading ? 'Preparing Preview' : 'Waiting for Preview'}</button>
          </div>
        </aside>
      </div>
    </form>
  )
}

function activityStageLabel(stage: string) {
  return stage.replace(/_/g, ' ')
}

function formatActivityTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatLogDetails(details: Record<string, string>) {
  return Object.entries(details).map(([key, value]) => `${key}: ${value}`).join(' | ')
}

function previewPercent(value: number, total: number) {
  if (!total) return 0
  return Math.round((value / total) * 100)
}

function previewLanguageEntries(preview: ImportPreview | null): [string, number][] {
  const languageFiles = preview?.file_statistics.language_files
  if (languageFiles && Object.keys(languageFiles).length > 0) {
    return Object.entries(languageFiles).sort((left, right) => right[1] - left[1]).slice(0, 6)
  }
  const fallbackEntries: [string, number][] = [
    ['python', preview?.file_statistics.python_files ?? 0],
    ['typescript', preview?.file_statistics.typescript_files ?? 0],
    ['javascript', preview?.file_statistics.javascript_files ?? 0],
    ['docs/config', (preview?.file_statistics.markdown_files ?? 0) + (preview?.file_statistics.config_files ?? 0)],
  ]
  return fallbackEntries.filter(([, count]) => count > 0)
}

function languageLabel(language: string) {
  const labels: Record<string, string> = {
    csharp: 'C#',
    cpp: 'C++',
    css: 'CSS',
    go: 'Go',
    html: 'HTML',
    java: 'Java',
    javascript: 'JavaScript',
    kotlin: 'Kotlin',
    markdown: 'Markdown',
    php: 'PHP',
    python: 'Python',
    ruby: 'Ruby',
    rust: 'Rust',
    swift: 'Swift',
    typescript: 'TypeScript',
  }
  return labels[language] ?? language
}
