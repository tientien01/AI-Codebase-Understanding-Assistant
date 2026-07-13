import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { uploadFormData } from '../api/upload'
import type { ImportPreview } from '../types/api'
import { useImportController } from './useImportController'

vi.mock('../api/upload', () => ({
  uploadFormData: vi.fn(),
}))

type Request = <T>(url: string, options?: RequestInit) => Promise<T>

const preview: ImportPreview = {
  import_session_id: 'session-1',
  status: 'preview_ready',
  project_summary: {
    suggested_name: 'sample',
    source_type: 'upload',
    repository_size_bytes: 1,
    estimated_index_time_seconds: 1,
  },
  detected_stack: [],
  file_statistics: {
    total_files: 1,
    supported_files: 1,
    skipped_files: 0,
    python_files: 1,
    javascript_files: 0,
    typescript_files: 0,
    markdown_files: 0,
    config_files: 0,
  },
  folder_preview: ['main.py'],
  ignore_summary: [],
  security_warnings: [],
  indexing_plan: [],
  possible_duplicates: [],
  activity_logs: [],
}

function createDependencies() {
  const requestMock = vi.fn(async (url: string) => {
    if (url.endsWith('/github')) return { import_session_id: 'session-1' }
    return preview
  })

  return {
    requestMock,
    dependencies: {
      request: requestMock as unknown as Request,
      apiV1: '/api/v1',
      loadRepositories: vi.fn(async () => undefined),
      loadIndexStatus: vi.fn(async () => undefined),
      setSelectedRepositoryId: vi.fn(),
      setPage: vi.fn(),
      setApiError: vi.fn(),
    },
  }
}

describe('useImportController automatic previews', () => {
  beforeEach(() => {
    vi.mocked(uploadFormData).mockResolvedValue({ import_session_id: 'session-1' })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('uploads a selected folder automatically', async () => {
    const { dependencies } = createDependencies()
    const { result } = renderHook(() => useImportController(dependencies))
    const file = new File(['print("hello")'], 'main.py') as File & {
      webkitRelativePath?: string
    }
    Object.defineProperty(file, 'webkitRelativePath', { value: 'sample/main.py' })

    act(() => result.current.setFolderFiles([file]))

    await waitFor(() => expect(uploadFormData).toHaveBeenCalledOnce())
    expect(vi.mocked(uploadFormData).mock.calls[0][0].url).toBe(
      '/api/v1/import-sessions/upload-folder',
    )
  })

  it('uploads a selected ZIP automatically', async () => {
    const { dependencies } = createDependencies()
    const { result } = renderHook(() => useImportController(dependencies))
    const file = new File(['zip'], 'sample.zip', { type: 'application/zip' })

    act(() => {
      result.current.setImportMode('zip')
      result.current.setZipFile(file)
    })

    await waitFor(() => expect(uploadFormData).toHaveBeenCalledOnce())
    expect(vi.mocked(uploadFormData).mock.calls[0][0].url).toBe(
      '/api/v1/import-sessions/upload-zip',
    )
  })

  it('creates a GitHub preview after the existing debounce', async () => {
    const { dependencies, requestMock } = createDependencies()
    const { result } = renderHook(() => useImportController(dependencies))

    act(() => {
      result.current.setImportMode('github')
      result.current.setGithubUrl('https://github.com/example/project')
    })

    await waitFor(
      () => {
        expect(requestMock).toHaveBeenCalledWith(
          '/api/v1/import-sessions/github',
          expect.objectContaining({ method: 'POST' }),
        )
      },
      { timeout: 2_000 },
    )
  })
})
