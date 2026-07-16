import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ManagementShell, WorkspaceShell } from './AppShell'

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  window.sessionStorage.clear()
})

describe('WorkspaceShell collapsible navigation', () => {
  it('collapses to an icon rail and restores without changing navigation targets', () => {
    const { container } = render(
      <MemoryRouter>
        <WorkspaceShell page="graph" repository={repository} status={null} onReindex={() => undefined} />
      </MemoryRouter>,
    )

    const graphLink = screen.getByRole('link', { name: /Graph View/ })
    expect(graphLink.getAttribute('href')).toContain('/graph')
    fireEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }))

    expect(container.querySelector('.workspace-sidebar')?.classList.contains('collapsed')).toBe(true)
    expect(screen.getByRole('button', { name: 'Expand sidebar' }).getAttribute('aria-expanded')).toBe('false')
    expect(graphLink.getAttribute('title')).toBe('Graph View')
    expect(window.localStorage.getItem('aica:sidebar')).toBe('collapsed')

    fireEvent.click(screen.getByRole('button', { name: 'Expand sidebar' }))
    expect(container.querySelector('.workspace-sidebar')?.classList.contains('collapsed')).toBe(false)
  })

  it('shares the collapsed preference across management and workspace shells', () => {
    const management = render(
      <MemoryRouter>
        <ManagementShell page="projects" repository={repository} status={null} />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }))
    expect(management.container.querySelector('.management-sidebar')?.classList.contains('collapsed')).toBe(true)
    management.unmount()

    const workspace = render(
      <MemoryRouter>
        <WorkspaceShell page="overview" repository={repository} status={null} onReindex={() => undefined} />
      </MemoryRouter>,
    )
    expect(workspace.container.querySelector('.workspace-sidebar')?.classList.contains('collapsed')).toBe(true)
    expect(screen.getByRole('button', { name: 'Expand sidebar' })).toBeTruthy()
  })

  it('keeps Settings global and removes it from repository workspace navigation', () => {
    const management = render(
      <MemoryRouter>
        <ManagementShell page="settings" repository={repository} status={null} />
      </MemoryRouter>,
    )
    expect(screen.getAllByRole('link', { name: 'Settings' })).toHaveLength(1)
    management.unmount()

    render(
      <MemoryRouter>
        <WorkspaceShell page="overview" repository={repository} status={null} onReindex={() => undefined} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('link', { name: 'Settings' })).toBeNull()
  })

  it('returns from Graph View to the last Code Explorer file, line, and trace context', () => {
    const codeLocation = '/repositories/repo-1/code?path=backend%2Fapp.py&line=42&trace=value-context%3Av1%3Aexample'
    window.sessionStorage.setItem('aica:last-code-location:repo-1', codeLocation)

    render(
      <MemoryRouter initialEntries={['/repositories/repo-1/graph?view=data-flow']}>
        <WorkspaceShell page="graph" repository={repository} status={null} onReindex={() => undefined} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /Code Explorer/ }).getAttribute('href')).toBe(codeLocation)
  })
})

const repository = {
  id: 'repo-1',
  name: 'Demo',
  source_type: 'upload_folder' as const,
  status: 'indexed' as const,
  indexed_files: 12,
  total_files: 12,
  current_index_version: 3,
  detected_stack: ['TypeScript'],
  symbols: 10,
  endpoints: 2,
  chunks: 4,
  graph_nodes: 20,
}
