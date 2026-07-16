import type { AsyncViewState } from '../../features/server-state'

export function AsyncStateNotice({ state, onRetry }: { state: AsyncViewState; onRetry?: () => void }) {
  if (['initial', 'success', 'empty'].includes(state.kind)) return null
  const blocking = ['loading', 'unavailable', 'permission_denied', 'error_retryable', 'error_terminal', 'cancelled'].includes(state.kind)

  return (
    <div className={`async-state async-state-${state.kind} ${blocking ? 'blocking' : ''}`} role={state.kind.includes('error') ? 'alert' : 'status'}>
      <div>
        <strong>{titleFor(state.kind)}</strong>
        {state.message && <p>{state.message}</p>}
      </div>
      {state.kind === 'error_retryable' && onRetry && <button className="secondary" onClick={onRetry}>Try Again</button>}
    </div>
  )
}

function titleFor(kind: AsyncViewState['kind']) {
  const titles: Record<AsyncViewState['kind'], string> = {
    initial: 'Ready',
    loading: 'Loading',
    refreshing: 'Refreshing',
    limited: 'Limited data',
    success: 'Current',
    empty: 'No data',
    stale: 'Older index data',
    unavailable: 'Capability unavailable',
    permission_denied: 'Access denied',
    error_retryable: 'Temporary request failure',
    error_terminal: 'Request failed',
    cancelled: 'Request cancelled',
  }
  return titles[kind]
}
