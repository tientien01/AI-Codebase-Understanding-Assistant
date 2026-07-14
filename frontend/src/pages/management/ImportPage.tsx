import type { FormEvent } from 'react'
import { LanguageBar, PageTitle, Panel, PreviewLine, Progress, SourceCard, WizardSteps } from '../../components/common/ui'
import type { ImportActivityLog, ImportMode, ImportPreview, ImportSessionStatus } from '../../types/api'

export function ImportPage({
  mode,
  projectName,
  githubUrl,
  folderCount,
  folderSelectedCount,
  folderExcludedCount,
  zipFileName,
  preview,
  importStatus,
  uploadProgress,
  elapsedSeconds,
  canPreparePreview,
  isConfirming,
  isPreviewLoading,
  onModeChange,
  onNameChange,
  onGithubUrlChange,
  onFolderFiles,
  onZipFile,
  onSubmit,
  onCancel,
}: {
  mode: ImportMode
  projectName: string
  githubUrl: string
  folderCount: number
  folderSelectedCount: number
  folderExcludedCount: number
  zipFileName: string
  preview: ImportPreview | null
  importStatus: ImportSessionStatus | null
  uploadProgress: number
  elapsedSeconds: number
  canPreparePreview: boolean
  isConfirming: boolean
  isPreviewLoading: boolean
  onModeChange: (mode: ImportMode) => void
  onNameChange: (value: string) => void
  onGithubUrlChange: (value: string) => void
  onFolderFiles: (files: File[]) => void
  onZipFile: (file: File | null) => void
  onSubmit: (event: FormEvent) => void
  onCancel: () => void
}) {
  const activityLogs = preview?.activity_logs ?? importStatus?.activity_logs ?? []
  const showPreparation = isPreviewLoading || Boolean(preview) || activityLogs.length > 0

  return (
    <form onSubmit={onSubmit}>
      <PageTitle title="New Project" subtitle="Import a repository, review its files, then start indexing." />
      <WizardSteps activeStep={preview ? 1 : 0} />
      <div className="import-layout">
        <div className="form-sections">
          <Panel title="Import Repository">
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
                  <span>Paste a public GitHub repository URL, then choose Prepare Preview.</span>
                </label>
              )}
              {mode === 'folder' && (
                <label>
                  Local folder
                  <input type="file" multiple ref={(input) => input?.setAttribute('webkitdirectory', 'true')} onChange={(event) => onFolderFiles(Array.from(event.target.files ?? []))} />
                  <span>{folderSelectedCount
                    ? `${folderSelectedCount} selected · ${folderCount} to upload · ${folderExcludedCount} excluded`
                    : 'Choose a folder to upload.'}</span>
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
            </div>
            <div className="standard-pipeline" aria-label="Indexing behavior">
              <strong>Standard indexing pipeline</strong>
              <span>Supported source files are scanned securely, parsed, and prepared for code search and relationships.</span>
            </div>
          </Panel>
        </div>
        <aside className="preview-column">
          <Panel title="Import Preview">
            {showPreparation ? (
              <ImportPreparation
                activityLogs={activityLogs}
                importStatus={importStatus}
                preview={preview}
                elapsedSeconds={elapsedSeconds}
                mode={mode}
                uploadProgress={uploadProgress}
              />
            ) : null}
            <PreviewLine label="Repository" value={preview?.project_summary.suggested_name ?? (mode === 'github' ? githubUrl : projectName)} />
            <h3>Estimated Size</h3>
            <PreviewLine label="Files" value={String(preview?.file_statistics.total_files ?? folderCount)} />
            <PreviewLine label="Indexable" value={String(preview?.file_statistics.supported_files ?? 0)} />
            <PreviewLine label="Skipped" value={String(preview?.file_statistics.skipped_files ?? 0)} />
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
            <PreviewLine label="Estimated time" value={preview ? `${preview.project_summary.estimated_index_time_seconds}s` : 'available after preview'} />
          </Panel>
          <div className="footer-actions">
            <button type="button" className="secondary" onClick={onCancel} disabled={isConfirming}>Cancel</button>
            <button type="submit" className="primary" disabled={isConfirming || isPreviewLoading || (!preview && !canPreparePreview)}>
              {isConfirming ? 'Starting Index Job…' : preview ? 'Start Indexing' : isPreviewLoading ? 'Preparing Preview…' : 'Prepare Preview'}
            </button>
          </div>
        </aside>
      </div>
    </form>
  )
}

