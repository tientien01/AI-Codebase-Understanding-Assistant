import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import App from './App'
import { createAppQueryClient } from './features/server-state'

const repository = {
  id: 'repo-1',
  name: 'Owned repository',
  source_type: 'upload_folder',
  status: 'indexed',
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
  if (url.includes('/graph/')) return jsonResponse({ nodes: [], edges: [] })
  if (url.endsWith('/files/tree')) return jsonResponse([])
  return jsonResponse({})
}
