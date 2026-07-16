import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import App from './App'
import { createAppQueryClient } from './features/server-state'
import { isRepositoryUsable, reconcileRepositoryIndexStatus } from './utils/repository'
import type { IndexStatus } from './types/api'

const repository = {
  id: 'repo-1',
  name: 'Owned repository',
  source_type: 'upload_folder',
  status: 'indexed',
  current_index_version: 7,
  detected_stack: ['TypeScript'],
  total_files: 1,
  indexed_files: 1,
  symbols: 1,
  endpoints: 0,
  chunks: 1,
  graph_nodes: 1,
}

describe('App routing', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => responseFor(String(input))))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('redirects the legacy root to the canonical projects route', async () => {
    renderApp(['/'])

    expect(await screen.findByRole('heading', { name: 'Projects' })).toBeTruthy()
    expect(screen.getByTestId('location').textContent).toBe('/projects')
  })

  it('restores a direct source path and highlighted line from the URL', async () => {
    renderApp(['/repositories/repo-1/code?path=src%2Fauth.ts&line=2'])

    await waitFor(() => expect(document.getElementById('source-line-2')?.textContent).toContain('const token = login()'))
    expect(document.getElementById('source-line-2')?.classList.contains('selected')).toBe(true)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/repositories/repo-1/files/content?path=src%2Fauth.ts'),
      expect.any(Object),
    )
  })

  it('closes the identifier chooser by removing its selected line from the URL', async () => {
    renderApp(['/repositories/repo-1/code?path=src%2Fauth.ts&line=2'])

    fireEvent.click(await screen.findByRole('button', { name: 'Close identifier chooser' }))

    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/repositories/repo-1/code?path=src%2Fauth.ts'))
    expect(screen.queryByLabelText('Trace value from selected source line')).toBeNull()
  })

  it('loads evidence only from the repository and evidence identities in a direct URL', async () => {
    renderApp(['/repositories/repo-1/evidence/evidence%2F9'])

    expect(await screen.findByText('Owned evidence preview')).toBeTruthy()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/repositories/repo-1/evidence/evidence%2F9'),
      expect.any(Object),
    )
  })

  it('restores and updates shareable search state in the URL', async () => {
    renderApp(['/repositories/repo-1/search?q=login+token'])
    const input = await screen.findByPlaceholderText('Search functions, files, endpoints, concepts...')

    expect((input as HTMLInputElement).value).toBe('login token')
    fireEvent.change(input, { target: { value: 'refresh token' } })
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/repositories/repo-1/search?q=refresh+token'))
  })

  it('restores API endpoint selection, updates the URL, and opens exact source', async () => {
    renderApp(['/repositories/repo-1/api?endpoint=endpoint_login'])

    expect(await screen.findByText('API Detail')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Select POST /login' }).closest('tr')?.getAttribute('aria-selected')).toBe('true')

    fireEvent.click(screen.getByRole('button', { name: 'Select GET /users' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/repositories/repo-1/api?endpoint=endpoint_users'))

    fireEvent.click(screen.getByRole('button', { name: 'Open source' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/repositories/repo-1/code?path=src%2Fusers.ts&line=20'))
  })

  it('launches a bounded request-flow projection from API Detail', async () => {
    renderApp(['/repositories/repo-1/api?endpoint=endpoint_login'])

    fireEvent.click(await screen.findByRole('button', { name: 'Trace request flow' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe(
      '/repositories/repo-1/graph?view=api-flow&root=endpoint_login&depth=2',
    ))
  })

  it('does not replace an unknown repository with the first available repository', async () => {
    renderApp(['/repositories/missing/overview'])

    expect(await screen.findByRole('heading', { name: 'Repository not found' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Overview' })).toBeNull()
  })

  it('offers recovery for unknown and unsafe locations', async () => {
    renderApp(['/repositories/repo-1/code?path=C%3A%2Fprivate.key'])

    expect(await screen.findByRole('heading', { name: 'This location is not available' })).toBeTruthy()
    expect(screen.getByText('Source links must use a safe repository-relative path.')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Back to Projects' }).getAttribute('href')).toBe('/projects')
  })

  it('shows a retryable query error and recovers without reloading the app', async () => {
    let repositoryAttempts = 0
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/repositories') && repositoryAttempts++ === 0) {
        return errorResponse(503, 'service_unavailable', 'Repository service is temporarily unavailable.')
      }
      return responseFor(url)
    }))
    renderApp(['/projects'])

    expect(await screen.findByText('Temporary request failure')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }))
    expect(await screen.findByRole('heading', { name: 'Projects' })).toBeTruthy()
  })

  it('uses browser history for workspace navigation', async () => {
    renderApp(['/projects'])
    const openButtons = await screen.findAllByRole('button', { name: /Open Workspace/ })
    fireEvent.click(openButtons[0])

    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/repositories/repo-1/overview'))
    fireEvent.click(screen.getByRole('button', { name: 'History Back' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/projects'))
    fireEvent.click(screen.getByRole('button', { name: 'History Forward' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/repositories/repo-1/overview'))
  })

  it('loads the server-backed non-secret settings profile on the canonical route', async () => {
    renderApp(['/settings'])

    expect(await screen.findByText('Balanced')).toBeTruthy()
    expect(screen.getByText('Configured')).toBeTruthy()
    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/settings$/), expect.any(Object))
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/settings/ignore-patterns'), expect.any(Object))
  })

  it('preserves repository/index context while evaluation is explicitly unavailable', async () => {
    renderApp(['/repositories/repo-1/evaluation'])

    expect(await screen.findByRole('heading', { name: 'Evaluation' })).toBeTruthy()
    expect(screen.getByText('Active index: 7')).toBeTruthy()
    expect(screen.getByText('Capability unavailable')).toBeTruthy()
    expect(screen.getByText('POST /evaluation/runs')).toBeTruthy()
  })

  it('opens a completed versioned index while the repository list cache is still stale', async () => {
    const staleRepository = { ...repository, status: 'indexing', current_index_version: undefined }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/repositories')) return jsonResponse([staleRepository])
      if (url.endsWith('/index/status')) return jsonResponse(completedIndexStatus(8))
      return responseFor(url)
    }))
    renderApp(['/index-jobs'])

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/index/status'), expect.any(Object)))
    expect(await screen.findByText('Status: Completed')).toBeTruthy()
    const openWorkspace = await screen.findByRole('button', { name: 'Open Workspace' })
    await waitFor(() => expect((openWorkspace as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(openWorkspace)

    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/repositories/repo-1/overview'))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/repositories/repo-1/overview'), expect.any(Object)))
    expect(screen.queryByRole('heading', { name: 'Repository workspace is unavailable' })).toBeNull()
  })

  it('never treats progress-only, failed, cancelled or versionless jobs as usable', () => {
    const staleRepository = { ...repository, status: 'indexing', current_index_version: undefined }
    const valid = reconcileRepositoryIndexStatus(staleRepository, completedIndexStatus(8))
    expect(isRepositoryUsable(valid)).toBe(true)
    expect(valid?.current_index_version).toBe(8)

    for (const status of ['running', 'failed', 'cancelled']) {
      const unresolved = reconcileRepositoryIndexStatus(staleRepository, { ...completedIndexStatus(8), status, progress: 100 })
      expect(isRepositoryUsable(unresolved)).toBe(false)
    }
    expect(isRepositoryUsable(reconcileRepositoryIndexStatus(staleRepository, completedIndexStatus(undefined)))).toBe(false)
  })

  it('does not mistake an older completed job for the active re-index attempt', () => {
    const reindexingRepository = { ...repository, status: 'indexing', current_index_version: 8 }

    const currentActive = reconcileRepositoryIndexStatus(reindexingRepository, completedIndexStatus(8))
    expect(isRepositoryUsable(currentActive)).toBe(true)
    expect(currentActive?.current_index_version).toBe(8)
    expect(isRepositoryUsable(reconcileRepositoryIndexStatus(reindexingRepository, completedIndexStatus(7)))).toBe(false)

    const newlyActivated = reconcileRepositoryIndexStatus(reindexingRepository, completedIndexStatus(9))
    expect(isRepositoryUsable(newlyActivated)).toBe(true)
    expect(newlyActivated?.current_index_version).toBe(9)
  })

  it('keeps the activated version usable while a newer version is indexing', () => {
    const reindexingRepository = { ...repository, status: 'indexing', current_index_version: 8 }
    const runningStatus = { ...completedIndexStatus(9), status: 'running', progress: 35 }

    const activeRepository = reconcileRepositoryIndexStatus(reindexingRepository, runningStatus)

    expect(isRepositoryUsable(activeRepository)).toBe(true)
    expect(activeRepository?.current_index_version).toBe(8)
    expect(runningStatus.index_version).toBe(9)
  })
})

function renderApp(initialEntries: string[]) {
  const queryClient = createAppQueryClient()
  queryClient.setDefaultOptions({ queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <App />
        <LocationProbe />
        <HistoryControls />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}{location.search}</output>
}

function HistoryControls() {
  const navigate = useNavigate()
  return (
    <div aria-label="Test history controls">
      <button onClick={() => navigate(-1)}>History Back</button>
      <button onClick={() => navigate(1)}>History Forward</button>
    </div>
  )
}

function jsonResponse(data: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => data,
  } as Response
}

function errorResponse(status: number, code: string, message: string) {
  return {
    ok: false,
    status,
    json: async () => ({ error: { code, message } }),
  } as Response
}

function responseFor(url: string) {
  if (url.endsWith('/api/v1/repositories')) return jsonResponse([repository])
  if (url.endsWith('/api/v1/settings')) {
    return jsonResponse({
      indexing: { default_profile: 'balanced', max_file_size_mb: 1, max_upload_size_mb: 50 },
      providers: {
        llm_provider: 'openai-compatible',
        llm_model: 'operator-selected',
        llm_configured: true,
        embedding_provider: 'local',
        embedding_model: 'deterministic-fixture',
        embedding_configured: false,
        vector_store_provider: 'none',
      },
      security: { secret_scanning_enabled: true },
    })
  }
  if (url.endsWith('/api/v1/settings/ignore-patterns')) {
    return jsonResponse({ default_patterns: ['node_modules'], user_patterns: [], effective_patterns: ['node_modules', '.env'] })
  }
  if (url.includes('/files/content?path=')) {
    return jsonResponse({
      file_path: 'src/auth.ts',
      language: 'typescript',
      content: 'export function login() {}\nconst token = login()',
      lines: ['export function login() {}', 'const token = login()'],
      symbols: [],
    })
  }
  if (url.endsWith('/evidence/evidence%2F9')) {
    return jsonResponse({
      evidence_id: 'evidence/9',
      repository_id: 'repo-1',
      file_path: 'src/auth.ts',
      start_line: 1,
      end_line: 2,
      source_type: 'source',
      content_preview: 'Owned evidence preview',
      relevance_reason: 'Direct source support',
      confidence_score: 1,
      retrieval_source: 'exact',
      metadata: {},
    })
  }
  if (url.endsWith('/index/status')) {
    return jsonResponse({
      repository_id: 'repo-1',
      status: 'completed',
      current_step: 'completed',
      total_files: 1,
      processed_files: 1,
      skipped_files: 0,
      failed_files: 0,
      progress: 100,
      stats: {},
      logs: [],
      warnings: [],
    })
  }
  if (url.endsWith('/overview')) {
    return jsonResponse({
      repository_id: 'repo-1',
      name: 'Owned repository',
      detected_stack: ['TypeScript'],
      important_files: [],
      modules: [],
      endpoints: [],
      documentation_gaps: [],
      stats: {},
    })
  }
  if (url.endsWith('/api/endpoints')) return jsonResponse({ items: apiEndpoints, next_cursor: null })
  if (url.includes('/graph/')) return jsonResponse({ nodes: [], edges: [] })
  if (url.endsWith('/files/tree')) return jsonResponse([])
  return jsonResponse({})
}

const apiEndpoints = [
  {
    endpoint_key: 'endpoint_login',
    method: 'POST',
    path: '/login',
    handler: 'login',
    file_path: 'src/auth.ts',
    start_line: 4,
    end_line: 12,
    metadata: { framework: 'fastapi' },
  },
  {
    endpoint_key: 'endpoint_users',
    method: 'GET',
    path: '/users',
    handler: 'list_users',
    file_path: 'src/users.ts',
    start_line: 20,
    end_line: 35,
    metadata: { framework: 'fastapi' },
  },
]

function completedIndexStatus(indexVersion: number | undefined): IndexStatus {
  return {
    repository_id: 'repo-1',
    status: 'completed',
    current_step: 'completed',
    index_version: indexVersion,
    total_files: 178,
    processed_files: 178,
    skipped_files: 35,
    failed_files: 0,
    progress: 100,
    stats: { symbols: 12, endpoints: 2, chunks: 20, graph_nodes: 30 },
    logs: [],
    warnings: [],
    finished_at: '2026-07-15T08:20:55Z',
  }
}
