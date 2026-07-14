import { AsyncStateNotice } from '../../components/common/AsyncState'
import { ConfigRow, PageTitle, Panel } from '../../components/common/ui'
import { isBlockingAsyncState } from '../../features/server-state'
import type { AsyncViewState } from '../../features/server-state'
import type { IgnorePatternsResponse, SettingsResponse } from '../../types/api'

type SettingsPageProps = {
  isWorkspace: boolean
  settings?: SettingsResponse
  ignorePatterns?: IgnorePatternsResponse
  settingsState: AsyncViewState
  ignorePatternsState: AsyncViewState
  onRetry: () => void
}

export function SettingsPage({
  isWorkspace,
  settings,
  ignorePatterns,
  settingsState,
  ignorePatternsState,
  onRetry,
}: SettingsPageProps) {
  const profileState = settings && !hasCompleteSafeProfile(settings)
    ? { kind: 'limited' as const, message: 'The server returned only part of the allowlisted non-secret settings profile.' }
    : settingsState

  return (
    <div className="truthful-workspace-page">
      <PageTitle
        title="Settings"
        subtitle={isWorkspace
          ? 'Effective, read-only workspace configuration reported by the server.'
          : 'Effective, non-secret application configuration reported by the server.'}
      />

      <AsyncStateNotice state={profileState} onRetry={onRetry} />
      {!isBlockingAsyncState(profileState) && settings && (
        <div className="settings-grid">
          <Panel title="Indexing profile">
            <ConfigRow label="Default profile" value={title(settings.indexing.default_profile)} />
            <ConfigRow label="Maximum file size" value={megabytes(settings.indexing.max_file_size_mb)} />
            <ConfigRow label="Maximum upload size" value={megabytes(settings.indexing.max_upload_size_mb)} />
          </Panel>

          <Panel title="Provider readiness">
            <ConfigRow label="LLM provider" value={reported(settings.providers.llm_provider)} />
            <ConfigRow label="LLM model" value={reported(settings.providers.llm_model)} />
            <ConfigRow label="LLM status" value={configured(settings.providers.llm_configured)} />
            <ConfigRow label="Embedding provider" value={reported(settings.providers.embedding_provider)} />
            <ConfigRow label="Embedding model" value={reported(settings.providers.embedding_model)} />
            <ConfigRow label="Embedding status" value={configured(settings.providers.embedding_configured)} />
            <ConfigRow label="Vector store" value={reported(settings.providers.vector_store_provider)} />
          </Panel>

          <Panel title="Security invariants">
            <ConfigRow label="Secret scanning" value={enabled(settings.security.secret_scanning_enabled)} />
            <p className="boundary-copy">Security invariants are reported for visibility and cannot be disabled from this UI.</p>
          </Panel>

          <Panel title="Effective ignore patterns">
            <AsyncStateNotice state={ignorePatternsState} onRetry={onRetry} />
            {!isBlockingAsyncState(ignorePatternsState) && ignorePatterns && (
              <ul className="pattern-list" aria-label="Effective ignore patterns">
                {ignorePatterns.effective_patterns.map((pattern) => <li key={pattern}><code>{pattern}</code></li>)}
              </ul>
            )}
          </Panel>

          <Panel title="Changes and provider tests">
            <AsyncStateNotice state={{
              kind: 'unavailable',
              message: 'Settings changes and provider tests are unavailable because PATCH /settings/preferences and POST /settings/providers/test are not implemented.',
            }} />
          </Panel>
        </div>
      )}
    </div>
  )
}

function hasCompleteSafeProfile(settings: SettingsResponse) {
  return settings.indexing.default_profile !== undefined
    && settings.indexing.max_file_size_mb !== undefined
    && settings.indexing.max_upload_size_mb !== undefined
    && settings.providers.llm_provider !== undefined
    && settings.providers.llm_model !== undefined
    && settings.providers.llm_configured !== undefined
    && settings.providers.embedding_provider !== undefined
    && settings.providers.embedding_model !== undefined
    && settings.providers.embedding_configured !== undefined
    && settings.providers.vector_store_provider !== undefined
    && settings.security.secret_scanning_enabled !== undefined
}

function reported(value: string | undefined) {
  return value?.trim() || 'Not reported'
}

function title(value: string | undefined) {
  const text = reported(value)
  return text === 'Not reported' ? text : text.replaceAll('_', ' ').replace(/^./, (character) => character.toUpperCase())
}

function megabytes(value: number | undefined) {
  return value === undefined ? 'Not reported' : `${value} MB`
}

function configured(value: boolean | undefined) {
  return value === undefined ? 'Not reported' : value ? 'Configured' : 'Not configured'
}

function enabled(value: boolean | undefined) {
  return value === undefined ? 'Not reported' : value ? 'Enabled' : 'Disabled'
}
