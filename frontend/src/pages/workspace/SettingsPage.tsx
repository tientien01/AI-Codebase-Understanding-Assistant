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
  settingsState,
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
          ? 'The settings that affect this workspace right now.'
          : 'A concise, non-secret summary of what affects your projects and AI answers.'}
      />

      <AsyncStateNotice state={profileState} onRetry={onRetry} />
      {!isBlockingAsyncState(profileState) && settings && (
        <div className="settings-grid settings-grid-simple">
          <Panel title="Project limits">
            <ConfigRow label="Indexing profile" value={title(settings.indexing.default_profile)} />
            <ConfigRow label="Largest file" value={megabytes(settings.indexing.max_file_size_mb)} />
            <ConfigRow label="Upload limit" value={megabytes(settings.indexing.max_upload_size_mb)} />
          </Panel>

          <Panel title="AI Assistant">
            <ConfigRow label="Answer model" value={`${reported(settings.providers.llm_model)} (${reported(settings.providers.llm_provider)})`} />
            <ConfigRow label="Availability" value={configured(settings.providers.llm_configured)} />
            <p className="boundary-copy">Answers stay grounded in indexed source evidence. If the model is unavailable, the assistant clearly reports its fallback state.</p>
          </Panel>

          <Panel title="Safety">
            <ConfigRow label="Secret scanning" value={enabled(settings.security.secret_scanning_enabled)} />
            <p className="boundary-copy">Sensitive configuration and ignored paths stay protected. These controls are read-only here.</p>
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
