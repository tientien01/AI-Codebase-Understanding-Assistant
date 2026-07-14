import { ApiError, isRequestCancelled } from '../../api/client'
import type { IndexStatus } from '../../types/api'

const terminalJobStatuses = new Set([
  'completed',
  'completed_with_warnings',
  'failed',
  'cancelled',
  'cancelled_previous_index_retained',
  'index_failed_previous_index_retained',
])

export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2 || isRequestCancelled(error)) return false
  if (error instanceof ApiError) return error.retryable
  return error instanceof TypeError
}

export function retryDelay(failureCount: number): number {
  const base = Math.min(1_000 * 2 ** failureCount, 10_000)
  return base + deterministicJitter(`retry:${failureCount}`, 250)
}

export function indexRefetchInterval(
  status: IndexStatus | undefined,
  options: { hidden: boolean; repositoryId: string; failureCount?: number },
): number | false {
  if (options.hidden || (status && terminalJobStatuses.has(status.status))) return false
  const failureCount = Math.max(0, options.failureCount ?? 0)
  const base = Math.min(2_500 * 2 ** failureCount, 15_000)
  return base + deterministicJitter(options.repositoryId, 500)
}

export function isTerminalJobStatus(status?: string): boolean {
  return Boolean(status && terminalJobStatuses.has(status))
}

function deterministicJitter(value: string, maximum: number) {
  let hash = 0
  for (const character of value) hash = (hash * 31 + character.charCodeAt(0)) >>> 0
  return hash % (maximum + 1)
}
