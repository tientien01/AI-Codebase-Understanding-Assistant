import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FileTree } from './FileTree'
import type { FileTreeNode } from '../../types/api'

beforeEach(() => window.sessionStorage.clear())
afterEach(cleanup)

describe('FileTree', () => {
  it('collapses folders and restores repository-scoped expansion state', () => {
    const { unmount } = render(<FileTree nodes={nodes} repositoryId="repo-1" selectedFilePath="" onSelectFile={vi.fn()} />)

    expect(screen.queryByText('routes.py')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Expand backend' }))
    fireEvent.click(screen.getByRole('button', { name: 'Expand api' }))
    expect(screen.getByText('routes.py')).toBeTruthy()
    unmount()

    render(<FileTree nodes={nodes} repositoryId="repo-1" selectedFilePath="" onSelectFile={vi.fn()} />)
    expect(screen.getByText('routes.py')).toBeTruthy()
  })

  it('reveals the selected file ancestry and keeps search expansion transient', () => {
    const { rerender } = render(<FileTree nodes={nodes} repositoryId="repo-2" selectedFilePath="backend/api/routes.py" onSelectFile={vi.fn()} />)

    expect(screen.getByText('routes.py')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Collapse backend' }))
    expect(screen.queryByText('routes.py')).toBeNull()

    rerender(<FileTree nodes={nodes} repositoryId="repo-2" selectedFilePath="backend/api/routes.py" searchActive onSelectFile={vi.fn()} />)
    expect(screen.getByText('routes.py')).toBeTruthy()
    rerender(<FileTree nodes={nodes} repositoryId="repo-2" selectedFilePath="backend/api/routes.py" onSelectFile={vi.fn()} />)
    expect(screen.queryByText('routes.py')).toBeNull()
  })

  it('persists tree scroll without changing file selection', () => {
    const onSelectFile = vi.fn()
    const { unmount } = render(<FileTree nodes={nodes} repositoryId="repo-3" selectedFilePath="backend/api/routes.py" onSelectFile={onSelectFile} />)
    const tree = screen.getByRole('tree')
    Object.defineProperty(tree, 'scrollTop', { configurable: true, writable: true, value: 280 })
    fireEvent.scroll(tree)
    fireEvent.click(screen.getByText('routes.py'))
    expect(onSelectFile).toHaveBeenCalledWith('backend/api/routes.py')
    unmount()

    render(<FileTree nodes={nodes} repositoryId="repo-3" selectedFilePath="backend/api/routes.py" onSelectFile={vi.fn()} />)
    expect(screen.getByRole('tree').scrollTop).toBe(280)
  })
})

const nodes: FileTreeNode[] = [{
  name: 'backend',
  path: 'backend',
  type: 'directory',
  children: [{
    name: 'api',
    path: 'backend/api',
    type: 'directory',
    children: [{ name: 'routes.py', path: 'backend/api/routes.py', type: 'file', children: [] }],
  }],
}]