const PREPARATION_STEPS: Record<ImportMode, { label: string; stages: string[] }[]> = {
  github: [
    { label: 'Validate URL', stages: ['github_received'] },
    { label: 'Clone repository', stages: ['github_clone_started'] },
    { label: 'Secure source snapshot', stages: ['github_metadata_cleanup', 'github_tree_validation'] },
    { label: 'Scan and prepare preview', stages: ['github_cloned', 'preview_scan_started', 'preview_scan_completed'] },
  ],
  folder: [
    { label: 'Inspect folder', stages: [] },
    { label: 'Upload files', stages: ['folder_manifest_received', 'folder_upload_batch'] },
    { label: 'Secure source snapshot', stages: ['folder_saved'] },
    { label: 'Scan and prepare preview', stages: ['preview_scan_started', 'preview_scan_completed'] },
  ],
  zip: [
    { label: 'Validate ZIP', stages: [] },
    { label: 'Upload ZIP', stages: ['upload_received'] },
    { label: 'Extract securely', stages: ['upload_saved'] },
    { label: 'Scan and prepare preview', stages: ['archive_extracted', 'preview_scan_started', 'preview_scan_completed'] },
  ],
}

function ImportPreparation({
  activityLogs,
  importStatus,
  preview,
  elapsedSeconds,
  mode,
  uploadProgress,
}: {
  activityLogs: ImportActivityLog[]
  importStatus: ImportSessionStatus | null
  preview: ImportPreview | null
  elapsedSeconds: number
  mode: ImportMode
  uploadProgress: number
}) {
  const steps = PREPARATION_STEPS[mode]
  const observedStages = [...activityLogs.map((item) => item.stage), importStatus?.stage].filter(Boolean) as string[]
  const observedIndexes = observedStages.map((stage) => steps.findIndex((step) => step.stages.includes(stage)))
  const uploadIndex = mode === 'github' ? 0 : uploadProgress < 100 ? 1 : 2
  const currentIndex = Math.max(uploadIndex, ...observedIndexes)
  const failed = importStatus?.status === 'failed' || importStatus?.status === 'cancelled'

  return (
    <section className="import-preparation" aria-label="Repository preparation" aria-live="polite">
      <div className="preparation-heading">
        <h3>Preparation</h3>
        {!preview && <span>{formatElapsed(elapsedSeconds)}</span>}
      </div>
      <div className="preparation-steps">
        {steps.map((step, index) => {
          const state = preview || index < currentIndex ? 'completed' : index === currentIndex ? (failed ? 'failed' : 'active') : 'pending'
          return (
            <div className={`preparation-step ${state}`} key={step.label}>
              <span className="preparation-marker" aria-hidden="true">{state === 'completed' ? '✓' : index + 1}</span>
              <div>
                <strong>{step.label}</strong>
                {state === 'active' && importStatus?.message ? <small>{importStatus.message}</small> : null}
                {state === 'active' && mode !== 'github' && index === 1 ? (
                  <div className="preparation-upload-progress">
                    <small>{uploadProgress}% uploaded</small>
                    <Progress value={uploadProgress} />
                  </div>
                ) : null}
                {state === 'active' && mode === 'zip' && index === 2 && !importStatus?.message ? <small>Upload complete. Extracting and validating on the server.</small> : null}
                {state === 'failed' ? <small>{importStatus?.error_message ?? importStatus?.message ?? 'Preparation stopped.'}</small> : null}
              </div>
            </div>
          )
        })}
      </div>
      {preview ? (
        <div className="preview-ready-summary" role="status">
          <strong>Preview ready in {formatElapsed(elapsedSeconds)}</strong>
          <span>{preview.file_statistics.total_files} files · {preview.file_statistics.supported_files} indexable · {preview.file_statistics.skipped_files} skipped</span>
        </div>
      ) : null}
      {activityLogs.length ? (
        <details className="import-technical-details">
          <summary>View technical details</summary>
          <div className="import-activity-log">
            {activityLogs.map((item) => (
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
        </details>
      ) : null}
    </section>
  )
}

function activityStageLabel(stage: string) {
  return stage.replace(/_/g, ' ')
}

function formatElapsed(seconds: number) {
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
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
