import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { uploadFormData } from '../api/upload'
import type { ImportPreview } from '../types/api'
import { useImportController } from './useImportController'

vi.mock('../api/upload', () => ({
  uploadFormData: vi.fn(),
}))

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

function createTestContext() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const dependencies = {
    setSelectedRepositoryId: vi.fn(),
    setPage: vi.fn(),
    setApiError: vi.fn(),
  }
  return {
    dependencies,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  }
}

describe('useImportController automatic previews', () => {
  beforeEach(() => {
    vi.mocked(uploadFormData).mockResolvedValue({ import_session_id: 'session-1' })
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/import-sessions/github')) return jsonResponse({ import_session_id: 'session-1' })
      if (url.endsWith('/import-sessions/session-1/preview')) return jsonResponse(preview)
      return jsonResponse({})
    }))
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('uploads a selected folder automatically and queries its preview', async () => {
    const { dependencies, wrapper } = createTestContext()
    const { result } = renderHook(() => useImportController(dependencies), { wrapper })
    const file = new File(['print("hello")'], 'main.py') as File & { webkitRelativePath?: string }
    Object.defineProperty(file, 'webkitRelativePath', { value: 'sample/main.py' })

    act(() => result.current.setFolderFiles([file]))

    await waitFor(() => expect(uploadFormData).toHaveBeenCalledOnce())
    expect(vi.mocked(uploadFormData).mock.calls[0][0].url).toContain('/api/v1/import-sessions/upload-folder')
    await waitFor(() => expect(result.current.importPreview).toEqual(preview))
  })

  it('uploads a selected ZIP automatically', async () => {
    const { dependencies, wrapper } = createTestContext()
    const { result } = renderHook(() => useImportController(dependencies), { wrapper })
    const file = new File(['zip'], 'sample.zip', { type: 'application/zip' })

    act(() => {
      result.current.setImportMode('zip')
      result.current.setZipFile(file)
    })

    await waitFor(() => expect(uploadFormData).toHaveBeenCalledOnce())
    expect(vi.mocked(uploadFormData).mock.calls[0][0].url).toContain('/api/v1/import-sessions/upload-zip')
  })

  it('creates a GitHub preview after the existing debounce', async () => {
    const { dependencies, wrapper } = createTestContext()
    const { result } = renderHook(() => useImportController(dependencies), { wrapper })

    act(() => {
      result.current.setImportMode('github')
      result.current.setGithubUrl('https://github.com/example/project')
    })

    await waitFor(
      () => expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/import-sessions/github'),
        expect.objectContaining({ method: 'POST' }),
      ),
      { timeout: 2_000 },
    )
  })
})

function jsonResponse(data: unknown) {
  return { ok: true, status: 200, json: async () => data } as Response
}
