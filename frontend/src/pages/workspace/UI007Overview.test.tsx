import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CollapsibleAssistantPanel } from '../../components/chat/AssistantChat'
import { TopBar, WorkspaceShell } from '../../components/layout/AppShell'
import type { IndexStatus, Overview, Repository } from '../../types/api'
import { OverviewPage } from './OverviewPage'

afterEach(cleanup)

const overview: Overview = {
  repository_id: 'repo-1',
  name: 'recommend_hotel',
  detected_stack: ['FastAPI', 'Python'],
  important_files: Array.from({ length: 6 }, (_, index) => ({ file_path: `app/file-${index + 1}.py`, reason: `Reading reason ${index + 1}` })),
  modules: Array.from({ length: 6 }, (_, index) => ({ name: `Area ${index + 1}`, summary: `Indexed module signal ${index + 1}`, file_count: index + 1 })),
  endpoints: [{ method: 'POST', path: '/login', handler: 'login', file_path: 'app/routes/auth.py', start_line: 1, end_line: 5 }],
  documentation_gaps: ['No major documentation gap detected by MVP rules.'],
  stats: { files: 34, functions: 50, classes: 5, endpoints: 9, graph_nodes: 3701 },
}

const repository: Repository = {
  id: 'repo-1',
  name: 'recommend_hotel',
  source_type: 'github',
  status: 'indexed',
  current_index_version: 1,
  detected_stack: ['Python'],
  total_files: 34,
  indexed_files: 34,
  symbols: 55,
  endpoints: 9,
  chunks: 134,
  graph_nodes: 3701,
}

const indexStatus: IndexStatus = {
  repository_id: 'repo-1',
  status: 'completed',
  current_step: 'completed',
  total_files: 34,
  processed_files: 34,
  skipped_files: 0,
  failed_files: 0,
  progress: 100,
  stats: {},
  logs: [],
  warnings: [],
}

describe('UI-007 compact Overview compatibility', () => {
  it('does not turn legacy folder groups into an invented architecture', () => {
    render(<OverviewPage overview={overview} onQuestion={vi.fn()} onExploreArchitecture={vi.fn()} onOpenFile={vi.fn()} />)

    const architecture = screen.getByRole('heading', { name: 'Architecture Overview' }).closest('section')
    expect(architecture).toBeTruthy()
    expect(within(architecture!).queryByText('Area 1')).toBeNull()
    expect(within(architecture!).queryByText('Client and entrypoints')).toBeNull()
    expect(within(architecture!).getByText('Relationships remain unknown here until Graph Explorer confirms them.')).toBeTruthy()
  })

  it('keeps reading compact and explicitly withholds unsupported key areas', () => {
    render(<OverviewPage overview={overview} onQuestion={vi.fn()} onExploreArchitecture={vi.fn()} onOpenFile={vi.fn()} />)

    const keyAreas = screen.getByRole('heading', { name: 'Key Areas' }).closest<HTMLElement>('.panel')
    expect(keyAreas).toBeTruthy()
    expect(screen.queryByText('app/file-5.py')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'View all 6 files' }))
    expect(screen.getByText('app/file-5.py')).toBeTruthy()
    expect(within(keyAreas!).getByText('No key architecture area is supported by the current index.')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Documentation Gaps' })).toBeNull()
  })

  it('places suggestions inside a collapsible assistant drawer', () => {
    const onInput = vi.fn()
    render(
      <CollapsibleAssistantPanel
        input=""
        messages={[]}
        disabled={false}
        suggestions={['Explain the architecture']}
        onInput={onInput}
        onSubmit={vi.fn()}
        onEvidence={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Explain the architecture' }))
    expect(onInput).toHaveBeenCalledWith('Explain the architecture')
    fireEvent.click(screen.getByRole('button', { name: 'Collapse AI Assistant' }))
    expect(screen.queryByText('What do you want to understand?')).toBeNull()
    const open = screen.getByRole('button', { name: 'Open AI Assistant' })
    fireEvent.click(open)
    expect(screen.getByText('What do you want to understand?')).toBeTruthy()
  })

  it('keeps index state out of the search action area and removes duplicate sidebar diagnostics', () => {
    const { rerender } = render(
      <MemoryRouter>
        <TopBar mode="workspace" page="overview" repository={repository} status={indexStatus} />
      </MemoryRouter>,
    )

    expect(screen.getByPlaceholderText('Search anything...')).toBeTruthy()
    expect(screen.queryByText('Indexing 100%')).toBeNull()
    rerender(
      <MemoryRouter>
        <WorkspaceShell page="overview" repository={repository} status={indexStatus} onReindex={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Index Status' })).toBeTruthy()
    expect(screen.queryByText('Chunks')).toBeNull()
    expect(screen.queryByText('Step')).toBeNull()
  })
})
