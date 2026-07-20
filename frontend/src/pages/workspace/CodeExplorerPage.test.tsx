import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CodeExplorerPage } from './CodeExplorerPage'
import type { FileContent, FileTreeNode, Overview } from '../../types/api'

afterEach(cleanup)

describe('CodeExplorerPage', () => {
  it('filters the tree, preserves file selection, and presents source-focused intelligence', () => {
    const onSelectFile = vi.fn()
    const onTraceValue = vi.fn()
    const onSelectLine = vi.fn()
    const { container, rerender } = render(<CodeExplorerPage repositoryId="repo-code" fileTree={fileTree} selectedFilePath="backend/app/routes.py" fileContent={fileContent} overview={overview} onSelectFile={onSelectFile} onSelectLine={onSelectLine} onTraceValue={onTraceValue} />)

    expect(container.querySelectorAll('.file-tree')).toHaveLength(1)
    expect(screen.getAllByText('routes.py').length).toBeGreaterThan(0)
    expect(screen.getAllByText('backend/app/routes.py').length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Code editor')).toBeTruthy()
    expect(screen.getByLabelText('Open files')).toBeTruthy()
    expect(screen.getByText('Open in Editor')).toBeTruthy()
    expect(screen.getByText('Ln 1, Col 1')).toBeTruthy()
    expect(screen.getByText('Symbols')).toBeTruthy()
    expect(screen.getByText('POST /login')).toBeTruthy()
    expect(screen.queryByText('Call Relationships')).toBeNull()
    expect(screen.queryByText('Navigation unavailable')).toBeNull()
    expect(screen.queryByText(/Dang phat trien/i)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Select line 1 for value trace' }))
    expect(onSelectLine).toHaveBeenCalledWith('backend/app/routes.py', 1)
    fireEvent.click(screen.getByRole('button', { name: /login/ }))
    expect(onTraceValue).toHaveBeenCalledWith({ kind: 'token', filePath: 'backend/app/routes.py', line: 1, value: 'login' })

    fireEvent.change(screen.getByRole('textbox', { name: 'Search repository files' }), { target: { value: 'readme' } })
    expect(screen.getByText('README.md')).toBeTruthy()
    expect(within(screen.getByLabelText('Repository files')).queryByText('routes.py')).toBeNull()

    fireEvent.change(screen.getByRole('textbox', { name: 'Search repository files' }), { target: { value: '' } })
    fireEvent.click(within(screen.getByLabelText('Repository files')).getByRole('button', { name: 'routes.py' }))
    expect(onSelectFile).toHaveBeenCalledWith('backend/app/routes.py')

    rerender(<CodeExplorerPage repositoryId="repo-code" fileTree={fileTree} selectedFilePath="README.md" fileContent={null} overview={overview} onSelectFile={onSelectFile} onSelectLine={onSelectLine} onTraceValue={onTraceValue} />)
    expect(within(screen.getByLabelText(/Source content for backend\/app\/routes.py/)).getByText(/def login/)).toBeTruthy()
    expect(screen.getByText('Loading selection')).toBeTruthy()
  })

  it('does not render intelligence panels when the selected file has no parsed intelligence', () => {
    render(<CodeExplorerPage repositoryId="repo-code" fileTree={fileTree} selectedFilePath="README.md" fileContent={{ ...fileContent, file_path: 'README.md', symbols: [] }} overview={{ ...overview, endpoints: [] }} onSelectFile={vi.fn()} />)

    expect(screen.queryByLabelText('File intelligence')).toBeNull()
    expect(screen.queryByText('Symbols')).toBeNull()
    expect(screen.queryByText('API endpoints')).toBeNull()
  })

  it('keeps source visible while presenting an embedded value trace', () => {
    render(<CodeExplorerPage repositoryId="repo-code" fileTree={fileTree} selectedFilePath="backend/app/routes.py" selectedLine={1} fileContent={fileContent} overview={overview} tracePanel={<div>Trace result panel</div>} onSelectFile={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Expand files panel' })).toBeTruthy()
    expect(screen.getByLabelText('Embedded value trace')).toBeTruthy()
    expect(screen.getByText('Trace result panel')).toBeTruthy()
    expect(screen.getByLabelText(/Source content for backend\/app\/routes.py/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Expand files panel' }))
    expect(screen.getByRole('button', { name: 'Collapse files panel' })).toBeTruthy()
    expect(screen.getByLabelText('Repository files')).toBeTruthy()
  })

  it('temporarily collapses Files while trace is visible and restores the prior layout', async () => {
    const baseProps = { repositoryId: 'repo-code', fileTree, selectedFilePath: 'backend/app/routes.py', fileContent, overview, onSelectFile: vi.fn() }
    const { rerender } = render(<CodeExplorerPage {...baseProps} />)

    expect(screen.getByRole('button', { name: 'Collapse files panel' })).toBeTruthy()
    rerender(<CodeExplorerPage {...baseProps} tracePanel={<div>Trace result panel</div>} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Expand files panel' })).toBeTruthy())

    rerender(<CodeExplorerPage {...baseProps} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Collapse files panel' })).toBeTruthy())
  })

  it('dismisses the identifier chooser backed by a selected route line', () => {
    const onClearSelectedLine = vi.fn()
    render(<CodeExplorerPage repositoryId="repo-code" fileTree={fileTree} selectedFilePath="backend/app/routes.py" selectedLine={1} fileContent={fileContent} overview={overview} onSelectFile={vi.fn()} onClearSelectedLine={onClearSelectedLine} />)

    expect(screen.getByLabelText('Trace value from selected source line')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Close identifier chooser' }))

    expect(onClearSelectedLine).toHaveBeenCalledOnce()
    expect(screen.queryByLabelText('Trace value from selected source line')).toBeNull()
  })
})

const fileTree: FileTreeNode[] = [
  {
    name: 'backend',
    path: 'backend',
    type: 'directory',
    children: [{
      name: 'app',
      path: 'backend/app',
      type: 'directory',
      children: [{ name: 'routes.py', path: 'backend/app/routes.py', type: 'file', children: [] }],
    }],
  },
  { name: 'README.md', path: 'README.md', type: 'file', children: [] },
]

const fileContent: FileContent = {
  file_path: 'backend/app/routes.py',
  language: 'python',
  content: 'def login():\n    return "ok"',
  lines: ['def login():', '    return "ok"'],
  symbols: [{ evidence_id: 'symbol-login', file_path: 'backend/app/routes.py', symbol_name: 'login', start_line: 1, end_line: 2 }],
}

const overview: Overview = {
  repository_id: 'repo-code',
  name: 'Code Explorer',
  detected_stack: ['FastAPI'],
  important_files: [],
  modules: [],
  endpoints: [{ method: 'POST', path: '/login', handler: 'login', file_path: 'backend/app/routes.py', start_line: 1, end_line: 2 }],
  documentation_gaps: [],
  stats: {},
}
