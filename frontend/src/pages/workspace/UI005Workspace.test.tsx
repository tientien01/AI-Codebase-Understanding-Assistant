import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { IgnorePatternsResponse, IndexStatus, Repository, SettingsResponse } from '../../types/api'
import { EvaluationPage } from './EvaluationPage'
import { SettingsPage } from './SettingsPage'

afterEach(cleanup)

describe('UI-005 truthful settings and evaluation surfaces', () => {
  it('renders only the allowlisted non-secret settings and effective patterns reported by the server', () => {
    const settingsWithUnexpectedSecret = {
      ...settings,
      providers: { ...settings.providers, llm_api_key: 'must-not-render' },
    } as SettingsResponse
    render(
      <SettingsPage
        isWorkspace={false}
        settings={settingsWithUnexpectedSecret}
        ignorePatterns={ignorePatterns}
        settingsState={{ kind: 'success' }}
        ignorePatternsState={{ kind: 'success' }}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByText('Balanced')).toBeTruthy()
    expect(screen.getByText('1 MB')).toBeTruthy()
    expect(screen.getByText('Configured')).toBeTruthy()
    expect(screen.getByText('Not configured')).toBeTruthy()
    expect(screen.getByText('node_modules')).toBeTruthy()
    expect(screen.queryByText('must-not-render')).toBeNull()
    expect(screen.queryByText(/Dang phat trien/i)).toBeNull()
  })

  it('discloses limited, permission, and retryable settings states with recovery', () => {
    const onRetry = vi.fn()
    const { rerender } = render(
      <SettingsPage
        isWorkspace={false}
        settings={{ ...settings, providers: { ...settings.providers, llm_model: undefined } }}
        ignorePatterns={ignorePatterns}
        settingsState={{ kind: 'success' }}
        ignorePatternsState={{ kind: 'permission_denied', message: 'You do not have access to this data.' }}
        onRetry={onRetry}
      />,
    )
    expect(screen.getByText('Limited data')).toBeTruthy()

    rerender(
      <SettingsPage
        isWorkspace={false}
        settingsState={{ kind: 'error_retryable', message: 'Settings are temporarily unavailable.' }}
        ignorePatternsState={{ kind: 'initial' }}
        onRetry={onRetry}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('shows current repository/index facts and an explicit unavailable evaluation capability', () => {
    render(
      <EvaluationPage
        repository={repository}
        indexStatus={indexStatus}
        indexState={{ kind: 'success' }}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getAllByText('UI-005 Repository').length).toBeGreaterThan(0)
    expect(screen.getByText('Active index: 31')).toBeTruthy()
    expect(screen.getByText('42 of 48')).toBeTruthy()
    expect(screen.getByText('Capability unavailable')).toBeTruthy()
    expect(screen.getByText('POST /evaluation/runs')).toBeTruthy()
    expect(screen.getByText(/Offline deterministic CI evidence protects regressions/)).toBeTruthy()
    expect(screen.queryByText('Where is login implemented?')).toBeNull()
    expect(screen.queryByText('Answer groundedness')).toBeNull()
  })
})

const settings: SettingsResponse = {
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
}

const ignorePatterns: IgnorePatternsResponse = {
  default_patterns: ['node_modules'],
  user_patterns: [],
  effective_patterns: ['node_modules', '.env', '*.key'],
}

const repository: Repository = {
  id: 'repo-ui005',
  name: 'UI-005 Repository',
  source_type: 'upload_folder',
  status: 'indexed',
  current_index_version: 31,
  detected_stack: ['React'],
  total_files: 48,
  indexed_files: 42,
  symbols: 100,
  endpoints: 5,
  chunks: 200,
  graph_nodes: 80,
}

const indexStatus: IndexStatus = {
  repository_id: repository.id,
  index_version: 31,
  status: 'completed',
  current_step: 'completed',
  total_files: 48,
  processed_files: 42,
  skipped_files: 6,
  failed_files: 0,
  progress: 100,
  stats: {},
  logs: [],
  warnings: [],
}
