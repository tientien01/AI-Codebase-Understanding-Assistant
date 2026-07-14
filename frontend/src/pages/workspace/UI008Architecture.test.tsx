import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CollapsibleAssistantPanel } from '../../components/chat/AssistantChat'
import type { ArchitectureComponent, Overview } from '../../types/api'
import { OverviewPage } from './OverviewPage'

afterEach(cleanup)

const component = (
  id: string,
  label: string,
  kind: ArchitectureComponent['kind'],
  technology?: string,
): ArchitectureComponent => ({
  id,
  label,
  kind,
  layer: kind,
  summary: `${label} responsibility`,
  technology,
  file_paths: [`src/${id}.py`],
  endpoint_count: kind === 'api' ? 2 : 0,
  evidence: [{ type: 'indexed-file', detail: label, file_path: `src/${id}.py` }],
})

const overview: Overview = {
  repository_id: 'repo-1',
  name: 'Restaurant recommender',
  detected_stack: ['React', 'FastAPI', 'PostgreSQL'],
  important_files: [
    { file_path: 'README.md', reason: 'Project documentation' },
    { file_path: 'backend/main.py', reason: 'Application entrypoint' },
  ],
  modules: [],
  endpoints: [{ method: 'POST', path: '/auth/login', handler: 'login', file_path: 'backend/auth.py', start_line: 10, end_line: 30 }],
  documentation_gaps: [],
  stats: { files: 42, endpoints: 6 },
  architecture: {
    style: 'layered_web',
    style_reason: 'Presentation, API, application, and persistence roles were detected.',
    detector_version: 'rule-v2',
    system_type: 'Full-stack web application',
    summary: 'React client backed by FastAPI services and PostgreSQL persistence.',
    technologies: ['React', 'FastAPI', 'PostgreSQL'],
    coverage_state: 'ready',
    unknowns: ['Runtime deployment topology is not available from the current index.'],
    components: [
      component('actor:user', 'User', 'actor'),
      component('presentation:web', 'React Web App', 'presentation', 'React'),
      component('container:backend', 'FastAPI Backend', 'container', 'FastAPI'),
      component('api:auth', 'Authentication API', 'api'),
      component('application:auth', 'Authentication Service', 'application'),
      component('data:user', 'User Repository', 'data_access'),
      component('infra:postgres', 'PostgreSQL', 'infrastructure', 'PostgreSQL'),
    ],
    relations: [
      { source: 'actor:user', target: 'presentation:web', label: 'uses', support: 'inferred', evidence: [] },
      { source: 'presentation:web', target: 'container:backend', label: 'HTTPS / JSON', support: 'confirmed', evidence: [{ type: 'graph-edge', detail: 'client request' }] },
      { source: 'api:auth', target: 'application:auth', label: 'calls', support: 'confirmed', evidence: [{ type: 'graph-edge', detail: 'resolved call' }] },
      { source: 'application:auth', target: 'data:user', label: 'reads / writes', support: 'inferred', evidence: [{ type: 'structure', detail: 'layer boundary' }] },
      { source: 'data:user', target: 'infra:postgres', label: 'persists to', support: 'confirmed', evidence: [{ type: 'dependency', detail: 'postgresql' }] },
    ],
    primary_flows: [{
      id: 'flow:login',
      label: 'Login flow',
      summary: 'Authentication request path',
      steps: [
        { component_id: 'presentation:web', label: 'React Web App', support: 'confirmed' },
        { component_id: 'api:auth', label: 'Authentication API', support: 'confirmed' },
        { component_id: 'application:auth', label: 'Authentication Service', support: 'confirmed' },
      ],
      evidence: [{ type: 'endpoint', detail: 'POST /auth/login', file_path: 'backend/auth.py' }],
    }],
  },
}

describe('UI-008 sixty-second architecture', () => {
  it('shows repository identity, architecture boundaries, supported connections, and a primary flow', () => {
    const onExploreFlow = vi.fn()
    render(<OverviewPage overview={overview} onQuestion={vi.fn()} onExploreArchitecture={vi.fn()} onExploreFlow={onExploreFlow} onOpenFile={vi.fn()} />)

    expect(screen.getByText('Full-stack web application')).toBeTruthy()
    expect(screen.getByText('Layered Web')).toBeTruthy()
    const map = screen.getByLabelText('High-level repository architecture')
    expect(within(map).getByText('React Web App')).toBeTruthy()
    expect(within(map).getByText('FastAPI Backend')).toBeTruthy()
    expect(within(map).getByText('Authentication API')).toBeTruthy()
    expect(within(map).getByText('Authentication Service')).toBeTruthy()
    expect(within(map).getByText('User Repository')).toBeTruthy()
    expect(within(map).getAllByText('PostgreSQL')).toHaveLength(2)
    expect(within(map).getByText('HTTPS / JSON')).toBeTruthy()
    expect(screen.getByText('Confirmed relation')).toBeTruthy()
    expect(screen.getByText('Inferred relation')).toBeTruthy()
    expect(screen.queryByText('Key connections')).toBeNull()
    expect(screen.getByText('Login flow')).toBeTruthy()
    expect(screen.getByText('React Web App → Authentication API → Authentication Service')).toBeTruthy()
    const flowToggle = screen.getByRole('button', { name: 'Show Login flow' })
    expect(flowToggle.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(flowToggle)
    const steps = screen.getByRole('list', { name: 'Login flow steps' })
    expect(within(steps).getByText('React Web App')).toBeTruthy()
    expect(within(steps).getByText('Authentication API')).toBeTruthy()
    expect(within(steps).getByText('Authentication Service')).toBeTruthy()
    expect(within(steps).getAllByText('Confirmed by indexed evidence')).toHaveLength(3)
    fireEvent.click(screen.getByRole('button', { name: /Open in Graph/ }))
    expect(onExploreFlow).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Collapse Login flow' }))
    expect(screen.queryByRole('list', { name: 'Login flow steps' })).toBeNull()
  })

  it('provides a fresh-chat view, evidence disclosure, multiline composer, and collapsed rail', () => {
    const onSubmit = vi.fn()
    const citation = { evidence_id: 'e-1', file_path: 'backend/auth.py', start_line: 10, end_line: 30 }
    render(
      <CollapsibleAssistantPanel
        input="Explain login"
        messages={[
          { role: 'user', content: 'How does login work?' },
          { role: 'assistant', content: 'The request enters the authentication API.', citations: [citation], evidenceSufficient: true },
        ]}
        disabled={false}
        suggestions={['Explain the architecture']}
        onInput={vi.fn()}
        onSubmit={onSubmit}
        onEvidence={vi.fn()}
      />,
    )

    expect(screen.getByRole('textbox', { name: 'Message AI Assistant' }).tagName).toBe('TEXTAREA')
    expect(screen.getByText('Evidence')).toBeTruthy()
    fireEvent.keyDown(screen.getByRole('textbox', { name: 'Message AI Assistant' }), { key: 'Enter' })
    expect(onSubmit).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('button', { name: 'Start new chat' }))
    expect(screen.getByText('What do you want to understand?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Show chat history' }))
    expect(screen.getByText('The request enters the authentication API.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Collapse AI Assistant' }))
    expect(screen.queryByRole('textbox', { name: 'Message AI Assistant' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Open AI Assistant' })).toBeTruthy()
  })
})
