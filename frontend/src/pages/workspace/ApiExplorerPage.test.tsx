import { useState } from 'react'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ApiEndpoint } from '../../types/api'
import { ApiExplorerPage } from './ApiExplorerPage'
import { ApiDetails } from './SidePanels'
import { endpointKeyFor } from '../../utils/apiEndpoint'

afterEach(cleanup)

describe('ApiExplorerPage', () => {
  it('lets the endpoint panel fill the primary workspace column', () => {
    const { container } = render(<ApiExplorerPage endpoints={endpoints} onSelectEndpoint={vi.fn()} />)

    expect(container.querySelector('.api-explorer-page > .panel')).not.toBeNull()
    expect(container.querySelector('.api-layout')).toBeNull()
  })

  it('filters by every detected method and by path, handler, or source file', () => {
    render(<ApiExplorerPage endpoints={endpoints} onSelectEndpoint={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'PUT' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'GET' }))
    expect(screen.getByRole('button', { name: 'Select GET /users' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Select POST /login' })).toBeNull()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search endpoints' }), { target: { value: 'admin.py' } })
    expect(screen.getByText('No endpoint matches the current filters.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search endpoints' }), { target: { value: 'admin.py' } })
    expect(screen.getByRole('button', { name: 'Select PUT /users/{user_id}' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Select POST /login' })).toBeNull()
  })

  it('binds selected-row and detail state and exposes source and request-flow actions', () => {
    const onOpenSource = vi.fn()
    const onTraceFlow = vi.fn()

    function Harness() {
      const [selectedKey, setSelectedKey] = useState<string>()
      const selectedEndpoint = endpoints.find((endpoint) => endpointKeyFor(endpoint) === selectedKey)
      return (
        <>
          <ApiExplorerPage endpoints={endpoints} selectedEndpointKey={selectedKey} onSelectEndpoint={setSelectedKey} />
          <ApiDetails endpoint={selectedEndpoint} onOpenSource={onOpenSource} onTraceFlow={onTraceFlow} />
        </>
      )
    }

    render(<Harness />)
    expect(screen.getByText('Select an endpoint to inspect its handler and source evidence.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Select POST /login' }))
    const selectedRow = screen.getByRole('button', { name: 'Select POST /login' }).closest('tr')
    expect(selectedRow?.getAttribute('aria-selected')).toBe('true')
    expect(within(screen.getByText('API Detail').closest('section')!).getByText('login')).toBeTruthy()
    expect(screen.getByText('fastapi')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Open source' }))
    fireEvent.click(screen.getByRole('button', { name: 'Trace request flow' }))
    expect(onOpenSource).toHaveBeenCalledWith(endpoints[0])
    expect(onTraceFlow).toHaveBeenCalledWith(endpoints[0])
  })

  it('explains a stale endpoint deep link instead of silently selecting another row', () => {
    render(<ApiDetails requestedEndpointKey="endpoint_removed" onOpenSource={vi.fn()} onTraceFlow={vi.fn()} />)
    expect(screen.getByText('This endpoint is not available in the active index. Select another endpoint.')).toBeTruthy()
  })
})

const endpoints: ApiEndpoint[] = [
  {
    endpoint_key: 'endpoint_login',
    method: 'POST',
    path: '/login',
    handler: 'login',
    file_path: 'backend/routes/auth.py',
    start_line: 10,
    end_line: 24,
    metadata: { framework: 'fastapi' },
  },
  {
    endpoint_key: 'endpoint_users',
    method: 'GET',
    path: '/users',
    handler: 'list_users',
    file_path: 'backend/routes/users.py',
    start_line: 30,
    end_line: 45,
    metadata: { framework: 'fastapi' },
  },
  {
    endpoint_key: 'endpoint_update_user',
    method: 'PUT',
    path: '/users/{user_id}',
    handler: 'update_user',
    file_path: 'backend/routes/admin.py',
    start_line: 50,
    end_line: 75,
    metadata: { framework: 'fastapi' },
  },
]
