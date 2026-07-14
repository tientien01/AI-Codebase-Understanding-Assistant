import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../api/client'
import { graphProjectionParams } from '../../api/server'
import type { Repository } from '../../types/api'
import { toAsyncViewState } from './asyncState'
import { queryKeys } from './keys'
import { useServerMutations } from './mutations'
import { indexRefetchInterval, retryDelay, shouldRetry } from './policy'
import { useFileContentQuery } from './queries'

const repository: Repository = {
  id: 'repo-1',
  name: 'Repository',
  source_type: 'upload_folder',
  status: 'indexed',
  current_index_version: 7,
  detected_stack: [],
  total_files: 1,
  indexed_files: 1,
  symbols: 0,
  endpoints: 0,
  chunks: 0,
  graph_nodes: 0,
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('server-state ownership policy', () => {
  it('scopes query keys by repository and active index version', () => {
    expect(queryKeys.fileContent('repo-1', 7, 'src/a.ts')).toEqual([
      'repository', 'repo-1', 'version', 7, 'file', 'src/a.ts',
    ])
    expect(queryKeys.fileContent('repo-2', 7, 'src/a.ts')).not.toEqual(queryKeys.fileContent('repo-1', 7, 'src/a.ts'))
    expect(queryKeys.fileContent('repo-1', 8, 'src/a.ts')).not.toEqual(queryKeys.fileContent('repo-1', 7, 'src/a.ts'))
  })

  it('normalizes graph projection identity and serializes every bounded request input', () => {
    const projection = {
      indexVersion: 7,
      rootKeys: ['node-b', 'node-a', 'node-a'],
      nodeTypes: ['function'],
      edgeTypes: ['calls'],
      direction: 'outgoing' as const,
      maxDepth: 3,
      maxNodes: 80,
      maxEdges: 160,
      minConfidence: 0.5,
      supportLevels: ['deep'],
    }
    const reordered = { ...projection, rootKeys: ['node-a', 'node-b'] }

    expect(queryKeys.graph('repo-1', 7, 'function-flow', projection)).toEqual(
      queryKeys.graph('repo-1', 7, 'function-flow', reordered),
    )
    const params = new URLSearchParams(graphProjectionParams(reordered))
    expect(params.get('index_version')).toBe('7')
    expect(params.getAll('root_keys')).toEqual(['node-a', 'node-b'])
    expect(params.get('direction')).toBe('outgoing')
    expect(params.get('max_depth')).toBe('3')
    expect(params.get('max_nodes')).toBe('80')
    expect(params.get('max_edges')).toBe('160')
    expect(params.get('min_confidence')).toBe('0.5')
    expect(params.getAll('support_levels')).toEqual(['deep'])
  })

  it('bounds retries to classified transient failures', () => {
    expect(shouldRetry(0, new ApiError('forbidden', { status: 403, retryable: false }))).toBe(false)
    expect(shouldRetry(0, new ApiError('unavailable', { status: 503, retryable: true }))).toBe(true)
    expect(shouldRetry(2, new ApiError('unavailable', { status: 503, retryable: true }))).toBe(false)
    expect(shouldRetry(0, new TypeError('network'))).toBe(true)
    expect(retryDelay(1)).toBe(retryDelay(1))
    expect(retryDelay(1)).toBeGreaterThanOrEqual(2_000)
  })

  it('stops index polling for terminal states and while hidden', () => {
    const running = { status: 'running' } as never
    const completed = { status: 'completed' } as never

    expect(indexRefetchInterval(running, { hidden: false, repositoryId: 'repo-1' })).toBeTypeOf('number')
    expect(indexRefetchInterval(completed, { hidden: false, repositoryId: 'repo-1' })).toBe(false)
    expect(indexRefetchInterval(running, { hidden: true, repositoryId: 'repo-1' })).toBe(false)
  })

  it('projects permission, retryable, refreshing, stale, empty and cancelled states', () => {
    expect(toAsyncViewState(snapshot({ isError: true, error: new ApiError('no', { status: 403, retryable: false }) }))).toMatchObject({ kind: 'permission_denied' })
    expect(toAsyncViewState(snapshot({ isError: true, error: new ApiError('later', { status: 503, retryable: true }) }))).toMatchObject({ kind: 'error_retryable' })
    expect(toAsyncViewState(snapshot({ data: ['cached'], isFetching: true }))).toMatchObject({ kind: 'refreshing' })
    expect(toAsyncViewState(snapshot({ data: ['cached'], isStale: true }))).toMatchObject({ kind: 'stale' })
    expect(toAsyncViewState(snapshot({ data: [] }), { enabled: true, empty: (data) => Array.isArray(data) && data.length === 0 })).toMatchObject({ kind: 'empty' })
    expect(toAsyncViewState(snapshot({ isError: true, error: new DOMException('cancelled', 'AbortError') }))).toMatchObject({ kind: 'cancelled' })
  })

  it('forwards query cancellation when a file deep link is superseded', async () => {
    const signals: AbortSignal[] = []
    vi.stubGlobal('fetch', vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      const signal = init?.signal as AbortSignal
      signals.push(signal)
      return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError'))))
    }))
    const { wrapper } = testQueryClient()
    const { rerender } = renderHook(
      ({ filePath }) => useFileContentQuery(repository, filePath, true),
      { initialProps: { filePath: 'src/a.ts' }, wrapper },
    )
    await waitFor(() => expect(signals).toHaveLength(1))

    rerender({ filePath: 'src/b.ts' })

    await waitFor(() => expect(signals[0].aborted).toBe(true))
  })

  it('retains safe same-key cached data during a background refresh', async () => {
    let requestCount = 0
    vi.stubGlobal('fetch', vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestCount += 1
      if (requestCount === 1) {
        return Promise.resolve(jsonResponse({ file_path: 'src/a.ts', language: 'typescript', content: 'cached', lines: ['cached'], symbols: [] }))
      }
      const signal = init?.signal as AbortSignal
      return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError'))))
    }))
    const { queryClient, wrapper } = testQueryClient()
    const { result } = renderHook(() => useFileContentQuery(repository, 'src/a.ts', true), { wrapper })
    await waitFor(() => expect(result.current.data?.content).toBe('cached'))

    act(() => { void result.current.refetch() })

    await waitFor(() => expect(requestCount).toBe(2))
    expect(queryClient.getQueryState(queryKeys.fileContent('repo-1', 7, 'src/a.ts'))?.fetchStatus).toBe('fetching')
    expect(result.current.data?.content).toBe('cached')
  })

  it('invalidates only the affected graph/status/list families after expansion', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({})))
    const { queryClient, wrapper } = testQueryClient()
    queryClient.setQueryData(queryKeys.graph('repo-1', 7, 'project-map'), { nodes: [], edges: [] })
    queryClient.setQueryData(queryKeys.overview('repo-1', 7), { name: 'kept' })
    queryClient.setQueryData(queryKeys.graph('repo-2', 7, 'project-map'), { nodes: [], edges: [] })
    const { result } = renderHook(() => useServerMutations('repo-1', 7), { wrapper })

    await act(() => result.current.expandGraph.mutateAsync({ targetRepositoryId: 'repo-1', scopePath: 'src' }))

    expect(queryClient.getQueryState(queryKeys.graph('repo-1', 7, 'project-map'))?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(queryKeys.overview('repo-1', 7))?.isInvalidated).toBe(false)
    expect(queryClient.getQueryState(queryKeys.graph('repo-2', 7, 'project-map'))?.isInvalidated).toBe(false)
  })
})

function snapshot(overrides: Partial<Record<'data' | 'error' | 'isError' | 'isFetching' | 'isPending' | 'isStale', unknown>> = {}) {
  return {
    data: undefined,
    error: null,
    isError: false,
    isFetching: false,
    isPending: false,
    isStale: false,
    ...overrides,
  } as never
}

function testQueryClient() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return {
    queryClient,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  }
}

function jsonResponse(data: unknown) {
  return { ok: true, status: 200, json: async () => data } as Response
}
