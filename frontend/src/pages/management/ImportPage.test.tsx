import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ImportSessionStatus } from '../../types/api'
import { ImportPage } from './ImportPage'

const handlers = {
  onModeChange: vi.fn(),
  onNameChange: vi.fn(),
  onGithubUrlChange: vi.fn(),
  onFolderFiles: vi.fn(),
  onZipFile: vi.fn(),
  onSubmit: vi.fn(),
  onCancel: vi.fn(),
}

describe('ImportPage', () => {
  afterEach(cleanup)

  it('shows the real standard pipeline without inactive profile controls', () => {
    render(<ImportPage
      mode="github"
      projectName="sample"
      githubUrl="https://github.com/example/sample"
      folderCount={0}
      folderSelectedCount={0}
      folderExcludedCount={0}
      zipFileName=""
      preview={null}
      importStatus={null}
      uploadProgress={0}
      elapsedSeconds={0}
      canPreparePreview
      isConfirming={false}
      isPreviewLoading={false}
      {...handlers}
    />)

    expect(screen.getByText('Standard indexing pipeline')).toBeTruthy()
    expect(screen.queryByText('Configure Parsing and Indexing')).toBeNull()
    expect(screen.queryByText('Deep Analysis')).toBeNull()
    expect(screen.getByRole('button', { name: 'Prepare Preview' })).toBeTruthy()
  })

  it('groups acquisition events into a compact four-step preparation view', () => {
    const importStatus: ImportSessionStatus = {
      import_session_id: 'session-1',
      status: 'validating',
      stage: 'github_tree_validation',
      message: 'Checking repository paths and acquisition limits.',
      activity_logs: [
        { timestamp: '2026-07-14T10:00:00Z', level: 'info', stage: 'github_received', message: 'Request received.', details: {} },
        { timestamp: '2026-07-14T10:00:01Z', level: 'info', stage: 'github_clone_started', message: 'Clone started.', details: {} },
        { timestamp: '2026-07-14T10:00:02Z', level: 'info', stage: 'github_tree_validation', message: 'Validating.', details: {} },
      ],
    }

    render(<ImportPage
      mode="github"
      projectName="sample"
      githubUrl="https://github.com/example/sample"
      folderCount={0}
      folderSelectedCount={0}
      folderExcludedCount={0}
      zipFileName=""
      preview={null}
      importStatus={importStatus}
      uploadProgress={0}
      elapsedSeconds={3}
      canPreparePreview={false}
      isConfirming={false}
      isPreviewLoading
      {...handlers}
    />)

    expect(screen.getByText('Validate URL')).toBeTruthy()
    expect(screen.getByText('Clone repository')).toBeTruthy()
    expect(screen.getByText('Secure source snapshot')).toBeTruthy()
    expect(screen.getByText('Scan and prepare preview')).toBeTruthy()
    expect(screen.getByText('View technical details')).toBeTruthy()
    expect(screen.getByText('3s')).toBeTruthy()
  })

  it('shows folder upload percentage inside the source-specific preparation step', () => {
    const importStatus: ImportSessionStatus = {
      import_session_id: 'session-1',
      status: 'uploading',
      stage: 'folder_upload_batch',
      message: 'Folder upload batch saved.',
      activity_logs: [],
    }

    render(<ImportPage
      mode="folder"
      projectName="sample"
      githubUrl=""
      folderCount={320}
      folderSelectedCount={350}
      folderExcludedCount={30}
      zipFileName=""
      preview={null}
      importStatus={importStatus}
      uploadProgress={21}
      elapsedSeconds={4}
      canPreparePreview={false}
      isConfirming={false}
      isPreviewLoading
      {...handlers}
    />)

    expect(screen.getByText('Inspect folder')).toBeTruthy()
    expect(screen.getByText('Upload files')).toBeTruthy()
    expect(screen.getByText('21% uploaded')).toBeTruthy()
    expect(screen.getByText('350 selected · 320 to upload · 30 excluded')).toBeTruthy()
    expect(screen.queryByText('Clone repository')).toBeNull()
  })
})
