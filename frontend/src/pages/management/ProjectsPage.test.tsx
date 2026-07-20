import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Repository } from '../../types/api'
import { ProjectsPage } from './ProjectsPage'

function repository(index: number): Repository {
  return {
    id: `repo-${index}`,
    name: `Project ${String(index).padStart(2, '0')}`,
    source_type: index % 2 ? 'github_url' : 'upload_folder',
    source_label: index % 2 ? `owner/project-${index}` : undefined,
    status: 'indexed',
    detected_stack: index % 2 ? ['Python'] : ['TypeScript'],
    total_files: index,
    indexed_files: index,
    symbols: index,
    endpoints: index,
    chunks: index,
    graph_nodes: index,
    last_indexed_at: `2026-07-${String((index % 28) + 1).padStart(2, '0')}T00:00:00Z`,
  }
}

const handlers = {
  onNewProject: vi.fn(),
  onOpen: vi.fn(),
  onReindex: vi.fn(),
  onDelete: vi.fn(),
  onDeleteAll: vi.fn(),
  onViewIndexJobs: vi.fn(),
}

describe('ProjectsPage', () => {
  afterEach(cleanup)

  it('limits the project list to 25 entries and moves to the next page', () => {
    render(<ProjectsPage repositories={Array.from({ length: 26 }, (_, index) => repository(index + 1))} {...handlers} />)

    expect(screen.getByText('Showing 1–25 of 26')).toBeTruthy()
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(25)
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Showing 26–26 of 26')).toBeTruthy()
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(1)
  })

  it('filters projects by the global management search query', () => {
    render(<ProjectsPage repositories={[repository(1), repository(2)]} searchQuery="project 01" {...handlers} />)

    expect(screen.getByText('Project 01')).toBeTruthy()
    expect(screen.queryByText('Project 02')).toBeNull()
  })
})
