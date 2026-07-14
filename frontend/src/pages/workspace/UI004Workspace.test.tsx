import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ImpactResult, Overview } from '../../types/api'
import { ImpactPage } from './ImpactPage'
import { OverviewPage } from './OverviewPage'

afterEach(cleanup)

const overview: Overview = {
  repository_id: 'repo-1',
  name: 'Example repository',
  detected_stack: ['React', 'FastAPI'],
  important_files: [{ file_path: 'backend/app/main.py', reason: 'Registers the application boundary.' }],
  modules: [{ name: 'Authentication', summary: 'Owns login and session behavior.', file_count: 4 }],
  endpoints: [{ method: 'POST', path: '/login', handler: 'login', file_path: 'backend/app/routes.py', start_line: 12, end_line: 30 }],
  documentation_gaps: ['Authentication decisions'],
  stats: { files: 12, functions: 20, classes: 5, endpoints: 1, graph_nodes: 32, chunks: 50 },
}

describe('UI-004 workspace journeys', () => {
  it('opens architecture exploration and a justified source-backed tour', () => {
    const onExploreArchitecture = vi.fn()
    const onOpenFile = vi.fn()
    render(<OverviewPage overview={overview} onQuestion={vi.fn()} onExploreArchitecture={onExploreArchitecture} onOpenFile={onOpenFile} />)

    fireEvent.click(screen.getByRole('button', { name: 'Explore Architecture' }))
    expect(onExploreArchitecture).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('button', { name: 'Start Guided Tour' }))
    expect(screen.getByText('Step 1 of 1')).toBeTruthy()
    expect(screen.getAllByText('Registers the application boundary.')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Open Source' }))
    expect(onOpenFile).toHaveBeenCalledWith('backend/app/main.py')
  })

  it('separates direct, inferred, and unknown impact and discloses unavailable history', () => {
    render(
      <ImpactPage
        overview={overview}
        targetType="symbol"
        targetRef="login"
        result={impactResult()}
        onTargetType={vi.fn()}
        onTargetRef={vi.fn()}
        onRun={vi.fn()}
      />,
    )

    expect(screen.getByText('Unavailable: the compatibility API does not expose version snapshots.')).toBeTruthy()
    const groups = screen.getByText('Current graph relations with non-inferred support.').closest('.panel')?.parentElement
    expect(groups).toBeTruthy()
    expect(within(groups!).getByRole('heading', { name: 'Direct' })).toBeTruthy()
    expect(within(groups!).getByRole('heading', { name: 'Inferred' })).toBeTruthy()
    expect(within(groups!).getByRole('heading', { name: 'Unknown' })).toBeTruthy()
    expect(screen.getByText('Dynamic dispatch cannot be resolved.')).toBeTruthy()
  })
})

function impactResult(): ImpactResult {
  const direct = { node_id: 'route-login', node_type: 'endpoint', label: 'POST /login', file_path: 'backend/app/routes.py', depth: 1, confidence: 1, via_edge: 'calls', reason: 'Resolved call edge.' }
  const inferred = { node_id: 'audit', node_type: 'service', label: 'Audit service', depth: 2, confidence: 0.6, via_edge: 'may_call', reason: 'Heuristic relation.' }
  return {
    repository_id: 'repo-1',
    target: { node_id: 'login', node_type: 'function', label: 'login', file_path: 'backend/app/routes.py', line_range: '12-30' },
    risk_level: 'medium',
    risk_score: 0.5,
    direct: [direct],
    indirect: [inferred],
    affected_files: [direct],
    affected_endpoints: [direct],
    affected_tests: [],
    affected_symbols: [inferred],
    suggested_checks: ['Run authentication tests.'],
    missing_relations: ['Dynamic dispatch cannot be resolved.'],
  }
}
