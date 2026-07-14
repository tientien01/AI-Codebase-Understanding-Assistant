import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query'
import { ApiError, isRequestCancelled, safeErrorMessage } from '../../api/client'

export type AsyncViewState =
  | { kind: 'initial' | 'loading' | 'success' | 'empty'; message?: string }
  | { kind: 'refreshing' | 'stale'; message: string }
  | { kind: 'permission_denied' | 'error_retryable' | 'error_terminal' | 'cancelled'; message: string }

type QuerySnapshot = Pick<
  UseQueryResult<unknown, Error>,
  'data' | 'error' | 'isError' | 'isFetching' | 'isPending' | 'isStale'
>

export function toAsyncViewState(
  query: QuerySnapshot | undefined,
  options: { enabled: boolean; empty?: (data: unknown) => boolean } = { enabled: true },
): AsyncViewState {
  if (!options.enabled || !query) return { kind: 'initial' }
  if (query.isPending && query.isFetching) return { kind: 'loading', message: 'Loading current data…' }
  if (query.isError) {
    if (isRequestCancelled(query.error)) return { kind: 'cancelled', message: 'The superseded request was cancelled.' }
    if (query.error instanceof ApiError && [401, 403].includes(query.error.status)) {
      return { kind: 'permission_denied', message: 'You do not have access to this data.' }
    }
    return {
      kind: query.error instanceof ApiError && query.error.retryable ? 'error_retryable' : 'error_terminal',
      message: safeErrorMessage(query.error),
    }
  }
  if (query.data !== undefined && query.isFetching) return { kind: 'refreshing', message: 'Refreshing cached data…' }
  if (query.data !== undefined && options.empty?.(query.data)) return { kind: 'empty' }
  if (query.data !== undefined && query.isStale) return { kind: 'stale', message: 'Showing cached data while it is eligible for refresh.' }
  if (query.data !== undefined) return { kind: 'success' }
  return { kind: 'initial' }
}

export function isBlockingAsyncState(state: AsyncViewState) {
  return ['loading', 'permission_denied', 'error_retryable', 'error_terminal', 'cancelled'].includes(state.kind)
}

export function toMutationAsyncViewState(
  mutation: Pick<UseMutationResult<unknown, Error, unknown>, 'data' | 'error' | 'isError' | 'isPending'>,
): AsyncViewState {
  if (mutation.isPending) return { kind: 'loading', message: 'Applying the requested change…' }
  if (mutation.isError) {
    if (isRequestCancelled(mutation.error)) return { kind: 'cancelled', message: 'The request was cancelled.' }
    if (mutation.error instanceof ApiError && [401, 403].includes(mutation.error.status)) {
      return { kind: 'permission_denied', message: 'You do not have permission to perform this action.' }
    }
    return {
      kind: mutation.error instanceof ApiError && mutation.error.retryable ? 'error_retryable' : 'error_terminal',
      message: safeErrorMessage(mutation.error),
    }
  }
  return mutation.data === undefined ? { kind: 'initial' } : { kind: 'success' }
}
